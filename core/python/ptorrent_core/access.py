"""Access requests — the human-in-the-loop gate for protected content.

Flow:  request_access -> [request_clarify <-> request_respond]* -> grant | deny

- request_access / contact require a VERIFIED requester.
- grant delivers the secret over the live transport (engine), records only
  sha256(secret) + warning_hash on the chain.
- AMBER+STRICT / RED grants are non-transitive: a grantee cannot re-grant.
"""
from __future__ import annotations

import uuid

from . import chain as _chain
from ._util import canonical_json, now_iso, sha256_text
from .errors import PtErr, PtError

OPEN = "OPEN"
CLARIFY = "CLARIFY"
GRANTED = "GRANTED"
DENIED = "DENIED"


class AccessManager:
    def __init__(self, db, custody: "_chain.CustodyChain", identity, labels_mod):
        self.db = db
        self.custody = custody
        self.identity = identity
        self.labels = labels_mod

    # ── requests ──
    def request(self, target: str, message: str, owner_orcid: str = "") -> str:
        me = self.identity.require_verified("request_access")
        rid = "r" + uuid.uuid4().hex[:10]
        thread = [{"actor": me.orcid, "ts": now_iso(), "text": message}]
        self.db.execute(
            "INSERT INTO requests(id,target,requester_orcid,owner_orcid,state,thread,created) "
            "VALUES(?,?,?,?,?,?,?)",
            (rid, target, me.orcid, owner_orcid, OPEN, canonical_json(thread), now_iso()))
        self.custody.add_tx(_chain.REQUEST, actor=me.orcid, object_hash=target,
                            note=sha256_text(message))
        return rid

    def _row(self, rid: str):
        r = self.db.query_one("SELECT * FROM requests WHERE id=?", (rid,))
        if not r:
            raise PtError(PtErr.E_NOTFOUND, "no such request")
        return r

    def clarify(self, rid: str, message: str) -> None:
        r = self._row(rid)
        me = self.identity.require_verified("request_clarify")
        self._append(r, me.orcid, message, new_state=CLARIFY)

    def respond(self, rid: str, message: str) -> None:
        r = self._row(rid)
        me = self.identity.require_verified("request_respond")
        self._append(r, me.orcid, message, new_state=OPEN)

    def _append(self, r, actor: str, text: str, new_state: str) -> None:
        thread = __import__("json").loads(r["thread"])
        thread.append({"actor": actor, "ts": now_iso(), "text": text})
        self.db.execute("UPDATE requests SET thread=?, state=? WHERE id=?",
                        (canonical_json(thread), new_state, r["id"]))

    def grant(self, rid: str, secret: str, security: dict | None) -> dict:
        r = self._row(rid)
        me = self.identity.require_verified("grant_access")
        if r["owner_orcid"] and not _eq(r["owner_orcid"], me.orcid):
            raise PtError(PtErr.E_ACCESS, "only the request owner may grant")
        warning = (security or {}).get("warning", "")
        transitive = self.labels.caps_for(security)["grant_transitive"]
        thread = __import__("json").loads(r["thread"])
        thread_root = sha256_text(canonical_json(thread))
        self.db.execute("UPDATE requests SET state=?, secret_sha=?, resolved=? WHERE id=?",
                        (GRANTED, sha256_text(secret), now_iso(), rid))
        self.db.execute(
            "INSERT INTO grants(target,grantee_orcid,granted_by,transitive,ts) "
            "VALUES(?,?,?,?,?) ON CONFLICT(target,grantee_orcid) DO UPDATE SET ts=excluded.ts",
            (r["target"], r["requester_orcid"], me.orcid, int(transitive), now_iso()))
        self.custody.add_tx(
            _chain.GRANT, actor=me.orcid, object_hash=r["target"],
            note=(f"grantee={r['requester_orcid']} secret={sha256_text(secret)} "
                  f"warning={sha256_text(warning)} thread={thread_root} "
                  f"transitive={int(transitive)}"))
        # the secret itself is returned to the engine to deliver over the transport
        return {"deliver_to": r["requester_orcid"], "secret": secret,
                "target": r["target"], "transitive": transitive}

    def deny(self, rid: str, reason: str) -> None:
        r = self._row(rid)
        me = self.identity.require_verified("deny_access")
        self.db.execute("UPDATE requests SET state=?, resolved=? WHERE id=?",
                        (DENIED, now_iso(), rid))
        self.custody.add_tx(_chain.DENY, actor=me.orcid, object_hash=r["target"],
                            note=sha256_text(reason or ""))

    # ── checks ──
    def has_grant(self, target: str, orcid: str) -> bool:
        return bool(self.db.query_one(
            "SELECT 1 FROM grants WHERE target=? AND grantee_orcid=?", (target, orcid)))

    def can_access(self, target: str, security: dict | None) -> tuple[bool, str]:
        caps = self.labels.caps_for(security)
        mode = caps["seed"]
        me = self.identity.current()
        if mode == "free":
            return True, "public"
        if not me.is_verified:
            return False, "verified identity required"
        if mode == "verified":
            return True, "verified"
        if mode == "granted":
            return (self.has_grant(target, me.orcid), "grant required")
        if mode == "never":
            return (self.has_grant(target, me.orcid), "explicit grant only")
        return False, "denied"

    def list(self, direction: str) -> list[dict]:
        me = self.identity.current().orcid
        if direction == "incoming":
            rows = self.db.query("SELECT * FROM requests WHERE owner_orcid=? OR owner_orcid='' "
                                 "ORDER BY created DESC", (me,))
        else:
            rows = self.db.query("SELECT * FROM requests WHERE requester_orcid=? "
                                 "ORDER BY created DESC", (me,))
        return [{"id": r["id"], "target": r["target"],
                 "requester_orcid": r["requester_orcid"], "owner_orcid": r["owner_orcid"],
                 "state": r["state"], "thread": __import__("json").loads(r["thread"]),
                 "created": r["created"], "resolved": r["resolved"]} for r in rows]


def _eq(a: str, b: str) -> bool:
    n = lambda x: (x or "").replace("ORCID:", "").split("@", 1)[0].strip().upper()
    return bool(n(a)) and n(a) == n(b)
