"""Fault / inconsistency collection for the wizard.

Runs the core's authoritative build plus a set of cross-field consistency checks
and returns a flat list of faults. NEVER raises — a broken core, a parse error,
a contradictory field: all become faults the caller shows in a dialog and the
researcher goes and fixes. Nothing here is fatal.

Fault = {severity: error|warning|info, tab: <tab name>, field: <field key or "">,
         message: str, hint: str}
"""
from __future__ import annotations

import re

from . import model as M

_TAB_OF: dict[str, str] = {}
for _name, _fields in M.TABS:
    for _f in _fields:
        _TAB_OF[_f.key] = _name

_CWE_RE = re.compile(r"^CWE-\d+$")
_CVSS_RE = re.compile(r"^CVSS:[34]\.\d/")
_ORCID_RE = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def tab_of(field_key: str) -> str:
    return _TAB_OF.get(field_key, "Dataset")


def _f(sev, field, msg, hint=""):
    return {"severity": sev, "tab": _TAB_OF.get(field, ""), "field": field,
            "message": msg, "hint": hint}


def _orcid_ok(v: str) -> bool:
    v = (v or "").replace("https://orcid.org/", "").strip().upper()
    if not _ORCID_RE.match(v):
        return False
    total = 0
    for ch in v.replace("-", "")[:15]:
        total = (total + int(ch)) * 2
    check = (12 - total % 11) % 11
    return ("X" if check == 10 else str(check)) == v[-1]


def _csv(s):
    return [t.strip() for t in str(s or "").split(",") if t.strip()]


