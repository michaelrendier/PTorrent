"""Wizard model: the four-tab field ladder and the mapping to a `.ptorrent`
document via the core's authoritative `wizard.build`.

All help text is Unicode so the maths reads on one line. Editable field *values*
stay ASCII — the core's j_expr parser wants `sqrt`, `**`, `<=`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from ..common import mathtext as MT

# core (authoritative builder + vocab). Loaded lazily so sys.path can be arranged
# first; the wizard still previews (with a warning) if the core is unreachable.
_cw = _red = _lab = None
_CORE = False


def _load_core() -> bool:
    global _cw, _red, _lab, _CORE
    if _CORE:
        return True
    try:
        from ptorrent_core import wizard as cw
        from ptorrent_core import reductions as red
        from ptorrent_core import labels as lab
        _cw, _red, _lab, _CORE = cw, red, lab, True
    except Exception:  # noqa: BLE001
        _CORE = False
    return _CORE


_load_core()

TABULAR_FN = {
    "σ_face_bao_residual":  "D_M / r_drag  —  BAO distance vs sound horizon",
    "σ_face_rotation_curve": "V_obs / V_bar  —  rotation vs baryonic mass",
    "σ_face_spectral":      "peak_flux / continuum  —  line strength",
    "σ_face_photometric":   "flux_obs / flux_ref  —  photometric ratio",
    "σ_face_multiband":     "10^((k_m − j_m)/2.5)  —  colour / flux ratio",
    "σ_face_cmb_residual":  "C_l / C_l_ΛCDM  —  CMB power residual",
    "σ_face_cmb_peaks":     "|C_l| / σ_C_l  —  acoustic-peak S/N",
}
IMAGE_FN = dict(_red.IMAGE_FN_HELP) if _CORE else {
    "img_brightness_ratio":     "mean(foreground)/mean(background), Otsu split",
    "img_foreground_area_ratio": "foreground px / background px",
    "img_entropy_ratio":        "Shannon entropy(histogram) / log₂(bins), in [0,1]",
    "img_edge_density_ratio":   "edge px / interior px  (Sobel > threshold)",
    "img_gradient_energy_ratio": "Σ|∇I| / Σ I",
}

HAZARDS = list((_cw.HAZARDS if _CORE else {
    "crypto_exploitable": "reveals exploitable structure in a deployed crypto system",
    "exploit_code":       "contains exploit code / malware / attack tooling",
    "credentials":        "contains credentials, keys, or breach data",
    "poisonable":         "poisonable training/eval set, or a known-poisoned dataset",
    "side_channel":       "side-channel / HSM / hardware-attack measurements",
    "prepub_vuln":        "pre-publication vulnerability research",
}).items())

TLP_VALUES = ["CLEAR", "GREEN", "AMBER", "AMBER+STRICT", "RED"]
COLORS = ["gold", "blue", "red", "green", "purple", "cyan", "orange", "silver"]
JOB_TYPES = ["corpus", "dataset", "evaluation", "phonebook", "transfer"]
LICENSES = ["", "CC-BY-4.0", "CC0-1.0", "public domain", "ODbL-1.0",
            "MIT", "Apache-2.0", "other"]
PROVENANCE_KINDS = ["orcid-session", "oauth", "institutional", "api-key", "none"]


@dataclass
class Field:
    key: str
    label: str
    kind: str                     # text int float choice multi toggle list info action
    help: str = ""
    choices: list = field(default_factory=list)
    default: Any = ""
    required: bool = False
    visible: Callable[[dict], bool] = lambda a: True
    columns: list = field(default_factory=list)
    action: str = ""


def _eval_enabled(a: dict) -> bool:
    return a.get("type") == "evaluation" or a.get("enable_eval", False)


def _alg(a: dict) -> str:
    return a.get("eval_alg", "j_expr")


DATASET_TAB = [
    Field("name", "Job name", "text", required=True,
          help="Human-readable name. Also the phonebook display name and the "
               "default bin slug."),
    Field("type", "Job type", "choice", choices=JOB_TYPES, default="corpus",
          help="corpus / transfer → seed a bin.   dataset → pull structured data.   "
               "evaluation → run a reduction in situ, keep only the .peval.   "
               "phonebook → record where a dataset lives."),
    Field("color", "Card colour", "choice", choices=COLORS, default="cyan",
          help="Accent colour for the job card in every face."),
    Field("description", "Description", "text",
          help="One sentence: what this file does or describes."),
    Field("primary_tags", "Primary tags", "text",
          help="Comma-separated semantic domain tags  (PHYSICS, RIEMANN, …)."),
    Field("bin", "Output bin", "text",
          visible=lambda a: a.get("type") in ("corpus", "transfer"),
          help="Checkpoint filename. Blank → monad_<slug>.bin."),
    Field("dataset_url", "Dataset home URL", "text",
          help="Canonical page for the dataset. Seeds the phonebook entry. "
               "Required for a phonebook job."),
    Field("seeds", "Seed URLs", "list", columns=["tag", "url"],
          help="↵ to edit. Each row: a tag and a crawl start URL. "
               "Not needed for a phonebook-only job."),
    Field("license", "License (SPDX)", "choice", choices=LICENSES,
          help="SPDX id of the dataset's license, for the phonebook entry."),
    Field("citation", "Citation / DOI", "text",
          help="DOI or BibTeX key to cite this dataset."),
    Field("seed_listing", "Advertise my seeds", "choice",
          choices=["off", "opt-in"], default="off",
          help="off (default): hold + serve, but never appear in the phonebook "
               "live-seed list.   opt-in: allow listing (still needs your own "
               "per-peer consent and TLP:CLEAR)."),
]

CRAWLER_TAB = [
    Field("resolution", "Resolution ladder", "multi",
          choices=["declared_api", "known_api", "sitemap", "feed", "html"],
          default=["declared_api", "known_api", "sitemap", "feed", "html"],
          help="Order tried per seed. Space toggles a rung; the enabled set is "
               "tried left → right. 'api first' = keep declared_api / known_api on top."),
    Field("follow", "Follow links", "choice", choices=["none", "listed", "links"],
          default="none",
          help="none: seeds + declared APIs + sitemap only.   listed: follow ⟨a⟩ "
               "matching scope.allow_paths.   links: all in-scope links."),
    Field("max_pages", "Max pages", "int", default=500,
          help="Hard cap on fetched URLs for this job."),
    Field("max_depth", "Max depth", "int", default=0,
          help="0 = seeds only. Raised only with follow ≠ none."),
    Field("same_host_only", "Same host only", "toggle", default=True,
          help="Restrict the crawl to the hosts of the seed URLs."),
    Field("ua", "User-Agent", "text",
          default="Mozilla/5.0 (compatible; PtorrentBot/1.0; +https://github.com/michaelrendier/PTorrent)",
          help="Wire UA. Lead with Mozilla/5.0 for server compatibility but keep "
               "'compatible; ⟨token⟩;' so robots.txt can target you."),
    Field("respect_robots", "Respect robots.txt", "toggle", default=True,
          help="Always honoured for a locally-authored job. A job that arrives "
               "from a peer cannot switch this off."),
    Field("on_robots_unreachable", "If robots.txt unreachable", "choice",
          choices=["allow", "deny"], default="allow",
          help="What to do when robots.txt does not load. Either way the item "
               "records which."),
    Field("default_delay_s", "Default delay (s)", "float", default=1.0,
          help="Per-host wait when robots.txt states no Crawl-delay."),
    Field("max_concurrent_per_host", "Concurrency / host", "int", default=1,
          help="1 is true politeness."),
    Field("global_concurrency", "Global concurrency", "int", default=8,
          help="Parallelism across all hosts."),
    Field("timeout_s", "HTTP timeout (s)", "int", default=15, help="Per request."),
    Field("max_bytes_per_page", "Max bytes / page", "int", default=2_000_000,
          help="Body cap per fetch."),
    Field("conditional", "Conditional GET (ETag)", "toggle", default=True,
          help="Send If-None-Match / If-Modified-Since; a 304 → OK_UNCHANGED, no "
               "re-fetch. Cheap overnight re-runs."),
    Field("range_resume", "Range resume", "toggle", default=True,
          help="Continue an interrupted large GET."),

    Field("_eval_hdr", "── In-situ evaluation ──", "info",
          help="Run a reduction against each record as it streams past and keep "
               "only the σ-face tally + the .peval. This is how you evaluate "
               "196 GB you never download."),
    Field("enable_eval", "Enable in-situ evaluation", "toggle", default=False,
          visible=lambda a: a.get("type") != "evaluation",
          help="Turns a corpus / dataset job into an evaluation. Forced on when "
               "job type is 'evaluation'."),
    Field("eval_alg", "Algorithm / code block", "choice",
          choices=(["j_expr", "j_col", "j_num_den"]
                   + list(TABULAR_FN) + list(IMAGE_FN)),
          default="j_expr", visible=_eval_enabled,
          help="j_expr: safe arithmetic over column names.   j_col / j_num_den: "
               "column ratio.   σ_face_*: built-in tabular reductions.   img_*: "
               "image reductions (mean / area / entropy / edge / gradient), Pillow-backed."),
    Field("j_expr", "j_expr", "text", visible=lambda a: _eval_enabled(a) and _alg(a) == "j_expr",
          help="e.g.  √(pmra² + pmdec²) / max(parallax, 0.001)   — type it ASCII: "
               "sqrt(pmra**2 + pmdec**2)/max(parallax,0.001).  Functions: sqrt abs "
               "log log10 exp · max min.  No eval(), no escape hatch."),
    Field("j_expr_cols", "j_expr columns", "text",
          visible=lambda a: _eval_enabled(a) and _alg(a) == "j_expr",
          help="Comma-separated columns the expression needs — used for TAP "
               "minimum-column selection."),
    Field("j_col", "j_col", "text", visible=lambda a: _eval_enabled(a) and _alg(a) == "j_col",
          help="A single column that is already the J-ratio."),
    Field("j_num_col", "j_num_col", "text", visible=lambda a: _eval_enabled(a) and _alg(a) == "j_num_den",
          help="Numerator column for  J = num / den."),
    Field("j_den_col", "j_den_col", "text", visible=lambda a: _eval_enabled(a) and _alg(a) == "j_num_den",
          help="Denominator column for  J = num / den."),
    Field("fn_params", "fn params", "text",
          visible=lambda a: _eval_enabled(a) and _alg(a).startswith(("σ_", "img_")),
          help="key=value pairs, comma-separated.   bins=256   edge_threshold=48"),
    Field("max_rows", "Max records", "int", default=5000, visible=_eval_enabled,
          help="Cap on records evaluated.  ≈5000 = one API rate-limit window."),
    Field("methodology", "Methodology", "text", visible=_eval_enabled,
          help="Plain-language: what you are measuring and why. Travels in the .ptorrent."),
    Field("prediction", "Prediction", "text", visible=_eval_enabled,
          help="The σ-face distribution you expect, and why."),
]

CYBER_TAB = [
    Field("hazards", "This data / its output …", "multi",
          choices=[k for k, _ in HAZARDS],
          help="Space toggles. Any selection puts the job on the security track "
               "and drives classification, level, TLP, and labels."),
    Field("level3_test", "Attacker could build a working exploit", "toggle",
          default=False,
          visible=lambda a: bool(set(a.get("hazards", [])) &
                                 {"crypto_exploitable", "exploit_code", "credentials", "side_channel"}),
          help="RDOP Level-3 test: given only this + public info, in a reasonable "
               "timeframe. Yes → dual-use, embargo + ORCID acknowledgment, no override."),
    Field("_derived", "Derived classification", "info",
          visible=lambda a: bool(a.get("hazards")),
          help="Computed by the core from your answers above. Read-only preview; "
               "the core re-derives it authoritatively on add()."),
    Field("tlp", "TLP marking (override)", "choice", choices=[""] + TLP_VALUES,
          visible=lambda a: bool(a.get("hazards")),
          help="Blank → accept the derived value. You may only RAISE it."),
    Field("embargo_until", "Embargo until (YYYY-MM-DD)", "text",
          visible=lambda a: a.get("level3_test") is True,
          help="Public-disclosure date. Hard block in preflight until it passes."),
    Field("contact_orcid", "Contact ORCID", "text",
          visible=lambda a: bool(a.get("hazards")),
          help="The responsible researcher. Required for level ≥ 2; the build "
               "will not finish a level-3 file until this resolves to VERIFIED."),
    Field("cwe", "CWE ids", "text",
          visible=lambda a: a.get("level3_test") is True,
          help="Comma-separated, e.g.  CWE-327, CWE-1240."),
    Field("cvss_vector", "CVSS vector", "text",
          visible=lambda a: a.get("level3_test") is True,
          help="e.g.  CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/…"),
    Field("cvss_score", "CVSS score", "float",
          visible=lambda a: a.get("level3_test") is True, help="0.0 – 10.0"),
    Field("atlas_techniques", "ATLAS techniques", "text",
          visible=lambda a: "poisonable" in a.get("hazards", []),
          help="Comma-separated AML.Txxxx  (default AML.T0019, AML.T0020)."),
    Field("atlas_mitigations", "ATLAS mitigations applied", "text",
          visible=lambda a: "poisonable" in a.get("hazards", []),
          help="Comma-separated AML.Mxxxx  (e.g. AML.M0007 sanitize, AML.M0014 verify)."),
    Field("atlas_offensive", "Offensive sample (vs defensive benchmark)", "toggle",
          default=True, visible=lambda a: "poisonable" in a.get("hazards", []),
          help="Offensive → TLP:AMBER, hazard 'poisoned-dataset'.   "
               "Defensive benchmark → TLP:GREEN, 'adversarial-benchmark'."),
    Field("lawful_basis", "Lawful basis", "text",
          visible=lambda a: "credentials" in a.get("hazards", []),
          help="IRB / regulatory / contractual basis for holding this data."),
    Field("_prov_hdr", "── Auth provenance bindings ──", "info",
          help="Tie each sensitive data source to how it is authenticated. Written "
               "to auth_provenance[] in the .ptorrent; the access gate uses it."),
    Field("auth_provenance", "Source → provenance", "list",
          columns=["match", "kind", "detail"],
          help="match: a path or host prefix  (s3://stpubdata/ , /media/…/Datasets/ , "
               "https://data.lsst.cloud).   kind: " + " | ".join(PROVENANCE_KINDS) +
               ".   detail: provider / slot / note."),
    Field("scan", "Run byte scan now", "toggle", default=False,
          visible=lambda a: bool(a.get("hazards")),
          help="Report-don't-block. The verdict is attached as a label whatever "
               "it says; it never blocks the build or the download."),
    Field("warning", "Warning text", "text",
          visible=lambda a: bool(a.get("hazards")),
          help="Shown before any access. Blank → a sensible default is generated."),
]

USER_TAB = [
    Field("u_name", "Full name", "text", help="For authorship / the From: header."),
    Field("u_orcid", "ORCID", "text",
          help="0000-0000-0000-0000. Checksum-validated on entry."),
    Field("u_verify", "Verify ORCID now", "action", action="verify_orcid",
          help="↵ to resolve against pub.orcid.org (needs an attached engine and "
               "a network). VERIFIED unlocks contact info, access requests, "
               "seeding TLP > CLEAR, and voting."),
    Field("u_email", "Email", "text",
          help="Becomes the From: header and the RDOP contact address."),
    Field("u_affiliation", "Affiliation", "text",
          help="Institution, or 'independent researcher'."),
    Field("u_ua", "Default crawler UA", "text",
          help="Pre-fills the Crawler tab's User-Agent for new jobs."),
    Field("u_delay", "Default politeness delay (s)", "float", default=1.0,
          help="Pre-fills the Crawler tab's default delay."),
    Field("u_smtp_host", "SMTP host", "text", help="For RDOP NOTIFY email delivery."),
    Field("u_smtp_port", "SMTP port", "int", default=587, help=""),
    Field("u_smtp_user", "SMTP user", "text", help=""),
    Field("u_keys", "API key slots set", "info",
          help="Read-only: which credential slots the environment / keystore has."),
    Field("u_save", "Save profile", "action", action="save_profile",
          help="Persist this tab to ~/.config/ptorrent/wizard_profile.json and "
               "pre-fill it on the next launch."),
    Field("u_load", "Load profile", "action", action="load_profile",
          help="Re-read the saved profile into this tab."),
]

TABS = [
    ("Dataset", DATASET_TAB),
    ("Crawler options", CRAWLER_TAB),
    ("Cybersecurity", CYBER_TAB),
    ("User information", USER_TAB),
]


# ── answers → .ptorrent (via the core's authoritative builder) ──────────────

def _csv(s: str) -> list:
    return [t.strip() for t in str(s or "").split(",") if t.strip()]


def to_build_answers(a: dict) -> dict:
    out: dict = {
        "name": a.get("name", ""),
        "type": a.get("type", "corpus"),
        "color": a.get("color", "cyan"),
        "description": a.get("description", ""),
        "primary_tags": _csv(a.get("primary_tags", "")),
        "seeds": [r for r in a.get("seeds", []) if r.get("url")],
        "hazards": list(a.get("hazards", [])),
        "trackers": [],
        "seed_listing": a.get("seed_listing", "off"),
    }
    if a.get("bin"):
        out["bin"] = a["bin"]
    crawl = {
        "resolution": a.get("resolution") or ["declared_api", "known_api", "sitemap", "feed", "html"],
        "scope": {"max_pages": int(a.get("max_pages", 500)),
                  "max_depth": int(a.get("max_depth", 0)),
                  "same_host_only": bool(a.get("same_host_only", True)),
                  "follow": a.get("follow", "none")},
        "politeness": {"ua": a.get("ua", ""),
                       "respect_robots": bool(a.get("respect_robots", True)),
                       "on_robots_unreachable": a.get("on_robots_unreachable", "allow"),
                       "default_delay_s": float(a.get("default_delay_s", 1.0)),
                       "max_concurrent_per_host": int(a.get("max_concurrent_per_host", 1)),
                       "global_concurrency": int(a.get("global_concurrency", 8))},
        "http": {"timeout_s": int(a.get("timeout_s", 15)),
                 "max_bytes_per_page": int(a.get("max_bytes_per_page", 2_000_000)),
                 "conditional": bool(a.get("conditional", True)),
                 "range_resume": bool(a.get("range_resume", True))},
    }
    out["_crawl"] = crawl

    if a.get("type") == "evaluation" or a.get("enable_eval"):
        alg = a.get("eval_alg", "j_expr")
        ev: dict = {"methodology": a.get("methodology", ""),
                    "prediction": a.get("prediction", ""),
                    "max_rows": int(a.get("max_rows", 5000))}
        if alg == "j_expr":
            ev["j_expr"] = a.get("j_expr", "")
            ev["j_expr_cols"] = _csv(a.get("j_expr_cols", ""))
        elif alg == "j_col":
            ev["j_col"] = a.get("j_col", "")
        elif alg == "j_num_den":
            ev["j_num_col"] = a.get("j_num_col", "")
            ev["j_den_col"] = a.get("j_den_col", "")
        else:
            ev["fn"] = alg
            fp = {}
            for tok in _csv(a.get("fn_params", "")):
                if "=" in tok:
                    k, v = tok.split("=", 1)
                    try:
                        fp[k.strip()] = float(v) if "." in v else int(v)
                    except ValueError:
                        fp[k.strip()] = v.strip()
            if fp:
                ev["fn_params"] = fp
        out["type"] = "evaluation"
        out["evaluation"] = ev

    if a.get("level3_test") is True:
        out["level3_test"] = True
        out["embargo_until"] = a.get("embargo_until", "")
        out["contact_orcid"] = a.get("contact_orcid", "") or a.get("u_orcid", "")
        if _csv(a.get("cwe", "")):
            out["cwe"] = _csv(a.get("cwe", ""))
        if a.get("cvss_vector"):
            out["cvss"] = {"version": "4.0", "vector": a["cvss_vector"],
                           "score": float(a.get("cvss_score", 0) or 0)}
    elif a.get("hazards"):
        out["contact_orcid"] = a.get("contact_orcid", "") or a.get("u_orcid", "")
    if "poisonable" in a.get("hazards", []):
        out["atlas_offensive"] = bool(a.get("atlas_offensive", True))
        if _csv(a.get("atlas_techniques", "")):
            out["atlas_techniques"] = _csv(a["atlas_techniques"])
        if _csv(a.get("atlas_mitigations", "")):
            out["atlas_mitigations"] = _csv(a["atlas_mitigations"])
    if a.get("lawful_basis"):
        out["lawful_basis"] = a["lawful_basis"]
    if a.get("warning"):
        out["warning"] = a["warning"]
    if a.get("tlp"):
        out["tlp_override"] = a["tlp"]
    return out


def build(a: dict) -> dict:
    """Return {ptorrent, warnings}. Uses the core builder when available."""
    _load_core()
    ba = to_build_answers(a)
    crawl_extra = ba.pop("_crawl", None)
    if _CORE:
        res = _cw.build(ba)
    else:
        res = {"ptorrent": {"ptorrent_version": "1.2",
                            **{k: v for k, v in ba.items()
                               if k in ("name", "type", "color", "description")}},
               "warnings": ["core not on path — preview only"]}
    doc = res["ptorrent"]
    if crawl_extra:
        seeds = doc.get("crawl", {}).get("seeds", [])
        doc.setdefault("crawl", {})
        doc["crawl"].update(crawl_extra)
        if seeds:
            doc["crawl"]["seeds"] = seeds
    if a.get("dataset_url"):
        doc.setdefault("phonebook", {})["dataset_url"] = a["dataset_url"]
        if a.get("type") == "phonebook":
            doc["type"] = "phonebook"
    if a.get("license"):
        doc.setdefault("phonebook", {})["license"] = a["license"]
    if a.get("citation"):
        doc.setdefault("phonebook", {})["citation"] = a["citation"]
    prov = [r for r in a.get("auth_provenance", []) if r.get("match")]
    if prov:
        doc["auth_provenance"] = prov
    if a.get("tlp") and doc.get("security", {}).get("labels"):
        doc["security"]["labels"]["tlp"] = a["tlp"]
    return {"ptorrent": doc, "warnings": res.get("warnings", [])}
