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
  1. evaluation.j_col                    — single column that is already the ratio
  2. evaluation.j_num_col / j_den_col    — divide two columns
  3. evaluation.j_expr                   — portable arithmetic expression (researcher-defined)
  4. evaluation.fn                       — named function dispatch (complex dataset logic)
  5. Fallback: row['value']              — adapter's primary measurement

j_expr is a safe arithmetic expression over row column names:
  e.g. "sqrt(pmra**2 + pmdec**2) / max(parallax, 0.001)"
Allowed: +, -, *, /, **, sqrt, abs, max, min, log, log10, exp, pi, e
Column names are bound from row['raw'] then row. j_expr lives in the ptorrent file
so any researcher can read the evaluation method without external code.

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

# Restricted namespace for j_expr evaluation — arithmetic + basic math only.
# __builtins__ is empty so no module access or class hierarchy attacks.
_SAFE_MATH: dict = {
    "__builtins__": {},
    "sqrt": math.sqrt,
    "abs": abs,
    "max": max,
    "min": min,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "pi": math.pi,
    "e": math.e,
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
      3. ev_spec['j_expr']              portable arithmetic expression (researcher-defined)
      4. ev_spec['fn'] dispatch         named function for known datasets
      5. row['value']                   adapter primary measurement
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

    # 3. Portable expression — researcher-defined, lives in the ptorrent file.
    # Evaluated with a restricted namespace: arithmetic + basic math only.
    j_expr = ev_spec.get("j_expr")
    if j_expr:
        ns = dict(_SAFE_MATH)
        all_vals: dict = {}
        all_vals.update(row)
        all_vals.update(raw)  # raw overrides row for column names
        for k, v in all_vals.items():
            if k not in ns:
                try:
                    ns[k] = float(v)
                except (TypeError, ValueError):
                    pass
        try:
            result = eval(j_expr, {"__builtins__": {}}, ns)  # noqa: S307
            if result is not None:
                fv = float(result)
                if math.isfinite(fv) and fv > 0.0:
                    return fv
        except Exception:
            pass

    # 4. Named function dispatch
    fn_name = ev_spec.get("fn", "")
    if fn_name:
        j = _named_fn(fn_name, row, raw, ev_spec)
        if j is not None:
            return j

    # 5. Adapter primary measurement
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
        # 2MASS / GAIA: J = observed_flux / reference_flux
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
        v = row.get("value")
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass

    elif fn_name == "σ_face_s16":
        # GAIA DR3: J = kinematic energy proxy from astrometry.
        # J = sqrt(pmra² + pmdec²) / max(parallax, 0.001)
        # → large for nearby fast stars (disk, σ=1)
        # → small for distant slow halo stars
        # bp_rp color as fallback proxy.
        pmra  = raw.get("pmra")  or raw.get("PMRA")
        pmdec = raw.get("pmdec") or raw.get("PMDEC")
        plx   = raw.get("parallax") or raw.get("PARALLAX")
        if pmra is not None and pmdec is not None:
            try:
                pm_tot = math.sqrt(float(pmra)**2 + float(pmdec)**2)
                if plx is not None:
                    d_plx = max(abs(float(plx)), 0.001)
                    return pm_tot / d_plx
                return pm_tot / 10.0  # no parallax: normalize to typical
            except (TypeError, ValueError):
                pass
        # Color fallback: bp_rp → hot=blue=small, cool=red=large
        bprp = raw.get("bp_rp") or raw.get("BP_RP")
        if bprp is not None:
            try:
                return max(0.05, (float(bprp) + 1.0) / 2.5)
            except (TypeError, ValueError):
                pass

    elif fn_name == "σ_face_multiband":
        # 2MASS: J = j_m / k_m (linear flux ratio from magnitude difference)
        # Vera Rubin LSST: J = (u + g) / (i + z) — blue-to-red flux average
        # J/K ratio: J_flux/K_flux = 10^((k_m - j_m)/2.5)
        j_m = raw.get("j_m") or raw.get("J_m")
        k_m = raw.get("k_m") or raw.get("K_m")
        if j_m is not None and k_m is not None:
            try:
                jf, kf = float(j_m), float(k_m)
                if kf != 0.0:
                    # mag difference → flux ratio
                    return 10.0 ** ((kf - jf) / 2.5)
            except (TypeError, ValueError):
                pass
        # Vera Rubin LSST: u/g/r/i/z/y nJy fluxes
        u_f = raw.get("u") or raw.get("u_flux")
        y_f = raw.get("y") or raw.get("y_flux")
        if u_f is not None and y_f is not None:
            try:
                uf, yf = float(u_f), float(y_f)
                if yf > 0.0 and uf > 0.0:
                    return uf / yf   # blue/red ratio
            except (TypeError, ValueError):
                pass
        # Generic two-band ratio from value
        v = row.get("value")
        if v is not None:
            try:
                return max(0.01, float(v))
            except (TypeError, ValueError):
                pass

    elif fn_name == "σ_face_black_hole":
        # EHT M87: J = visibility amplitude normalized to mean
        # High-amplitude coherent signal → ring structure → σ=2→∞ transition
        vr = raw.get("visibility_real") or raw.get("vis_real") or raw.get("re")
        vi = raw.get("visibility_imag") or raw.get("vis_imag") or raw.get("im")
        if vr is not None and vi is not None:
            try:
                amp = math.sqrt(float(vr)**2 + float(vi)**2)
                # Normalize: typical EHT amplitudes 0.01–10 Jy
                # J=1 at the ring boundary
                return amp / 1.0
            except (TypeError, ValueError):
                pass
        # Brightness temperature proxy
        for k in ("T_b", "Tb", "brightness_temperature", "flux"):
            t = raw.get(k)
            if t is not None:
                try:
                    tb = float(t)
                    if tb > 0.0:
                        return tb / 1e9  # normalize to ~1 at ring
                except (TypeError, ValueError):
                    pass

    elif fn_name == "σ_face_cmb_peaks":
        # Planck CMB: J = C_l / sigma_C_l  (S/N per multipole)
        # High S/N acoustic peaks → σ=1 (mass assembly at recombination)
        cl      = raw.get("C_l") or raw.get("Cl") or raw.get("power")
        sigma_l = raw.get("sigma_C_l") or raw.get("sigma_Cl") or raw.get("error")
        if cl is not None and sigma_l is not None:
            try:
                cv, sv = float(cl), float(sigma_l)
                if sv > 0.0:
                    return abs(cv) / sv
            except (TypeError, ValueError):
                pass
        # Fallback: C_l absolute value normalized to typical scale (~3000 μK²)
        if cl is not None:
            try:
                return abs(float(cl)) / 3000.0
            except (TypeError, ValueError):
                pass

    elif fn_name == "σ_face_cmb_residual":
        # Planck/WMAP residual: J = C_l / C_l_ΛCDM
        for num_k in ("C_l", "Cl", "power_obs"):
            for den_k in ("C_l_LCDM", "Cl_LCDM", "power_lcdm"):
                n = raw.get(num_k)
                d = raw.get(den_k)
                if n is not None and d is not None:
                    try:
                        nd, dd = float(n), float(d)
                        if dd != 0.0:
                            return abs(nd) / abs(dd)
                    except (TypeError, ValueError):
                        pass

    elif fn_name == "σ_face_temperature_deviation":
        # WMAP CMB: J = |ΔT| / T_mean_pixel
        # Mean pixel T ≈ 2725 mK. ΔT fluctuations ≈ 0.1 mK → J ≈ 3.7e-5
        # Scale so J=1 at ΔT = σ (1 standard deviation ≈ 0.07 mK)
        # J = |ΔT_mK| / 0.07  → peaks at σ=½ near 1σ deviations
        for k in ("temperature_K", "T", "temp", "signal", "value"):
            t = raw.get(k) or row.get(k)
            if t is not None:
                try:
                    tv = float(t)
                    # If clearly in Kelvin range (~2.725), extract deviation
                    if abs(tv) > 1.0:
                        dev_mK = abs(tv - 2725.0)  # deviation from mean in mK
                    else:
                        dev_mK = abs(tv) * 1000.0  # already a deviation in K
                    return max(0.001, dev_mK / 0.07)
                except (TypeError, ValueError):
                    pass

    elif fn_name == "σ_face_signal":
        # SETI Breakthrough: J = signal power / noise floor proxy
        # Power in dB: J = 10^(power_dB / 10) / reference
        # Narrowband coherent signal → high J → σ=½ or σ=1
        power_db = raw.get("power_dB") or raw.get("power") or raw.get("snr")
        if power_db is not None:
            try:
                pv = float(power_db)
                # dB to linear, normalized: 0 dB → J=1
                return max(0.001, 10.0 ** (pv / 10.0))
            except (TypeError, ValueError):
                pass
        # Frequency/drift-rate structure: drift rate × bandwidth → coherence proxy
        drift = raw.get("drift_rate") or raw.get("driftRate")
        freq  = raw.get("frequency_Hz") or raw.get("frequency")
        if drift is not None and freq is not None:
            try:
                dr = abs(float(drift))
                fv = abs(float(freq))
                if fv > 0.0:
                    return max(0.001, dr / fv * 1e6)  # normalized coherence
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
    # j_expr_cols are declared by the researcher alongside j_expr
    for col in ev_spec.get("j_expr_cols", []):
        needed.append(col)

    # For named functions, add their known columns
    fn = ev_spec.get("fn", "")
    _FN_COLS = {
        "σ_face_bao_residual":           ["D_M", "r_drag"],
        "σ_face_rotation_curve":         ["Vobs", "Vbar"],
        "σ_face_spectral":               ["peak_flux", "continuum"],
        "σ_face_cmb_residual":           ["C_l", "C_l_LCDM"],
        "σ_face_photometric":            ["flux_obs", "flux_ref"],
        "σ_face_s16":                    ["pmra", "pmdec", "parallax", "bp_rp"],
        "σ_face_multiband":              ["j_m", "h_m", "k_m"],
        "σ_face_black_hole":             ["visibility_real", "visibility_imag"],
        "σ_face_cmb_peaks":              ["C_l", "sigma_C_l"],
        "σ_face_temperature_deviation":  ["temperature_K"],
        "σ_face_signal":                 ["power_dB", "frequency_Hz", "drift_rate"],
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
