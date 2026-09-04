"""Durable state: one sqlite file backing the event stream, jobs, items,
artifacts, phonebook (materialized view), the conditional-GET cache, votes,
and access requests.

Design point Q4: events are replayable by monotonic `seq` across a restart.
The custody chain (chain.py) is a separate append-only substrate; every custody
transaction also lands here as an event with kind "CUSTODY".
"""
from __future__ import annotations

import json
import sqlite3
import threading
from typing import Any, Iterable

from ._util import now_epoch, now_iso

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    seq      INTEGER PRIMARY KEY AUTOINCREMENT,
    ts       TEXT NOT NULL,
    kind     TEXT NOT NULL,
    job_id   TEXT,
    payload  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_events_job ON events(job_id);

CREATE TABLE IF NOT EXISTS jobs (
    id       TEXT PRIMARY KEY,
    type     TEXT NOT NULL,
    name     TEXT NOT NULL,
    color    TEXT,
    status   TEXT NOT NULL,
    doc      TEXT NOT NULL,           -- the parsed .ptorrent
    state    TEXT NOT NULL,           -- progress / security / error blob
    created  TEXT NOT NULL,
    updated  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS items (
    job_id   TEXT NOT NULL,
    idx      INTEGER NOT NULL,
    tag      TEXT,
    url      TEXT,
    line     INTEGER,
    status   TEXT NOT NULL,
    resolved_via TEXT,
    robots_state TEXT,
    detail   TEXT,
    PRIMARY KEY (job_id, idx)
);

CREATE TABLE IF NOT EXISTS artifacts (
    file_hash     TEXT PRIMARY KEY,
    file_name     TEXT,
    kind          TEXT,
    size          INTEGER,
    retained      INTEGER,
    producer_orcid TEXT,
    source_url    TEXT,
    fetched_at    TEXT,
    parent_hash   TEXT,
    job_id        TEXT,
    labels_hash   TEXT,
    tlp           TEXT
);

CREATE TABLE IF NOT EXISTS phonebook (
    key        TEXT PRIMARY KEY,
    name       TEXT,
    entry      TEXT NOT NULL,         -- full PhonebookEntry JSON
    domain_tags TEXT,
    verify_status TEXT,
    last_verified TEXT,
    security_level INTEGER DEFAULT 0,
    seen_count INTEGER DEFAULT 1,
    updated    TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS phonebook_fts
    USING fts5(key UNINDEXED, name, description, tags);

CREATE TABLE IF NOT EXISTS etag_cache (
    url          TEXT PRIMARY KEY,
    etag         TEXT,
    last_modified TEXT,
    sha256       TEXT,
    resolved_via TEXT,
    fetched_at   TEXT
);

CREATE TABLE IF NOT EXISTS votes (
    vote_id    TEXT PRIMARY KEY,
    target     TEXT NOT NULL,
    voter_orcid TEXT NOT NULL,
    value      TEXT NOT NULL,         -- up | down
    status     TEXT NOT NULL,         -- ACTIVE | ADDRESSED | DISPUTED
    reason     TEXT,
    resolution TEXT,
    fixed_hash TEXT,
    resolution_kind TEXT,             -- verified | unverified
    ts         TEXT NOT NULL,
    UNIQUE (target, voter_orcid)
);

CREATE TABLE IF NOT EXISTS requests (
    id          TEXT PRIMARY KEY,
    target      TEXT NOT NULL,
    requester_orcid TEXT NOT NULL,
    owner_orcid TEXT,
    state       TEXT NOT NULL,        -- OPEN | CLARIFY | GRANTED | DENIED
    thread      TEXT NOT NULL,        -- JSON list of {actor, ts, text}
    secret_sha  TEXT,
    created     TEXT NOT NULL,
    resolved    TEXT
);

CREATE TABLE IF NOT EXISTS grants (
    target       TEXT NOT NULL,
    grantee_orcid TEXT NOT NULL,
    granted_by   TEXT NOT NULL,
    transitive   INTEGER DEFAULT 0,
    ts           TEXT NOT NULL,
    PRIMARY KEY (target, grantee_orcid)
);

CREATE TABLE IF NOT EXISTS config (
    k TEXT PRIMARY KEY,
    v TEXT NOT NULL
);
"""


class DB:
    def __init__(self, path: str):
        self.path = path
        self._local = threading.local()
        self._wlock = threading.Lock()
        with self._connect() as c:
            c.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        return conn

    # ── events ──────────────────────────────────────────────────────────────
    def append_event(self, kind: str, payload: dict, job_id: str | None = None) -> int:
        with self._wlock, self._connect() as c:
            cur = c.execute(
                "INSERT INTO events(ts,kind,job_id,payload) VALUES(?,?,?,?)",
                (now_iso(), kind, job_id, json.dumps(payload, ensure_ascii=False)),
            )
            return int(cur.lastrowid)

    def events_since(self, seq: int, limit: int = 500) -> list[dict]:
        rows = self._connect().execute(
            "SELECT seq,ts,kind,job_id,payload FROM events WHERE seq > ? ORDER BY seq LIMIT ?",
            (seq, limit),
        ).fetchall()
        return [{"seq": r["seq"], "ts": r["ts"], "kind": r["kind"],
                 "job_id": r["job_id"], "payload": json.loads(r["payload"])} for r in rows]

    def latest_seq(self) -> int:
        r = self._connect().execute("SELECT COALESCE(MAX(seq),0) s FROM events").fetchone()
        return int(r["s"])

    # ── generic upsert helpers ─────────────────────────────────────────────
    def execute(self, sql: str, params: Iterable = ()) -> sqlite3.Cursor:
        with self._wlock, self._connect() as c:
            return c.execute(sql, tuple(params))

    def query(self, sql: str, params: Iterable = ()) -> list[sqlite3.Row]:
        return self._connect().execute(sql, tuple(params)).fetchall()

    def query_one(self, sql: str, params: Iterable = ()) -> sqlite3.Row | None:
        return self._connect().execute(sql, tuple(params)).fetchone()

    # ── config ─────────────────────────────────────────────────────────────
    def config_get(self, key: str, default: Any = None) -> Any:
        r = self.query_one("SELECT v FROM config WHERE k=?", (key,))
        return json.loads(r["v"]) if r else default

    def config_all(self) -> dict:
        return {r["k"]: json.loads(r["v"]) for r in self.query("SELECT k,v FROM config")}

    def config_set(self, key: str, value: Any) -> None:
        self.execute("INSERT INTO config(k,v) VALUES(?,?) "
                     "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                     (key, json.dumps(value, ensure_ascii=False)))