def collect(answers: dict) -> list[dict]:
    a = answers
    out: list[dict] = []

    # ── run the authoritative build (never let it raise) ──
    doc = None
    try:
        res = M.build(a)
        doc = res.get("ptorrent")
        for w in res.get("warnings", []):
            out.append(_f("warning", _guess_field(w), w,
                          "from the core wizard — adjust the related field"))
    except Exception as e:  # noqa: BLE001
        out.append(_f("error", "name",
                      f".ptorrent build failed: {e}",
                      "the fields as entered do not form a valid .ptorrent"))

    # ── cross-field consistency (wizard layer) ──
    if not str(a.get("name", "")).strip():
        out.append(_f("error", "name", "job name is empty",
                      "every .ptorrent needs a name"))

    jtype = a.get("type", "corpus")
    has_source = bool([r for r in a.get("seeds", []) if r.get("url")]) or bool(a.get("dataset_url"))
    if jtype in ("corpus", "dataset", "transfer", "evaluation") and not has_source:
        out.append(_f("warning", "seeds", "no seed URLs and no dataset home URL",
                      "add at least one seed on the Dataset tab, or a dataset_url"))

    for i, r in enumerate(a.get("seeds", [])):
        u = r.get("url", "")
        if u and not re.match(r"^https?://", u):
            out.append(_f("warning", "seeds", f"seed {i} URL has no http(s):// scheme: {u!r}",
                          "prefix the URL with https://"))

    # evaluation coherence
    eval_on = jtype == "evaluation" or a.get("enable_eval")
    if eval_on:
        alg = a.get("eval_alg", "j_expr")
        if alg == "j_expr":
            expr = (a.get("j_expr") or "").strip()
            if not expr:
                out.append(_f("error", "j_expr", "evaluation is j_expr but the expression is empty",
                              "enter an arithmetic expression over column names"))
            else:
                cols = set(_csv(a.get("j_expr_cols", "")))
                names = _expr_names(expr)
                if not cols:
                    out.append(_f("warning", "j_expr_cols", "j_expr has no declared columns",
                                  "list the columns it needs for TAP minimum-column selection"))
                missing = names - cols - {"pi", "e"}
                if cols and missing:
                    out.append(_f("warning", "j_expr_cols",
                                  "j_expr uses columns not in j_expr_cols: " + ", ".join(sorted(missing)),
                                  "add them to j_expr_cols, or fix the expression"))
                bad = _expr_syntax_error(expr)
                if bad:
                    out.append(_f("error", "j_expr", f"j_expr will not parse: {bad}",
                                  "functions: sqrt abs log log10 exp max min; operators + - * / **"))
        elif alg == "j_col":
            if not (a.get("j_col") or "").strip():
                out.append(_f("error", "j_col", "evaluation is j_col but no column named", ""))
        elif alg == "j_num_den":
            if not (a.get("j_num_col") or "").strip() or not (a.get("j_den_col") or "").strip():
                out.append(_f("error", "j_num_col", "j_num_den needs both a numerator and a denominator column", ""))
        else:  # a named fn
            for tok in _csv(a.get("fn_params", "")):
                if "=" not in tok:
                    out.append(_f("warning", "fn_params",
                                  f"fn param {tok!r} is not key=value", "e.g. bins=256, edge_threshold=48"))
        if alg.startswith("img_") and not has_source:
            out.append(_f("info", "seeds", "image reduction chosen but no seeds to fetch images from", ""))

    # cybersecurity coherence
    hazards = set(a.get("hazards", []))
    if hazards:
        contact = (a.get("contact_orcid") or a.get("u_orcid") or "").strip()
        if not contact:
            out.append(_f("warning", "contact_orcid",
                          "security-relevant data but no contact ORCID",
                          "name the responsible researcher"))
        elif not _orcid_ok(contact):
            out.append(_f("warning", "contact_orcid",
                          f"contact ORCID {contact!r} fails the ISO 7064 checksum", ""))
        if a.get("level3_test") is True:
            e = (a.get("embargo_until") or "").strip()
            if not e:
                out.append(_f("error", "embargo_until",
                              "Level-3 dual-use requires an embargo date", "YYYY-MM-DD"))
            elif not _DATE_RE.match(e):
                out.append(_f("error", "embargo_until", f"embargo date {e!r} is not YYYY-MM-DD", ""))
            if not contact:
                out.append(_f("error", "contact_orcid",
                              "Level-3 will not finish without a contact ORCID", ""))
            for c in _csv(a.get("cwe", "")):
                if not _CWE_RE.match(c):
                    out.append(_f("warning", "cwe", f"{c!r} is not CWE-<n>", "e.g. CWE-327"))
            vec = (a.get("cvss_vector") or "").strip()
            if vec and not _CVSS_RE.match(vec):
                out.append(_f("warning", "cvss_vector",
                              "CVSS vector should start CVSS:3.x/ or CVSS:4.0/", ""))
        if "credentials" in hazards and not (a.get("lawful_basis") or "").strip():
            out.append(_f("warning", "lawful_basis",
                          "credential / breach data selected but no lawful basis stated", ""))
        if "poisonable" in hazards and not _csv(a.get("atlas_techniques", "")):
            out.append(_f("info", "atlas_techniques",
                          "poisoned dataset but no ATLAS technique — defaults AML.T0019 / AML.T0020", ""))
        # TLP override may only raise — compare against the value derived WITHOUT
        # the override (model.build applies the override into `doc` itself)
        ov = a.get("tlp", "")
        if ov:
            try:
                base = M.build({**a, "tlp": ""}).get("ptorrent", {})
                derived = (base.get("security", {}).get("labels", {}) or {}).get("tlp", "CLEAR")
            except Exception:  # noqa: BLE001
                derived = "CLEAR"
            order = ["CLEAR", "GREEN", "AMBER", "AMBER+STRICT", "RED"]
            if ov in order and derived in order and order.index(ov) < order.index(derived):
                out.append(_f("error", "tlp",
                              f"TLP override {ov} is lower than the derived {derived}",
                              "you may only RAISE the marking"))
    for r in a.get("auth_provenance", []):
        if r.get("match") and r.get("kind") not in M.PROVENANCE_KINDS:
            out.append(_f("warning", "auth_provenance",
                          f"provenance kind {r.get('kind')!r} not one of "
                          + " / ".join(M.PROVENANCE_KINDS), ""))

    # user info
    uo = (a.get("u_orcid") or "").strip()
    if uo and not _orcid_ok(uo):
        out.append(_f("warning", "u_orcid",
                      f"your ORCID {uo!r} fails the ISO 7064 checksum",
                      "check the digits — the last char is a MOD-11-2 check digit"))

    # errors first, then warnings, then info; stable within a group
    rank = {"error": 0, "warning": 1, "info": 2}
    out.sort(key=lambda f: rank.get(f["severity"], 3))
    return out


# ── helpers ──

def _expr_names(expr: str) -> set[str]:
    toks = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", expr))
    return toks - {"sqrt", "abs", "log", "log10", "exp", "max", "min"}


def _expr_syntax_error(expr: str) -> str:
    try:
        from ptorrent_core.jexpr import JExpr
    except Exception:  # noqa: BLE001
        return ""
    try:
        JExpr(expr)
        return ""
    except Exception as e:  # noqa: BLE001
        return str(e).split(":", 1)[-1].strip() if ":" in str(e) else str(e)


def _guess_field(msg: str) -> str:
    m = msg.lower()
    if "embargo" in m:
        return "embargo_until"
    if "contact" in m or "orcid" in m:
        return "contact_orcid"
    if "cwe" in m:
        return "cwe"
    if "cvss" in m:
        return "cvss_vector"
    if "name" in m:
        return "name"
    if "lawful" in m:
        return "lawful_basis"
    return ""
