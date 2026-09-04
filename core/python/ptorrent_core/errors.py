"""Error codes. Mirrors libptorrent pt_err, plus the runtime-layer extensions.

Negative ints so a function returning a count can use >= 0 for success, exactly
as the C core does.
"""
from __future__ import annotations

from enum import IntEnum


class PtErr(IntEnum):
    OK = 0
    # ── from libptorrent (include/ptorrent.h) ──
    E_INVAL = -1          # NULL / out-of-range argument
    E_NOMEM = -2
    E_PARSE = -3          # malformed input
    E_IO = -4
    E_NOTFOUND = -5
    E_UNSUPPORTED = -6    # valid but not implemented in this build
    E_TYPE = -7           # JSON value present but wrong type
    E_TRUNCATED = -8
    E_INDEX_MISMATCH = -9  # corpus dedup: index from a different generation
    # ── runtime layer (this package) ──
    E_IDENTITY = -20       # action needs a VERIFIED identity
    E_SELF_VOTE = -21      # voting your own work
    E_DUP_VOTE = -22       # a vote by this voter on this target already exists
    E_EMBARGO = -23        # embargo_until not yet reached
    E_ROBOTS = -24         # every seed denied by robots.txt
    E_QUARANTINE = -25     # rejected at phonebook intake
    E_ACCESS = -26         # no GRANT for a protected artifact / wrong actor
    E_MARKING_DOWNGRADE = -27  # attempt to lower a security marking without DISCLOSE


_MESSAGES = {
    PtErr.OK: "ok",
    PtErr.E_INVAL: "invalid argument",
    PtErr.E_NOMEM: "out of memory",
    PtErr.E_PARSE: "parse error",
    PtErr.E_IO: "i/o error",
    PtErr.E_NOTFOUND: "not found",
    PtErr.E_UNSUPPORTED: "unsupported in this build",
    PtErr.E_TYPE: "wrong type",
    PtErr.E_TRUNCATED: "truncated",
    PtErr.E_INDEX_MISMATCH: "index space mismatch",
    PtErr.E_IDENTITY: "a verified ORCID identity is required for this action",
    PtErr.E_SELF_VOTE: "you cannot vote on your own work",
    PtErr.E_DUP_VOTE: "you have already voted on this target; votes are not editable",
    PtErr.E_EMBARGO: "seeding blocked: embargo has not passed",
    PtErr.E_ROBOTS: "every seed URL is disallowed by robots.txt",
    PtErr.E_QUARANTINE: "rejected at intake",
    PtErr.E_ACCESS: "access denied",
    PtErr.E_MARKING_DOWNGRADE: "cannot lower a security marking without a signed DISCLOSE",
}


def strerror(e: PtErr) -> str:
    return _MESSAGES.get(PtErr(e), "unknown error")


class PtError(Exception):
    """Raised across the surface API. Carries a PtErr code and a human string."""

    def __init__(self, code: PtErr, detail: str = ""):
        self.code = PtErr(code)
        self.detail = detail
        super().__init__(f"{self.code.name}: {detail or strerror(self.code)}")

    def to_dict(self) -> dict:
        return {"error": self.code.name, "code": int(self.code),
                "message": self.detail or strerror(self.code)}
