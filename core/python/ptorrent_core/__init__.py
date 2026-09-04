"""PTorrent Core — the platform-independent runtime.

The posix/runtime branch libptorrent's README parks: robots-compliant api-first
crawler, per-host scheduler + network gate, .peval evaluator, phonebook,
ORCID identity + access gate, thumbs voting, and a hash-linked custody chain
with CASE/STIX exporters.

Every skin (curses, Android, iOS, .NET, browser) binds the same surface:

    from ptorrent_core import Engine
    e = Engine("~/.ptorrent")
    r = e.add({...}, start=True)          # returns {job_id, phonebook_key, ...}
    while True:
        snap = e.snapshot()
        for ev in e.events(since=seq): ...

or the identical JSON-RPC method names over ptorrentd (schema/v1.json).
"""
from __future__ import annotations

from .engine import Engine, Roots
from .errors import PtErr, PtError, strerror
from .ptfile import JobType, PtFile, parse as parse_ptfile
from .sigma import SigmaFace, classify as classify_sigma
from .wizard import build as build_ptorrent, questionnaire as wizard_questionnaire

__version__ = "1.0.0-dev"
__all__ = [
    "Engine", "Roots", "PtErr", "PtError", "strerror",
    "PtFile", "JobType", "parse_ptfile",
    "SigmaFace", "classify_sigma",
    "build_ptorrent", "wizard_questionnaire",
    "__version__",
]
