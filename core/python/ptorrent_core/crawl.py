"""Crawler — consumes a `crawl` spec, drives resolve + net, emits CrawlResult
records and per-URL Item statuses.

Robots is a hard gate: `respect_robots:false` is honoured only for a locally
authored job (engine passes `trusted=True`); an inbox-origin job that sets it
gets a ROBOTS_OVERRIDE event and the flag is ignored.

Nothing is dropped: every seed becomes an Item with a terminal status.
"""
from __future__ import annotations

import re
import time
import urllib.parse
from dataclasses import dataclass, field

from . import resolve as _resolve
from .net import HostQueue, HttpClient, NetError, NetworkGate, RobotsCache


class ItemState:
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    OK = "OK"
    OK_UNCHANGED = "OK_UNCHANGED"
    SKIPPED = "SKIPPED"
    MALFORMED = "MALFORMED"
    ROBOTS_DENIED = "ROBOTS_DENIED"
    DEFERRED = "DEFERRED"
    ERROR = "ERROR"


@dataclass
class CrawlItem:
    idx: int
    tag: str
    url: str
    status: str = ItemState.PENDING
    resolved_via: str = "none"
    robots_state: str = ""
    detail: str = ""


@dataclass
class CrawlResult:
    item: CrawlItem
    text: str | None = None
    rows: list | None = None
    content_sha: str = ""
    unchanged: bool = False


def _robots_ua(politeness: dict) -> str:
    explicit = politeness.get("robots_ua")
    if explicit:
        return explicit
    ua = politeness.get("ua", "")
    m = re.search(r"compatible;\s*([A-Za-z0-9._-]+)", ua)
    return m.group(1) if m else "*"


