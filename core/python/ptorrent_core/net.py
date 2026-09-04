"""The I/O layer libptorrent deliberately parks: robots.txt gate, a per-host
queue with one delay clock, an HTTP client with gzip + conditional GET + Range
resume, and the whole-internet network gate.

Nothing here is bypassable from a downloaded .ptorrent: `respect_robots:false`
is refused for inbox-origin jobs by crawl.py; this module always consults
`RobotsCache.can_fetch` before a request.
"""
from __future__ import annotations

import gzip
import random
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import zlib
from dataclasses import dataclass, field

from ._util import now_iso, sha256_bytes

_PROBE_HOSTS = [("8.8.8.8", 53), ("1.1.1.1", 53)]


def internet_up(timeout: float = 3.0) -> bool:
    for host, port in _PROBE_HOSTS:
        try:
            s = socket.create_connection((host, port), timeout=timeout)
            s.close()
            return True
        except OSError:
            continue
    return False


class NetworkGate:
    """Blocks the caller while the whole internet is unreachable. Never aborts."""

    def __init__(self, on_state=None, check_interval: float = 10.0):
        self._on_state = on_state or (lambda up: None)
        self._interval = check_interval
        self._down_since: float | None = None

    def wait(self, cancel=None) -> None:
        first = True
        while not (cancel and cancel.is_set()):
            if internet_up():
                if self._down_since is not None:
                    self._on_state(True)
                    self._down_since = None
                return
            if first:
                self._down_since = time.time()
                self._on_state(False)
                first = False
            time.sleep(self._interval)


# ── robots.txt ─────────────────────────────────────────────────────────────

@dataclass
class RobotsInfo:
    parser: urllib.robotparser.RobotFileParser | None
    fetched_at: float
    reachable: bool
    crawl_delay: float | None = None
    sitemaps: list = field(default_factory=list)


class RobotsCache:
    TTL = 24 * 3600

    def __init__(self, ua: str, timeout: float = 8.0):
        self.ua = ua
        self.timeout = timeout
        self._cache: dict[str, RobotsInfo] = {}
        self._lock = threading.Lock()

    def _host_key(self, url: str) -> str:
        p = urllib.parse.urlparse(url)
        return f"{p.scheme}://{p.netloc}"

    def _fetch(self, host_key: str) -> RobotsInfo:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(host_key + "/robots.txt")
        reachable = True
        try:
            req = urllib.request.Request(host_key + "/robots.txt",
                                         headers={"User-Agent": self.ua})
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                body = r.read(512_000).decode("utf-8", "replace")
            rp.parse(body.splitlines())
            sitemaps = [ln.split(":", 1)[1].strip()
                        for ln in body.splitlines()
                        if ln.lower().startswith("sitemap:")]
        except Exception:
            reachable = False
            sitemaps = []
            rp = None
        delay = None
        if rp is not None:
            try:
                d = rp.crawl_delay(self.ua)
                delay = float(d) if d is not None else None
            except Exception:
                delay = None
        return RobotsInfo(rp, time.time(), reachable, delay, sitemaps)

    def info(self, url: str) -> RobotsInfo:
        hk = self._host_key(url)
        with self._lock:
            got = self._cache.get(hk)
            if got and (time.time() - got.fetched_at) < self.TTL:
                return got
            got = self._fetch(hk)
            self._cache[hk] = got
            return got

    def can_fetch(self, robots_ua: str, url: str, on_unreachable: str = "allow") -> tuple[bool, str]:
        """Returns (allowed, robots_state). robots_ua is the bare product token."""
        inf = self.info(url)
        if not inf.reachable or inf.parser is None:
            allowed = on_unreachable == "allow"
            return allowed, ("unreachable_allowed" if allowed else "unreachable_denied")
        try:
            ok = inf.parser.can_fetch(robots_ua, url)
        except Exception:
            ok = on_unreachable == "allow"
            return ok, ("unreachable_allowed" if ok else "unreachable_denied")
        return ok, ("allowed" if ok else "denied")


# ── per-host scheduler ─────────────────────────────────────────────────────

