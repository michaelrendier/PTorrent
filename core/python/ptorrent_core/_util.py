"""Small shared helpers. Stdlib only."""
from __future__ import annotations

import hashlib
import json
import re
import time
from typing import Any

# ── time ──────────────────────────────────────────────────────────────────────

def now_iso() -> str:
    """UTC, millisecond, Zulu — the one timestamp format used everywhere."""
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + f".{int(time.time() * 1000) % 1000:03d}Z"


def now_epoch() -> float:
    return time.time()


_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def is_iso_date(s: str) -> bool:
    return bool(_ISO_RE.match(s or ""))


# ── hashing / canonical form ────────────────────────────────────────────────

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_json(obj: Any) -> str:
    """Stable serialisation for hashing: sorted keys, tight separators, UTF-8."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def sha256_canonical(obj: Any) -> str:
    return sha256_text(canonical_json(obj))


def sha256_file(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


# ── ORCID ───────────────────────────────────────────────────────────────────

_ORCID_RE = re.compile(r"^(\d{4})-(\d{4})-(\d{4})-(\d{3}[0-9X])$")


def orcid_normalise(value: str) -> str | None:
    """Strip a URL prefix, uppercase the check char. Return None if not shaped like an ORCID."""
    if not value:
        return None
    v = value.strip()
    v = v.replace("https://orcid.org/", "").replace("http://orcid.org/", "").strip("/")
    v = v.upper()
    return v if _ORCID_RE.match(v) else None


def orcid_checksum_ok(orcid: str) -> bool:
    """ISO 7064 MOD 11-2 over the 15 leading digits; last char is the check digit."""
    m = _ORCID_RE.match(orcid or "")
    if not m:
        return False
    digits = (m.group(1) + m.group(2) + m.group(3) + m.group(4))[:15]
    total = 0
    for ch in digits:
        total = (total + int(ch)) * 2
    remainder = total % 11
    check = (12 - remainder) % 11
    expected = "X" if check == 10 else str(check)
    return expected == orcid[-1]


def slugify(text: str, maxlen: int = 48) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:maxlen] or "untitled"
