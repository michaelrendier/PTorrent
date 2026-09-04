"""Warning-label vocabulary + validation + the TLP -> capability mapping.

Normalises the external standards that are designed to travel attached to an
artifact through every hop:

  TLP 2.0 (FIRST)            handling label — CLEAR|GREEN|AMBER|AMBER+STRICT|RED
  STIX 2.1 data markings     the carriage mechanism (see custody.export_stix)
  CSAF 2.x (OASIS)           the machine-readable advisory form (see custody.export_csaf)
  MITRE CWE / CAPEC          weakness / attack-pattern class
  MITRE ATLAS               AML.Txxxx techniques, AML.Mxxxx mitigations (data hazards)
  FIRST CVSS 4.0 / EPSS      severity / exploit-likelihood
  CISA SSVC                 decision label

PTorrent-original fields: `hazard_class` (controlled vocab) and `scan`.
`epss` is time-varying and is NOT part of labels_hash so the digest stays stable.
"""
from __future__ import annotations

import re

from ._util import canonical_json, sha256_text
from .errors import PtErr, PtError

TLP_VALUES = ("CLEAR", "GREEN", "AMBER", "AMBER+STRICT", "RED")

# TLP -> what PTorrent permits. Consumed by access.py / phonebook.py / engine.
TLP_CAPS = {
    "CLEAR":        {"phonebook_list": True,  "seed": "free",     "grant_transitive": True},
    "GREEN":        {"phonebook_list": False, "seed": "verified",  "grant_transitive": True},
    "AMBER":        {"phonebook_list": False, "seed": "granted",   "grant_transitive": True},
    "AMBER+STRICT": {"phonebook_list": False, "seed": "granted",   "grant_transitive": False},
    "RED":          {"phonebook_list": False, "seed": "never",     "grant_transitive": False},
}

HAZARD_CLASSES = (
    "crypto-attack-vector", "exploit-code", "malware-sample", "credential-dump",
    "poisoned-dataset", "adversarial-benchmark", "side-channel-measurement",
    "pre-publication-vuln", "pii", "phi", "financial-records",
)

_CWE_RE = re.compile(r"^CWE-\d+$")
_CAPEC_RE = re.compile(r"^CAPEC-\d+$")
_ATLAS_T_RE = re.compile(r"^AML\.T\d{4}(\.\d{3})?$")
_ATLAS_M_RE = re.compile(r"^AML\.M\d{4}$")
_CVSS_RE = re.compile(r"^CVSS:[34]\.\d/")
_CVE_RE = re.compile(r"^CVE-\d{4}-\d{4,}$")


def validate(labels: dict) -> list[str]:
    """Return a list of problem strings ([] == valid). Never raises."""
    problems: list[str] = []
    if not isinstance(labels, dict):
        return ["labels must be an object"]

    tlp = labels.get("tlp")
    if tlp is not None and tlp not in TLP_VALUES:
        problems.append(f"tlp {tlp!r} not one of {TLP_VALUES}")

    for k, rx, name in (
        ("cwe", _CWE_RE, "CWE-<n>"),
        ("capec", _CAPEC_RE, "CAPEC-<n>"),
    ):
        for v in labels.get(k, []) or []:
            if not rx.match(str(v)):
                problems.append(f"{k} entry {v!r} is not {name}")

    atlas = labels.get("atlas") or {}
    for v in atlas.get("techniques", []) or []:
        if not _ATLAS_T_RE.match(str(v)):
            problems.append(f"atlas technique {v!r} is not AML.Txxxx")
    for v in atlas.get("mitigations_applied", []) or []:
        if not _ATLAS_M_RE.match(str(v)):
            problems.append(f"atlas mitigation {v!r} is not AML.Mxxxx")

    for v in labels.get("hazard_class", []) or []:
        if v not in HAZARD_CLASSES:
            problems.append(f"hazard_class {v!r} not in controlled vocab")

    cvss = labels.get("cvss") or {}
    if cvss:
        vec = cvss.get("vector", "")
        if vec and not _CVSS_RE.match(vec):
            problems.append(f"cvss.vector {vec!r} does not start CVSS:3.x/ or CVSS:4.0/")
        sc = cvss.get("score")
        if sc is not None and not (0.0 <= float(sc) <= 10.0):
            problems.append(f"cvss.score {sc} out of range 0..10")

    cve = labels.get("cve_id") or labels.get("advisory", {}).get("cve_id")
    if cve and not _CVE_RE.match(cve):
        problems.append(f"cve_id {cve!r} is not CVE-YYYY-NNNN+")

    epss = labels.get("epss")
    if epss is not None and not (0.0 <= float(epss) <= 1.0):
        problems.append(f"epss {epss} out of range 0..1")

    return problems


_HASH_KEYS = ("tlp", "iep", "cwe", "capec", "cvss", "ssvc", "atlas",
              "hazard_class", "advisory")


def labels_hash(labels: dict) -> str:
    """Stable digest of the durable label content. Excludes `epss` (time-varying)
    and `scan` (verdict may be re-run)."""
    subset = {k: labels[k] for k in _HASH_KEYS if k in labels}
    return sha256_text(canonical_json(subset))


def tlp_of(security: dict | None) -> str:
    if not security:
        return "CLEAR"
    return (security.get("labels") or {}).get("tlp") or (
        "CLEAR" if security.get("classification", "public") == "public" else "AMBER"
    )


def caps_for(security: dict | None) -> dict:
    return TLP_CAPS[tlp_of(security)]


def require_valid(labels: dict) -> None:
    p = validate(labels)
    if p:
        raise PtError(PtErr.E_PARSE, "; ".join(p))
