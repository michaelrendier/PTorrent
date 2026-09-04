"""ASCII math  ->  Unicode, for DISPLAY ONLY.

All on-screen text in the curses GUI is Unicode so equations read cleanly on a
single line. Editable field *values* stay ASCII (the core's j_expr parser wants
`sqrt`, `**`, `<=`); this module only prettifies help text, band tables, and a
read-only echo of what the researcher typed.

A real LaTeX -> Unicode pass is out of scope here (TreasureHunt territory).
"""
from __future__ import annotations

import re

# glyphs used across the GUI
SIGMA = "σ"
OMEGA = "Ω"
D_STAR = "d⋆"
INF = "∞"
HALF = "½"
LE = "≤"
GE = "≥"
NE = "≠"
TO = "→"
SQRT = "√"
CDOT = "·"
TIMES = "×"

_SUP = str.maketrans("0123456789+-n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻ⁿ")

_WORDS = [
    (r"\bOMEGA_ZS\b", OMEGA + "_ZS"), (r"\bOmega_ZS\b", OMEGA + "_ZS"),
    (r"\bOMEGA\b", OMEGA), (r"\bOmega\b", OMEGA),
    (r"\bD_STAR\b", D_STAR), (r"\bd_star\b", D_STAR), (r"\bd\*", D_STAR),
    (r"\bSIGMA\b", SIGMA), (r"\bSigma\b", SIGMA),
    (r"\bpi\b", "π"), (r"\binfty\b", INF), (r"\binf\b", INF),
    (r"\bsqrt\b", SQRT), (r"\balpha\b", "α"), (r"\bbeta\b", "β"),
    (r"\bgamma\b", "γ"), (r"\bdelta\b", "δ"), (r"\btheta\b", "θ"),
    (r"\blambda\b", "λ"), (r"\bmu\b", "μ"), (r"\btau\b", "τ"),
]
_OPS = [("<=", LE), (">=", GE), ("!=", NE), ("->", TO), ("=>", TO),
        (" * ", " " + CDOT + " ")]


def unicodize(s: str) -> str:
    """Prettify a line of math for display. Idempotent-ish; never touches values
    that will be parsed."""
    if not s:
        return s
    for pat, rep in _WORDS:
        s = re.sub(pat, rep, s)
    for a, b in _OPS:
        s = s.replace(a, b)
    # exponents:  x**2  ->  x²   ;   x**-1 -> x⁻¹   ;  x**n -> xⁿ
    s = re.sub(r"\*\*\s*(-?\d+|n)", lambda m: m.group(1).translate(_SUP), s)
    # bare sqrt(  already handled by word swap -> "√ (" tidy
    s = s.replace(SQRT + "(", SQRT + "(").replace(SQRT + " (", SQRT + "(")
    return s


def band_table() -> list[str]:
    """The σ-face assignment table, Unicode, one line per band."""
    return [
        f"J < {D_STAR}                {INF}   BH interior — compressible",
        f"{D_STAR} {LE} J < 1           {HALF}   causality — critical line",
        f"1 {LE} J < 1/{D_STAR}         1   Yang–Mills — mass assembly",
        f"1/{D_STAR} {LE} J < 1/{D_STAR}+{OMEGA}   2   gravity — force regime",
        f"J {GE} 1/{D_STAR} + {OMEGA}       {INF}   BH interior — force extreme",
        f"J non-finite            —   undefined (counted, no face)",
    ]


CONSTANTS_LINE = f"{D_STAR} = 0.246     {OMEGA}_ZS = 0.5671432904097838  (Lambert W(1))"
