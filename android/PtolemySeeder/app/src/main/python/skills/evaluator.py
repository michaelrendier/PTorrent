"""
skills/evaluator.py — PTorrent in-situ σ-face evaluator.

Applies Ainulindale σ-face terms to a structured dataset WITHOUT materialising
it. The evaluator traverses the source via the appropriate adapter, computes
j_ratio per row from the ptorrent's evaluation spec, tallies σ-face faces,
and writes a .peval result file.

Principle: the computation travels to the data. The data does not travel here.

Supports:
  - tap_adql : IVOA TAP/ADQL — request only needed columns, dataset stays remote
  - fits, fits_table, s3_fits : FITS streaming — process chunk by chunk
  - Any adapter mode registered in skills/adapters

J-ratio extraction from evaluation spec (in priority order):
  1. evaluation.j_col        — single column that is already the ratio
  2. evaluation.j_num_col / evaluation.j_den_col  — divide two columns
  3. evaluation.fn           — named function dispatch (known dataset types)
  4. Fallback: row['value']  — adapter's primary measurement as j_ratio

Constants (do not rederive):
  D_STAR   = 0.246                   spectral ground state / causal floor
  OMEGA_ZS = 0.5671432904097838      Lambert W(1), dark energy VEV
"""

from __future__ import annotations

import json
import math
import os
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterator, Optional

# ── Constants ──────────────────────────────────────────────────────────────────

D_STAR   = 0.246
OMEGA_ZS = 0.5671432904097838

_SIGMA_TABLE = {
    "½": "causality",
    "1": "Yang-Mills",
    "2": "gravity",
    "∞": "BH interior",
}


# ── σ-face assignment ──────────────────────────────────────────────────────────

def sigma_face(j_ratio: float) -> str:
    """
    Assign σ-face from buoyancy ratio J.

    J = observed / baryonic (or normalised equivalent per dataset).

    Thresholds (D_STAR = 0.246, OMEGA_ZS = 0.5671):
      J < D_STAR              → ∞   Fermat-forbidden void
      D_STAR ≤ J < 1          → ½   neutral buoyancy — causality intact
      1 ≤ J < 1/D_STAR        → 1   Yang-Mills — mass assembly
      1/D_STAR ≤ J < 1/D_STAR + OMEGA_ZS → 2   gravity dominated
      J ≥ 1/D_STAR + OMEGA_ZS → ∞   extreme — BH interior equivalent
    """
    if not math.isfinite(j_ratio) or j_ratio <= 0:
        return "∞"
    if j_ratio < D_STAR:
        return "∞"
    if j_ratio < 1.0:
        return "½"
    if j_ratio < 1.0 / D_STAR:           # ≈ 4.065
        return "1"
    if j_ratio < 1.0 / D_STAR + OMEGA_ZS:
        return "2"
    return "∞"


def tally(faces: list) -> dict:
    counts = {"½": 0, "1": 0, "2": 0, "∞": 0}
    for f in faces:
        counts[f] = counts.get(f, 0) + 1
    return counts


# ── J-ratio extraction ─────────────────────────────────────────────────────────

def _j_ratio_from_row(row: dict, ev_spec: dict) -> Optional[float]:
    """
    Extract J-ratio from a streamed row using the evaluation spec.

    Priority:
      1. ev_spec['j_col']               single pre-normalised column
      2. ev_spec['j_num_col'] / ev_spec['j_den_col']
      3. ev_spec['fn'] dispatch         named function for known datasets
      4. row['value']                   adapter primary measurement
    """
    raw = row.get("raw", {})

    # 1. Single J column
    j_col = ev_spec.get("j_col")
    if j_col:
        v = raw.get(j_col) or row.get(j_col)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass

    # 2. Numerator / denominator columns
    num_col = ev_spec.get("j_num_col")
    den_col = ev_spec.get("j_den_col")
    if num_col and den_col:
        num = raw.get(num_col) or row.get(num_col)
        den = raw.get(den_col) or row.get(den_col)
        if num is not None and den is not None:
            try:
                n, d = float(num), float(den)
                if d != 0.0:
                    return n / d
            except (TypeError, ValueError):
                pass

    # 3. Named function dispatch
    fn_name = ev_spec.get("fn", "")
    if fn_name:
        j = _named_fn(fn_name, row, raw, ev_spec)
        if j is not None:
            return j

    # 4. Adapter primary measurement
    v = row.get("value")
    if v is not None:
        try:
            return float(v)
        except (TypeError, ValueError):
            pass

    return None


