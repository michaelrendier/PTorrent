"""Chain-of-custody exporters + marking rules.

Native hash-linked JSON is authoritative. CASE/UCO is the canonical evidentiary
projection; STIX 2.1 the disclosure subset; AFF4 the container form (stub).

marking_inherit / assert_no_downgrade enforce that a derived artifact carries at
least the restrictiveness of its parent, and that a marking only ever drops via
a signed DISCLOSE.
"""
from __future__ import annotations

import uuid

from . import chain as _chain
from . import labels as _labels
from ._util import now_iso
from .errors import PtErr, PtError

_TLP_ORDER = {"CLEAR": 0, "GREEN": 1, "AMBER": 2, "AMBER+STRICT": 3, "RED": 4}


def marking_of(security: dict | None) -> dict:
    s = security or {}
    return {"tlp": _labels.tlp_of(s), "level": int(s.get("level", 0)),
            "labels_hash": _labels.labels_hash(s.get("labels", {}))}


def marking_inherit(parent: dict, child: dict | None) -> dict:
    """Child inherits parent; a child may only RAISE restrictiveness."""
    child = child or {}
    p_tlp = parent.get("tlp", "CLEAR")
    c_tlp = child.get("tlp", p_tlp)
    tlp = c_tlp if _TLP_ORDER.get(c_tlp, 0) >= _TLP_ORDER.get(p_tlp, 0) else p_tlp
    return {
        "tlp": tlp,
        "level": max(int(parent.get("level", 0)), int(child.get("level", 0))),
        "labels_hash": child.get("labels_hash") or parent.get("labels_hash", ""),
    }


def assert_no_downgrade(old: dict, new: dict, *, disclose_signed: bool) -> None:
    if disclose_signed:
        return
    if _TLP_ORDER.get(new.get("tlp", "CLEAR"), 0) < _TLP_ORDER.get(old.get("tlp", "CLEAR"), 0) \
       or int(new.get("level", 0)) < int(old.get("level", 0)):
        raise PtError(PtErr.E_MARKING_DOWNGRADE,
                      f"{old.get('tlp')}/L{old.get('level')} -> {new.get('tlp')}/L{new.get('level')}")


# ── exporters ──────────────────────────────────────────────────────────────

def export_native(chain: "_chain.CustodyChain") -> dict:
    return chain.export_native()


def _stix_id(t: str) -> str:
    return f"{t}--{uuid.uuid4()}"


_TLP_MARKING_IDS = {
    # STIX 2.1 predefined TLP marking-definition ids
    "CLEAR": "marking-definition--94868c89-83c2-464b-929b-a1a8aa3c8487",
    "GREEN": "marking-definition--bab4a63c-aed9-4cf5-a766-dfca5abac2bb",
    "AMBER": "marking-definition--55d920b0-5e8b-4f79-9ee9-91f868d9b421",
    "AMBER+STRICT": "marking-definition--939a9414-2ddd-4d32-a0cd-375ea402b003",
    "RED": "marking-definition--e828b379-4e03-4974-9ac4-e53a884c97c1",
}


def export_stix(chain: "_chain.CustodyChain", researcher: dict) -> dict:
    objects: list[dict] = [{
        "type": "identity", "spec_version": "2.1", "id": _stix_id("identity"),
        "created": now_iso(), "modified": now_iso(),
        "name": researcher.get("name", "researcher"), "identity_class": "individual",
        "external_references": [{"source_name": "ORCID",
                                 "external_id": researcher.get("orcid", ""),
                                 "url": f"https://orcid.org/{researcher.get('orcid','')}"}],
    }]
    seen_markings: set[str] = set()
    for tx in chain.all_tx():
        tlp = (tx.marking or {}).get("tlp")
        mref = _TLP_MARKING_IDS.get(tlp) if tlp else None
        if mref and mref not in seen_markings:
            seen_markings.add(mref)
            objects.append({"type": "marking-definition", "spec_version": "2.1",
                            "id": mref, "definition_type": "tlp",
                            "name": f"TLP:{tlp}"})
        obj = {
            "type": "x-ptorrent-custody", "spec_version": "2.1", "id": _stix_id("x-ptorrent-custody"),
            "created": now_iso(),
            "x_tx_type": tx.type, "x_actor": tx.actor, "x_object_hash": tx.object_hash,
            "x_parent_hash": tx.parent_hash, "x_tx_hash": tx.tx_hash, "x_note": tx.note,
        }
        if mref:
            obj["object_marking_refs"] = [mref]
        objects.append(obj)
    return {"type": "bundle", "id": _stix_id("bundle"), "spec_version": "2.1",
            "objects": objects}


def export_case(chain: "_chain.CustodyChain") -> dict:
    """Minimal CASE/UCO JSON-LD: each tx -> a ProvenanceRecord in a graph."""
    graph = []
    for tx in chain.all_tx():
        graph.append({
            "@id": f"kb:tx-{tx.tx_hash[:16]}",
            "@type": "case-investigation:ProvenanceRecord",
            "uco-core:startTime": now_iso(),
            "uco-core:description": tx.type,
            "case-investigation:exhibitNumber": tx.object_hash,
            "ptorrent:actor": tx.actor,
            "ptorrent:parentHash": tx.parent_hash,
            "ptorrent:prevHash": tx.prev_hash,
            "ptorrent:marking": tx.marking,
            "ptorrent:note": tx.note,
        })
    return {
        "@context": {
            "kb": "http://example.org/kb/",
            "case-investigation": "https://ontology.caseontology.org/case/investigation/",
            "uco-core": "https://ontology.unifiedcyberontology.org/uco/core/",
            "ptorrent": "https://github.com/michaelrendier/PTorrent/ns#",
        },
        "@graph": graph,
    }


def export_aff4(chain: "_chain.CustodyChain") -> dict:
    raise PtError(PtErr.E_UNSUPPORTED, "AFF4 container export is not implemented in this build")


def export(chain, fmt: str, researcher: dict | None = None):
    fmt = (fmt or "native").lower()
    if fmt == "native":
        return export_native(chain)
    if fmt == "stix":
        return export_stix(chain, researcher or {})
    if fmt == "case":
        return export_case(chain)
    if fmt == "aff4":
        return export_aff4(chain)
    raise PtError(PtErr.E_INVAL, f"unknown export format {fmt!r}")
