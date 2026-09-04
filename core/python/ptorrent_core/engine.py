"""Engine — the façade every skin binds to (in-process or over JSON-RPC).

Design decisions locked in this session:
  * co-equal Python API + JSON schema (schema/v1.json)
  * the core owns worker threads + the per-host crawl scheduler; skins poll
    snapshot() / events(since_seq)
  * in-process execution for all jobs; a subprocess-sandbox shim is triggered
    only by security.level >= 3, a chain FLAG, or an explicit "sandbox": true
  * durable, replayable events (sqlite); the custody chain is the evidentiary
    substrate and every custody tx also lands as an event
"""
from __future__ import annotations

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from . import chain as _chain
from . import custody as _custody
from . import labels as _labels
from . import phonebook as _pb
from . import preflight as _preflight
from . import ptfile as _ptfile
from . import wizard as _wizard
from ._util import now_iso, sha256_canonical, sha256_text, slugify
from .access import AccessManager
from .artifacts import BinaryArtifactStore
from .crawl import Crawler, ItemState
from .db import DB
from .errors import PtErr, PtError
from .evaluate import Evaluator
from .identity import IdentityManager
from .votes import Votes


@dataclass
class Roots:
    base: str
    data_root: str = ""
    tmp_root: str = ""
    inbox_root: str = ""
    chain_path: str = ""
    db_path: str = ""
    token_path: str = ""

    def resolved(self) -> "Roots":
        b = os.path.abspath(self.base)
        return Roots(
            base=b,
            data_root=self.data_root or os.path.join(b, "artifacts"),
            tmp_root=self.tmp_root or os.path.join(b, "tmp"),
            inbox_root=self.inbox_root or os.path.join(b, "inbox"),
            chain_path=self.chain_path or os.path.join(b, "custody_chain.json"),
            db_path=self.db_path or os.path.join(b, "ptorrent.db"),
            token_path=self.token_path or os.path.join(b, "identity.json"),
        )


@dataclass
class _Job:
    id: str
    pf: object
    status: str = "QUEUED"
    progress: dict = field(default_factory=dict)
    error: str = ""
    trusted: bool = True
    cancel: threading.Event = field(default_factory=threading.Event)
    pause: threading.Event = field(default_factory=threading.Event)
    future: object = None


