"""Thumbs up / down — researcher review percentages.

Rules (enforced here + in engine):
  1. down  => mandatory `reason` (the bug report), <= 4000 chars
  2. up    => no reason
  3. voter must be VERIFIED
  4. voter != producer_orcid of the target artifact
  5. one vote per (voter, target), PERMANENT — not editable, not retractable
  6. lifecycle after cast: producer `address`  and downvoter `dispute` only

Percentages: pct_useful = up / (up + down_active), down_active excludes ADDRESSED
(non-disputed). `score` = Wilson lower bound (95%) for ranking.
"""
from __future__ import annotations

import math
import uuid

from . import chain as _chain
from ._util import now_iso, sha256_text
from .errors import PtErr, PtError

ACTIVE = "ACTIVE"
ADDRESSED = "ADDRESSED"
DISPUTED = "DISPUTED"


def _wilson(up: int, n: int, z: float = 1.96) -> float:
    if n == 0:
        return 0.0
    phat = up / n
    denom = 1 + z * z / n
    centre = phat + z * z / (2 * n)
    margin = z * math.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n)
    return max(0.0, (centre - margin) / denom)


class Votes:
    def __init__(self, db, custody: "_chain.CustodyChain", artifacts):
        self.db = db
        self.custody = custody
        self.artifacts = artifacts

    def _producer(self, target: str) -> str:
        art = self.artifacts.get(target)
        if art:
            return art.producer_orcid
        tx = self.custody.latest_of_type(_chain.ANNOUNCE, target) or \
            self.custody.latest_of_type(_chain.ACQUIRE, target) or \
            self.custody.latest_of_type(_chain.EVALUATE, target)
        return tx.actor if tx else ""

    def cast(self, target: str, value: str, voter_orcid: str,
             reason: str | None = None) -> dict:
        if value not in ("up", "down"):
            raise PtError(PtErr.E_INVAL, "value must be 'up' or 'down'")
        if value == "down":
            reason = (reason or "").strip()
            if not reason:
                raise PtError(PtErr.E_INVAL, "a thumbs-down requires a reason / bug report")
            if len(reason) > 4000:
                raise PtError(PtErr.E_INVAL, "reason exceeds 4000 chars")
        else:
            reason = None
        producer = self._producer(target)
        if producer and _orcid_eq(producer, voter_orcid):
            raise PtError(PtErr.E_SELF_VOTE)
        if self.db.query_one(
                "SELECT 1 FROM votes WHERE target=? AND voter_orcid=?", (target, voter_orcid)):
            raise PtError(PtErr.E_DUP_VOTE)

        vid = "v" + uuid.uuid4().hex[:10]
        self.db.execute(
            "INSERT INTO votes(vote_id,target,voter_orcid,value,status,reason,ts) "
            "VALUES(?,?,?,?,?,?,?)",
            (vid, target, voter_orcid, value, ACTIVE, reason, now_iso()))
        note = f"{value}" + (f" {sha256_text(reason)}" if reason else "")
        self.custody.add_tx(_chain.VOTE, actor=voter_orcid, object_hash=target, note=note)
        return {"vote_id": vid, "tally": self.tally(target)}

    def address(self, vote_id: str, actor_orcid: str, resolution: str,
                fixed_hash: str | None = None) -> dict:
        row = self.db.query_one("SELECT * FROM votes WHERE vote_id=?", (vote_id,))
        if not row:
            raise PtError(PtErr.E_NOTFOUND, "no such vote")
        if row["value"] != "down":
            raise PtError(PtErr.E_INVAL, "only thumbs-down carry a bug report to address")
        producer = self._producer(row["target"])
        if not producer or not _orcid_eq(producer, actor_orcid):
            raise PtError(PtErr.E_ACCESS, "only the producer of the target may address a downvote")
        resolution = (resolution or "").strip()
        if not resolution:
            raise PtError(PtErr.E_INVAL, "a resolution is mandatory")
        kind = "verified" if (fixed_hash and self.artifacts.get(fixed_hash)) else "unverified"
        self.db.execute(
            "UPDATE votes SET status=?, resolution=?, fixed_hash=?, resolution_kind=? "
            "WHERE vote_id=?", (ADDRESSED, resolution, fixed_hash or "", kind, vote_id))
        self.custody.add_tx(_chain.VOTE_ADDRESSED, actor=actor_orcid,
                            object_hash=row["target"], parent_hash="",
                            note=f"{sha256_text(resolution)} fixed={fixed_hash or '-'} kind={kind}")
        return {"tally": self.tally(row["target"]), "resolution_kind": kind}

    def dispute(self, vote_id: str, actor_orcid: str, reason: str) -> dict:
        row = self.db.query_one("SELECT * FROM votes WHERE vote_id=?", (vote_id,))
        if not row:
            raise PtError(PtErr.E_NOTFOUND, "no such vote")
        if not _orcid_eq(row["voter_orcid"], actor_orcid):
            raise PtError(PtErr.E_ACCESS, "only the original downvoter may dispute the resolution")
        if row["status"] != ADDRESSED or row["resolution_kind"] != "unverified":
            raise PtError(PtErr.E_INVAL, "only an unverified ADDRESSED downvote can be disputed")
        reason = (reason or "").strip()
        if not reason:
            raise PtError(PtErr.E_INVAL, "a dispute needs a reason")
        self.db.execute("UPDATE votes SET status=? WHERE vote_id=?", (ACTIVE, vote_id))
        self.custody.add_tx(_chain.VOTE_DISPUTED, actor=actor_orcid,
                            object_hash=row["target"], note=sha256_text(reason))
        return {"tally": self.tally(row["target"])}

    def tally(self, target: str, viewer_verified: bool = False) -> dict:
        rows = self.db.query("SELECT * FROM votes WHERE target=?", (target,))
        up = sum(1 for r in rows if r["value"] == "up")
        down_all = [r for r in rows if r["value"] == "down"]
        down_active = [r for r in down_all if r["status"] == ACTIVE]
        addressed = [r for r in down_all if r["status"] == ADDRESSED]
        n = up + len(down_active)
        pct = round(up / n, 4) if n else None
        reasons = []
        for r in down_all:
            reasons.append({
                "reason": r["reason"],
                "status": r["status"],
                "resolution": r["resolution"] or None,
                "fixed_hash": r["fixed_hash"] or None,
                "voter": r["voter_orcid"] if viewer_verified else "a verified researcher",
                "ts": r["ts"],
            })
        return {
            "up": up, "down": len(down_active), "down_total": len(down_all),
            "addressed": len(addressed), "n": n, "pct": pct,
            "score": round(_wilson(up, n), 4) if n else 0.0,
            "reasons": reasons,
        }

    def reputation(self, orcid: str) -> dict:
        arts = self.db.query("SELECT file_hash FROM artifacts WHERE producer_orcid=?", (orcid,))
        up = down = addr = 0
        for a in arts:
            t = self.tally(a["file_hash"])
            up += t["up"]; down += t["down"]; addr += t["addressed"]
        n = up + down
        return {"artifacts": len(arts), "up": up, "down_active": down,
                "down_addressed": addr, "pct_useful": round(up / n, 4) if n else None,
                "score": round(_wilson(up, n), 4) if n else 0.0}


def _orcid_eq(a: str, b: str) -> bool:
    def norm(x):
        return (x or "").replace("ORCID:", "").split("@", 1)[0].strip().upper()
    return bool(norm(a)) and norm(a) == norm(b)
