"""`.ptorrent` parse + validate. Pure Python.

Fail-closed, matching libptorrent's documented choices:
  - corpus job with neither `txt` nor `urls`   -> rejected at parse
  - corpus job with no `bin`                    -> rejected at parse
  - evaluation with no J method                 -> rejected at parse
  - unmodelled JSON fields                      -> retained (self.raw), never discarded

Spec v1.2 additions modelled: `crawl` block, `distribution` block, `security.labels`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum

from . import labels as _labels
from ._util import is_iso_date
from .errors import PtErr, PtError


class JobType(str, Enum):
    CORPUS = "corpus"
    DATASET = "dataset"
    TRANSFER = "transfer"
    PHONEBOOK = "phonebook"
    EVALUATION = "evaluation"


class JMethod(str, Enum):
    NONE = "none"
    COL = "j_col"
    NUM_DEN = "j_num_den"
    EXPR = "j_expr"
    FN = "fn"


_DEFAULT_CRAWL_POLITENESS = {
    "ua": "Mozilla/5.0 (compatible; PtorrentBot/1.0; +https://github.com/michaelrendier/PTorrent)",
    "robots_ua": None,
    "respect_robots": True,
    "on_robots_unreachable": "allow",   # allow | deny
    "default_delay_s": 1.0,
    "max_delay_s": 30.0,
    "max_concurrent_per_host": 1,
    "global_concurrency": 8,
    "jitter": True,
    "obey_retry_after": True,
    "accept_language": "en",
    "send_from_header": True,
    "host_ua": {},
    "backoff": {"on": [429, 503], "base_s": 2, "max_s": 300, "give_up_after": 5},
}
_DEFAULT_CRAWL_HTTP = {
    "timeout_s": 15,
    "max_bytes_per_page": 2_000_000,
    "accept": ["text/html", "application/json", "text/plain"],
    "range_resume": True,
    "conditional": True,
    "cache": "etag",
}
_DEFAULT_CRAWL_SCOPE = {
    "allow_hosts": [], "allow_paths": [], "deny_paths": [],
    "max_depth": 0, "max_pages": 500, "same_host_only": True, "follow": "none",
}
_DEFAULT_EXTRACT = {
    "html": {"strip": ["script", "style", "nav", "header", "footer", "aside",
                        "noscript", "form", "button"],
             "main_selector": None, "min_chars": 40},
    "json": {"pointer": None, "fields": []},
}


def _merge(default: dict, override) -> dict:
    out = json.loads(json.dumps(default))
    if isinstance(override, dict):
        for k, v in override.items():
            if isinstance(v, dict) and isinstance(out.get(k), dict):
                out[k] = _merge(out[k], v)
            else:
                out[k] = v
    return out


@dataclass
class PtFile:
    raw: dict
    version: str
    type: JobType
    name: str
    color: str
    description: str
    bin: str = ""
    txt: str = ""
    requires_bin: str = ""
    primary_tags: list = field(default_factory=list)
    primary_weight: float = 1.0
    context_weight: float = 1.0
    urls: list = field(default_factory=list)          # [{tag,url}]
    source: dict = field(default_factory=dict)
    phonebook: dict = field(default_factory=dict)
    security: dict = field(default_factory=dict)
    resources: dict = field(default_factory=dict)
    distribution: dict = field(default_factory=dict)
    evaluation: dict = field(default_factory=dict)
    crawl: dict = field(default_factory=dict)
    data_model: dict = field(default_factory=dict)

    # ── derived ──
    @property
    def j_method(self) -> JMethod:
        ev = self.evaluation
        if ev.get("j_col"):
            return JMethod.COL
        if ev.get("j_num_col") and ev.get("j_den_col"):
            return JMethod.NUM_DEN
        if ev.get("j_expr"):
            return JMethod.EXPR
        if ev.get("fn"):
            return JMethod.FN
        return JMethod.NONE

    @property
    def security_level(self) -> int:
        return int(self.security.get("level", 0)) if self.security else 0

    @property
    def tlp(self) -> str:
        return _labels.tlp_of(self.security)

    @property
    def seed_listing(self) -> str:
        return (self.distribution or {}).get("seed_listing", "off")

    def crawl_seeds(self) -> list[dict]:
        """Effective seed list: crawl.seeds, else embedded urls[], else []."""
        if self.crawl.get("seeds"):
            return list(self.crawl["seeds"])
        return [dict(u) for u in self.urls]

    def embargoed(self, today_iso: str) -> bool:
        e = (self.security or {}).get("embargo_until", "")
        return bool(e) and today_iso < e

    def to_snapshot_security(self) -> dict:
        s = self.security or {}
        return {
            "level": self.security_level,
            "classification": s.get("classification", "public"),
            "embargo_until": s.get("embargo_until", ""),
            "contact_orcid": s.get("contact_orcid", ""),
            "tlp": self.tlp,
            "acknowledge_required": bool(s.get("acknowledge_required", False)),
        }


def _need(obj: dict, key: str, kind=str):
    if key not in obj:
        raise PtError(PtErr.E_PARSE, f"missing required field {key!r}")
    v = obj[key]
    if not isinstance(v, kind):
        raise PtError(PtErr.E_TYPE, f"field {key!r} must be {kind.__name__}")
    return v


def parse(text: str) -> PtFile:
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as e:
        raise PtError(PtErr.E_PARSE, f"line {e.lineno} col {e.colno}: {e.msg}") from None
    if not isinstance(obj, dict):
        raise PtError(PtErr.E_TYPE, "top-level value must be an object")

    ver = str(obj.get("ptorrent_version", "1.0"))
    tname = _need(obj, "type")
    try:
        jtype = JobType(tname)
    except ValueError:
        raise PtError(PtErr.E_PARSE, f"unknown type {tname!r}") from None

    pf = PtFile(
        raw=obj,
        version=ver,
        type=jtype,
        name=_need(obj, "name"),
        color=obj.get("color", "gold"),
        description=obj.get("description", ""),
        bin=obj.get("bin", ""),
        txt=obj.get("txt", ""),
        requires_bin=obj.get("requires_bin", ""),
        primary_tags=list(obj.get("primary_tags", [])),
        primary_weight=float(obj.get("primary_weight", 1.0)),
        context_weight=float(obj.get("context_weight", 1.0)),
        urls=[{"tag": u.get("tag", ""), "url": u["url"]}
              for u in obj.get("urls", []) if isinstance(u, dict) and u.get("url")],
        source=dict(obj.get("source", {})),
        phonebook=dict(obj.get("phonebook", {})),
        security=dict(obj.get("security", {})),
        resources=dict(obj.get("resources", {})),
        distribution=dict(obj.get("distribution", {})),
        evaluation=dict(obj.get("evaluation", {})),
        data_model=dict(obj.get("data_model", {})),
    )

    # normalise the crawl block against defaults
    craw = obj.get("crawl", {})
    if craw or jtype in (JobType.CORPUS, JobType.DATASET, JobType.TRANSFER):
        pf.crawl = {
            "seeds": list(craw.get("seeds", [])),
            "resolution": craw.get("resolution",
                                   ["declared_api", "known_api", "sitemap", "feed", "html"]),
            "scope": _merge(_DEFAULT_CRAWL_SCOPE, craw.get("scope")),
            "politeness": _merge(_DEFAULT_CRAWL_POLITENESS, craw.get("politeness")),
            "http": _merge(_DEFAULT_CRAWL_HTTP, craw.get("http")),
            "extract": _merge(_DEFAULT_EXTRACT, craw.get("extract")),
        }

    _validate(pf)
    return pf


def _validate(pf: PtFile) -> None:
    if pf.type in (JobType.CORPUS, JobType.TRANSFER):
        if not pf.bin and not pf.requires_bin:
            raise PtError(PtErr.E_PARSE, "corpus/transfer job needs `bin` (or `requires_bin`)")
    if pf.type == JobType.CORPUS:
        if not pf.txt and not pf.urls and not pf.crawl.get("seeds"):
            raise PtError(PtErr.E_PARSE, "corpus job has neither `txt`, `urls`, nor `crawl.seeds`")
    if pf.type == JobType.EVALUATION:
        if pf.j_method is JMethod.NONE:
            raise PtError(PtErr.E_PARSE,
                          "evaluation job declares no J method (j_col / j_num_col+j_den_col / j_expr / fn)")
    if pf.type == JobType.PHONEBOOK and not pf.phonebook.get("dataset_url"):
        raise PtError(PtErr.E_PARSE, "phonebook entry needs phonebook.dataset_url")

    # security block
    s = pf.security
    if s:
        lvl = int(s.get("level", 0))
        if lvl not in (0, 1, 2, 3):
            raise PtError(PtErr.E_PARSE, f"security.level {lvl} not in 0..3")
        if lvl >= 1 and not s.get("labels"):
            raise PtError(PtErr.E_PARSE, "security.level >= 1 requires a `security.labels` block")
        if s.get("classification", "public") != "public" and not (s.get("labels") or {}).get("tlp"):
            raise PtError(PtErr.E_PARSE, "non-public classification requires security.labels.tlp")
        e = s.get("embargo_until", "")
        if e and not is_iso_date(e):
            raise PtError(PtErr.E_PARSE, f"security.embargo_until {e!r} is not YYYY-MM-DD")
        if s.get("labels"):
            _labels.require_valid(s["labels"])
        if lvl >= 2 and not s.get("contact_orcid"):
            raise PtError(PtErr.E_PARSE, "security.level >= 2 requires security.contact_orcid")

    # distribution block
    d = pf.distribution
    if d and d.get("seed_listing", "off") not in ("off", "opt-in"):
        raise PtError(PtErr.E_PARSE, "distribution.seed_listing must be 'off' or 'opt-in'")

    # crawl politeness sanity
    pol = pf.crawl.get("politeness", {})
    if pol and pol.get("on_robots_unreachable") not in ("allow", "deny"):
        raise PtError(PtErr.E_PARSE, "crawl.politeness.on_robots_unreachable must be 'allow' or 'deny'")


def load(path: str) -> PtFile:
    with open(path, encoding="utf-8") as f:
        return parse(f.read())
