"""The Phonebook — the Alexandrian intake.

Every dataset any user points a .ptorrent at is checked into the library; if the
canonical key is not present it is added (PHONEBOOK_ADD custody tx). The dataset
metadata is always catalogued; a *peer appearing as a live seed source* is
opt-in (distribution.seed_listing == "opt-in" AND the seeding peer consents AND
security.level == 0 / TLP == CLEAR).
"""
from __future__ import annotations

import json
import urllib.parse

from . import chain as _chain
from . import labels as _labels
from ._util import canonical_json, now_iso, sha256_text
from .errors import PtErr, PtError


def canonical_key(pf) -> str:
    """Normalised dataset_url, or sha256 of the source/api descriptor."""
    url = ""
    if pf.type.value == "phonebook":
        url = pf.phonebook.get("dataset_url", "")
    elif pf.source.get("endpoint"):
        return "src:" + sha256_text(canonical_json(pf.source))[:24]
    elif pf.crawl_seeds():
        url = pf.crawl_seeds()[0]["url"]
    if not url:
        return "name:" + sha256_text(pf.name)[:24]
    p = urllib.parse.urlparse(url)
    host = p.netloc.lower().lstrip("www.")
    path = p.path.rstrip("/")
    return f"{p.scheme}://{host}{path}"


def synth_entry(pf, key: str, added_by: str) -> dict:
    pb = pf.phonebook or {}
    return {
        "key": key,
        "name": pf.name,
        "domain_tags": list(pf.primary_tags),
        "dataset_url": pb.get("dataset_url", key if key.startswith("http") else ""),
        "api": pb.get("api", pf.source or {}),
        "dumps": pb.get("dumps", []),
        "license": pb.get("license", ""),
        "citation": pb.get("citation", ""),
        "size_records": pb.get("size_records", 0),
        "size_gb": pb.get("size_gb", 0.0),
        "last_verified": pb.get("last_verified", ""),
        "verify_status": "UNKNOWN",
        "security_level": pf.security_level,
        "tlp": pf.tlp,
        "contact_orcid": (pf.security or {}).get("contact_orcid", ""),
        "seen_count": 1,
        "first_seen_by": added_by,
        "last_seen_by": [added_by],
        "description": pf.description,
    }