class Crawler:
    def __init__(self, pf, *, db, event, cancel, pause, trusted: bool):
        self.pf = pf
        self.spec = pf.crawl
        self.db = db
        self.event = event            # event(kind, payload)
        self.cancel = cancel          # threading.Event
        self.pause = pause            # threading.Event  (set == paused)
        self.trusted = trusted

        pol = self.spec["politeness"]
        http_cfg = self.spec["http"]
        self.robots_ua = _robots_ua(pol)
        self.respect_robots = bool(pol.get("respect_robots", True))
        if not self.respect_robots and not trusted:
            self.event("ROBOTS_OVERRIDE",
                       {"note": "respect_robots:false ignored for inbox-origin job"})
            self.respect_robots = True
        self.on_unreachable = pol.get("on_robots_unreachable", "allow")

        self.gate = NetworkGate(on_state=lambda up: self.event(
            "NETWORK", {"up": up}))
        self.robots = RobotsCache(ua=pol["ua"])
        self.sched = HostQueue(
            default_delay_s=pol["default_delay_s"], max_delay_s=pol["max_delay_s"],
            per_host=pol["max_concurrent_per_host"],
            global_concurrency=pol["global_concurrency"], jitter=pol["jitter"])
        self.http = HttpClient(
            ua=pol["ua"], accept_language=pol["accept_language"],
            timeout=http_cfg["timeout_s"], max_bytes=http_cfg["max_bytes_per_page"],
            from_header=None, etag_store=db)
        self._backoff = pol["backoff"]

    # ── frontier ──
    def _seeds(self) -> list[CrawlItem]:
        out = []
        for i, s in enumerate(self.pf.crawl_seeds()):
            out.append(CrawlItem(i, s.get("tag", ""), s["url"]))
        return out

    def _persist(self, job_id: str, it: CrawlItem) -> None:
        self.db.execute(
            "INSERT INTO items(job_id,idx,tag,url,line,status,resolved_via,robots_state,detail) "
            "VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(job_id,idx) DO UPDATE SET "
            "status=excluded.status,resolved_via=excluded.resolved_via,"
            "robots_state=excluded.robots_state,detail=excluded.detail",
            (job_id, it.idx, it.tag, it.url, None, it.status, it.resolved_via,
             it.robots_state, it.detail))

    def run(self, job_id: str):
        """Generator of CrawlResult. Updates items + emits events as it goes."""
        items = self._seeds()
        total = len(items)
        for it in items:
            self._persist(job_id, it)
        max_pages = int(self.spec["scope"].get("max_pages", 500))

        for n, it in enumerate(items):
            if self.cancel.is_set():
                return
            while self.pause.is_set() and not self.cancel.is_set():
                time.sleep(0.2)
            if n >= max_pages:
                it.status = ItemState.SKIPPED
                it.detail = "max_pages reached"
                self._persist(job_id, it)
                continue

            it.status = ItemState.ACTIVE
            self._persist(job_id, it)
            self.event("ITEM_ACTIVE", {"idx": it.idx, "url": it.url, "tag": it.tag})

            self.gate.wait(self.cancel)
            # feed robots crawl-delay into the scheduler for this host
            inf = self.robots.info(it.url)
            self.sched.set_host_delay(it.url, inf.crawl_delay)

            if self.respect_robots:
                allowed, rstate = self.robots.can_fetch(
                    self.robots_ua, it.url, self.on_unreachable)
                it.robots_state = rstate
                if not allowed:
                    it.status = ItemState.ROBOTS_DENIED
                    self._persist(job_id, it)
                    self.event("ITEM_ROBOTS_DENIED", {"idx": it.idx, "url": it.url})
                    continue

            attempt = 0
            while True:
                if self.cancel.is_set():
                    return
                try:
                    with self.sched.slot(it.url):
                        res = _resolve.resolve(
                            it.url, order=self.spec["resolution"], http=self.http,
                            robots=self.robots, robots_ua=self.robots_ua,
                            on_unreachable=self.on_unreachable, extract=self.spec["extract"],
                            source=self.pf.source, api=self.pf.phonebook.get("api"))
                    break
                except NetError as e:
                    attempt += 1
                    if attempt > self._backoff.get("give_up_after", 5):
                        it.status = ItemState.ERROR
                        it.detail = f"net: {e}"
                        self._persist(job_id, it)
                        self.event("ITEM_ERROR", {"idx": it.idx, "detail": it.detail})
                        res = None
                        break
                    wait = min(self._backoff["base_s"] ** attempt, self._backoff["max_s"])
                    self.sched.penalise(it.url, wait)
                    it.status = ItemState.DEFERRED
                    it.detail = f"retry in {wait}s (attempt {attempt})"
                    self._persist(job_id, it)
                    self.event("ITEM_DEFERRED", {"idx": it.idx, "wait_s": wait})
                    time.sleep(min(wait, 5))
            if res is None:
                continue

            # 429 / 503 handling
            if res.status in self._backoff.get("on", [429, 503]):
                ra = 0.0
                wait = min(self._backoff["base_s"], self._backoff["max_s"])
                self.sched.penalise(it.url, ra or wait)
                it.status = ItemState.DEFERRED
                it.detail = f"http {res.status}"
                self._persist(job_id, it)
                self.event("ITEM_DEFERRED", {"idx": it.idx, "http": res.status})
                continue

            it.resolved_via = res.via
            if res.via == "none" and res.status == -1:
                it.status = ItemState.ROBOTS_DENIED
                self._persist(job_id, it)
                self.event("ITEM_ROBOTS_DENIED", {"idx": it.idx, "url": it.url})
                continue
            if res.status == 304:
                it.status = ItemState.OK_UNCHANGED
                self._persist(job_id, it)
                self.event("ITEM_OK", {"idx": it.idx, "unchanged": True,
                                       "resolved_via": it.resolved_via})
                yield CrawlResult(it, content_sha=res.sha256, unchanged=True)
                continue
            if res.status not in (0, 200) or (res.text is None and res.rows is None):
                it.status = ItemState.SKIPPED
                it.detail = f"http {res.status}" if res.status else "no content"
                self._persist(job_id, it)
                self.event("ITEM_SKIPPED", {"idx": it.idx, "detail": it.detail})
                continue

            min_chars = int((self.spec["extract"].get("html") or {}).get("min_chars", 40))
            if res.text is not None and len(res.text) < min_chars:
                it.status = ItemState.SKIPPED
                it.detail = f"under min_chars ({len(res.text)})"
                self._persist(job_id, it)
                self.event("ITEM_SKIPPED", {"idx": it.idx, "detail": it.detail})
                continue

            it.status = ItemState.OK
            self._persist(job_id, it)
            self.event("ITEM_OK", {"idx": it.idx, "resolved_via": it.resolved_via,
                                   "bytes": len(res.text or "") or None,
                                   "rows": len(res.rows or []) or None})
            yield CrawlResult(it, text=res.text, rows=res.rows, content_sha=res.sha256)

    def summary_counts(self, job_id: str) -> dict:
        rows = self.db.query(
            "SELECT status, COUNT(*) c FROM items WHERE job_id=? GROUP BY status", (job_id,))
        return {r["status"]: r["c"] for r in rows}