def _named_fn(fn_name: str, row: dict, raw: dict, ev_spec: dict) -> Optional[float]:
    """Named evaluation functions for known dataset types."""

    if fn_name == "σ_face_bao_residual":
        # DESI / WMAP / Planck BAO: J = D_M / r_drag
        for num_k in ("D_M", "DM", "D_M_over_rd"):
            for den_k in ("r_drag", "rd", "R_DRAG", "r_d"):
                n = raw.get(num_k)
                d = raw.get(den_k)
                if n is not None and d is not None:
                    try:
                        nd, dd = float(n), float(d)
                        if dd != 0.0:
                            return nd / dd
                    except (TypeError, ValueError):
                        pass
        # Pre-normalised ratio columns
        for k in ("D_M_over_rd", "ratio", "j_ratio"):
            v = raw.get(k)
            if v is not None:
                try:
                    return float(v)
                except (TypeError, ValueError):
                    pass

    elif fn_name == "σ_face_rotation_curve":
        # SPARC / Vera Rubin: J = V_obs / V_bar
        for num_k in ("Vobs", "V_obs", "v_obs"):
            for den_k in ("Vbar", "V_bar", "v_bar"):
                n = raw.get(num_k)
                d = raw.get(den_k)
                if n is not None and d is not None:
                    try:
                        nd, dd = float(n), float(d)
                        if dd != 0.0:
                            return nd / dd
                    except (TypeError, ValueError):
                        pass

    elif fn_name == "σ_face_spectral":
        # JWST / EHT spectral: J = peak_flux / continuum
        for num_k in ("peak_flux", "flux_peak", "F_peak"):
            for den_k in ("continuum", "F_cont", "flux_cont"):
                n = raw.get(num_k)
                d = raw.get(den_k)
                if n is not None and d is not None:
                    try:
                        nd, dd = float(n), float(d)
                        if dd != 0.0:
                            return nd / dd
                    except (TypeError, ValueError):
                        pass

    elif fn_name == "σ_face_cmb_residual":
        # Planck / WMAP CMB: J = C_l_obs / C_l_ΛCDM
        for num_k in ("C_l", "Cl", "power_obs"):
            for den_k in ("C_l_LCDM", "Cl_LCDM", "power_lcdm"):
                n = raw.get(num_k)
                d = raw.get(den_k)
                if n is not None and d is not None:
                    try:
                        nd, dd = float(n), float(d)
                        if dd != 0.0:
                            return nd / dd
                    except (TypeError, ValueError):
                        pass

    elif fn_name == "σ_face_photometric":
        # 2MASS / GAIA: J = observed_mag / expected_mag (ratio in linear flux)
        for num_k in ("flux_obs", "F_obs", "flux"):
            for den_k in ("flux_ref", "F_ref", "flux_expected"):
                n = raw.get(num_k)
                d = raw.get(den_k)
                if n is not None and d is not None:
                    try:
                        nd, dd = float(n), float(d)
                        if dd != 0.0:
                            return nd / dd
                    except (TypeError, ValueError):
                        pass
        # Fallback: use raw value as J directly
        v = row.get("value")
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass

    return None


# ── Source prep: request only needed columns ──────────────────────────────────

def _prep_source(source: dict, ev_spec: dict) -> dict:
    """
    Return a source dict that requests only the columns needed for J-ratio.
    Never requests more than necessary — the in-situ minimum.
    """
    src = dict(source)

    # Collect the column names we actually need
    needed: list = []
    if ev_spec.get("j_col"):
        needed.append(ev_spec["j_col"])
    if ev_spec.get("j_num_col"):
        needed.append(ev_spec["j_num_col"])
    if ev_spec.get("j_den_col"):
        needed.append(ev_spec["j_den_col"])

    # For named functions, add their known columns
    fn = ev_spec.get("fn", "")
    _FN_COLS = {
        "σ_face_bao_residual":    ["D_M", "r_drag"],
        "σ_face_rotation_curve":  ["Vobs", "Vbar"],
        "σ_face_spectral":        ["peak_flux", "continuum"],
        "σ_face_cmb_residual":    ["C_l", "C_l_LCDM"],
        "σ_face_photometric":     ["flux_obs", "flux_ref"],
    }
    if fn in _FN_COLS:
        needed.extend(_FN_COLS[fn])

    # Apply to TAP source as SELECT columns — minimum data movement
    if src.get("mode") == "tap_adql" and needed and not src.get("query"):
        src["columns"] = list(dict.fromkeys(needed))  # deduplicate, order-preserving

    return src


# ── .peval writer ─────────────────────────────────────────────────────────────