class Phonebook:
    def __init__(self, db, custody: "_chain.CustodyChain"):
        self.db = db
        self.custody = custody

    # ── intake ──
    def intake(self, pf, added_by: str, scan_result: dict | None = None) -> dict:
        key = canonical_key(pf)
        row = self.db.query_one("SELECT entry, seen_count FROM phonebook WHERE key=?", (key,))
        if row:
            entry = json.loads(row["entry"])
            entry["seen_count"] = int(row["seen_count"]) + 1
            lsb = set(entry.get("last_seen_by", []))
            lsb.add(added_by)
            entry["last_seen_by"] = sorted(lsb)[:20]
            for k in ("api", "dumps"):
                new = (pf.phonebook or {}).get(k)
                if new and not entry.get(k):
                    entry[k] = new
            self._write(key, entry, seen_inc=True)
            return {"key": key, "quarantine": "admitted", "created": False}

        entry = synth_entry(pf, key, added_by)
        if scan_result:
            entry["scan"] = scan_result
        self._write(key, entry, seen_inc=False)
        self.custody.add_tx(
            _chain.PHONEBOOK_ADD, actor=added_by, object_hash=sha256_text(key),
            marking={"tlp": pf.tlp, "level": pf.security_level,
                     "labels_hash": _labels.labels_hash((pf.security or {}).get("labels", {}))},
            note=f"key={key} name={pf.name[:60]}")
        return {"key": key, "quarantine": "admitted", "created": True}

    def _write(self, key: str, entry: dict, seen_inc: bool) -> None:
        self.db.execute(
            "INSERT INTO phonebook(key,name,entry,domain_tags,verify_status,last_verified,"
            "security_level,seen_count,updated) VALUES(?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET entry=excluded.entry, name=excluded.name, "
            "domain_tags=excluded.domain_tags, verify_status=excluded.verify_status, "
            "last_verified=excluded.last_verified, security_level=excluded.security_level, "
            "seen_count=excluded.seen_count, updated=excluded.updated",
            (key, entry["name"], canonical_json(entry),
             ",".join(entry.get("domain_tags", [])), entry.get("verify_status", "UNKNOWN"),
             entry.get("last_verified", ""), int(entry.get("security_level", 0)),
             int(entry.get("seen_count", 1)), now_iso()))
        # FTS
        self.db.execute("DELETE FROM phonebook_fts WHERE key=?", (key,))
        self.db.execute(
            "INSERT INTO phonebook_fts(key,name,description,tags) VALUES(?,?,?,?)",
            (key, entry["name"], entry.get("description", ""),
             " ".join(entry.get("domain_tags", []))))

    # ── read ──
    def get(self, key: str, viewer_verified: bool = False) -> dict | None:
        r = self.db.query_one("SELECT entry FROM phonebook WHERE key=?", (key,))
        if not r:
            return None
        entry = json.loads(r["entry"])
        entry["live_seeds"] = self.live_seeds(key, entry)
        entry["listing_allowed"] = entry.get("tlp", "CLEAR") == "CLEAR"
        if not viewer_verified:
            entry.pop("contact_orcid", None)
        return entry

    def search(self, q: str, *, domain: str | None = None, api: bool | None = None,
               dump: bool | None = None, max_gb: float | None = None,
               verified_since: str | None = None, security_level: int | None = None,
               sort: str = "seen", limit: int = 50) -> list[dict]:
        if q:
            rows = self.db.query(
                "SELECT p.entry FROM phonebook_fts f JOIN phonebook p ON p.key=f.key "
                "WHERE phonebook_fts MATCH ? LIMIT 500", (q,))
        else:
            rows = self.db.query("SELECT entry FROM phonebook LIMIT 500")
        out = []
        for r in rows:
            e = json.loads(r["entry"])
            if domain and domain not in e.get("domain_tags", []):
                continue
            if api is not None and bool((e.get("api") or {}).get("available",
                                        bool(e.get("api")))) != api:
                continue
            if dump is not None and bool(e.get("dumps")) != dump:
                continue
            if max_gb is not None and float(e.get("size_gb", 0) or 0) > max_gb:
                continue
            if verified_since and (e.get("last_verified", "") or "") < verified_since:
                continue
            if security_level is not None and int(e.get("security_level", 0)) > security_level:
                continue
            out.append(e)
        keyfn = {
            "seen": lambda e: -int(e.get("seen_count", 0)),
            "verified": lambda e: e.get("last_verified", ""),
            "size": lambda e: -float(e.get("size_gb", 0) or 0),
        }.get(sort, lambda e: -int(e.get("seen_count", 0)))
        out.sort(key=keyfn)
        return out[:limit]

    def add(self, entry: dict, added_by: str) -> str:
        key = entry.get("key") or ("name:" + sha256_text(entry.get("name", "?"))[:24])
        entry.setdefault("seen_count", 1)
        entry.setdefault("verify_status", "UNKNOWN")
        self._write(key, entry, seen_inc=False)
        self.custody.add_tx(_chain.PHONEBOOK_ADD, actor=added_by,
                            object_hash=sha256_text(key), note=f"key={key} manual")
        return key

    # ── live seeds ──
    def live_seeds(self, key: str, entry: dict | None = None) -> list[dict]:
        entry = entry or (json.loads(
            self.db.query_one("SELECT entry FROM phonebook WHERE key=?", (key,))["entry"]))
        if entry.get("tlp", "CLEAR") != "CLEAR":
            return []
        # SEED_LISTED presence beacons keyed on the phonebook key hash
        kh = sha256_text(key)
        listed: dict[str, dict] = {}
        for tx in self.custody.all_tx():
            if tx.object_hash != kh:
                continue
            if tx.type == _chain.SEED_LISTED:
                listed[tx.actor] = {"peer_id": tx.actor, "orcid":
                                    tx.actor.replace("ORCID:", "").split("@")[0]
                                    if tx.actor.startswith("ORCID:") else None,
                                    "last_seen": now_iso(), "mode": tx.note}
            elif tx.type == _chain.SEED_UNLISTED:
                listed.pop(tx.actor, None)
        return list(listed.values())

    def stats(self) -> dict:
        r = self.db.query_one(
            "SELECT COUNT(*) c, "
            "SUM(CASE WHEN verify_status='STALE' THEN 1 ELSE 0 END) stale, "
            "SUM(CASE WHEN verify_status='DEAD' THEN 1 ELSE 0 END) dead FROM phonebook")
        return {"count": r["c"] or 0, "stale": r["stale"] or 0, "dead": r["dead"] or 0}
