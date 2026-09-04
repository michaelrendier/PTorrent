"""σ-face classification and tally.

Mirrors libptorrent src/pt_sigma.c. The two constants are fixed and published,
NOT fit parameters.

    d*     = 0.246                 spectral ground state
    Omega  = 0.5671432904097838   Lambert W(1)

FIX vs the Android `evaluator.sigma_face`: a non-finite J (NaN / inf) is
UNDEFINED, never INF. The INF face is entered from both ends of the band table
already; folding "no value" into it silently inflates the one bucket that has
two disjoint physical meanings. A row that could not be measured is unmeasured.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

D_STAR = 0.246
OMEGA_ZS = 0.5671432904097838


class SigmaFace(str, Enum):
    UNDEFINED = "undefined"
    HALF = "half"
    ONE = "one"
    TWO = "two"
    INF = "inf"


_LABEL = {
    SigmaFace.UNDEFINED: "undefined",
    SigmaFace.HALF: "½",
    SigmaFace.ONE: "1",
    SigmaFace.TWO: "2",
    SigmaFace.INF: "∞",
}
_SEMANTIC = {
    SigmaFace.UNDEFINED: "undefined",
    SigmaFace.HALF: "causality",
    SigmaFace.ONE: "Yang-Mills",
    SigmaFace.TWO: "gravity",
    SigmaFace.INF: "BH interior",
}


def classify(j: float) -> SigmaFace:
    """Total function: every double maps to a face. Non-finite -> UNDEFINED."""
    try:
        j = float(j)
    except (TypeError, ValueError):
        return SigmaFace.UNDEFINED
    if not math.isfinite(j):
        return SigmaFace.UNDEFINED
    if j < D_STAR:
        return SigmaFace.INF          # BH interior — compressible limit
    if j < 1.0:
        return SigmaFace.HALF         # causality — critical line
    if j < 1.0 / D_STAR:              # ~4.065
        return SigmaFace.ONE          # Yang-Mills — mass assembly
    if j < 1.0 / D_STAR + OMEGA_ZS:
        return SigmaFace.TWO          # gravity — force regime
    return SigmaFace.INF             # BH interior — force extreme


def label(f: SigmaFace) -> str:
    return _LABEL[f]


def semantic(f: SigmaFace) -> str:
    return _SEMANTIC[f]


@dataclass
class SigmaTally:
    undefined: int = 0
    half: int = 0
    one: int = 0
    two: int = 0
    inf: int = 0

    def add(self, f: SigmaFace) -> None:
        setattr(self, f.value, getattr(self, f.value) + 1)

    @property
    def finite(self) -> int:
        return self.half + self.one + self.two + self.inf

    @property
    def total(self) -> int:
        return self.finite + self.undefined

    def fractions(self) -> dict:
        n = self.finite
        if not n:
            return {"½": 0.0, "1": 0.0, "2": 0.0, "∞": 0.0}
        return {
            "½": round(self.half / n, 4),
            "1": round(self.one / n, 4),
            "2": round(self.two / n, 4),
            "∞": round(self.inf / n, 4),
        }

    def to_dict(self) -> dict:
        return {
            "undefined": self.undefined, "half": self.half, "one": self.one,
            "two": self.two, "inf": self.inf,
            "finite": self.finite, "total": self.total,
            "fractions": self.fractions(),
            "sigma_half_frac": self.fractions()["½"],
        }
