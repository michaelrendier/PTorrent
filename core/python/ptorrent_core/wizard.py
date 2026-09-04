"""The "Create New .ptorrent" wizard — core-exposed so every skin asks the same
questions and produces the same file.

Step C (cybersecurity self-identification) is a decision tree whose answers
deterministically set classification / level / labels. Advisory in the skin,
authoritative in the core: engine.add() re-runs ptfile validation and will
re-raise the level or reject a hand-edited downgrade.
"""
from __future__ import annotations

from . import ptfile as _ptfile
from ._util import is_iso_date
from .errors import PtErr, PtError

# hazard selections in step C
HAZARDS = {
    "crypto_exploitable": "reveals exploitable structure in a deployed crypto system",
    "exploit_code": "contains exploit code / malware / attack tooling",
    "credentials": "contains credentials, keys, or breach data",
    "poisonable": "poisonable training/eval set, or a known-poisoned / adversarial dataset",
    "side_channel": "side-channel / HSM / hardware-attack measurements",
    "prepub_vuln": "pre-publication vulnerability research",
}


def questionnaire() -> dict:
    """The form a skin renders. Returned verbatim so all skins match."""
    return {
        "steps": [
            {"id": "A", "title": "Basics",
             "fields": ["name", "type", "color", "description", "primary_tags"]},
            {"id": "B", "title": "Source",
             "fields": ["seeds[] (tag,url)", "source{} (mode,endpoint)"]},
            {"id": "C", "title": "Cybersecurity self-identification",
             "question": "Does this dataset — or its evaluation output — do any of these?",
             "multi": list(HAZARDS.items()),
             "followups": {
                 "level3_test": "Could a competent attacker build a working exploit "
                                "from this + public info, in a reasonable timeframe?",
                 "atlas": "Offensive sample or defensive benchmark?",
             }},
            {"id": "D", "title": "Distribution",
             "fields": ["distribution.seed_listing (off|opt-in)"]},
        ]
    }


