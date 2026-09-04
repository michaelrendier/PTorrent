"""In-situ σ-face evaluator — de-monad'd.

Adapted from android/PtolemySeeder/app/src/main/python/skills/evaluator.py
(Cody Michael Allison, LGPL-3.0-or-later). Changes:
  * j_expr goes through jexpr.JExpr (recursive-descent, NO eval())
  * σ assignment uses sigma.classify -> non-finite J is UNDEFINED, not ∞
  * consumes an iterable of row dicts (the crawler's CrawlResult.rows, or an
    adapter) — the data never materialises here
"""
from __future__ import annotations

import math
from typing import Callable, Iterable

from . import reductions as _reductions
from . import sigma as _sigma
from ._util import now_iso
from .jexpr import JExpr
from .errors import PtErr, PtError


def _num(v):
    try:
        f = float(v)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def _fn_ratio(fn: str, raw: dict):
    """A compact port of the common named handlers. Unknown fn -> None."""
    pairs = {
        "σ_face_bao_residual": (("D_M", "DM"), ("r_drag", "rd", "r_d")),
        "σ_face_rotation_curve": (("Vobs", "V_obs", "v_obs"), ("Vbar", "V_bar", "v_bar")),
        "σ_face_spectral": (("peak_flux", "F_peak"), ("continuum", "F_cont")),
        "σ_face_cmb_residual": (("C_l", "Cl", "power_obs"), ("C_l_LCDM", "Cl_LCDM", "power_lcdm")),
        "σ_face_photometric": (("flux_obs", "F_obs", "flux"), ("flux_ref", "F_ref")),
    }
    if fn in pairs:
        nums, dens = pairs[fn]
        n = next((raw[k] for k in nums if k in raw), None)
        d = next((raw[k] for k in dens if k in raw), None)
        n, d = _num(n), _num(d)
        if n is not None and d not in (None, 0.0):
            return n / d
    if fn == "σ_face_multiband":
        jm, km = _num(raw.get("j_m") or raw.get("J_m")), _num(raw.get("k_m") or raw.get("K_m"))
        if jm is not None and km is not None:
            return 10.0 ** ((km - jm) / 2.5)
    if fn == "σ_face_cmb_peaks":
        cl = _num(raw.get("C_l") or raw.get("Cl") or raw.get("power"))
        sig = _num(raw.get("sigma_C_l") or raw.get("error"))
        if cl is not None and sig not in (None, 0.0):
            return abs(cl) / sig
    return None


class Evaluator:
    def __init__(self, pf):
        self.pf = pf
        self.ev = pf.evaluation or {}
        self._expr = None
        if self.ev.get("j_expr"):
            self._expr = JExpr(self.ev["j_expr"])

    @property
    def is_image_fn(self) -> bool:
        return self.ev.get("fn", "") in _reductions.IMAGE_FN

    def required_columns(self) -> list[str]:
        cols = list(self.ev.get("j_expr_cols", []))
        for k in ("j_col", "j_num_col", "j_den_col"):
            if self.ev.get(k):
                cols.append(self.ev[k])
        if self._expr:
            cols.extend(self._expr.variables)
        return sorted(set(cols))

    def j_ratio(self, row: dict):
        raw = row.get("raw", row) if isinstance(row, dict) else {}
        raw = raw or row
        ev = self.ev
        if ev.get("j_col"):
            v = _num(raw.get(ev["j_col"]))
            if v is not None:
                return v
        if ev.get("j_num_col") and ev.get("j_den_col"):
            n, d = _num(raw.get(ev["j_num_col"])), _num(raw.get(ev["j_den_col"]))
            if n is not None and d not in (None, 0.0):
                return n / d
        if self._expr:
            b = {k: _num(v) for k, v in raw.items()}
            try:
                return self._expr.eval(b)
            except PtError as e:
                if e.code == PtErr.E_NOTFOUND:
                    raise
                return math.nan
        if ev.get("fn"):
            return _fn_ratio(ev["fn"], raw)
        return _num(row.get("value")) if isinstance(row, dict) else None

    def run_images(self, urls: Iterable[str], fetch: Callable[[str], bytes | None], *,
                   max_rows: int = 5_000, on_acquire=None, on_progress=None) -> dict:
        """Image / binary reduction path. `fetch(url) -> bytes|None` is robots-gated
        upstream. Each image is reduced then discarded; `on_acquire(url, sha, size)`
        records the ACQUIRE(retained=false) lineage."""
        tally = _sigma.SigmaTally()
        errors: list[str] = []
        fn = self.ev["fn"]
        params = self.ev.get("fn_params", {})
        count = 0
        t0 = __import__("time").time()
        for url in urls:
            if count >= max_rows:
                break
            data = None
            try:
                data = fetch(url)
            except Exception as e:  # noqa: BLE001
                errors.append(f"{url}: fetch {e}")
            if not data:
                tally.add(_sigma.SigmaFace.UNDEFINED)
                count += 1
                continue
            if on_acquire:
                import hashlib
                on_acquire(url, hashlib.sha256(data).hexdigest(), len(data))
            j, why = _reductions.reduce_image(fn, data, params)
            del data
            if j is None:
                errors.append(f"{url}: {why}")
                tally.add(_sigma.SigmaFace.UNDEFINED)
            else:
                tally.add(_sigma.classify(j))
            count += 1
            if on_progress and count % 50 == 0:
                on_progress(count, tally.to_dict())
        return self._result(tally, count, errors, t0)

    def run(self, rows: Iterable[dict], *, max_rows: int = 50_000,
            on_progress=None) -> dict:
        tally = _sigma.SigmaTally()
        errors: list[str] = []
        count = 0
        t0 = __import__("time").time()
        for row in rows:
            if count >= max_rows:
                break
            try:
                j = self.j_ratio(row)
            except PtError:
                raise
            if j is None:
                errors.append(f"row {count}: no j_ratio")
                count += 1
                continue
            tally.add(_sigma.classify(j))
            count += 1
            if on_progress and count % 500 == 0:
                on_progress(count, tally.to_dict())
        return self._result(tally, count, errors, t0)

    def _result(self, tally, count, errors, t0) -> dict:
        return {
            "peval_version": "1.1",
            "name": self.pf.name,
            "bin_name": self.pf.requires_bin or self.pf.bin,
            "timestamp": now_iso(),
            "elapsed_s": round(__import__("time").time() - t0, 2),
            "row_count": count,
            "tally": tally.to_dict(),
            "prediction": self.ev.get("prediction", ""),
            "methodology": self.ev.get("methodology", ""),
            "ainulindale": {"D_STAR": _sigma.D_STAR, "OMEGA_ZS": _sigma.OMEGA_ZS,
                            "SIGMA": 0.5,
                            "pass": tally.to_dict()["sigma_half_frac"] >= 0.5},
            "errors": errors[:20],
        }