class HostQueue:
    """One delay clock per host + a per-host concurrency semaphore + a global cap.

    Usage:
        with sched.slot(url):
            ... do the request ...
        sched.penalise(url, seconds)   # after a 429/503/Retry-After
    """

    def __init__(self, default_delay_s: float = 1.0, max_delay_s: float = 30.0,
                 per_host: int = 1, global_concurrency: int = 8, jitter: bool = True):
        self.default_delay = default_delay_s
        self.max_delay = max_delay_s
        self.per_host = max(1, per_host)
        self.jitter = jitter
        self._global = threading.BoundedSemaphore(max(1, global_concurrency))
        self._host_sem: dict[str, threading.BoundedSemaphore] = {}
        self._next_ok: dict[str, float] = {}
        self._host_delay: dict[str, float] = {}
        self._lock = threading.Lock()

    def _host(self, url: str) -> str:
        return urllib.parse.urlparse(url).netloc.lower()

    def set_host_delay(self, url: str, crawl_delay: float | None) -> None:
        h = self._host(url)
        d = self.default_delay if not crawl_delay else min(float(crawl_delay), self.max_delay)
        with self._lock:
            self._host_delay[h] = d

    def penalise(self, url: str, seconds: float) -> None:
        h = self._host(url)
        with self._lock:
            self._next_ok[h] = max(self._next_ok.get(h, 0.0), time.time() + seconds)

    class _Slot:
        def __init__(self, q, url):
            self.q, self.url = q, url

        def __enter__(self):
            self.q._acquire(self.url)
            return self

        def __exit__(self, *exc):
            self.q._release(self.url)

    def slot(self, url: str) -> "_Slot":
        return HostQueue._Slot(self, url)

    def _acquire(self, url: str, cancel=None):
        h = self._host(url)
        with self._lock:
            sem = self._host_sem.setdefault(h, threading.BoundedSemaphore(self.per_host))
            delay = self._host_delay.get(h, self.default_delay)
        self._global.acquire()
        sem.acquire()
        while True:
            with self._lock:
                wait = self._next_ok.get(h, 0.0) - time.time()
            if wait <= 0:
                break
            if cancel and cancel.is_set():
                break
            time.sleep(min(wait, 1.0))
        with self._lock:
            j = random.uniform(0, delay * 0.25) if self.jitter else 0.0
            self._next_ok[h] = time.time() + delay + j

    def _release(self, url: str):
        h = self._host(url)
        with self._lock:
            sem = self._host_sem.get(h)
        if sem is not None:
            try:
                sem.release()
            except ValueError:
                pass
        try:
            self._global.release()
        except ValueError:
            pass


# ── HTTP client ────────────────────────────────────────────────────────────

@dataclass
class HttpResponse:
    url: str
    status: int
    headers: dict
    body: bytes
    from_cache: bool = False       # True on a 304 unchanged
    sha256: str = ""


class HttpClient:
    def __init__(self, ua: str, accept_language: str = "en",
                 timeout: float = 15.0, max_bytes: int = 2_000_000,
                 from_header: str | None = None, etag_store=None):
        self.ua = ua
        self.accept_language = accept_language
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.from_header = from_header
        self.etag = etag_store   # db.DB or None

    def _headers(self, url: str, accept: list[str], extra: dict | None) -> dict:
        h = {
            "User-Agent": self.ua,
            "Accept": ",".join(accept) if accept else "*/*",
            "Accept-Language": self.accept_language,
            "Accept-Encoding": "gzip, deflate",
        }
        if self.from_header:
            h["From"] = self.from_header
        if self.etag is not None:
            row = self.etag.query_one(
                "SELECT etag,last_modified FROM etag_cache WHERE url=?", (url,))
            if row:
                if row["etag"]:
                    h["If-None-Match"] = row["etag"]
                if row["last_modified"]:
                    h["If-Modified-Since"] = row["last_modified"]
        if extra:
            h.update(extra)
        return h

    @staticmethod
    def _decompress(data: bytes, enc: str) -> bytes:
        enc = (enc or "").lower()
        try:
            if enc == "gzip":
                return gzip.decompress(data)
            if enc == "deflate":
                try:
                    return zlib.decompress(data)
                except zlib.error:
                    return zlib.decompress(data, -zlib.MAX_WBITS)
        except Exception:
            return data
        return data

    def get(self, url: str, accept: list[str] | None = None,
            extra_headers: dict | None = None) -> HttpResponse:
        headers = self._headers(url, accept or [], extra_headers)
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                raw = r.read(self.max_bytes + 1)
                enc = r.headers.get("Content-Encoding", "")
                body = self._decompress(raw, enc)[: self.max_bytes]
                resp = HttpResponse(url, r.status, dict(r.headers), body)
        except urllib.error.HTTPError as e:
            if e.code == 304:
                row = self.etag.query_one(
                    "SELECT sha256 FROM etag_cache WHERE url=?", (url,)) if self.etag else None
                return HttpResponse(url, 304, dict(e.headers or {}), b"",
                                    from_cache=True, sha256=(row["sha256"] if row else ""))
            return HttpResponse(url, e.code, dict(e.headers or {}), b"")
        except (urllib.error.URLError, socket.timeout, ConnectionError) as e:
            raise NetError(str(e)) from None

        resp.sha256 = sha256_bytes(resp.body)
        if self.etag is not None and resp.status == 200:
            self.etag.execute(
                "INSERT INTO etag_cache(url,etag,last_modified,sha256,resolved_via,fetched_at) "
                "VALUES(?,?,?,?,?,?) ON CONFLICT(url) DO UPDATE SET "
                "etag=excluded.etag,last_modified=excluded.last_modified,"
                "sha256=excluded.sha256,fetched_at=excluded.fetched_at",
                (url, resp.headers.get("ETag"), resp.headers.get("Last-Modified"),
                 resp.sha256, None, now_iso()))
        return resp


class NetError(Exception):
    pass