def build(answers: dict) -> dict:
    """answers -> {ptorrent: <dict>, warnings: [...]}"""
    warnings: list[str] = []
    a = answers or {}
    jtype = a.get("type", "corpus")
    doc: dict = {
        "ptorrent_version": "1.2",
        "type": jtype,
        "name": a.get("name") or _fail("name is required"),
        "color": a.get("color", "gold"),
        "description": a.get("description", ""),
        "primary_tags": list(a.get("primary_tags", [])),
    }
    if jtype in ("corpus", "transfer"):
        doc["bin"] = a.get("bin") or f"monad_{_slug(doc['name'])}.bin"
    if a.get("seeds"):
        doc["crawl"] = {"seeds": [{"tag": s.get("tag", ""), "url": s["url"]}
                                  for s in a["seeds"] if s.get("url")]}
    if a.get("source"):
        doc["source"] = dict(a["source"])
    if jtype == "evaluation":
        ev = a.get("evaluation", {})
        if not any(ev.get(k) for k in ("j_col", "j_expr", "fn")) and not (
                ev.get("j_num_col") and ev.get("j_den_col")):
            _fail("evaluation needs a J method (j_col / j_num_col+j_den_col / j_expr / fn)")
        doc["evaluation"] = ev

    # ── Step C ──
    hz = set(a.get("hazards", []))
    labels: dict = {}
    sec: dict = {}
    if not hz:
        # none of the above -> Level 0, TLP:CLEAR implicit, no security block written
        pass
    else:
        atlas_pick = None
        if "poisonable" in hz:
            offensive = a.get("atlas_offensive", True)
            atlas_pick = {
                "techniques": a.get("atlas_techniques", ["AML.T0019", "AML.T0020"]),
                "mitigations_applied": a.get("atlas_mitigations", []),
                "note": a.get("atlas_note", ""),
            }
            labels["atlas"] = atlas_pick
            labels.setdefault("hazard_class", []).append(
                "poisoned-dataset" if offensive else "adversarial-benchmark")
            labels["tlp"] = "AMBER" if offensive else "GREEN"
            sec.setdefault("level", 1)
            sec.setdefault("classification", "restricted" if offensive else "sensitive")

        weaponisable = hz & {"crypto_exploitable", "exploit_code", "credentials", "side_channel"}
        if weaponisable:
            if a.get("level3_test") is True:
                sec.update({"classification": "dual-use", "level": 3,
                            "acknowledge_required": True, "chain_of_custody": True})
                labels["tlp"] = "AMBER+STRICT"
                sec["embargo_until"] = a.get("embargo_until", "")
                if not sec["embargo_until"] or not is_iso_date(sec["embargo_until"]):
                    warnings.append("Level 3 selected but no valid embargo_until date")
                sec["contact_orcid"] = a.get("contact_orcid", "")
                if not sec["contact_orcid"]:
                    warnings.append("Level 3 requires a VERIFIED contact_orcid before add() will accept it")
                if a.get("cwe"):
                    labels["cwe"] = list(a["cwe"])
                if a.get("cvss"):
                    labels["cvss"] = a["cvss"]
                if a.get("cve_id"):
                    labels["cve_id"] = a["cve_id"]
                for h in ("crypto-attack-vector" if "crypto_exploitable" in hz else None,
                          "exploit-code" if "exploit_code" in hz else None,
                          "credential-dump" if "credentials" in hz else None,
                          "side-channel-measurement" if "side_channel" in hz else None):
                    if h:
                        labels.setdefault("hazard_class", []).append(h)
            else:
                sec.setdefault("classification", "restricted")
                sec.setdefault("level", 2)
                labels.setdefault("tlp", "AMBER")
                sec.setdefault("contact_orcid", a.get("contact_orcid", ""))

        if "credentials" in hz:
            sec["level"] = max(int(sec.get("level", 0)), 1)
            labels.setdefault("hazard_class", []).append("credential-dump")
            if not a.get("lawful_basis"):
                warnings.append("credential/breach data selected but no lawful_basis stated")

        if "prepub_vuln" in hz and int(sec.get("level", 0)) < 2:
            sec.setdefault("classification", "restricted")
            sec["level"] = max(int(sec.get("level", 0)), 2)
            labels.setdefault("tlp", "AMBER")
            labels.setdefault("hazard_class", []).append("pre-publication-vuln")

    if a.get("scan"):
        labels["scan"] = a["scan"]   # report-don't-block; never blocks the build

    if labels.get("hazard_class"):
        labels["hazard_class"] = sorted(set(labels["hazard_class"]))
    if labels:
        sec["labels"] = labels
    if sec:
        sec.setdefault("warning", a.get("warning", _default_warning(sec)))
        doc["security"] = sec

    # ── Step D ──
    listing = a.get("seed_listing", "off")
    if labels.get("tlp", "CLEAR") != "CLEAR":
        listing = "off"
    doc["distribution"] = {"seed_listing": listing, "trackers": a.get("trackers", [])}

    # validate what we produced (fail-closed, same path as add())
    try:
        _ptfile.parse(__import__("json").dumps(doc))
    except PtError as e:
        warnings.append(f"produced file does not validate: {e.detail}")

    return {"ptorrent": doc, "warnings": warnings}


def _default_warning(sec: dict) -> str:
    lvl = sec.get("level", 0)
    return (f"This dataset is classified {sec.get('classification', 'sensitive')} "
            f"(level {lvl}). " + (
                "A competent attacker could use it to construct a working exploit. "
                "Access is ORCID-acknowledged and recorded on the PTorrent custody chain."
                if lvl >= 3 else
                "Handle per its TLP marking; do not redistribute outside its scope."))


def _slug(s: str) -> str:
    from ._util import slugify
    return slugify(s, 32)


def _fail(msg: str):
    raise PtError(PtErr.E_INVAL, msg)