def _write_peval(
    name: str,
    dataset: str,
    bin_name: str,
    faces: list,
    ev_spec: dict,
    row_count: int,
    errors: list,
    out_path: str,
    elapsed: float,
) -> dict:
    counts  = tally(faces)
    total   = sum(counts.values())
    fracs   = {f: round(counts[f] / total, 4) if total else 0.0
               for f in counts}

    # σ=½ fraction is the Ainulindale prediction
    half_frac = fracs.get("½", 0.0)

    result = {
        "ptorrent_version": "1.0",
        "peval_version":    "1.0",
        "name":             name,
        "dataset":          dataset,
        "bin_name":         bin_name,
        "timestamp":        datetime.now(timezone.utc).isoformat(),
        "elapsed_s":        round(elapsed, 2),
        "row_count":        row_count,
        "face_counts":      counts,
        "face_fractions":   fracs,
        "sigma_half_frac":  half_frac,
        "prediction":       ev_spec.get("prediction", ""),
        "sigma_table":      ev_spec.get("σ_table", _SIGMA_TABLE),
        "ainulindale": {
            "D_STAR":   D_STAR,
            "OMEGA_ZS": OMEGA_ZS,
            "SIGMA":    0.5,
            "pass":     half_frac >= 0.5,
        },
        "errors": errors[:20],  # cap error list
    }

    os.makedirs(os.path.dirname(out_path) if os.path.dirname(out_path) else ".",
                exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return result


# ── EvaluationRunner ──────────────────────────────────────────────────────────

class EvaluationRunner:
    """
    In-situ σ-face evaluator for PTorrent evaluation-type jobs.

    Traverses the source dataset without materialising it.
    Computes σ-face per row using the evaluation spec's J-ratio formula.
    Writes a .peval result file.
    """

    def __init__(
        self,
        entry: dict,
        files_dir: str,
        on_progress: Optional[Callable] = None,
        max_rows: int = 50_000,
    ):
        self.entry       = entry
        self.files_dir   = files_dir
        self.on_progress = on_progress or (lambda *a, **kw: None)
        self.max_rows    = max_rows

    def run(self) -> dict:
        """Execute the evaluation. Returns result dict."""
        entry    = self.entry
        name     = entry.get("name", "unnamed")
        ev_spec  = entry.get("evaluation", {})
        dm       = entry.get("data_model", {})
        source   = dict(dm.get("access", {}))
        bin_name = entry.get("requires_bin", entry.get("bin", ""))
        out_name = entry.get("output", name.replace(" ", "_") + ".peval")
        out_path = os.path.join(self.files_dir, out_name)

        # Merge source-level fields from ptorrent source block
        source_block = entry.get("source", {})
        for k, v in source_block.items():
            if k not in source:
                source[k] = v

        # Determine adapter mode
        mode = source.get("mode") or dm.get("native_format", "").lower()
        if not mode:
            return {"complete": False, "error": "no adapter mode in data_model.access"}

        # Prep source: request only needed columns
        source = _prep_source(source, ev_spec)

        # Inject max_rows limit
        source.setdefault("max_rows", self.max_rows)

        # Load adapter
        from skills.adapters import get_adapter
        try:
            adapter = get_adapter(source)
        except ValueError as e:
            return {"complete": False, "error": str(e)}

        t0     = time.time()
        faces  = []
        errors = []
        count  = 0

        try:
            for row in adapter.stream_rows(source):
                j = _j_ratio_from_row(row, ev_spec)
                if j is None:
                    errors.append(f"row {count}: j_ratio=None, raw_keys={list(row.get('raw', {}).keys())[:6]}")
                    count += 1
                    continue

                faces.append(sigma_face(j))
                count += 1

                if count % 500 == 0:
                    self.on_progress(
                        name, "EVALUATE", source.get("endpoint", ""),
                        count, self.max_rows, count, len(errors)
                    )

                if count >= self.max_rows:
                    break

        except Exception as e:
            errors.append(f"stream error: {e}")

        elapsed = time.time() - t0

        if not faces:
            return {
                "complete": False,
                "error": f"no rows yielded j_ratio (rows_attempted={count})",
                "errors": errors[:5],
            }

        result = _write_peval(
            name     = name,
            dataset  = source.get("endpoint", source.get("url", "unknown")),
            bin_name = bin_name,
            faces    = faces,
            ev_spec  = ev_spec,
            row_count = count,
            errors   = errors,
            out_path = out_path,
            elapsed  = elapsed,
        )
        result["complete"] = True
        result["peval_path"] = out_path
        return result