class Engine:
    def __init__(self, base_dir: str, *, roots: Roots | None = None,
                 max_workers: int = 4, difficulty: int = 2):
        self.roots = (roots or Roots(base=base_dir)).resolved()
        for d in (self.roots.base, self.roots.data_root, self.roots.tmp_root,
                  self.roots.inbox_root):
            os.makedirs(d, exist_ok=True)

        self.db = DB(self.roots.db_path)
        self.custody = _chain.CustodyChain(self.roots.chain_path, difficulty=difficulty)
        self.artifacts = BinaryArtifactStore(self.roots.data_root, self.db, self.custody)
        self.identity = IdentityManager(self.roots.token_path, self.db)
        self.phonebook = _pb.Phonebook(self.db, self.custody)
        self.votes = Votes(self.db, self.custody, self.artifacts)
        self.access = AccessManager(self.db, self.custody, self.identity, _labels)

        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="pt-job")
        self._jobs: dict[str, _Job] = {}
        self._lock = threading.Lock()
        self._restore_jobs()

    # ══ events ═════════════════════════════════════════════════════════════
    def _emit(self, kind: str, payload: dict, job_id: str | None = None) -> int:
        return self.db.append_event(kind, payload, job_id)

    def events(self, since_seq: int = 0, limit: int = 500) -> list[dict]:
        return self.db.events_since(since_seq, limit)

    # ══ snapshot ═══════════════════════════════════════════════════════════
    def snapshot(self) -> dict:
        with self._lock:
            jobs = [self._job_view(j) for j in self._jobs.values()]
        return {
            "jobs": jobs,
            "phonebook": self.phonebook.stats(),
            "chain": {"tip_hash": self.custody.tip(), "height": self.custody.height,
                      "valid": self.custody.valid_chain()},
            "identity": self.identity.current().to_dict(),
            "events_seq": self.db.latest_seq(),
        }

    def _job_view(self, j: _Job) -> dict:
        pf = j.pf
        return {
            "id": j.id, "type": pf.type.value, "name": pf.name, "color": pf.color,
            "status": j.status, "progress": j.progress, "error": j.error,
            "security": pf.to_snapshot_security(),
        }

    def job(self, job_id: str) -> dict:
        j = self._jobs.get(job_id)
        if not j:
            raise PtError(PtErr.E_NOTFOUND, f"no job {job_id!r}")
        return self._job_view(j)

    def items(self, job_id: str, offset: int = 0, limit: int = 500) -> list[dict]:
        rows = self.db.query(
            "SELECT idx,tag,url,status,resolved_via,robots_state,detail FROM items "
            "WHERE job_id=? ORDER BY idx LIMIT ? OFFSET ?", (job_id, limit, offset))
        return [dict(r) for r in rows]

    def artifact(self, file_hash: str) -> dict:
        a = self.artifacts.get(file_hash)
        if not a:
            raise PtError(PtErr.E_NOTFOUND, "no such artifact")
        d = a.to_dict()
        d["votes"] = self.votes.tally(file_hash, self.identity.current().is_verified)
        d["seeders"] = self.custody.seeders(file_hash)
        return d

    # ══ add / lifecycle ════════════════════════════════════════════════════
    def preflight(self, ptorrent) -> dict:
        pf = self._as_pf(ptorrent)
        return _preflight.check(pf, self.roots.data_root).to_dict()

    def ptorrent_build(self, answers: dict) -> dict:
        return _wizard.build(answers)

    def wizard_questionnaire(self) -> dict:
        return _wizard.questionnaire()

    def add(self, ptorrent, *, start: bool = False, sandbox: bool | None = None,
            trusted: bool | None = None, added_by: str | None = None) -> dict:
        pf = self._as_pf(ptorrent)
        # quarantine / intake
        pre = _preflight.check(pf, self.roots.data_root)
        actor = added_by or self.identity.peer_id()
        pb_res = self.phonebook.intake(pf, actor)

        if not pre.passed and any(f.fatal_embargo for f in pre.failures):
            self._emit("QUARANTINE", {"name": pf.name, "reason": "embargo",
                                      "detail": pre.summary()})
            raise PtError(PtErr.E_EMBARGO, pre.summary())

        jid = "j" + sha256_text(f"{pf.name}:{time.time()}")[:10]
        trusted = self._infer_trusted(ptorrent) if trusted is None else trusted
        j = _Job(id=jid, pf=pf, trusted=trusted)
        with self._lock:
            self._jobs[jid] = j
        self._persist_job(j)
        self._emit("JOB_ADDED", {"job_id": jid, "type": pf.type.value, "name": pf.name,
                                 "phonebook_key": pb_res["key"],
                                 "quarantine": pb_res["quarantine"],
                                 "preflight_passed": pre.passed}, jid)
        if not pre.passed:
            j.status = "BLOCKED"
            j.error = pre.summary()
            self._persist_job(j)
        elif start:
            self.start(jid)
        return {"job_id": jid, "phonebook_key": pb_res["key"],
                "quarantine": pb_res["quarantine"],
                "preflight": pre.to_dict()}

    def start(self, job_id: str) -> dict:
        j = self._require_job(job_id)
        if j.status in ("RUNNING", "DONE"):
            return self._job_view(j)
        j.cancel.clear()
        j.pause.clear()
        j.status = "RUNNING"
        self._persist_job(j)
        j.future = self._pool.submit(self._run_job, j)
        return self._job_view(j)

    def pause(self, job_id: str) -> dict:
        j = self._require_job(job_id)
        j.pause.set()
        if j.status == "RUNNING":
            j.status = "PAUSED"
            self._persist_job(j)
        self._emit("JOB_PAUSED", {"job_id": job_id}, job_id)
        return self._job_view(j)

    def resume(self, job_id: str) -> dict:
        j = self._require_job(job_id)
        j.pause.clear()
        if j.status == "PAUSED":
            j.status = "RUNNING"
            self._persist_job(j)
        self._emit("JOB_RESUMED", {"job_id": job_id}, job_id)
        return self._job_view(j)

    def abort(self, job_id: str) -> dict:
        j = self._require_job(job_id)
        j.cancel.set()
        j.pause.clear()
        j.status = "ERROR" if j.status == "RUNNING" else j.status
        j.error = j.error or "aborted"
        self._persist_job(j)
        self._emit("JOB_ABORTED", {"job_id": job_id}, job_id)
        return self._job_view(j)

    def pause_all(self):
        for jid in list(self._jobs):
            self.pause(jid)

    def resume_all(self):
        for jid in list(self._jobs):
            self.resume(jid)

    # ══ job runner ═════════════════════════════════════════════════════════
    def _run_job(self, j: _Job):
        pf = j.pf
        try:
            if pf.type.value in ("corpus", "dataset", "transfer"):
                self._run_crawl(j)
            elif pf.type.value == "evaluation":
                self._run_eval(j)
            elif pf.type.value == "phonebook":
                j.status = "DONE"
            else:
                raise PtError(PtErr.E_UNSUPPORTED, f"job type {pf.type.value}")
            if j.status not in ("ERROR",):
                j.status = "DONE"
        except PtError as e:
            j.status = "ERROR"
            j.error = e.detail or str(e)
        except Exception as e:  # noqa: BLE001
            j.status = "ERROR"
            j.error = f"{type(e).__name__}: {e}"
        self._persist_job(j)
        self._emit("JOB_" + j.status, {"job_id": j.id, "error": j.error,
                                       "progress": j.progress}, j.id)

    def _run_crawl(self, j: _Job):
        pf = j.pf
        marking = _custody.marking_of(pf.security)
        crawler = Crawler(pf, db=self.db,
                          event=lambda k, p: self._emit(k, p, j.id),
                          cancel=j.cancel, pause=j.pause, trusted=j.trusted)
        studied = skipped = 0
        blob_chunks: list[bytes] = []
        rows_out: list[dict] = []
        for res in crawler.run(j.id):
            if res.unchanged:
                skipped += 1
            elif res.text is not None:
                blob_chunks.append(res.text.encode("utf-8"))
                studied += 1
            elif res.rows is not None:
                rows_out.extend(res.rows)
                studied += 1
            else:
                skipped += 1
            counts = crawler.summary_counts(j.id)
            j.progress = {"studied": studied, "skipped": skipped,
                          "items": counts}
            self._persist_job(j)

        # artifact-before-stream: write the accumulated payload, then ACQUIRE
        payload = (b"\n\n".join(blob_chunks) if blob_chunks
                   else json.dumps(rows_out, ensure_ascii=False).encode("utf-8"))
        if payload:
            art = self.artifacts.acquire(
                payload, kind="dump" if rows_out else "corpus", job_id=j.id,
                producer_orcid=self.identity.peer_id(),
                file_name=f"{slugify(pf.name)}.{'json' if rows_out else 'txt'}",
                source_url=(pf.crawl_seeds()[0]["url"] if pf.crawl_seeds() else ""),
                marking=marking, retain=True,
                ext=".json" if rows_out else ".txt")
            self.custody.add_tx(_chain.ANNOUNCE, actor=self.identity.peer_id(),
                                object_hash=art.file_hash, file_name=art.file_name,
                                file_size=art.size, marking=marking,
                                note=f"job={j.id}")
            j.progress["artifact"] = art.file_hash

    def _run_eval(self, j: _Job):
        pf = j.pf
        marking = _custody.marking_of(pf.security)
        ev = Evaluator(pf)
        crawler = Crawler(pf, db=self.db,
                          event=lambda k, p: self._emit(k, p, j.id),
                          cancel=j.cancel, pause=j.pause, trusted=j.trusted)

        if ev.is_image_fn:
            # image / binary reduction: fetch each seed raw (robots-gated),
            # reduce, discard. ACQUIRE(retained=false) per image = lineage w/o bytes.
            ua_token = crawler.robots_ua
            def _fetch(url: str) -> bytes | None:
                if crawler.respect_robots:
                    ok, _st = crawler.robots.can_fetch(ua_token, url, crawler.on_unreachable)
                    if not ok:
                        return None
                with crawler.sched.slot(url):
                    r = crawler.http.get(url, accept=["image/*", "*/*"])
                return r.body if r.status == 200 and r.body else None

            def _acq(url, sha, size):
                self.custody.add_tx(
                    _chain.ACQUIRE, actor=self.identity.peer_id(), object_hash=sha,
                    marking=marking, file_size=size,
                    note=f"kind=image retained=0 src={url}", commit=False)

            urls = [s["url"] for s in pf.crawl_seeds()]
            result = ev.run_images(
                urls, _fetch, max_rows=int(pf.evaluation.get("max_rows", 5000)),
                on_acquire=_acq,
                on_progress=lambda n, t: self._emit(
                    "EVALUATE", {"job_id": j.id, "rows": n,
                                 "sigma_half_frac": t["sigma_half_frac"]}, j.id))
            self.custody.commit()
        else:
            rows: list[dict] = []
            if pf.crawl or pf.source:
                for res in crawler.run(j.id):
                    if res.rows:
                        rows.extend(res.rows)
            result = ev.run(iter(rows or []),
                            on_progress=lambda n, t: self._emit(
                                "EVALUATE", {"job_id": j.id, "rows": n,
                                             "sigma_half_frac": t["sigma_half_frac"]}, j.id))
        blob = json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8")
        art = self.artifacts.acquire(
            blob, kind="peval", job_id=j.id, producer_orcid=self.identity.peer_id(),
            file_name=f"{slugify(pf.name)}.peval",
            source_url=(pf.source.get("endpoint", "") if pf.source else ""),
            marking=marking, retain=True, ext=".peval")
        self.custody.add_tx(
            _chain.EVALUATE, actor=self.identity.peer_id(), object_hash=art.file_hash,
            parent_hash="", file_name=art.file_name, file_size=art.size,
            marking=marking, note=f"job={j.id} rows={result['row_count']} "
                                  f"half={result['tally']['sigma_half_frac']}")
        j.progress = {"row_count": result["row_count"],
                      "tally": result["tally"], "artifact": art.file_hash}

    # ══ seeding ════════════════════════════════════════════════════════════
    def seed(self, file_hash: str, list_mode: str = "off") -> dict:
        art = self.artifacts.get(file_hash)
        if not art:
            raise PtError(PtErr.E_NOTFOUND, "no such artifact")
        security = self._security_for(file_hash)
        caps = _labels.caps_for(security)
        if caps["seed"] == "never":
            raise PtError(PtErr.E_ACCESS, "TLP:RED — seeding is never permitted")
        if caps["seed"] in ("verified", "granted") and not self.identity.current().is_verified:
            raise PtError(PtErr.E_IDENTITY, "seeding this marking requires a VERIFIED identity")
        peer = self.identity.peer_id()
        self.custody.add_tx(_chain.SEED, actor=peer, object_hash=file_hash,
                            marking=_custody.marking_of(security), note="hold")
        # opt-in phonebook listing beacon
        mode = self.db.config_get("phonebook.list_my_seeds", "off")
        if list_mode != "off":
            mode = list_mode
        listed = False
        if mode != "off" and art.tlp == "CLEAR":
            pbrow = self.db.query_one(
                "SELECT key FROM phonebook WHERE json_extract(entry,'$.name') IS NOT NULL "
                "AND key IN (SELECT key FROM phonebook)")
            # attach to any phonebook key that references this job's source
            for r in self.db.query("SELECT key, entry FROM phonebook"):
                self.custody.add_tx(
                    _chain.SEED_LISTED, actor=peer,
                    object_hash=sha256_text(r["key"]), note=mode, commit=False)
            self.custody.commit()
            listed = True
        self._emit("SEED", {"file_hash": file_hash, "peer": peer,
                            "listed": listed, "mode": mode})
        return {"file_hash": file_hash, "listed": listed, "list_mode": mode}

    def unseed(self, file_hash: str) -> dict:
        peer = self.identity.peer_id()
        self.custody.add_tx(_chain.UNSEED, actor=peer, object_hash=file_hash, note="")
        self._emit("UNSEED", {"file_hash": file_hash, "peer": peer})
        return {"file_hash": file_hash}

    # ══ votes ══════════════════════════════════════════════════════════════
    def vote(self, target: str, value: str, reason: str | None = None) -> dict:
        me = self.identity.require_verified("vote")
        return self.votes.cast(target, value, me.orcid, reason)

    def vote_address(self, vote_id: str, resolution: str,
                     fixed_hash: str | None = None) -> dict:
        me = self.identity.require_verified("vote_address")
        return self.votes.address(vote_id, me.orcid, resolution, fixed_hash)

    def vote_dispute(self, vote_id: str, reason: str) -> dict:
        me = self.identity.require_verified("vote_dispute")
        return self.votes.dispute(vote_id, me.orcid, reason)

    def votes_for(self, target: str) -> dict:
        return self.votes.tally(target, self.identity.current().is_verified)

    # ══ phonebook ══════════════════════════════════════════════════════════
    def phonebook_search(self, q: str = "", **filters) -> list[dict]:
        return self.phonebook.search(q, **filters)

    def phonebook_get(self, key: str) -> dict:
        e = self.phonebook.get(key, self.identity.current().is_verified)
        if not e:
            raise PtError(PtErr.E_NOTFOUND, "no such phonebook entry")
        return e

    def phonebook_add(self, entry: dict) -> dict:
        key = self.phonebook.add(entry, self.identity.peer_id())
        return {"key": key}

    def phonebook_verify(self, key: str = "all") -> dict:
        # runs synchronously here; a fuller build makes it a job type
        import urllib.request
        keys = ([key] if key != "all"
                else [r["key"] for r in self.db.query("SELECT key FROM phonebook")])
        checked = 0
        for k in keys:
            row = self.db.query_one("SELECT entry FROM phonebook WHERE key=?", (k,))
            if not row:
                continue
            e = json.loads(row["entry"])
            status = "UNKNOWN"
            url = e.get("dataset_url") or (e.get("dumps") or [{}])[0].get("url", "")
            if url:
                try:
                    req = urllib.request.Request(url, method="HEAD",
                                                 headers={"User-Agent": "PtorrentBot/1.0"})
                    with urllib.request.urlopen(req, timeout=8) as r:
                        status = "LIVE" if r.status < 400 else "STALE"
                except Exception:
                    status = "DEAD"
            e["verify_status"] = status
            e["last_verified"] = now_iso()[:10]
            self.phonebook._write(k, e, seen_inc=False)
            self.custody.add_tx(_chain.PHONEBOOK_VERIFY, actor=self.identity.peer_id(),
                                object_hash=sha256_text(k), note=f"status={status}")
            checked += 1
        self._emit("PHONEBOOK_VERIFY", {"checked": checked})
        return {"checked": checked}

    # ══ identity ═══════════════════════════════════════════════════════════
    def identity_set(self, orcid: str) -> dict:
        return self.identity.set_orcid(orcid).to_dict()

    def identity_verify(self) -> dict:
        i = self.identity.verify_public().to_dict()
        self._emit("IDENTITY_VERIFIED", {"orcid": i["orcid"], "name": i["name"]})
        return i

    def identity_begin(self, redirect_uri: str) -> dict:
        return self.identity.begin(redirect_uri)

    def identity_complete(self, code: str, state: str) -> dict:
        return self.identity.complete(code, state).to_dict()

    def identity_clear(self) -> dict:
        self.identity.clear()
        return self.identity.current().to_dict()

    # ══ access ═════════════════════════════════════════════════════════════
    def request_access(self, target: str, message: str, owner_orcid: str = "") -> dict:
        rid = self.access.request(target, message, owner_orcid)
        self._emit("REQUEST", {"request_id": rid, "target": target})
        return {"request_id": rid}

    def request_clarify(self, request_id: str, message: str) -> dict:
        self.access.clarify(request_id, message)
        return {"request_id": request_id, "state": "CLARIFY"}

    def request_respond(self, request_id: str, message: str) -> dict:
        self.access.respond(request_id, message)
        return {"request_id": request_id, "state": "OPEN"}

    def grant_access(self, request_id: str, secret: str) -> dict:
        r = self.db.query_one("SELECT target FROM requests WHERE id=?", (request_id,))
        security = self._security_for(r["target"]) if r else None
        out = self.access.grant(request_id, secret, security)
        self._emit("GRANT", {"request_id": request_id, "grantee": out["deliver_to"]})
        return out  # engine's transport delivers out["secret"] to out["deliver_to"]

    def deny_access(self, request_id: str, reason: str) -> dict:
        self.access.deny(request_id, reason)
        self._emit("DENY", {"request_id": request_id})
        return {"request_id": request_id, "state": "DENIED"}

    def requests(self, direction: str = "incoming") -> list[dict]:
        return self.access.list(direction)

    def contact(self, orcid: str, message: str) -> dict:
        me = self.identity.require_verified("contact")
        tid = "t" + sha256_text(f"{me.orcid}:{orcid}:{time.time()}")[:10]
        self._emit("CONTACT", {"thread_id": tid, "from": me.orcid, "to": orcid,
                               "message_sha": sha256_text(message)})
        return {"thread_id": tid}

    def researcher(self, orcid: str) -> dict:
        verified_viewer = self.identity.current().is_verified
        base = {"orcid": orcid, "verified": False, "name": orcid}
        base["reputation"] = self.votes.reputation(orcid)
        if verified_viewer:
            base["contactable"] = True
            base["profile_url"] = f"https://orcid.org/{orcid}"
        return base

    # ══ config / chain ═════════════════════════════════════════════════════
    def config(self) -> dict:
        return self.db.config_all()

    def config_set(self, patch: dict) -> dict:
        for k, v in (patch or {}).items():
            self.db.config_set(k, v)
        return self.db.config_all()

    def chain_export(self, fmt: str = "native") -> dict:
        return _custody.export(self.custody, fmt, self.identity.current().to_dict())

    def chain_verify(self) -> dict:
        return {"valid": self.custody.valid_chain(), "height": self.custody.height,
                "tip_hash": self.custody.tip()}

    # ══ shutdown ═══════════════════════════════════════════════════════════
    def close(self):
        for j in self._jobs.values():
            j.cancel.set()
        self._pool.shutdown(wait=False, cancel_futures=True)
        self.custody.commit()

    # ══ internal ═══════════════════════════════════════════════════════════
    def _as_pf(self, ptorrent):
        if hasattr(ptorrent, "type"):
            return ptorrent
        if isinstance(ptorrent, dict):
            return _ptfile.parse(json.dumps(ptorrent))
        if isinstance(ptorrent, str) and os.path.exists(ptorrent):
            return _ptfile.load(ptorrent)
        return _ptfile.parse(ptorrent)

    def _infer_trusted(self, ptorrent) -> bool:
        # a path under inbox_root is treated as untrusted (from a peer)
        if isinstance(ptorrent, str) and os.path.exists(ptorrent):
            return not os.path.abspath(ptorrent).startswith(self.roots.inbox_root)
        return True

    def _security_for(self, file_hash: str) -> dict | None:
        art = self.artifacts.get(file_hash)
        if not art:
            return None
        return {"classification": "public" if art.tlp == "CLEAR" else "restricted",
                "level": 0, "labels": {"tlp": art.tlp}}

    def _require_job(self, job_id: str) -> _Job:
        j = self._jobs.get(job_id)
        if not j:
            raise PtError(PtErr.E_NOTFOUND, f"no job {job_id!r}")
        return j

    def _persist_job(self, j: _Job):
        pf = j.pf
        self.db.execute(
            "INSERT INTO jobs(id,type,name,color,status,doc,state,created,updated) "
            "VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
            "status=excluded.status,state=excluded.state,updated=excluded.updated",
            (j.id, pf.type.value, pf.name, pf.color, j.status,
             json.dumps(pf.raw, ensure_ascii=False),
             json.dumps({"progress": j.progress, "error": j.error,
                         "trusted": j.trusted}, ensure_ascii=False),
             now_iso(), now_iso()))

    def _restore_jobs(self):
        for r in self.db.query("SELECT id,doc,status,state FROM jobs"):
            try:
                pf = _ptfile.parse(r["doc"])
            except PtError:
                continue
            st = json.loads(r["state"] or "{}")
            j = _Job(id=r["id"], pf=pf,
                     status=("PAUSED" if r["status"] == "RUNNING" else r["status"]),
                     progress=st.get("progress", {}), error=st.get("error", ""),
                     trusted=st.get("trusted", True))
            self._jobs[j.id] = j
