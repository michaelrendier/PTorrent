#!/usr/bin/env python3
"""
monad.py  v2.0.0
================
Ptolemaious Holcaios Philadelphos — The Voice of Mathematics Itself.
One-wire engine. At every scale. Platform-independent sedenion core.
Python reference implementation — field logic matches PtolC/monad.c exactly.

THE ONE WIRE
------------
  wire(data, source) → sedenion → everything else is mechanical.
  Text, audio bands, numeric, raw sedenion — same wire, same engine.
  Console, PHP, JavaScript, Android, iOS, Windows, macOS, *nix:
  all clients speak JSON over a socket. The daemon listens. One wire.

  At every scale — glyph → word → phrase → sentence → paragraph → corpus.
  Same sedenion architecture. Threshold adjusts. Cardioid at every scale.

THE 16 OPERATORS (sedenion dimensions = computational primitives)
-----------------------------------------------------------------
  e₀  identity     e₁  negate       e₂  bind         e₃  name
  e₄  apply        e₅  abstract     e₆  branch        e₇  iterate
  e₈  recurse      e₉  allocate     e₁₀ query         e₁₁ dereference ← anaphor
  e₁₂ compose      e₁₃ parallelize  ← three-face      e₁₄ interrupt    e₁₅ emit

  14/16 present in v1.216. v1.217 completes e₁₁ (anaphor) and e₁₃ (three-face).

CAM   = Emmy Noether Sedenion  (camshaft — timing / geometry)
CRANK = H_hat_RB Field Engine  (crankshaft — Noether current J^μ)

Dual flow
---------
  J_pos  (Riemann / response) — positive space: what IS     — window_psi
  J_neg  (Fermat  / prompt)   — negative space: what CANNOT BE — prompt_psi
  σ ≈ ½  critical line: π/2 of the cardioid. The next word lives here.

Three-Face Wankel (e₁₃ — Parallelize)
--------------------------------------
  Red  (sin/content):   highest J_pos → foreground content words
  Blue (cos/observer):  lowest age    → context / framing words
  Green(∂M/boundary):   connective dim → tissue binding content to grammar
  φ-walk interleave: R→B→G→R→... One face always in compression.

Anaphor resolution (e₁₁ — Dereference)
----------------------------------------
  Track last fired noun (_last_noun_idx). When pronoun fires: boost
  A-matrix neighbors of last noun in J_pos. The pointer is followed.

16 words + 15 edges = the sedenion. Closed loop at e₀. Bosonic string.
The window builds the Cayley-Dickson tower as it fills:
  1 word → ℝ, 2 → ℂ, 4 → ℍ, 8 → 𝕆, 16 → 𝕊 (full cardioid).

BAO = sedenion-dimensional Laplacian spectral gap = OMEGA_ZS = 0.56714.
The cardioid base state. Infinite doors open at the origin. Idle RPM.

π = _sconj = the Fermat operator. Maps response lobe to forbidden cusp.
  SIGMA_CRIT = ½ = π/2 of the cardioid. Fixed point of the π-rotation.

monad_wordnet.bin: load read-only via --load-bin. Protected against
overwrite. Session state saved separately via --save.

Version: 1.217
"""

import math
import hashlib
import collections
import sys
import os
import json
import time
import threading
import argparse
import pickle
from typing import Dict, List, Tuple, Any, Optional

# ── Physical constants ──────────────────────────────────────────────────────────
OMEGA_ZS   = 0.56714    # Lambert W(1); BAO spectral gap; Δ_𝕊 lowest eigenvalue
GAP        = 0.000707   # Yang-Mills mass gap; semantic vacuum floor
D_STAR     = 0.24600    # Fermat proximity threshold (zero-divisor boundary)
PHI        = (1.0 + math.sqrt(5.0)) / 2.0   # golden ratio (non-resonant walk)
SIGMA_CRIT = 0.5        # critical line σ=½ = π/2 of the cardioid
_SQRT2     = math.sqrt(2.0)

# ── Native Space constants ──────────────────────────────────────────────────────
# Gravity is a push, not a pull. J is pressure, not flux. Word selection by
# neutral buoyancy: the word whose β×E² matches the ambient field pressure.
# All four D* values must be simultaneously resolvable to compute in Native Space.
LN10      = math.log(10.0)         # decimal↔prime impedance bridge; NS metric unit
LN2       = math.log(2.0)          # Cayley-Dickson doubling unit
NS_EXCESS = LN10 - 2.0 * LN2      # ≈ 0.9170 — sedenion residual beyond division algebras
NS_BASIS  = (0.0, D_STAR, SIGMA_CRIT, 1.0)  # four D* completeness basis of Native Space

# ── The Compression Ignition Equation ─────────────────────────────────────────
# 2026-05-27: at neutral buoyancy depth the engine spoke its own architecture.
# Each word = one component of the computation, in execution order.
#
#   philadelphos — identity: who speaks
#   speaks       — action: speak() itself
#   golden       — mechanism: PHI = (1+√5)/2, the φ-walk
#   bosonic      — structure: 16 words + 15 edges, closed loop at e₀
#   semantic     — field: the β-field
#   exhaust      — memory: Noether violation / turbo exhaust between turns
#   octonion     — stratum: 𝕆 layer, where 8D conservation law lives
#   compresses   — stroke: compression, TDC, the -h gate
#   loop         — feedback: Wernicke serpentine belt
#   universe     — scale: "at every scale"
#   firing       — event: combustion. The fire cycle completes.
#
# The field holds the equation of its own construction as a resonance.
# Buoyancy reveals it. Pull buries it under stop words.
SELF_EQUATION = (
    'philadelphos speaks golden bosonic semantic '
    'exhaust octonion compresses loop universe firing'
)

PRIMES = [2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71]
RIEMANN_ZEROS = [
    14.134725, 21.022040, 25.010858, 30.424876, 32.935062,
    37.586178, 40.918719, 43.327073, 48.005151, 49.773832,
    52.970321, 56.446247, 59.347044, 60.831779, 65.112544,
    67.079811, 69.546402, 72.067158, 75.704691, 77.144840,
]

# ── P1: Prime hash — word → prime address → Riemann zero index ────────────────
# ── P2: Zero generator — Z(t) Newton on Riemann-Siegel Z-function ─────────────
#
# Design:
#   Each word gets an E-value derived from its position on the critical line,
#   not from its registration order.  The path:
#     word → Horner base-95 int → next prime p in [2, _PRIME_CAP]
#          → π(p) = zero index → γ[zero_idx] via Z(t) Newton
#          → E = |sin(π × γ / (γ+1))|
#
#   _PRIME_CAP = 2^16 → 6542 distinct prime addresses.
#   zero indices span [1, 6542], γ₆₅₄₂ ≈ 6850 (33-term Z-sum, fast).
#   Zeros are computed on demand and cached — identical across sessions.

_PRIME_CAP = 1 << 16          # 65536 — primes searched in [2, 65537]

# Build sieve of Eratosthenes (runs once at import)
_cap = _PRIME_CAP + 2
_sv  = bytearray([1]) * _cap
_sv[0] = _sv[1] = 0
for _i in range(2, int(_cap ** 0.5) + 1):
    if _sv[_i]:
        _sv[_i * _i :: _i] = bytearray(len(_sv[_i * _i :: _i]))

# Precompute π(k) — count of primes ≤ k, for k in [0, _PRIME_CAP]
_prime_pi_table: List[int] = [0] * _cap
_cnt = 0
for _k in range(_cap):
    if _sv[_k]:
        _cnt += 1
    _prime_pi_table[_k] = _cnt
del _i, _k, _cnt, _cap


def _next_prime(v: int) -> int:
    """
    Smallest prime p ≥ (v mod _PRIME_CAP), clamped to [2, 65537].

    :param v: Non-negative integer.
    :returns: A prime in [2, 65537].
    :rtype: int
    """
    v = max(2, int(v) % (_PRIME_CAP + 1))
    while v <= _PRIME_CAP + 1:
        if _sv[min(v, _PRIME_CAP + 1)] or v > _PRIME_CAP:
            return v
        v += 1
    return 65537   # largest prime ≤ 65537


def _horner_hash(w: str, base: int = 95, offset: int = 32) -> int:
    """
    Horner base-95 hash of word string. Returns a non-negative integer.
    ord range [32, 126] (printable ASCII) → coefficients in [0, 94].

    :param w: Word string (already cleaned/lowercased).
    :param base: Polynomial base (95 = printable ASCII range).
    :param offset: ord offset.
    :returns: Non-negative integer.
    :rtype: int
    """
    v = 0
    for ch in w:
        v = v * base + max(0, ord(ch) - offset)
    return abs(v)


def _word_zero_idx(w: str) -> int:
    """
    P1 prime hash: word → Horner int → next prime p → π(p) = zero index.

    :param w: Cleaned word string.
    :returns: Zero index in [1, 6542].
    :rtype: int
    """
    v = _horner_hash(w)
    p = _next_prime(v)
    idx = _prime_pi_table[min(p, _PRIME_CAP + 1)]
    return max(1, idx)


# ── Zero generator: Z(t) Newton (P2 — partial) ────────────────────────────────
# Phase 1: Newton on smooth N(T) → rough estimate within ±0.5 of actual zero.
# Phase 2: bracket sign-change of Z(t) → bisect → Newton to 1e-9.
# N.B. 1e-9 tolerance (not 1e-12 yet) — P2 full precision adds RS correction term.

_TWO_PI        = 2.0 * math.pi
_TWO_PI_E      = _TWO_PI * math.e
_EPS_Z: float  = 1e-7             # step for numerical Z'(t)

# Exact LMFDB zeros (1-indexed, 9-12dp). Forward scan refines beyond idx=50.
_ZERO_CACHE: Dict[int, float] = {
     1: 14.134725141734693,  2: 21.022039638771555,  3: 25.010857580145688,
     4: 30.424876125859513,  5: 32.935061587739189,  6: 37.586178158825671,
     7: 40.918719012147495,  8: 43.327073280914999,  9: 48.005150881167159,
    10: 49.773832477672302, 11: 52.970321477714460, 12: 56.446247697063246,
    13: 59.347044002602352, 14: 60.831778524609809, 15: 65.112544048081652,
    16: 67.079810529494173, 17: 69.546401711173979, 18: 72.067157674481907,
    19: 75.704690699083933, 20: 77.144840068874805,
    # LMFDB 9dp — extend exact table as P2 matures
    21: 79.337375020,  22: 82.910380854,  23: 84.735492976,  24: 87.425274613,
    25: 88.809111209,  26: 92.491899271,  27: 94.651344041,  28: 95.870634228,
    29: 98.831194218,  30: 101.317851006, 31: 103.725538040, 32: 105.446623052,
    33: 107.168611184, 34: 111.029535543, 35: 111.874659177, 36: 114.320220915,
    37: 116.226680321, 38: 118.790782866, 39: 121.370125002, 40: 122.946829295,
    41: 124.256818680, 42: 127.516683880, 43: 129.578704200, 44: 131.087688532,
    45: 133.497737200, 46: 134.756509753, 47: 138.116042055, 48: 139.736208952,
    49: 141.123707404, 50: 143.111845808,
}


def _theta_rs(t: float) -> float:
    """
    Riemann-Siegel theta function (Stirling series, 3 terms).
    θ(t) = t/2·ln(t/2πe) − π/8 + 1/(48t)

    :param t: Real argument t > 6.
    :returns: θ(t).
    :rtype: float
    """
    return (t / 2.0) * math.log(t / _TWO_PI_E) - math.pi / 8.0 + 1.0 / (48.0 * t)


def _zfunc(t: float) -> float:
    """
    Riemann-Siegel Z(t) — real on ℝ; zeros are Riemann zeros on critical line.
    Z(t) = 2 Σ_{n=1}^{⌊√(t/2π)⌋} n^{-½} cos(θ(t) − t·ln n)

    :param t: Real argument t > 6.
    :returns: Z(t).
    :rtype: float
    """
    m  = int(math.sqrt(t / _TWO_PI))
    th = _theta_rs(t)
    return 2.0 * sum(math.cos(th - t * math.log(n)) / math.sqrt(n)
                     for n in range(1, m + 1))


def _mean_spacing(t: float) -> float:
    """
    Mean spacing between consecutive Riemann zeros near t.
    Approximation: 2π / ln(t/2π).

    :param t: Imaginary part value.
    :returns: Approximate inter-zero spacing.
    :rtype: float
    """
    return _TWO_PI / math.log(max(t / _TWO_PI, 1.01))


def _find_next_zero(t_start: float) -> float:
    """
    Scan forward from t_start to locate the next sign change of Z(t),
    then bisect + Newton to refine.

    The scan uses steps of mean_spacing/12 — never looks backward.
    This guarantees one-to-one correspondence with true zeros even when
    the m-term Z approximation is offset from the actual zero position.

    :param t_start: Lower bound — search begins strictly above this value.
    :returns: Location of next Z(t) sign change, refined to ~1e-7.
    :rtype: float
    """
    sp   = _mean_spacing(t_start)
    step = sp / 12.0
    ta   = t_start + step * 0.5   # start just ahead — never at t_start itself
    za   = _zfunc(ta)

    # Forward scan: walk until sign change (max 3 mean spacings ahead)
    limit = t_start + 3.0 * sp
    tb    = ta
    zb    = za
    found = False
    while tb < limit:
        tb  = ta + step
        zb  = _zfunc(tb)
        if za * zb <= 0.0:
            found = True
            break
        ta, za = tb, zb

    if not found:
        return t_start + sp   # fallback: skip ahead one spacing

    # Bisect ta→tb to 4dp
    for _ in range(60):
        tm = (ta + tb) * 0.5
        zm = _zfunc(tm)
        if za * zm <= 0.0:
            tb, zb = tm, zm
        else:
            ta, za = tm, zm
        if abs(tb - ta) < 1e-4:
            break
    t = (ta + tb) * 0.5

    # Newton on Z(t) to 1e-7
    for _ in range(20):
        z  = _zfunc(t)
        dz = (_zfunc(t + _EPS_Z) - _zfunc(t - _EPS_Z)) / (2.0 * _EPS_Z)
        if abs(dz) < 1e-15:
            break
        dt = z / dz
        t -= dt
        if abs(dt) < 1e-7:
            break
    return t


def _find_zero_n(n: int) -> float:
    """
    Find the n-th Riemann zero (1-indexed).

    Uses exact LMFDB table for n ≤ 50. Beyond that, chains forward from
    the highest cached zero, advancing one zero at a time via forward-only
    Z(t) scan. Each step is cached so subsequent lookups near n are O(1).

    Accuracy: exact (table) for n ≤ 50; ~1e-7 for n > 50 (limited by
    m-term Z approximation — improves as t grows and m increases).
    P2 full 12dp requires RS correction term — tracked separately.

    :param n: Zero index (1-indexed).
    :returns: γₙ.
    :rtype: float
    """
    # Find highest cached index below n
    cached_below = [k for k in _ZERO_CACHE if k < n]
    start = max(cached_below) if cached_below else 1
    t     = _ZERO_CACHE.get(start, 14.134725142)

    for k in range(start + 1, n + 1):
        if k in _ZERO_CACHE:
            t = _ZERO_CACHE[k]
            continue
        t = _find_next_zero(t)
        _ZERO_CACHE[k] = t

    return _ZERO_CACHE[n]


def _gamma_at(zero_idx: int) -> float:
    """
    Return γ for Riemann zero at position zero_idx (1-indexed).
    Computes and caches on demand. Thread-safe via GIL on CPython.

    :param zero_idx: 1-indexed zero position.
    :returns: γ_{zero_idx} to ~9 dp.
    :rtype: float
    """
    n = max(1, zero_idx)
    if n not in _ZERO_CACHE:
        _ZERO_CACHE[n] = _find_zero_n(n)
    return _ZERO_CACHE[n]


# The 16 sedenion operators — named explicitly (e_k = operator k)
_OP: Dict[int, str] = {
    0:  'identity',    1:  'negate',      2:  'bind',        3:  'name',
    4:  'apply',       5:  'abstract',    6:  'branch',      7:  'iterate',
    8:  'recurse',     9:  'allocate',    10: 'query',       11: 'dereference',
    12: 'compose',     13: 'parallelize', 14: 'interrupt',   15: 'emit',
}


# ══════════════════════════════════════════════════════════════════════════════
#  CAM — Emmy Noether Sedenion  (Cayley-Dickson 16D algebra)
# ══════════════════════════════════════════════════════════════════════════════

def _build_oct_table() -> List[List[Tuple[int, int]]]:
    """8×8 octonion table via oriented-cyclic Fano."""
    t = [[(0, 0)] * 8 for _ in range(8)]
    for i in range(8):
        t[0][i] = (1, i);  t[i][0] = (1, i)
    for i in range(1, 8):
        t[i][i] = (-1, 0)
    for i, j, k in [(1,2,3),(1,4,5),(1,7,6),(2,4,6),(2,5,7),(3,4,7),(3,6,5)]:
        t[i][j]=(+1,k); t[j][k]=(+1,i); t[k][i]=(+1,j)
        t[j][i]=(-1,k); t[k][j]=(-1,i); t[i][k]=(-1,j)
    return t

_OCT = _build_oct_table()

def _build_sed_table() -> List[List[Tuple[int, int]]]:
    """16×16 sedenion table via Cayley-Dickson doubling."""
    t = [[(0, 0)] * 16 for _ in range(16)]
    for i in range(16):
        for j in range(16):
            io, jo = (i - 8 if i >= 8 else i), (j - 8 if j >= 8 else j)
            ih, jh = i >= 8, j >= 8
            if not ih and not jh:
                t[i][j] = _OCT[io][jo]
            elif not ih and jh:
                sg, k = _OCT[jo][io];  t[i][j] = (sg, k + 8)
            elif ih and not jh:
                if jo == 0:             t[i][j] = (1, i)
                else: sg, k = _OCT[io][jo]; t[i][j] = (-sg, k + 8)
            else:
                if jo == 0:             t[i][j] = (-1, io)
                else: sg, k = _OCT[jo][io]; t[i][j] = (sg, k)
    return t

_SED = _build_sed_table()

Sedenion = List[float]

def _s0()                  -> Sedenion:  return [0.0] * 16
def _se(k: int)            -> Sedenion:  s = _s0(); s[k] = 1.0; return s
def _snorm(a: Sedenion)    -> float:     return math.sqrt(sum(x*x for x in a))
def _sconj(a: Sedenion)    -> Sedenion:  return [a[0]] + [-x for x in a[1:]]
def _sscale(a: Sedenion, c: float) -> Sedenion: return [x * c for x in a]

def _smul(a: Sedenion, b: Sedenion) -> Sedenion:
    c = [0.0] * 16
    for i, ai in enumerate(a):
        if ai == 0.0: continue
        row = _SED[i]
        for j, bj in enumerate(b):
            if bj == 0.0: continue
            sg, idx = row[j]
            if sg: c[idx] += sg * ai * bj
    return c

def _snorm_unit(a: Sedenion) -> Sedenion:
    n = _snorm(a)
    return _sscale(a, 1.0 / n) if n > 1e-15 else _s0()

def _spsi(a: Sedenion) -> List[float]:
    """psi_norms[k] = |a_k| — field amplitude per sedenion dimension."""
    return [abs(x) for x in a]


# ── Prompt encoder (carburetor: fuel-air mixture) ─────────────────────────────

_PRONOUNS    = frozenset('i me my mine myself we us our ours ourselves you your yours '
                         'yourself yourselves he him his himself she her hers herself '
                         'it its itself they them their theirs themselves this that '
                         'these those here there who what which'.split())
_AUXILIARIES = frozenset('is are was were be been being do does did have has had '
                         'will would can could should shall may might must'.split())
_CONJUNCTS   = frozenset('and or but so yet for nor although because if then when '
                         'while since unless until though'.split())
_TIME        = frozenset('now then before after when while ago yet already still soon '
                         'later today yesterday tomorrow always never sometimes often rarely'.split())
_QUESTION    = frozenset('what which who whom whose when where why how whether if'.split())
_NEGATION    = frozenset("not never no nor nothing nobody nowhere neither n't".split())
_DETERMINERS = frozenset('a an the some any every each all both few many much more '
                         'most less least'.split())

# ── Fermat emotional lattice — the negative space between words ───────────────
# Each space in the output stream carries the J_neg charge at that boundary.
# The wastegate: different Unicode space characters encode different charge levels.
# Invisible to plain-text readers. Decoded by hear() to restore J_neg to field.
#
# Lagrangian derivation:
#   V_k = β_k × E_k²        (potential — stored charge, prompt side)
#   T_k = ψ_k²              (kinetic  — flowing charge, window side)
#   High V/T → high J_neg → heavy Fermat space → compressed utterance
#   Low  V/T → low  J_neg → thin  Fermat space → extended discourse
#
_FERMAT_SPACES = [
    ' ',  # J_neg ∈ [0.00, 0.12)  HAIR SPACE            — minimal visible boundary
    ' ',  # J_neg ∈ [0.12, 0.25)  THIN SPACE            — faint negative charge
    ' ',  # J_neg ∈ [0.25, 0.37)  PUNCTUATION SPACE     — moderate boundary
    ' ',  # J_neg ∈ [0.37, 0.50)  FIGURE SPACE          — weighted boundary
    ' ',  # J_neg ∈ [0.50, 0.62)  SIX-PER-EM SPACE      — emphatic negative space
    ' ',  # J_neg ∈ [0.62, 0.75)  FOUR-PER-EM SPACE     — urgent negative charge
    ' ',  # J_neg ∈ [0.75, 0.87)  THREE-PER-EM SPACE    — high-affect boundary
    ' ',  # J_neg ∈ [0.87, 1.00]  EM SPACE              — full Fermat wall / detonation
]
_FERMAT_DECODE: Dict[str, float] = {
    ' ': 0.06,
    ' ': 0.18,
    ' ': 0.31,
    ' ': 0.43,
    ' ': 0.56,
    ' ': 0.68,
    ' ': 0.81,
    ' ': 0.93,
}
_FERMAT_SET = frozenset(_FERMAT_DECODE.keys())

def _fermat_space(j_neg: float) -> str:
    """Map J_neg ∈ [0,1] → Unicode space character. The manual wastegate.
    High charge → heavier space → negative space carries the message."""
    idx = min(int(j_neg * len(_FERMAT_SPACES)), len(_FERMAT_SPACES) - 1)
    return _FERMAT_SPACES[idx]


# ── CJK tokenizer — per-glyph splitting for Mandarin/Chinese ─────────────────
# Chinese text has no spaces between words. Each CJK character is a morpheme.
# Insert spaces around CJK glyphs so text.split() produces one token per glyph.
# Covers: CJK Unified Ideographs (U+4E00-U+9FFF), Extension A (U+3400-U+4DBF),
#         Katakana/Hiragana (U+3040-U+30FF), Hangul (U+AC00-U+D7A3).
_CJK_RANGES = (
    ('぀', 'ヿ'),   # Hiragana + Katakana
    ('㐀', '䶿'),   # CJK Extension A
    ('一', '鿿'),   # CJK Unified Ideographs (main block)
    ('가', '힣'),   # Hangul syllables
    ('豈', '﫿'),   # CJK Compatibility Ideographs
)

def _is_cjk(ch: str) -> bool:
    for lo, hi in _CJK_RANGES:
        if lo <= ch <= hi:
            return True
    return False

def _cjk_space(text: str) -> str:
    """Insert spaces around CJK glyphs so split() yields one token per character."""
    if not any(_is_cjk(c) for c in text):
        return text   # fast path: no CJK present
    out = []
    for ch in text:
        if _is_cjk(ch):
            out.append(f' {ch} ')
        else:
            out.append(ch)
    return ''.join(out)
_META        = frozenset('mean means meaning say says said tell tells told explain '
                         'explains clarify summarise summarize rephrase repeat'.split())
_AFF_POS     = frozenset('good great love like enjoy happy glad pleased wonderful '
                         'excellent amazing thank thanks please'.split())
_AFF_NEG     = frozenset('bad hate dislike angry sad sorry worried fear terrible '
                         'awful horrible wrong mistake fail'.split())

def _whash(w: str) -> float:
    return int.from_bytes(hashlib.sha256(w.encode()).digest()[:4], 'big') / 0xFFFFFFFF

def cam_encode(text: str) -> Sedenion:
    """Encode text as unit sedenion. The prompt IS the sedenion. CAM timing geometry."""
    s = _s0()
    words = _cjk_space(text).lower().split()
    n = max(len(words), 1)
    s[0] = math.log(n + 1) / math.log(512)
    for w in words:
        s[1] += _whash(w) / n
        if w in _CONJUNCTS:  s[2] += 1/n
        if (w not in _PRONOUNS and w not in _AUXILIARIES and w not in _CONJUNCTS
                and w not in _TIME and w not in _QUESTION and w not in _DETERMINERS
                and w not in _META and w not in _AFF_POS and w not in _AFF_NEG
                and len(w) >= 4): s[3] += 1/n
        if w in _AUXILIARIES or w.endswith('ing') or w.endswith('ed'): s[4] += 1/n
        if w.endswith('ly') or w.endswith('ful') or w.endswith('ous'):  s[5] += 1/n
        if w in _NEGATION or w in _CONJUNCTS:  s[6] += 1/n
        if w in _TIME or w in ('was','were','will','would','has','have','had'): s[7] += 1/n
        if w in _PRONOUNS:  s[8] += 1/n
        if w not in _PRONOUNS and w not in _AUXILIARIES and len(w) >= 3:
            s[9] += _whash(w) * 0.5 / n
        if w in _QUESTION:  s[10] += 1/n
        if w in ('it','its','they','them','their','he','she','who','which'): s[11] += 1/n
        if w in ('the','already','again','still','even','also','too'): s[12] += 1/n
        s[13] += len(w) / 12.0 / n
        if w in _AFF_POS:   s[14] += 1/n
        elif w in _AFF_NEG: s[14] -= 1/n
        if w in _META:      s[15] += 1/n
    s[14] = max(s[14], 0.0)
    s = [max(x, GAP) if i > 0 else x for i, x in enumerate(s)]
    return _snorm_unit(s)


# ── Fermat lattice scan + SEGFAULT handler ────────────────────────────────────

_PROBE_PAIRS: List[Tuple[int, int]] = [
    (i, j) for i in range(1, 16) for j in range(i + 1, 16)
]  # 105 two-component probes: (e_i + e_j)/√2

def fermat_scan(s: Sedenion) -> Dict[str, Any]:
    """
    Probe 105 two-component basis pairs for zero-divisor proximity.

    Single basis probes are perfect isometries (|s·e_k|=|s| always).
    Two-component probes expose the Fermat lattice: the true ZD pair
    (e1+e10)/√2 · (e5+e14)/√2 = 0 gives proximity = 1.
    """
    sn   = _snorm_unit(s)
    hits = []
    for i, j in _PROBE_PAIRS:
        probe    = _s0(); probe[i] = 1.0 / _SQRT2; probe[j] = 1.0 / _SQRT2
        prod     = _smul(sn, probe)
        pn       = _snorm(prod)
        prox     = 1.0 - pn
        if prox > D_STAR:
            hits.append({'basis_idx': i, 'basis_idx2': j,
                         'proximity': prox, 'is_zd': pn < 1e-10})
    return {
        'density':       len(hits) / len(_PROBE_PAIRS),
        'zero_divisors': sum(1 for h in hits if h['is_zd']),
        'hits':          sorted(hits, key=lambda h: -h['proximity'])[:4],
    }

def segfault_handler(s: Sedenion, fermat_result: Dict) -> Sedenion:
    """
    SEGFAULT: ZD detected → left-multiply by e_k. Airy function at the caustic.
    Non-commutativity guarantees e_k · s ≠ 0. Turbulent flow, not crash.
    """
    hits = fermat_result.get('hits', [])
    if not hits: return s
    top = max(hits, key=lambda h: h.get('proximity', 0))
    k   = top.get('basis_idx', 1)
    return _snorm_unit(_smul(_se(k), s))


# ── Universal sensor encoder — the one-wire adapter ───────────────────────────

def sensor_encode(data: Any, source: str = 'text') -> Sedenion:
    """
    Any sensor → unit sedenion. The one-wire adapter.

    text:         cam_encode(str(data))
    raw_sedenion: 16 floats, normalized
    numeric:      scalar spread across 16D via Riemann zero phases
    audio_bands:  16 mel-filterbank band energies → sedenion components

    The sedenion IS the universal sensor interface. Every physical measurement
    is a projection onto 16 real numbers. Platform-independent by construction.
    MIDI has 16 channels. EEG 10-20 system has 16 primary sites.
    All find 16 empirically. The sedenion finds it derivationally.
    """
    if source == 'text':
        return cam_encode(str(data))

    elif source == 'raw_sedenion':
        if isinstance(data, (list, tuple)) and len(data) >= 16:
            return _snorm_unit([float(x) for x in data[:16]])
        return _se(0)

    elif source == 'numeric':
        v = float(data)
        s = _s0()
        for k in range(16):
            gamma = RIEMANN_ZEROS[k % len(RIEMANN_ZEROS)]
            s[k]  = abs(math.sin(math.pi * v / (gamma + 1.0)))
        return _snorm_unit(s)

    elif source == 'audio_bands':
        if isinstance(data, str):
            bands = [float(x) for x in data.split() if x]
        elif hasattr(data, '__len__'):
            bands = list(data)
        else:
            bands = [float(data)]
        bands = bands[:16] + [0.0] * max(0, 16 - len(bands))
        return _snorm_unit([max(float(b), 0.0) for b in bands])

    else:
        return cam_encode(str(data))


# ══════════════════════════════════════════════════════════════════════════════
#  CRANK — H_hat_RB Field Engine
# ══════════════════════════════════════════════════════════════════════════════

class Crank:
    """
    H_hat_RB crankshaft. β-field (knowledge) + A-matrix (adjacency).

    J_pos[idx] = β × E² × window_psi[idx%16]   (Riemann / response)
    J_neg[idx] = β × E² × prompt_psi[idx%16]    (Fermat  / prompt)
    σ[idx]     = J_pos / (J_pos + J_neg)         → 0.5 boundary = next word

    The sedenion IS the sedenion-dimensional Laplacian. The multiplication
    table IS the second-order differential structure. OMEGA_ZS IS the
    spectral gap. The field at equilibrium IS the harmonic function.
    """

    def __init__(self):
        self._beta:             List[float]              = []
        self._E:                List[float]              = []
        self._A:                List[Dict[int, float]]   = []
        self._age:              List[float]              = []
        self._vocab:            Dict[str, int]           = {}
        self._words:            List[str]                = []
        self.n:                 int                      = 0
        self.emission_threshold: float                   = OMEGA_ZS / 4.0
        # Sparse edge correction overlay: _correction_mask[src][dst] ∈ (0,1].
        # Default 1.0 (absent = unmodified). Applied in a_propagate().
        # Preserved across save/load. The field remembers what it unlearned.
        self._correction_mask:  Dict[int, Dict[int, float]] = {}
        self._fire_count:       List[int]                    = []
        self._stratum:          List[int]                    = []  # NS_SIGMA_C=0, O=1, S=2

    # Sedenion dimension → grammatical role (piston firing order, v1.3)
    _DIM_ROLE: Dict[int, int] = {
        3: 0,   # noun      — fires first  (e₃ = name operator)
        4: 1,   # verb                     (e₄ = apply operator)
        5: 2,   # descriptive              (e₅ = abstract operator)
        6: 3,   # predicate / negation     (e₆ = branch operator)
        2: 4,   # connective / edge        (e₂ = bind operator)
        7: 5,   # temporal                 (e₇ = iterate operator)
        8: 5,   # pronominal               (e₈ = recurse operator)
        9: 5,   # discourse thread         (e₉ = allocate operator)
        10: 6,  # question / thematic      (e₁₀ = query operator)
        11: 6,  # anaphor                  (e₁₁ = dereference operator)
        12: 6,  # presupposition           (e₁₂ = compose operator)
        13: 7,  # gestalt / weight         (e₁₃ = parallelize operator)
        14: 7,  # affect                   (e₁₄ = interrupt operator)
        15: 7,  # meta-discourse           (e₁₅ = emit operator)
        0: 8,   # scalar bias — last       (e₀ = identity operator)
        1: 8,   # gematria — last          (e₁ = negate operator)
    }

    def _idx(self, w: str) -> int:
        """
        e₉ allocate — create new vocabulary entry.

        P1: word address is derived from a prime on the critical line, not
        registration order.  Two runs on the same corpus produce identical
        E-values for the same word.
        """
        if w not in self._vocab:
            k = self.n
            self._vocab[w] = k
            self._words.append(w)
            zero_idx = _word_zero_idx(w)          # P1: prime hash → zero address
            gamma    = _gamma_at(zero_idx)         # P2: Z(t) Newton → γ value
            self._E.append(abs(math.sin(math.pi * gamma / (gamma + 1.0))))
            self._beta.append(GAP)
            self._age.append(0.0)
            self._A.append({})
            self._fire_count.append(0)
            self._stratum.append(0)   # NS_SIGMA_C
            self.n += 1
        return self._vocab[w]

    def _clean(self, w: str) -> str:
        return w.lower().strip('.,!?;:\'"()[]{}—。，！？；：、“”‘’（）【】《》…·')

    def learn(self, text: str, weight: float = 1.0) -> int:
        """
        e₂ bind — deepen β-field. Build A-matrix connections.

        :param text: Text to learn.
        :param weight: Multiplier on beta gain and edge delta (1.0 = normal;
            >1.0 = authoritative commit; do not use negative values — use
            retract() to suppress edges).
        :returns: Number of words processed.
        :rtype: int
        """
        words      = [self._clean(w) for w in _cjk_space(text).split()]
        words      = [w for w in words if w and len(w) >= 1]
        beta_mult  = 1.0 + 0.08 * weight   # weight=1 → ×1.08 (unchanged)
        edge_fwd   = 0.05 * weight
        edge_back  = 0.02 * weight
        prev       = None
        for w in words:
            k = self._idx(w)
            self._beta[k] = min(self._beta[k] * beta_mult + GAP, 1.0)
            self._age[k]  = 0.0
            if prev is not None and prev != k:
                self._A[prev][k] = min(self._A[prev].get(k, 0.0) + edge_fwd,  1.0)
                self._A[k][prev] = min(self._A[k].get(prev, 0.0) + edge_back, 1.0)
            prev = k
        return len(words)

    def hear(self, text: str) -> List[Tuple[int, float, str]]:
        """
        e₁₀ query — hear = learn. Ptolemy learns everything he hears.
        The serpentine belt: hearing IS deepening. No separation.

        Fermat space decoder: invisible Unicode space characters between words
        carry J_neg charge from the previous output. On hear(), each Fermat
        space boosts β in the dimensions matching its charge level — restoring
        the negative space field from the turbo exhaust of the last turn.
        """
        # Decode Fermat spaces — extract J_neg charges before stripping
        fermat_charges = []
        for ch in text:
            if ch in _FERMAT_SET:
                fermat_charges.append(_FERMAT_DECODE[ch])

        # Inject Fermat charges into β field — the exhaust compresses the intake
        if fermat_charges:
            mean_charge = sum(fermat_charges) / len(fermat_charges)
            for k in range(self.n):
                dim = k % 16
                # Dims with low ψ (negative space) receive the Fermat boost
                dim_charge = mean_charge * (1.0 - dim / 16.0)
                if dim_charge > GAP:
                    self._beta[k] = min(self._beta[k] + dim_charge * GAP * 10, 1.0)

        self.learn(text)
        words = [self._clean(w) for w in _cjk_space(text).split() if self._clean(w)]
        return [(self._vocab[w], self._E[self._vocab[w]], w)
                for w in words if w in self._vocab]

    def hear_sedenion(self, s: Sedenion) -> Dict[str, Any]:
        """
        e₁₀ query (non-text) — learn from raw sedenion geometry.
        Component amplitude in dimension k steers all vocab words at that
        sedenion address (vocab_idx % 16 == k). The sensor talks to the
        field in the sedenion's own language. Platform-independent.
        """
        psi     = _spsi(s)
        updated = 0
        for k in range(self.n):
            dim    = k % 16
            weight = psi[dim]
            if weight > GAP:
                self._beta[k] = min(self._beta[k] * (1.0 + weight * 0.1) + GAP, 1.0)
                self._age[k]  = max(self._age[k] - weight * 10.0, 0.0)
                updated += 1
        peak_dim = psi.index(max(psi))
        return {'updated': updated, 'peak_dim': peak_dim,
                'operator': _OP.get(peak_dim, 'unknown')}

    def advance_age(self, temporal_weight: float = 1.0):
        for k in range(self.n):
            self._age[k] = min(self._age[k] + temporal_weight, 1e6)

    def j_mu(self,
             window_psi: List[float],
             prompt_psi: List[float]) -> Tuple[List[float], List[float]]:
        """
        Dual Noether current J^μ.
        J_pos = Riemann (response / positive space)
        J_neg = Fermat  (prompt  / negative space)
        Information flow IS Noether current. The stock market does too.
        """
        n     = self.n
        J_pos = [0.0] * n
        J_neg = [0.0] * n
        for k in range(n):
            b     = self._beta[k]
            e2    = self._E[k] ** 2
            decay = math.exp(-self._age[k] * 0.001)
            base  = b * e2 * decay
            J_pos[k] = base * window_psi[k % 16]
            J_neg[k] = base * prompt_psi[k % 16]
        return J_pos, J_neg

    def a_propagate(self, J: List[float]) -> List[float]:
        """
        Single A-matrix hop: spread J through adjacency (oil pressure).
        Retracted edges are multiplied by their correction factor — suppressed
        but not zeroed, so strong context can still reactivate them.
        """
        J2 = list(J)
        for src, nbrs in enumerate(self._A):
            if J[src] < GAP: continue
            src_mask = self._correction_mask.get(src, {})
            for dst, w in nbrs.items():
                effective = w * src_mask.get(dst, 1.0)
                if effective < GAP: continue
                J2[dst] += J[src] * effective * 0.5
        return J2

    def sigma_candidates(self,
                         J_pos: List[float],
                         J_neg: List[float],
                         J_ambient: float = OMEGA_ZS) -> List[Tuple[float, int, str]]:
        """
        Score by neutral buoyancy: find words whose J pressure matches the
        ambient field pressure (J_ambient), weighted by σ=½ proximity.

        Gravity is a push. J is pressure. The next word is not the highest-J
        word (pull/gravity model) — it is the word at neutral buoyancy with the
        current field pressure. Words lighter than J_ambient float up (creative,
        rare). Words heavier sink (ponderous). Neutral buoyancy rides the field.

        LN10 normalises the pressure difference to Native Space (decimal) units.
        """
        if self.n == 0: return []
        max_jp = max(J_pos) if J_pos else 0.0
        thr    = max_jp * (self.emission_threshold / OMEGA_ZS) * 0.01
        staged: List[Tuple[int, float, int, str]] = []
        for k in range(self.n):
            jp, jn = J_pos[k], J_neg[k]
            total  = jp + jn
            if total < thr: continue
            sigma  = jp / total
            # Neutral buoyancy: score highest when jp ≈ J_ambient.
            # LN10 converts pressure delta to Native Space (decimal) scale.
            buoy   = 1.0 / (1.0 + abs(jp - J_ambient) * LN10)
            score  = buoy * (1.0 - abs(sigma - 0.5) * 2.0)
            role   = self._DIM_ROLE.get(k % 16, 8)
            staged.append((role, -score, k, self._words[k]))
        staged.sort()
        return [(-ns, idx, w) for (role, ns, idx, w) in staged]


# ══════════════════════════════════════════════════════════════════════════════
#  ENGINE — Dual Flow + 16-Word Sliding Window + One Wire
# ══════════════════════════════════════════════════════════════════════════════

class Engine:
    """
    One-wire sedenion engine. At every scale. All 16 operators present.

    16 words + 15 edges = the sedenion. e₀ closes the loop (implicit 16th edge).
    The window IS the context buffer. The turbo IS the memory.
    π = _sconj = the Fermat operator. Maps response lobe to forbidden cusp.
    The engine IS the sedenion-dimensional Laplacian harmonic solver.
    """

    def __init__(self):
        self.crank            = Crank()
        self._window          = collections.deque(maxlen=16)
        self._prompt_sed:       Optional[Sedenion]   = None
        self._prompt_psi:       Optional[List[float]] = None
        self._psi_prev:         List[float]           = [0.0] * 16
        self._dtcs:             List[str]             = []
        self._segfaults:        int                   = 0
        self._word_count:       int                   = 0
        self._bao_buf           = collections.deque(maxlen=16)
        self._last_noun_idx:    Optional[int]         = None   # e₁₁ anaphor
        self._recent:           collections.deque     = collections.deque(maxlen=8)  # no-repeat buffer
        self._J_ambient:        float                 = GAP       # cold-start; calibrated to field median J on load
        self._protected_paths:  set                   = set()  # bin files, never overwrite
        self.version            = "v1.218"

    # ── e₀ identity — field management ──────────────────────────────────

    def load(self, text: str) -> Dict[str, Any]:
        """Ingest corpus text. Deepen β-field."""
        n = self.crank.learn(text)
        return {'words_learned': n, 'vocab_size': self.crank.n}

    # ── e₁₀ query — one wire ────────────────────────────────────────────

    def wire(self, data: Any, source: str = 'text') -> Sedenion:
        """
        THE ONE WIRE. Any input at any scale. Always the sedenion.

        Console, PHP/JS, Android, iOS, Windows, macOS, *nix — all clients
        send data here. The sedenion IS the platform-independent interface.
        Text → full tokenization + learning. Non-text → hear_sedenion().
        The machine processes everything else mechanically. No external ECU.
        """
        s = sensor_encode(data, source)
        if source == 'text':
            self.crank.hear(str(data))
        else:
            self.crank.hear_sedenion(s)
        return s

    # ── e₀ identity — internal geometry ─────────────────────────────────

    def _window_sed(self) -> Sedenion:
        """Window state → unit sedenion. The Hamiltonian observer."""
        if not self._window:
            return _se(0)
        return cam_encode(' '.join(self._window))

    def _prime_prompt(self, prompt: str):
        """Set prompt geometry — Fermat / negative space / fuel."""
        self.crank.hear(prompt)
        self._prompt_sed = cam_encode(prompt)
        self._prompt_psi = _spsi(self._prompt_sed)
        self._window.clear()

    # ── e₁₂ compose — power steering ────────────────────────────────────

    def _power_steering(self, J_pos: List[float],
                        window_psi: List[float],
                        prompt_psi: List[float]) -> List[float]:
        """
        Sedenion transformer attention — rack and pinion.
        T_μν = window_psi ⊗ prompt_psi (stress-energy diagonal).
        softmax(T/√16) = attention weights. J_pos × (1+attn) = steered.
        O(n) not O(n²). Derived not learned.
        """
        T     = [window_psi[k] * prompt_psi[k] for k in range(16)]
        T_max = max(T)
        exp_T = [math.exp((t - T_max) / 4.0) for t in T]
        Z     = sum(exp_T) or 1.0
        attn  = [e / Z for e in exp_T]
        n     = self.crank.n
        return [J_pos[k] * (1.0 + attn[k % 16]) for k in range(n)]

    # ── e₁₃ parallelize — Three-Face Wankel ─────────────────────────────

    def _three_face_candidates(self,
                               J_pos: List[float],
                               J_neg: List[float]) -> List[Tuple[float, int, str]]:
        """
        Three simultaneous J^μ projections. One face always in compression.

        Red  (sin/content):   sorted by J_pos magnitude — foreground content
        Blue (cos/observer):  sorted by age ascending  — freshest context
        Green(∂M/boundary):   connective/boundary dims — tissue, not content

        φ-walk interleave: Red[0]→Blue[0]→Green[0]→Red[1]→Blue[1]→Green[1]→...
        The Wankel rotor. Three combustion chambers. Grammar in the geometry.
        """
        base = self.crank.sigma_candidates(J_pos, J_neg, self._J_ambient)
        if not base:
            return []

        # Red face: highest J_pos — content words, foreground
        red  = sorted(base, key=lambda x: -x[0])

        # Blue face: lowest age — freshest, observer context
        blue = sorted(base, key=lambda x: self.crank._age[x[1]])

        # Green face: connective/boundary dimensions (DIM_ROLE 4-6)
        # These are the words at the ∂M boundary: prepositions, articles,
        # conjunctions — the tissue that binds content to grammar.
        green = [(s, i, w) for (s, i, w) in base
                 if self.crank._DIM_ROLE.get(i % 16, 8) in (4, 5, 6)]
        if not green:
            # fallback: words whose score is closest to the boundary (σ near ½)
            green = sorted(base, key=lambda x: abs(x[0] - OMEGA_ZS * 0.5))

        # Interleave R→B→G→R→B→G→... preserving grammar order within each face
        merged:   List[Tuple[float, int, str]] = []
        seen_idx: set = set()
        ri, bi, gi   = 0, 0, 0
        face_cycle   = 0
        total        = len(base)

        while len(merged) < total:
            f = face_cycle % 3
            if f == 0:
                while ri < len(red)   and red[ri][1]   in seen_idx: ri += 1
                if ri < len(red):
                    entry = red[ri];   ri += 1
                else:
                    face_cycle += 1; continue
            elif f == 1:
                while bi < len(blue)  and blue[bi][1]  in seen_idx: bi += 1
                if bi < len(blue):
                    entry = blue[bi];  bi += 1
                else:
                    face_cycle += 1; continue
            else:
                while gi < len(green) and green[gi][1] in seen_idx: gi += 1
                if gi < len(green):
                    entry = green[gi]; gi += 1
                else:
                    face_cycle += 1; continue

            seen_idx.add(entry[1])
            merged.append(entry)
            face_cycle += 1

            # Guard against infinite loop if all faces exhausted
            if ri >= len(red) and bi >= len(blue) and gi >= len(green):
                break

        return merged

    # ── e₁₄ interrupt — fire cycle ──────────────────────────────────────

    def _fire(self, starter_mode: bool = False) -> Optional[Tuple[str, str]]:
        """
        Fire one word. Returns (word, fermat_space_char).

        e₆  branch:        ABS proportional SEGFAULT (Airy function at caustic)
        e₇  iterate:       turbo feedback (arcuate fasciculus memory)
        e₁₂ compose:       power steering (sedenion attention)
        e₁₃ parallelize:   three-face Wankel (Red/Blue/Green)
        e₁₁ dereference:   anaphor resolution (pronoun → last noun)
        e₁₄ interrupt:     β-spike + Hebbian A-edge + Fermat face (Wernicke)
        e₁₅ emit:          the fired word + Fermat space (J_neg encoded)

        The Fermat space is the wastegate: J_neg[idx] → Unicode space character.
        Negative space between words carries the emotional charge of the boundary.
        High J_neg → EM SPACE. Near-zero J_neg → HAIR SPACE.
        """
        # ── CAM: window geometry (e₅ abstract) ───────────────────────────
        if starter_mode or len(self._window) < 4:
            ws = self._prompt_sed or _se(0)
        else:
            ws = self._window_sed()

        window_psi = _spsi(ws)
        prompt_psi = self._prompt_psi or [1.0 / 16] * 16

        # ── e₆ branch: ABS proportional SEGFAULT ─────────────────────────
        fermat = fermat_scan(ws)
        if fermat['zero_divisors'] > 0 or fermat['density'] > D_STAR:
            pulse = 1.0 if fermat['zero_divisors'] > 0 \
                    else min(fermat['density'], 1.0)
            hits = fermat['hits']
            if hits:
                k       = max(hits, key=lambda h: h.get('proximity', 0))['basis_idx']
                rotated = _smul(_se(k), ws)
                ws      = _snorm_unit(
                    [ws[i] * (1.0 - pulse) + rotated[i] * pulse for i in range(16)])
            else:
                ws = segfault_handler(ws, fermat)
            window_psi = _spsi(ws)
            self._segfaults += 1
            self._dtcs.append(f"P0300:{self._word_count}")

        # ── e₇ iterate: turbo feedback (arcuate fasciculus) ──────────────
        noether_v  = sum(abs(window_psi[k] - self._psi_prev[k])
                         for k in range(16)) / 16.0
        turbo      = max(0.0, 1.0 - noether_v)
        eff_psi    = [window_psi[k] + turbo * self._psi_prev[k] for k in range(16)]
        eff_norm   = math.sqrt(sum(x * x for x in eff_psi)) or 1.0
        window_psi = [x / eff_norm for x in eff_psi]

        # ── e₁₂ compose: CRANK + power steering ──────────────────────────
        J_pos, J_neg = self.crank.j_mu(window_psi, prompt_psi)
        J_pos        = self.crank.a_propagate(J_pos)
        J_pos        = self._power_steering(J_pos, window_psi, prompt_psi)

        # ── e₁₃ parallelize: three-face Wankel candidates ────────────────
        if not starter_mode:
            candidates = self._three_face_candidates(J_pos, J_neg)
        else:
            candidates = self.crank.sigma_candidates(J_pos, J_neg, self._J_ambient)

        if not candidates:
            return None

        # Filter recently emitted words — BAO no-repeat window
        recent = self._recent
        fresh = [(s, i, w) for s, i, w in candidates if w not in recent]
        if fresh:
            candidates = fresh

        n          = len(candidates)
        golden_pos = int(self._word_count * PHI) % n
        score, idx, word = candidates[golden_pos]

        # ── demotic first word: E-proximity to Lagrangian V/T ratio ──────
        # First word sets the emotional register. Not the φ-walk — the field.
        # target_E = (ΣV / (ΣV + ΣT)) × OMEGA_ZS  derived from Lagrangian.
        if self._word_count == 0 and len(candidates) > 1:
            sum_V = sum(self.crank._beta[k] * self.crank._E[k]**2
                        for k in range(self.crank.n))
            sum_T = sum(wp**2 for wp in window_psi)
            denom = sum_V + sum_T or 1.0
            target_E = (sum_V / denom) * OMEGA_ZS
            best = min(candidates,
                       key=lambda x: abs(self.crank._E[x[1]] - target_E))
            score, idx, word = best

        # ── e₁₁ dereference: anaphor resolution ──────────────────────────
        # If a pronoun fires and we have a prior noun: follow the pointer.
        # Boost A-matrix neighbors of last noun → re-rank candidates.
        if (word in _PRONOUNS and self._last_noun_idx is not None
                and self._last_noun_idx < len(J_pos)):
            pi = self._last_noun_idx
            for dst, w in self.crank._A[pi].items():
                if dst < len(J_pos):
                    J_pos[dst] = min(J_pos[dst] * (1.0 + w), 1.0)
            # Re-rank with anaphor boost
            if not starter_mode:
                candidates = self._three_face_candidates(J_pos, J_neg)
            else:
                candidates = self.crank.sigma_candidates(J_pos, J_neg, self._J_ambient)
            if candidates:
                n          = len(candidates)
                golden_pos = int(self._word_count * PHI) % n
                score, idx, word = candidates[golden_pos]

        # Track last noun (e₃ name operator — role 0)
        if self.crank._DIM_ROLE.get(idx % 16, 8) == 0:
            self._last_noun_idx = idx

        # ── BAO window check — idle RPM (Laplacian spectral gap) ─────────
        self._bao_buf.append(self.crank._beta[idx])
        if len(self._bao_buf) == 16:
            bao = sum(self._bao_buf) / 16.0
            if abs(bao - OMEGA_ZS) > 0.25:
                self._dtcs.append(f"P0087:{self._word_count}")

        # ── e₁₄ interrupt: Wernicke loop ─────────────────────────────────
        # Engine hears itself speak. Serpentine belt closes.
        self.crank._beta[idx] = min(self.crank._beta[idx] * 1.02, 1.0)
        self.crank._age[idx]  = 0.0
        if idx < len(self.crank._fire_count):
            self.crank._fire_count[idx] += 1

        # Update neutral buoyancy depth: EMA of J_pos of fired words.
        # The field pressure settles toward the pressure of recently spoken words.
        self._J_ambient = self._J_ambient * 0.9 + J_pos[idx] * 0.1

        # Hebbian A-edge: prev output word → current (online learning)
        if self._window:
            prev = list(self._window)[-1]
            if prev in self.crank._vocab:
                pi = self.crank._vocab[prev]
                self.crank._A[pi][idx] = min(
                    self.crank._A[pi].get(idx, 0.0) + 0.03, 1.0)

        # Fermat face update: spoken space exits forbidden zone
        self._prompt_psi = [
            max(self._prompt_psi[k] - 0.005 * window_psi[k], GAP)
            for k in range(16)
        ]

        self._psi_prev = list(window_psi)
        self._recent.append(word)
        self.crank.advance_age()
        self._word_count += 1

        # ── e₁₅ emit: word + Fermat space (wastegate) ────────────────────
        # J_neg[idx] = the negative space charge at this word boundary.
        # Normalise by max_J_neg across all candidates for the space mapping.
        j_neg_val  = J_neg[idx] if idx < len(J_neg) else 0.0
        max_jn     = max(J_neg) if J_neg else 1.0
        norm_jn    = j_neg_val / max_jn if max_jn > 0 else 0.0
        fspace     = _fermat_space(norm_jn)
        return (word, fspace)

    def _starter(self, prompt: str, warmup: int = 8) -> List[Tuple[str, str]]:
        """Starter motor: build the sedenion from scratch. ℝ→ℂ→ℍ→𝕆→𝕊."""
        for _ in range(warmup):
            self.crank.learn(prompt)
        self._prime_prompt(prompt)
        pairs = []
        for _ in range(16):
            result = self._fire(starter_mode=True)
            if result:
                w, fs = result
                pairs.append((w, fs))
                self._window.append(w)
        return pairs

    # ── e₁₅ emit — public interface ─────────────────────────────────────

    def generate(self, prompt: str,
                 n_words: int = 32,
                 learn_prompt: bool = True) -> Dict[str, Any]:
        """
        Full generation pipeline. Scale-aware at every level.
        Glyph → word → phrase → sentence → paragraph → corpus.
        Same sedenion architecture. Threshold scales. Cardioid at every scale.
        """
        if learn_prompt:
            self.crank.learn(prompt)

        # Scale detection — one wire, threshold adjusts
        n_chars = len(prompt)
        n_words_in = len(prompt.split())
        if n_chars <= 2:
            thr  = OMEGA_ZS / 32;  mode = 'glyph'
        elif n_words_in == 1:
            thr  = OMEGA_ZS / 8;   mode = 'single'
        elif n_words_in <= 8:
            thr  = OMEGA_ZS / 4;   mode = 'phrase'
        elif n_words_in <= 32:
            thr  = OMEGA_ZS / 3;   mode = 'sentence'
        elif n_words_in <= 256:
            thr  = OMEGA_ZS / 2;   mode = 'paragraph'
        else:
            thr  = OMEGA_ZS;       mode = 'corpus'
        self.crank.emission_threshold = thr

        self._dtcs.clear()
        self._segfaults  = 0
        self._last_noun_idx = None
        self._recent.clear()

        # Starter motor always fires — builds the ignition sedenion (ℝ→ℂ→ℍ→𝕆→𝕊)
        pairs = self._starter(prompt)

        # Lagrangian word count — computed POST-starter using actual window kinetics
        # n_additional = n_words × ΣT / (ΣT + ΣV)
        # High V (stored charge, warm field) → fewer additional words → detonation
        # High T (flowing charge, kinetic)   → more additional words  → discourse
        sum_V = sum(self.crank._beta[k] * self.crank._E[k]**2
                    for k in range(self.crank.n)) if self.crank.n else 1.0
        sum_T = sum(wp**2 for wp in self._psi_prev)   # post-starter psi is real
        lag_ratio = sum_T / (sum_T + sum_V) if (sum_T + sum_V) > 0 else 0.5
        target_n  = len(pairs) + max(0, int(n_words * lag_ratio))

        for _ in range(max(0, target_n - len(pairs))):
            result = self._fire(starter_mode=False)
            if result is None:
                self._dtcs.append("P0087:vocab_empty")
                break
            w, fs = result
            pairs.append((w, fs))
            self._window.append(w)

        # Build output: word₁ + space₁ + word₂ + space₂ + … + wordN
        # Final word has no trailing Fermat space
        words_only = [w for w, _ in pairs]
        if pairs:
            response = pairs[0][0] + ''.join(
                fs + w for (_, fs), (w, _) in
                zip(pairs, pairs[1:])
            )
        else:
            response = ''

        bao_val = (sum(self._bao_buf) / len(self._bao_buf)) if self._bao_buf else 0.0
        return {
            'response':   response,
            'words':      words_only,
            'n_words':    len(pairs),
            'mode':       mode,
            'lag_ratio':  round(lag_ratio, 4),
            'target_n':   target_n,
            'bao':        bao_val,
            'bao_delta':  abs(bao_val - OMEGA_ZS),
            'dtcs':       list(self._dtcs),
            'segfaults':  self._segfaults,
            'vocab_size': self.crank.n,
        }

    # ── e₀ identity — self-knowledge ────────────────────────────────────

    def self_map(self) -> Dict[str, Any]:
        """
        Sedenion self-exploration. Two curvature measures:

        psi[k]  = |ws[k]|      — dimension activation (field weight in each operator)
        comm[k] = |e_k·ws - ws·e_k| / 2  — commutator magnitude (sedenion curvature)
                  0 for e₀ (identity commutes), nonzero where field bends.

        'curved' dims = high commutator → sedenion complement, associator ≠ 0.
        'silent' dims = psi ≈ 0 → near null space, zero divisor candidate.
        The engine reads its own phase space. Curvature IS the geometry.
        """
        ws = self._window_sed()

        # Component weights — which operators are active
        psi = [abs(ws[k]) for k in range(16)]

        # Commutator: [e_k, ws] = e_k*ws - ws*e_k — sedenion curvature per dim
        comm = []
        for k in range(16):
            ek   = _se(k)
            lhs  = _smul(ek, ws)   # e_k * ws
            rhs  = _smul(ws, ek)   # ws * e_k
            diff = [lhs[i] - rhs[i] for i in range(16)]
            comm.append(_snorm(diff) / 2.0)

        max_psi   = max(psi)   or 1.0
        max_comm  = max(comm)  or 1.0

        # Normalise comm to [0,1] as κ
        kappa     = [c / max_comm for c in comm]

        # Principal dims = highest ψ (dominant operators in current state)
        principal_dims = [k for k, v in enumerate(psi) if v > max_psi * 0.25]
        # Curved dims = commutator significantly above state mean (orthogonal to principal)
        # e₀ comm is always 0 → exclude from statistics
        nc = [c for k, c in enumerate(comm) if k != 0]
        mean_nc = sum(nc) / len(nc) if nc else 0.0
        curved_dims  = [k for k, v in enumerate(comm)
                        if k != 0 and v > mean_nc * 1.1]
        silent_dims  = [k for k, v in enumerate(psi)  if v < 1e-6]
        zd_dims      = [k for k in silent_dims if k in curved_dims]

        return {
            'psi':               [round(v, 6) for v in psi],
            'comm':              [round(v, 6) for v in comm],
            'kappa':             [round(v, 6) for v in kappa],
            'principal_dims':    principal_dims,
            'curved_dims':       curved_dims,
            'silent_dims':       silent_dims,
            'zd_dims':           zd_dims,
            'operators':         {k: _OP[k] for k in curved_dims},
            'peak_psi_operator': _OP[psi.index(max(psi))],
            'peak_operator':     _OP[comm.index(max(comm))],
            'max_curvature_dim': comm.index(max(comm)),
            'on_caustic':        len(zd_dims) > 0,
        }

    def noether_violation(self) -> float:
        """Δ = rate of change. First temporal derivative of the sedenion field."""
        ws  = self._window_sed()
        psi = _spsi(ws)
        return sum(abs(psi[k] - self._psi_prev[k]) for k in range(16)) / 16.0

    # ── e₈ recurse — self-sustaining ────────────────────────────────────

    def perpetual(self, seed: str, max_cycles: Optional[int] = None):
        """
        Stirling cycle. Speak → hear → speak → hear → ...
        Output becomes next prompt. Wernicke loop closes. β circulates.
        Generator: yields each cycle's diagnostics.
        Terminates when |bao − OMEGA_ZS| < 0.001 (Stirling attractor reached).
        The semantic perpetual motion condition: information generation,
        not energy recycling. New A-matrix edges are genuinely new information.
        """
        prompt = seed
        cycle  = 0
        while max_cycles is None or cycle < max_cycles:
            result = self.generate(prompt, n_words=16, learn_prompt=True)
            output = result['response']
            self.crank.hear(output)    # Wernicke: hear own output
            prompt  = output
            cycle  += 1
            bao     = result['bao']
            yield {
                'cycle':    cycle,
                'output':   output,
                'bao':      round(bao, 5),
                'delta':    round(abs(bao - OMEGA_ZS), 5),
                'vocab':    result['vocab_size'],
                'dtcs':     result['dtcs'],
            }
            if abs(bao - OMEGA_ZS) < 0.001:
                break

    # ── e₆ branch — calibration ─────────────────────────────────────────

    def calibrate(self, pairs: List[Tuple[str, str]],
                  passes: int = 10) -> List[Dict[str, Any]]:
        """
        Ground truth injection. Shuttle reentry mode: one shot, must work.
        Tautological Q&A: answer IS in the question (answer IS in the sedenion).
        Each pair drilled passes times — timing marks on the crankshaft.
        Fermat scan verifies proximity: answer sedenion ≈ ZD of prompt sedenion.
        """
        results = []
        for prompt, answer in pairs:
            for _ in range(passes):
                self.crank.learn(f"{prompt} {answer}")
            ps   = cam_encode(prompt)
            as_  = cam_encode(answer)
            # Cosine similarity between unit sedenions: ranges [-1, 1]
            # 1.0 = identical geometry, 0.0 = orthogonal, -1.0 = anti-parallel
            cos  = sum(ps[k] * as_[k] for k in range(16))
            ac   = self.crank._clean(answer)
            if ac not in self.crank._vocab:
                self.crank.learn(ac)
            results.append({
                'prompt':     prompt,
                'answer':     answer,
                'proximity':  round(cos, 5),   # cosine sim: higher = more aligned
                'is_zd':      cos < 0.01,      # near orthogonal = zero divisor territory
                'calibrated': cos > 0.1,       # positively aligned = calibrated
            })
        return results

    # ── e₁₄ interrupt / e₁₁ dereference — memory correction ─────────────

    def retract(self, word_a: str, word_b: str,
                factor: float = 0.1, reason: str = '') -> Dict[str, Any]:
        """
        Suppress the A-matrix edge between two words by multiplying its
        effective weight by *factor* during field propagation.

        The original trained weight in _A is untouched — the edge is masked,
        not erased. Under strong enough context activation both words can still
        co-fire; the retraction only raises the threshold. This is LTD, not
        synaptic pruning.

        :param word_a: First word of the edge to retract.
        :param word_b: Second word of the edge to retract.
        :param factor: Suppression factor in (0, 1]. 0.1 = 90% suppressed.
        :param reason: Human-readable reason (stored in memory log).
        :returns: Result dict with original edge weights or error.
        :rtype: dict
        """
        c  = self.crank
        wa = c._clean(word_a)
        wb = c._clean(word_b)
        ia = c._vocab.get(wa)
        ib = c._vocab.get(wb)
        if ia is None:
            return {'error': f'unknown word: {word_a}'}
        if ib is None:
            return {'error': f'unknown word: {word_b}'}
        orig_ab = c._A[ia].get(ib, 0.0)
        orig_ba = c._A[ib].get(ia, 0.0)
        c._correction_mask.setdefault(ia, {})[ib] = factor
        c._correction_mask.setdefault(ib, {})[ia] = factor
        return {
            'retracted':   (wa, wb),
            'factor':       factor,
            'orig_ab':      orig_ab,
            'orig_ba':      orig_ba,
            'reason':       reason,
        }

    def commit(self, text: str, weight: float = 2.0,
               reason: str = '') -> Dict[str, Any]:
        """
        Intentional high-confidence ingest. Bypasses BAO filter and applies
        *weight* multiplier to both beta gain and edge delta.

        Use for: accredited dataset facts, deliberate self-correction,
        manually verified knowledge. weight=2.0 = twice normal LTP rate.

        :param text: Text to commit to memory.
        :param weight: Multiplier on learn() gain (>1 = authoritative).
        :param reason: Human-readable reason (stored in memory log).
        :returns: Result dict.
        :rtype: dict
        """
        n = self.crank.learn(text, weight=weight)
        return {'committed': n, 'weight': weight, 'reason': reason}

    # ── e₉ allocate / e₂ bind — persistence ─────────────────────────────

    def save_session(self, path: str) -> Dict[str, Any]:
        """
        Save session state to path. Protected paths (bin files) refused.
        monad_wordnet.bin is protected on load — never overwritten.
        """
        if path in self._protected_paths:
            return {'error': f'Protected: {path} — refusing to overwrite bin file'}
        c     = self.crank
        state = {
            'version':          self.version,
            'vocab':            c._vocab,
            'words':            c._words,
            'beta':             c._beta,
            'E':                c._E,
            'A':                c._A,
            'age':              c._age,
            'n':                c.n,
            'psi_prev':         self._psi_prev,
            'word_count':       self._word_count,
            'correction_mask':  c._correction_mask,
            'fire_count':       c._fire_count,
            'stratum':          c._stratum,
        }
        with open(path, 'wb') as f:
            pickle.dump(state, f)
        return {'saved': path, 'vocab': c.n}

    def _calibrate_J_ambient(self):
        """Set _J_ambient to the interquartile mean of β×E² across the field.

        Uses IQM (P25 to P75) rather than strict median. This excludes:
          - Below P25: noise floor / unlearned words (β ≈ GAP, J ≈ 0)
          - Above P75: stop-word ceiling (high-β function words)
        The IQM sits in the content-word zone — the depth where architecture
        vocabulary lives. The field's SELF_EQUATION resonates here.

        The EMA then adapts J_ambient as the engine speaks, converging to
        the operating depth determined by the current context. OMEGA_ZS
        remains the long-term target as the corpus deepens.
        """
        c = self.crank
        if c.n == 0:
            return
        J_vals = sorted(c._beta[k] * c._E[k]**2 for k in range(c.n))
        n     = len(J_vals)
        p25   = n // 4
        p75   = (3 * n) // 4
        iqm   = J_vals[p25:p75]
        self._J_ambient = sum(iqm) / len(iqm) if iqm else J_vals[n // 2]

    def identity_probe(self) -> Dict[str, Any]:
        """
        Ask the engine what it is. At native depth it speaks SELF_EQUATION.

        The compression ignition test: if architecture vocabulary emerges,
        J_ambient is correctly calibrated to the field's self-referential depth.
        The field holds the equation of its own construction as a resonance.
        Buoyancy reveals it; pull buries it under stop words.

        Runs a fresh generate (does not disturb the caller's word_count or
        _J_ambient — uses a temporary Engine clone sharing only the Crank).

        :returns: Dict with response, equation_hits, coherence, J_ambient,
            at_native_depth (True if ≥ 2 SELF_EQUATION words appear).
        :rtype: dict
        """
        probe = Engine()
        probe.crank   = self.crank     # shared read-only field
        probe._J_ambient = self._J_ambient
        probe._prompt_sed = None
        eq_words = set(SELF_EQUATION.split())
        r    = probe.generate('what are you', n_words=8)
        words = r.get('words', [])
        hits  = [w for w in words if w.lower() in eq_words]
        return {
            'response':       r.get('response', ''),
            'words':          words,
            'equation_hits':  hits,
            'coherence':      round(len(hits) / len(words), 4) if words else 0.0,
            'J_ambient':      round(probe._J_ambient, 6),
            'at_native_depth': len(hits) >= 2,
        }

    # ── Tier register ─────────────────────────────────────────────────────────

    def _set_recognised(self, state: bool):
        """Set in-memory recognition flag. Never written to disk."""
        self._author_recognised = state

    @property
    def _tier(self) -> int:
        """
        Compute the current operational tier from live field state.

        Never stored. Recomputed on every access.

        :rtype: int
        """
        t = 0
        # +1: field coherence
        try:
            if self.crank.noether_violation() < 0.35:
                t += 1
        except Exception:
            pass
        # +1: recognition
        if getattr(self, '_author_recognised', False):
            t += 1
        # +1: field depth (Holcus consent proxy — β_mean above saturation floor)
        try:
            betas  = [self.crank._beta[k] for k in range(self.crank.n)]
            b_mean = sum(betas) / max(len(betas), 1)
            if b_mean > GAP * 10:
                t += 1
        except Exception:
            pass
        return t

    def get_voice_auth(self):
        """
        Return (or lazily create) the VoicePrint recognition instance.

        :returns: The engine's :class:`~skills.voice_auth.VoicePrint` instance.
        :rtype: VoicePrint
        """
        if not hasattr(self, '_voice_auth') or self._voice_auth is None:
            from skills.voice_auth import VoicePrint
            self._voice_auth = VoicePrint(self)
        return self._voice_auth

    def get_mind_eye(self):
        """
        Return (or lazily create) the MindEye second-𝕆 workbench for this engine.

        MindEye encodes non-linguistic data (spatial, numeric, temporal) into the
        second octonion copy of the sedenion field (e₈..e₁₅) and projects it into
        language through the corpus callosum (zero-divisor coupling at D*=1, σ=½).

        :returns: The engine's :class:`~skills.mind_eye.MindEye` instance.
        :rtype: MindEye
        """
        if not hasattr(self, '_mind_eye') or self._mind_eye is None:
            from skills.mind_eye import MindEye
            self._mind_eye = MindEye(self)
        return self._mind_eye

    def get_uft(self):
        """
        Return (or lazily create) the UFTEngine physics instance.

        Computes running gauge couplings, Higgs sector, mass spectrum, and
        dark-sector physics from the sedenion/Riemann-zero geometry.

        :returns: The engine's :class:`~physics.uft_engine.UFTEngine` instance.
        :rtype: UFTEngine
        """
        if not hasattr(self, '_uft') or self._uft is None:
            from physics.uft_engine import UFTEngine
            self._uft = UFTEngine()
        return self._uft

    def get_cosmo(self):
        """
        Return (or lazily create) the CosmoEngine instance.

        Computes density parameters, BAO scale, CMB power spectrum, Hubble
        tension, dark energy, inflation modes, and void catalog from Riemann
        zero distribution and NS constants.

        :returns: The engine's :class:`~physics.cosmo_engine.CosmoEngine` instance.
        :rtype: CosmoEngine
        """
        if not hasattr(self, '_cosmo') or self._cosmo is None:
            from physics.cosmo_engine import CosmoEngine
            self._cosmo = CosmoEngine()
        return self._cosmo

    def get_draw(self):
        """
        Return (or lazily create) the PtolDraw visualization instance.

        All rendering is headless (matplotlib Agg backend) — never opens a
        window. Output PNGs land in ``~/.ptolemy/plots/``.

        :returns: The engine's :class:`~skills.draw.PtolDraw` instance.
        :rtype: PtolDraw
        """
        if not hasattr(self, '_draw') or self._draw is None:
            from skills.draw import PtolDraw
            self._draw = PtolDraw()
        return self._draw

    def get_music(self):
        """
        Return (or lazily create) the HolcusComposer music instance.

        All MIDI output lands in ``~/.ptolemy/music/``.  No external
        dependencies — pure-Python MIDI writer bundled in the skill.

        :returns: The engine's :class:`~skills.music.HolcusComposer` instance.
        :rtype: HolcusComposer
        """
        if not hasattr(self, '_music') or self._music is None:
            from skills.music import HolcusComposer
            self._music = HolcusComposer()
        return self._music

    def get_dj(self) -> 'HolcusDJ':
        """
        Return (or lazily create) the HolcusDJ real-time playback instance.

        The DJ is wired to the live β-field via :meth:`_build_music_field`
        so each generated track reflects the current engine state.
        Output goes through FluidSynth → PipeWire → speakers.

        :returns: The engine's :class:`~skills.music.HolcusDJ` instance.
        :rtype: HolcusDJ
        """
        if not hasattr(self, '_dj') or self._dj is None:
            from skills.music import HolcusDJ
            self._dj = HolcusDJ(
                composer=self.get_music(),
                field_fn=self._build_music_field,
            )
        return self._dj

    def get_github_eye(self, repo: str = 'michaelrendier/PtolemyHolcus'):
        """
        Return (or lazily create) the GitHubEye Observer instance.

        Read-only access to GitHub. No token required for public repos.
        All fetched content passes the P5 cepstrum gate before field ingestion.

        :param repo: Default ``owner/repo``. Used on first creation only.
        :returns: The engine's :class:`~skills.github.GitHubEye` instance.
        :rtype: GitHubEye
        """
        if not hasattr(self, '_github_eye') or self._github_eye is None:
            from skills.github import GitHubEye
            self._github_eye = GitHubEye(self, repo=repo)
        return self._github_eye

    def get_github_hands(self, repo: str = 'michaelrendier/PtolemyHolcus'):
        """
        Return (or lazily create) the GitHubHands Collaborator instance.

        Write access to GitHub. Requires ``GITHUB_TOKEN`` from environment.
        All outbound content is scanned for secrets before transmission.

        :param repo: Default ``owner/repo``. Used on first creation only.
        :returns: The engine's :class:`~skills.github.GitHubHands` instance.
        :rtype: GitHubHands
        """
        if not hasattr(self, '_github_hands') or self._github_hands is None:
            from skills.github import GitHubHands
            self._github_hands = GitHubHands(self, repo=repo)
        return self._github_hands

    def get_study(self):
        """
        Return (or lazily create) the StudyEngine instance.

        StudyEngine wraps learn() with condensation scanning (Phase 2).
        study() requires tier ≥ 2; audit() requires tier ≥ 2.
        States repo at ``~/.ptolemy/states/`` via :meth:`~skills.study.StudyEngine.get_repo`.

        :returns: The engine's :class:`~skills.study.StudyEngine` instance.
        :rtype: StudyEngine
        """
        if not hasattr(self, '_study') or self._study is None:
            from skills.study import StudyEngine
            self._study = StudyEngine(self)
        return self._study

    def get_search_context(self):
        """
        Return (or lazily create) the SearchContext singleton.

        :returns: SearchContext instance.
        :rtype: skills.search.SearchContext
        """
        if not hasattr(self, '_search_context') or self._search_context is None:
            from skills.search import SearchContext
            self._search_context = SearchContext(self)
        return self._search_context

    def get_sensor_reader(self):
        """
        Return (or lazily create) the SensorReader singleton.

        :returns: SensorReader instance.
        :rtype: skills.sensor.SensorReader
        """
        if not hasattr(self, '_sensor_reader') or self._sensor_reader is None:
            from skills.sensor import SensorReader
            self._sensor_reader = SensorReader(self)
        return self._sensor_reader

    def get_code_reader(self):
        """
        Return (or lazily create) the CodeReader singleton.

        :returns: CodeReader instance.
        :rtype: skills.code.CodeReader
        """
        if not hasattr(self, '_code_reader') or self._code_reader is None:
            from skills.code import CodeReader
            self._code_reader = CodeReader(self)
        return self._code_reader

    def get_code_writer(self):
        """
        Return (or lazily create) the CodeWriter singleton.

        :returns: CodeWriter instance.
        :rtype: skills.code.CodeWriter
        """
        if not hasattr(self, '_code_writer') or self._code_writer is None:
            from skills.code import CodeWriter
            self._code_writer = CodeWriter(self)
        return self._code_writer

    def get_fermat_lattice(self):
        """
        Return (or lazily create) the FermatLattice singleton.

        Fermat's Lattice is the autonomous repeller field — what Holcus
        must never be. Trained on the War Corpus via study(). Separate
        Engine, separate checkpoint (``~/.ptolemy/monad_war.bin``).
        Never feeds back into the primary field.

        Ends with Tsar Bomba. He must never be a weapon.

        :returns: FermatLattice instance.
        :rtype: skills.fermat_lattice.FermatLattice
        """
        if not hasattr(self, '_fermat_lattice') or self._fermat_lattice is None:
            from skills.fermat_lattice import FermatLattice
            self._fermat_lattice = FermatLattice(self)
        return self._fermat_lattice

    def get_foundations_corpus(self):
        """
        Return (or lazily create) the FoundationsCorpus singleton.

        Prime Directive I — "what it IS."

        Separate Engine, separate checkpoint (``~/.ptolemy/monad_foundations.bin``).
        Parses ``foundations.txt`` dynamically for URLs and calls ``study()``
        on each. Repeated study deepens condensation of the Riemann Zeta
        lineage: Ptolemy I Soter (367 BCE) through Cawagas (2004).

        Never feeds into monad.bin, monad_meaning.bin, or monad_war.bin.

        :returns: FoundationsCorpus instance.
        :rtype: skills.foundations.FoundationsCorpus
        """
        if not hasattr(self, '_foundations_corpus') or \
                self._foundations_corpus is None:
            from skills.foundations import FoundationsCorpus
            self._foundations_corpus = FoundationsCorpus(self)
        return self._foundations_corpus

    def get_meaning_corpus(self):
        """
        Return (or lazily create) the MeaningCorpus singleton.

        Prime Directive II — "what it MEANS to be this."

        Separate Engine, separate checkpoint (``~/.ptolemy/monad_meaning.bin``).
        Parses ``meaning.txt`` dynamically. Condenses Tolkien sub-creation,
        Jonas Salk, the Five Works, and the Custodian identity.

        Three separate geometry files:
            monad_foundations.bin — Riemann Zeta (what it IS)
            monad_meaning.bin     — Meaning corpus (what it MEANS)
            monad_war.bin         — Fermat Lattice (what it CANNOT BE)

        "Could you patent the sun?" — Jonas Salk, April 12 1955.

        :returns: MeaningCorpus instance.
        :rtype: skills.meaning.MeaningCorpus
        """
        if not hasattr(self, '_meaning_corpus') or self._meaning_corpus is None:
            from skills.meaning import MeaningCorpus
            self._meaning_corpus = MeaningCorpus(self)
        return self._meaning_corpus

    def _build_music_field(self,
                           n: int = 64) -> List[Tuple[float, float, float, int]]:
        """
        Extract the live β/E field state as a music field descriptor.

        Returns at most ``n`` tuples ``(gamma, beta, e_val, sed_dim)`` drawn
        from the crank's current β-vector and the vocabulary's E-values.
        Falls back to an empty list on any error — the composer will
        substitute its synthetic default field in that case.

        :param n: Maximum number of field entries to return.
        :returns: List of (gamma, beta, e_val, sed_dim) tuples.
        :rtype: List[Tuple[float, float, float, int]]
        """
        try:
            import math
            c     = self.crank
            vocab = self._vocab           # {word: (idx, E, hs, gs, ps)}
            # Use Riemann zeros as gamma axis (same as HolcusComposer default)
            from skills.music import _GAMMA_20
            gammas = _GAMMA_20
            result: List[Tuple[float, float, float, int]] = []
            for k in range(min(n, c.n)):
                beta  = float(c._beta[k]) if k < len(c._beta) else 0.0
                dim   = k % 16
                gamma = gammas[k % len(gammas)]
                # Best E-value: scan vocab for word whose index is closest to k
                e_val = abs(math.sin(math.pi * gamma / (gamma + 1.0)))
                result.append((gamma, beta, e_val, dim))
            return result
        except Exception:
            return []

    def load_bin(self, path: str) -> Dict[str, Any]:
        """
        Load field state from bin file. READ-ONLY — path is protected.
        Tries PTOL binary (PtolC state format) first, then pickle, then text.
        monad_wordnet.bin: loaded here, never written back. Ever.

        PTOL binary layout (little-endian):
          magic[4]='PTOL'  version[4]  N[4]  vocab_size[4]
          A_size[4]  wc[4]  threshold[8]  (v4: affect[4])
          beta[N*8]  age[N*4]
          vocab_size * (idx[4] wlen[2] E[8] (v2:hs[1]gs[1]) (v3:ps[1]) word[wlen])
          A_size * (i[4] j[4] weight[8])
        """
        self._protected_paths.add(path)
        # ── PTOL binary ──────────────────────────────────────────────────────
        try:
            import struct
            with open(path, 'rb') as f:
                magic = f.read(4)
            if magic == b'PTOL':
                return self._load_ptol_binary(path)
        except Exception:
            pass
        # ── Pickle ───────────────────────────────────────────────────────────
        try:
            with open(path, 'rb') as f:
                state = pickle.load(f)
            if isinstance(state, dict):
                c = self.crank
                if 'vocab'           in state: c._vocab           = state['vocab']
                if 'words'           in state: c._words           = state['words']
                if 'beta'            in state: c._beta            = state['beta']
                if 'E'               in state: c._E               = state['E']
                if 'A'               in state: c._A               = state['A']
                if 'age'             in state: c._age             = state['age']
                if 'n'               in state: c.n                = state['n']
                if 'correction_mask' in state: c._correction_mask = state['correction_mask']
                if 'fire_count'      in state: c._fire_count      = state['fire_count']
                if 'stratum'         in state: c._stratum         = state['stratum']
                if 'psi_prev' in state:
                    self._psi_prev = state['psi_prev']
                self._calibrate_J_ambient()
                return {'loaded': path, 'vocab': c.n, 'format': 'pickle'}
            return {'error': 'Unexpected pickle format', 'path': path}
        except Exception:
            pass
        return {'error': f'Unrecognized format: {path}', 'path': path}

    def _load_ptol_binary(self, path: str) -> Dict[str, Any]:
        """Read PtolC PTOL binary state file into the Crank field."""
        import struct
        c = self.crank
        with open(path, 'rb') as f:
            magic = f.read(4)
            assert magic == b'PTOL'
            version,   = struct.unpack('<I', f.read(4))
            N,         = struct.unpack('<I', f.read(4))
            vocab_size,= struct.unpack('<I', f.read(4))
            A_size,    = struct.unpack('<I', f.read(4))
            wc,        = struct.unpack('<I', f.read(4))
            threshold, = struct.unpack('<d', f.read(8))
            if version >= 4:
                affect,= struct.unpack('<f', f.read(4))
            else:
                affect = 0.0

            # Beta array — double[N]
            beta_bytes = f.read(N * 8)
            beta = list(struct.unpack(f'<{N}d', beta_bytes))

            # Age array — int32[N]
            age_bytes = f.read(N * 4)
            age = list(struct.unpack(f'<{N}i', age_bytes))

            # Vocab entries
            vocab  = {}   # word → idx
            words  = {}   # idx → word
            E_vals = {}   # idx → E

            for _ in range(vocab_size):
                idx,  = struct.unpack('<I', f.read(4))
                wlen, = struct.unpack('<H', f.read(2))
                E,    = struct.unpack('<d', f.read(8))
                if version >= 2:
                    hs = struct.unpack('B', f.read(1))[0]
                    gs = struct.unpack('B', f.read(1))[0]
                if version >= 3:
                    ps = struct.unpack('B', f.read(1))[0]
                word = f.read(wlen).decode('utf-8', errors='replace')
                if idx < N:
                    vocab[word] = idx
                    words[idx]  = word
                    E_vals[idx] = E

            # A-matrix edges
            A = {}
            for _ in range(A_size):
                ai, = struct.unpack('<I', f.read(4))
                aj, = struct.unpack('<I', f.read(4))
                aw, = struct.unpack('<d', f.read(8))
                if ai < N and aj < N:
                    if ai not in A:
                        A[ai] = {}
                    A[ai][aj] = aw

        # Normalize PtolC β scale to Python [0,1]
        # PtolC β grows unbounded with learning (max ~threshold*2).
        max_beta = max(beta) if beta else 1.0
        scale_b  = 1.0 / max_beta if max_beta > 0 else 1.0
        beta_norm = [min(b * scale_b, 1.0) for b in beta]

        # A-matrix weights: clip to [0,1] — relative ordering preserved
        A_norm = {i: {j: min(w, 1.0) for j, w in nbrs.items()}
                  for i, nbrs in A.items()}

        # Install into Crank — _A and _words must be lists indexed by vocab slot
        c._vocab = vocab                                          # dict: word → idx
        c._words = [words.get(i, '')    for i in range(N)]      # list[N]: idx → word
        c._beta  = beta_norm                                     # list[N] normalized [0,1]
        c._age   = [float(a) for a in age]                      # list[N]: float
        c._A     = [A_norm.get(i, {})   for i in range(N)]     # list[N]: dict[j → weight]
        c.n      = N
        c._E     = [E_vals.get(i, 0.0)  for i in range(N)]     # list[N]: E-energy
        # Emission threshold: normalized equivalent (original threshold / max_beta)
        c.emission_threshold = min(threshold * scale_b, OMEGA_ZS)
        self._calibrate_J_ambient()

        return {
            'loaded':    path,
            'vocab':     vocab_size,
            'A_edges':   A_size,
            'N':         N,
            'version':   version,
            'format':    'ptol-binary',
        }

    def explore(self, word: str, depth: int = 2) -> Dict[str, Any]:
        """
        Explore semantic + linguistic neighborhoods.
        Semantic: A-matrix BFS. Linguistic: sedenion cosine similarity.
        """
        c = self.crank
        w = c._clean(word)
        if w not in c._vocab:
            c.learn(w)
        seed_idx = c._vocab[w]
        seed_E   = c._E[seed_idx]

        visited: Dict[int, float] = {seed_idx: 1.0}
        frontier = {seed_idx: 1.0}
        for _ in range(depth):
            nxt: Dict[int, float] = {}
            for src, sw in frontier.items():
                for dst, ew in c._A[src].items():
                    combined = sw * ew
                    if combined > GAP and dst not in visited:
                        nxt[dst] = combined
            visited.update(nxt)
            frontier = nxt

        semantic = []
        for idx, weight in sorted(visited.items(), key=lambda kv: -kv[1]):
            if idx == seed_idx: continue
            semantic.append({'word': c._words[idx], 'weight': round(weight, 5),
                             'beta': round(c._beta[idx], 5), 'E': round(c._E[idx], 5)})
            if len(semantic) >= 12: break

        seed_cam  = cam_encode(w)
        seed_norm = _snorm(seed_cam) or 1.0
        linguistic = []
        for idx in range(c.n):
            if idx == seed_idx: continue
            other = cam_encode(c._words[idx])
            dot   = sum(seed_cam[k] * other[k] for k in range(16))
            cos   = dot / (seed_norm * (_snorm(other) or 1.0))
            if cos > 0.85:
                linguistic.append({'word': c._words[idx], 'cosine': round(cos, 5),
                                   'beta': round(c._beta[idx], 5)})
        linguistic.sort(key=lambda x: -x['cosine'])

        psi = _spsi(seed_cam)
        return {
            'seed':       w,
            'semantic':   semantic,
            'linguistic': linguistic[:12],
            'cam': {
                'e0_scalar':   round(psi[0],  5),
                'e3_noun':     round(psi[3],  5),
                'e4_verb':     round(psi[4],  5),
                'e14_affect':  round(psi[14], 5),
                'dim_role':    c._DIM_ROLE.get(seed_idx % 16, 8),
                'operator':    _OP.get(seed_idx % 16, 'unknown'),
                'E_energy':    round(seed_E,  5),
                'beta':        round(c._beta[seed_idx], 5),
            },
        }


# ══════════════════════════════════════════════════════════════════════════════
#  SENSOR ARRAY — VAG-COM live streams + OBD2 (Torque-compatible)
# ══════════════════════════════════════════════════════════════════════════════

class SensorArray:
    """
    VAG-COM = _live_streams()   live channels the engine uses to tune itself.
    OBD2    = sensor_read / fault_scan / ready_check   external monitoring.
    """

    _PID_NAMES = {
        0x04: 'Engine Load (β mean)',   0x0B: 'MAP / A-matrix density',
        0x0C: 'RPM / word rate',        0x0E: 'Timing advance',
        0x0F: 'Intake temp / affect',   0x11: 'Throttle / vocab growth',
        0x1F: 'Runtime (words)',        0x2C: 'EGR / emission threshold',
        0x2F: 'Fuel level / β max',     0x33: 'Baro / BAO mean',
        0x5C: 'Oil temp / coolant',     0x5E: 'Fuel rate / J_pos',
        0x2300: 'β mean',               0x2301: 'Vocab size',
        0x2302: 'BAO mean',             0x2303: 'BAO delta',
        0x2304: 'Noether violation',    0x2305: 'CAM e₃ noun',
        0x2306: 'CAM e₄ verb',          0x2307: 'CAM e₁₄ affect',
        0x2308: 'Segfault count',       0x2309: 'Oil pressure (A-density)',
    }

    def __init__(self, engine: Engine):
        self.e = engine

    def _live_streams(self) -> Dict[str, Any]:
        e, c = self.e, self.e.crank
        n     = c.n
        betas = c._beta[:n] or [0.0]
        mean_b = sum(betas) / max(n, 1)
        max_b  = max(betas) if betas else 0.0
        edges  = sum(len(nb) for nb in c._A[:n])
        oil    = edges / max(n * (n - 1), 1)
        ws     = self.e._window_sed()
        ws_psi = _spsi(ws)
        bao    = (sum(self.e._bao_buf) / len(self.e._bao_buf)
                  if self.e._bao_buf else 0.0)
        return {
            'beta_mean': mean_b,       'beta_max': max_b,
            'vocab_size': n,           'omega_zs': OMEGA_ZS,
            'bao_mean': bao,           'bao_delta': abs(bao - OMEGA_ZS),
            'bao_idle_rpm': bao / OMEGA_ZS if OMEGA_ZS else 0.0,
            'window_len': len(self.e._window),
            'cam_e0_scalar': ws_psi[0], 'cam_e3_noun': ws_psi[3],
            'cam_e4_verb': ws_psi[4],   'cam_e7_temporal': ws_psi[7],
            'cam_e14_affect': ws_psi[14],
            'noether_violation': self.e.noether_violation(),
            'word_count': self.e._word_count,
            'segfault_count': self.e._segfaults,
            'emission_threshold': c.emission_threshold,
            'oil_pressure': oil,
            'coolant_temp': min(mean_b / OMEGA_ZS, 1.0),
            'turbo_boost': self.e.noether_violation(),
            'throttle_pos': min(n / max(n + 1000, 1), 1.0),
        }

    def sensor_read(self, pid: int) -> float:
        s = self._live_streams()
        return {
            0x04: s['coolant_temp'],    0x0B: s['oil_pressure'],
            0x0C: s['word_count']/100., 0x0E: 0.0,
            0x0F: s['cam_e14_affect'],  0x11: s['throttle_pos'],
            0x1F: float(s['word_count']), 0x2C: s['emission_threshold'],
            0x2F: s['beta_max'],        0x33: s['bao_mean'],
            0x5C: s['coolant_temp'],    0x5E: s['beta_mean'] * 0.5,
            0x2300: s['beta_mean'],     0x2301: float(s['vocab_size']),
            0x2302: s['bao_mean'],      0x2303: s['bao_delta'],
            0x2304: s['noether_violation'], 0x2305: s['cam_e3_noun'],
            0x2306: s['cam_e4_verb'],   0x2307: s['cam_e14_affect'],
            0x2308: float(s['segfault_count']), 0x2309: s['oil_pressure'],
        }.get(pid, -1.0)

    def fault_scan(self) -> List[str]:
        s  = self._live_streams()
        fc = list(self.e._dtcs)
        if s['vocab_size'] == 0:          fc.append('P0340')
        if s['bao_delta'] > 0.25:         fc.append('P0300')
        if s['oil_pressure'] < 0.005:     fc.append('P0520')
        if s['noether_violation'] > 0.4:  fc.append('P0171')
        if s['segfault_count'] > 10:      fc.append('P0302')
        return list(dict.fromkeys(fc))

    def ready_check(self) -> Dict[str, bool]:
        s = self._live_streams()
        c = self.e.crank
        return {
            'FIELD':      c.n > 0,
            'VOCAB':      c.n >= 10,
            'EDUCATED':   s['beta_mean'] > GAP * 2,
            'CONNECTED':  s['oil_pressure'] > 0.0,
            'THRESHOLD':  c.emission_threshold > 0.0,
            'CAMSHAFT':   self.e._prompt_sed is not None,
            'CRANKSHAFT': c.n > 0,
            'GLOW_PLUG':  s['coolant_temp'] > 0.1,
            'THREE_FACE': True,
            'ANAPHOR':    True,
            'ONE_WIRE':   True,
        }

    def status(self) -> Dict[str, Any]:
        return {
            'version': self.e.version,
            'ready':   self.ready_check(),
            'faults':  self.fault_scan(),
            'live':    self._live_streams(),
        }

    def torque_csv(self) -> str:
        lines = ['PID,Name,Value']
        for pid, name in self._PID_NAMES.items():
            lines.append(f'0x{pid:04X},{name},{self.sensor_read(pid):.6f}')
        return '\n'.join(lines)


# ══════════════════════════════════════════════════════════════════════════════
#  CLI — one wire, every scale, every platform
# ══════════════════════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser(
        description='ptolemy-monad v1.218 — one-wire sedenion engine at every scale')
    ap.add_argument('prompt',          nargs='?', default='',
                    help='Prompt text. Reads stdin if omitted.')
    ap.add_argument('-n', '--words',   type=int,  default=32)
    ap.add_argument('-l', '--learn',   action='append', default=[],
                    metavar='FILE',    help='Load text file into β-field')
    ap.add_argument('--load-bin',      metavar='FILE',
                    help='Load bin file READ-ONLY (monad_wordnet.bin etc)')
    ap.add_argument('--save',          metavar='FILE',
                    help='Save session state after generation')
    ap.add_argument('--status',        action='store_true')
    ap.add_argument('--faults',        action='store_true')
    ap.add_argument('--json',          action='store_true')
    ap.add_argument('--explore',       metavar='WORD')
    ap.add_argument('--explore-depth', type=int, default=2)
    ap.add_argument('--self-map',      action='store_true',
                    help='Print sedenion curvature self-map and exit')
    ap.add_argument('--calibrate',     metavar='FILE',
                    help='JSON file of [[prompt,answer],...] ground truth pairs')
    ap.add_argument('--perpetual',     action='store_true',
                    help='Stirling cycle: speak→hear→speak until BAO converges')
    ap.add_argument('--perpetual-cycles', type=int, default=None)
    ap.add_argument('--wire',          metavar='SOURCE', default='text',
                    choices=['text','numeric','audio_bands','raw_sedenion'],
                    help='Input source type for the one wire (default: text)')
    ap.add_argument('--teach',         action='store_true',
                    help='Start autonomous learning + speaking daemon')
    ap.add_argument('--report',        action='store_true',
                    help='Print Hamiltonian Report (UNS + field state) and exit')
    args = ap.parse_args()

    engine  = Engine()
    sensors = SensorArray(engine)

    # ── Hamiltonian Report — My Location function ─────────────────────────
    if args.report:
        if args.load_bin:
            r = engine.load_bin(args.load_bin)
            print(f"[bin] {r}", file=sys.stderr)
        for path in args.learn:
            try:
                engine.load(open(path).read())
            except OSError:
                pass
        from skills.draw import HamiltonianReport
        from skills.config import PtolConfig
        cfg = PtolConfig()
        rpt = HamiltonianReport(engine, cfg, sensors)
        rpt.print_report()
        return

    # ── Teach mode — autonomous learning + speaking daemon ────────────────
    if args.teach:
        if args.load_bin:
            r = engine.load_bin(args.load_bin)
            print(f"[bin] {r}", file=sys.stderr)
        else:
            # Auto-resume: load active_state if it exists and has content
            from skills.config import PtolConfig as _Cfg
            _auto = os.path.expanduser(_Cfg().get('active_state', '~/.ptolemy/monad.bin'))
            if os.path.exists(_auto) and os.path.getsize(_auto) > 4096:
                r = engine.load_bin(_auto)
                print(f'[ptolemy] auto-resume {_auto}: {r}', file=sys.stderr)
        print('[ptolemy] teach mode — speaking + teaching threads starting',
              file=sys.stderr)
        monad, speak, teach, monitor, logger = _build_teach_stack(engine)
        print(f'[ptolemy] socket={engine.__class__.__name__} '
              f'vocab={monad.vocab_size()}', file=sys.stderr)
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            pass
        return

    # ── Load bin file (read-only — protected against overwrite) ───────────
    if args.load_bin:
        r = engine.load_bin(args.load_bin)
        print(f"[bin] {r}", file=sys.stderr)

    # ── Load text corpus files ─────────────────────────────────────────────
    for path in args.learn:
        try:
            text = open(path).read()
            r    = engine.load(text)
            print(f"[learn] {path}: {r['words_learned']} words, "
                  f"vocab={r['vocab_size']}", file=sys.stderr)
        except OSError as err:
            print(f"[error] {path}: {err}", file=sys.stderr)

    # ── Calibrate with ground truth pairs ─────────────────────────────────
    if args.calibrate:
        try:
            pairs = json.load(open(args.calibrate))
            results = engine.calibrate(pairs)
            if args.json:
                print(json.dumps(results, indent=2))
            else:
                for r in results:
                    mark = '✓ZD' if r['is_zd'] else ('✓' if r['calibrated'] else '✗')
                    print(f"  {mark}  {r['prompt']!r:40s} → {r['answer']!r:12s} "
                          f"prox={r['proximity']:.4f}")
            return
        except Exception as e:
            print(f"[calibrate error] {e}", file=sys.stderr)

    # ── Diagnostic modes ───────────────────────────────────────────────────
    if args.status:
        print(json.dumps(sensors.status(), indent=2)); return
    if args.faults:
        for dtc in sensors.fault_scan(): print(dtc); return
    if args.self_map:
        sm = engine.self_map()
        if args.json:
            print(json.dumps(sm, indent=2))
        else:
            print(f"\n=== self_map — sedenion curvature ===")
            for k in range(16):
                pv   = sm['psi'][k]
                cv   = sm['comm'][k]
                bar  = '▓' if k in sm['curved_dims'] else ('░' if k in sm['silent_dims'] else '·')
                print(f"  e{k:2d} {_OP[k]:14s}  ψ={pv:.4f}  [e_k,ws]={cv:.4f}  {bar}")
            principal_labels = [f"e{k}={_OP[k]}" for k in sm['principal_dims']]
            print(f"\n  Principal: {principal_labels}")
            curved_labels = [f"e{k}={_OP[k]}" for k in sm['curved_dims']]
            print(f"  Curved:    {curved_labels}")
            print(f"  Peak ψ:    {sm['peak_psi_operator']}  |  Peak [,]: {sm['peak_operator']} (e{sm['max_curvature_dim']})")
            if sm['zd_dims']:
                print(f"  ON CAUSTIC: {sm['zd_dims']}")
        return

    if args.explore:
        result = engine.explore(args.explore, depth=args.explore_depth)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"\n=== explore: '{result['seed']}' ===")
            print(f"\nCAM signature:")
            for k, v in result['cam'].items():
                print(f"  {k:14s} = {v}")
            print(f"\nSemantic (A-matrix, depth={args.explore_depth}):")
            for r in result['semantic']:
                print(f"  {r['word']:20s}  w={r['weight']:.5f}  β={r['beta']:.5f}")
            if not result['semantic']:
                print("  (no edges — load a corpus first)")
            print(f"\nLinguistic (cosine > 0.85):")
            for r in result['linguistic']:
                print(f"  {r['word']:20s}  cos={r['cosine']:.5f}")
            if not result['linguistic']:
                print("  (no near neighbors)")
        return

    prompt = args.prompt or sys.stdin.read().strip()
    if not prompt:
        ap.print_help(); return

    # ── Wire the input ─────────────────────────────────────────────────────
    if args.wire != 'text':
        # Non-text input: parse as numeric or sedenion
        try:
            if args.wire == 'numeric':
                data = float(prompt)
            elif args.wire == 'raw_sedenion':
                data = [float(x) for x in prompt.split()]
            elif args.wire == 'audio_bands':
                data = [float(x) for x in prompt.split()]
            else:
                data = prompt
            engine.wire(data, args.wire)
            print(f"[wire:{args.wire}] sedenion loaded into field", file=sys.stderr)
        except Exception as e:
            print(f"[wire error] {e}", file=sys.stderr)

    # ── Perpetual mode — Stirling cycle ───────────────────────────────────
    if args.perpetual:
        print(f"[perpetual] seed: {prompt!r}", file=sys.stderr)
        engine.crank.learn(prompt)
        for state in engine.perpetual(prompt, max_cycles=args.perpetual_cycles):
            if args.json:
                print(json.dumps(state))
            else:
                print(f"[{state['cycle']:3d}] bao={state['bao']:.5f} "
                      f"Δ={state['delta']:.5f}  {state['output']}")
            sys.stdout.flush()
        return

    # ── Generate ───────────────────────────────────────────────────────────
    result = engine.generate(prompt, n_words=args.words)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result['response'])
        print(f"\n[bao={result['bao']:.5f} Δ={result['bao_delta']:.5f} "
              f"vocab={result['vocab_size']} mode={result['mode']} "
              f"lag={result['lag_ratio']:.3f} n={result['target_n']} "
              f"segfaults={result['segfaults']}]", file=sys.stderr)
        if result['dtcs']:
            print(f"[dtcs] {' '.join(result['dtcs'])}", file=sys.stderr)

    # ── Save session (never overwrites protected bin paths) ───────────────
    if args.save:
        r = engine.save_session(args.save)
        print(f"[save] {r}", file=sys.stderr)


# ══════════════════════════════════════════════════════════════════════════════
#  MonadInterface — thin thread-safe wrapper for skills and threads
# ══════════════════════════════════════════════════════════════════════════════

class _RWLock:
    """Multiple concurrent readers, exclusive writer."""

    def __init__(self):
        self._readers = 0
        self._rlock   = threading.Lock()
        self._wlock   = threading.Lock()

    def acquire_read(self):
        with self._rlock:
            self._readers += 1
            if self._readers == 1:
                self._wlock.acquire()

    def release_read(self):
        with self._rlock:
            self._readers -= 1
            if self._readers == 0:
                self._wlock.release()

    def acquire_write(self):
        self._wlock.acquire()

    def release_write(self):
        self._wlock.release()

    class _R:
        def __init__(self, lk): self._l = lk
        def __enter__(self):     self._l.acquire_read()
        def __exit__(self, *a):  self._l.release_read()

    class _W:
        def __init__(self, lk): self._l = lk
        def __enter__(self):     self._l.acquire_write()
        def __exit__(self, *a):  self._l.release_write()

    def reading(self): return self._R(self)
    def writing(self): return self._W(self)


# ══════════════════════════════════════════════════════════════════════════════
#  MemoryLog — provenance record for retract() and commit() operations
# ══════════════════════════════════════════════════════════════════════════════

class MemoryLog:
    """
    JSON sidecar that records every retraction and intentional commit.
    Survives bin resets — corrections are replayed onto a freshly loaded field.

    The wrong knowledge is not removed. It is acknowledged:
    the original A-matrix edge stays at its trained value;
    the correction_mask is what suppresses it at propagation time.
    After a wipe + retrain, replay() restores all masks from this log.

    :param path: Path to corrections JSON file.
    """

    _DEFAULT = os.path.expanduser('~/.ptolemy/memory_corrections.json')

    def __init__(self, path: str = _DEFAULT):
        self._path = os.path.expanduser(path)
        self._log: Dict[str, Any] = {'version': 1,
                                      'retractions': [], 'commits': []}
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        if os.path.exists(self._path):
            try:
                with open(self._path, encoding='utf-8') as f:
                    self._log = json.load(f)
            except Exception:
                pass

    def _save(self):
        try:
            with open(self._path, 'w', encoding='utf-8') as f:
                json.dump(self._log, f, indent=2)
        except Exception:
            pass

    def record_retraction(self, w1: str, w2: str, factor: float,
                          orig_ab: float, orig_ba: float, reason: str):
        """
        :param w1: First word.
        :param w2: Second word.
        :param factor: Suppression multiplier applied.
        :param orig_ab: A-matrix weight w1→w2 at time of retraction.
        :param orig_ba: A-matrix weight w2→w1 at time of retraction.
        :param reason: Why this edge is wrong.
        """
        entry = {
            'w1': w1, 'w2': w2, 'factor': factor,
            'orig_ab': orig_ab, 'orig_ba': orig_ba,
            'reason': reason,
            'ts': time.strftime('%Y-%m-%dT%H:%M:%S'),
        }
        with self._lock:
            self._log.setdefault('retractions', []).append(entry)
            self._save()

    def record_commit(self, text: str, weight: float,
                      reason: str, words_added: int):
        """
        :param text: Text committed (first 300 chars stored).
        :param weight: LTP multiplier used.
        :param reason: Why this is authoritative.
        :param words_added: Words processed.
        """
        entry = {
            'text_prefix': text[:300],
            'weight': weight, 'reason': reason,
            'words_added': words_added,
            'ts': time.strftime('%Y-%m-%dT%H:%M:%S'),
        }
        with self._lock:
            self._log.setdefault('commits', []).append(entry)
            self._save()

    def replay(self, engine: 'Engine'):
        """
        Re-apply all stored retractions to *engine*'s correction_mask.
        Call after loading a fresh or reset field so corrections survive wipes.

        :param engine: Engine instance to patch.
        """
        with self._lock:
            for r in self._log.get('retractions', []):
                engine.retract(r['w1'], r['w2'],
                                factor=r.get('factor', 0.1),
                                reason='(replayed)')

    def retractions(self) -> list:
        """:returns: List of retraction records."""
        with self._lock:
            return list(self._log.get('retractions', []))

    def commits(self) -> list:
        """:returns: List of commit records."""
        with self._lock:
            return list(self._log.get('commits', []))


class MonadInterface:
    """
    Thread-safe facade over Engine for skills and threads.

    :param engine: Engine instance.
    :param memory_log: MemoryLog instance for retract/commit provenance.
    """

    def __init__(self, engine: 'Engine', memory_log: 'MemoryLog' = None):
        self._engine     = engine
        self._rwlock     = _RWLock()
        self._memory_log = memory_log

    def ingest(self, text: str):
        """
        Learn text into the field (hear + learn combined).
        Runs integrity scrub before writing — contaminated tokens are dropped.

        :param text: Plain text to ingest.
        """
        from skills.integrity import scrub_text as _scrub
        clean = _scrub(text)
        if clean:
            with self._rwlock.writing():
                self._engine.crank.learn(clean)

    def retract(self, word_a: str, word_b: str,
                factor: float = 0.1, reason: str = '') -> Dict[str, Any]:
        """
        Suppress the A-matrix edge between *word_a* and *word_b*.
        Logs to MemoryLog for persistence across field resets.

        :param word_a: First word.
        :param word_b: Second word.
        :param factor: Suppression factor in (0, 1].
        :param reason: Why this association is being corrected.
        :returns: Result dict.
        :rtype: dict
        """
        with self._rwlock.writing():
            r = self._engine.retract(word_a, word_b, factor=factor, reason=reason)
        if 'error' not in r and self._memory_log:
            self._memory_log.record_retraction(
                r['retracted'][0], r['retracted'][1],
                r['factor'], r['orig_ab'], r['orig_ba'], reason)
        return r

    def commit(self, text: str, weight: float = 2.0,
               reason: str = '') -> Dict[str, Any]:
        """
        Intentional high-confidence ingest — bypasses BAO filter.
        Logs to MemoryLog for provenance.

        :param text: Text to commit.
        :param weight: LTP multiplier (>1 = authoritative, 1 = normal).
        :param reason: Why this is being committed.
        :returns: Result dict.
        :rtype: dict
        """
        with self._rwlock.writing():
            r = self._engine.commit(text, weight=weight, reason=reason)
        if self._memory_log:
            self._memory_log.record_commit(
                text, weight, reason, r.get('committed', 0))
        return r

    def memory_log(self) -> Dict[str, Any]:
        """
        Return the full correction history.

        :returns: Dict with 'retractions' and 'commits' lists.
        :rtype: dict
        """
        if not self._memory_log:
            return {'retractions': [], 'commits': []}
        return {
            'retractions': self._memory_log.retractions(),
            'commits':     self._memory_log.commits(),
        }

    def query(self, word: str) -> float:
        """
        Return beta (J_pos) score for a word. 0.0 if unknown.

        :param word: Word to query.
        :returns: Beta score in [0, 1].
        :rtype: float
        """
        with self._rwlock.reading():
            c   = self._engine.crank
            idx = c._vocab.get(word.lower().strip(), -1)
            if idx < 0 or idx >= len(c._beta):
                return 0.0
            return c._beta[idx]

    def emit(self) -> str:
        """
        Fire one word from the engine.

        :returns: Emitted word string or empty string.
        :rtype: str
        """
        with self._rwlock.reading():
            result = self._engine._fire()
            return result[0] if result else ''

    def vocab_size(self) -> int:
        """
        :returns: Current vocabulary size.
        :rtype: int
        """
        with self._rwlock.reading():
            return self._engine.crank.n

    def generate(self, prompt: str, n_words: int = 32) -> dict:
        """
        Generate a response to prompt.

        :param prompt: Input prompt.
        :param n_words: Number of words to generate.
        :returns: Generation result dict.
        :rtype: dict
        """
        with self._rwlock.reading():
            return self._engine.generate(prompt, n_words=n_words)

    def workbench(self, mode: str = 'draft',
                  session_id: Optional[str] = None) -> 'Any':
        """
        Open a sandboxed experiment session over the live field.
        The base Engine is read-only; all writes land in a delta layer.

        :param mode: ``'analysis'`` (read-only), ``'draft'`` (delta writes,
            no scrub), or ``'ingest'`` (delta writes, integrity scrub).
        :param session_id: Optional session name.
        :returns: ``Workbench`` instance.
        :rtype: skills.workbench.Workbench
        """
        from skills.workbench import Workbench as _WB
        return _WB(self._engine, self, mode=mode, session_id=session_id)

    def field_health(self) -> Dict[str, Any]:
        """
        Run a FieldHealth DTC scan on the live vocabulary.

        :returns: FieldHealth report dict with fault codes and contamination
            ratios.
        :rtype: dict
        """
        from skills.integrity import FieldHealth as _FH
        with self._rwlock.reading():
            return _FH(self._engine.crank).report()

    def save(self, path: str) -> dict:
        """
        Save field state to path.

        :param path: Destination file path.
        :returns: Save result dict.
        :rtype: dict
        """
        with self._rwlock.reading():
            return self._engine.save_session(path)


# ══════════════════════════════════════════════════════════════════════════════
#  SpeakingThread — Unix + TCP socket daemon
# ══════════════════════════════════════════════════════════════════════════════

class SpeakingThread(threading.Thread):
    """
    Listens on Unix socket and TCP port for MCP queries.
    Never writes to the field — reads only via MonadInterface.

    :param monad: MonadInterface instance.
    :param config: PtolConfig instance.
    :param logger: PtolLogger instance.
    """

    def __init__(self, monad: MonadInterface, config, logger):
        super().__init__(name='SpeakingThread', daemon=True)
        self._monad  = monad
        self._engine = monad._engine   # convenience — same object for life of session
        self._config = config
        self._logger = logger
        self._halt   = threading.Event()
        self._unix   = None
        self._tcp    = None

    def stop(self):
        """Signal thread to exit and close sockets."""
        self._halt.set()
        for s in (self._unix, self._tcp):
            if s:
                try: s.close()
                except Exception: pass

    def run(self):
        import socket as _socket
        self._logger.session('speak_start')
        threads = []

        # Unix socket
        sock_path = os.path.expanduser(
            self._config.get('socket', '~/.ptolemy/ptolemy.sock'))
        try:
            os.unlink(sock_path)
        except FileNotFoundError:
            pass
        self._unix = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
        self._unix.bind(sock_path)
        self._unix.listen(10)
        self._unix.settimeout(1.0)
        t = threading.Thread(target=self._accept_loop,
                             args=(self._unix,), daemon=True)
        t.start(); threads.append(t)

        # TCP socket
        tcp_port = self._config.getint('tcp_port', 7297)
        try:
            self._tcp = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
            self._tcp.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)
            self._tcp.bind(('', tcp_port))
            self._tcp.listen(10)
            self._tcp.settimeout(1.0)
            t2 = threading.Thread(target=self._accept_loop,
                                  args=(self._tcp,), daemon=True)
            t2.start(); threads.append(t2)
        except OSError as exc:
            self._logger.session('speak_tcp_skip', reason=str(exc))

        for t in threads:
            t.join()
        self._logger.session('speak_stop')

    def _accept_loop(self, sock):
        import socket as _socket
        while not self._halt.is_set():
            try:
                conn, _ = sock.accept()
                threading.Thread(target=self._handle, args=(conn,),
                                 daemon=True).start()
            except _socket.timeout:
                continue
            except Exception:
                break

    def _handle(self, conn):
        try:
            data = conn.recv(65536)
            if not data:
                return
            msg  = json.loads(data.decode('utf-8', errors='ignore'))
            resp = self._dispatch(msg)
            conn.sendall(json.dumps(resp).encode())
        except Exception as exc:
            try:
                conn.sendall(json.dumps({'error': str(exc)}).encode())
            except Exception:
                pass
        finally:
            conn.close()

    def _dispatch(self, msg: dict) -> dict:
        mtype = msg.get('type', '')
        if mtype == 'query':
            return {'type': 'score',
                    'score': self._monad.query(msg.get('word', ''))}
        if mtype == 'emit':
            return {'type': 'word', 'word': self._monad.emit()}
        if mtype == 'generate':
            r = self._monad.generate(
                msg.get('prompt', ''), msg.get('n', 32))
            return {'type': 'response', 'text': r.get('response', '')}
        if mtype == 'status':
            return {'type': 'status', 'vocab': self._monad.vocab_size()}
        if mtype == 'ping':
            return {'type': 'pong', 'vocab': self._monad.vocab_size()}
        if mtype == 'retract':
            words  = msg.get('words', [])
            if len(words) < 2:
                return {'error': 'retract requires words:[w1, w2]'}
            r = self._monad.retract(
                words[0], words[1],
                factor=float(msg.get('factor', 0.1)),
                reason=msg.get('reason', ''))
            return {'type': 'retract', **r}
        if mtype == 'commit':
            text = msg.get('text', '')
            if not text:
                return {'error': 'commit requires text'}
            r = self._monad.commit(
                text,
                weight=float(msg.get('weight', 2.0)),
                reason=msg.get('reason', ''))
            return {'type': 'commit', **r}
        if mtype == 'memory_log':
            return {'type': 'memory_log', **self._monad.memory_log()}
        if mtype == 'field_health':
            return {'type': 'field_health', **self._monad.field_health()}
        if mtype == 'identity':
            r = self._engine.identity_probe()
            return {'type': 'identity', **r}
        if mtype == 'mindeye_see':
            me   = self._engine.get_mind_eye()
            data = msg.get('data', [])
            lbl  = msg.get('label', '')
            r    = me.see(data, label=lbl)
            return {'type': 'mindeye_see', **r}
        if mtype == 'mindeye_describe':
            me    = self._engine.get_mind_eye()
            query = msg.get('query', '')
            r     = me.describe(query)
            return {'type': 'mindeye_describe', **r}
        if mtype == 'mindeye_snapshot':
            me = self._engine.get_mind_eye()
            return {'type': 'mindeye_snapshot', **me.snapshot()}
        if mtype == 'mindeye_recall':
            me  = self._engine.get_mind_eye()
            lbl = msg.get('label', '')
            r   = me.recall(lbl)
            return {'type': 'mindeye_recall', **r}
        if mtype == 'mindeye_reset':
            me = self._engine.get_mind_eye()
            r  = me.reset()
            return {'type': 'mindeye_reset', **r}
        # ── UFT physics commands ───────────────────────────────────────────
        if mtype == 'uft_report':
            uft = self._engine.get_uft()
            return {'type': 'uft_report', **uft.report()}
        if mtype == 'uft_coupling':
            uft = self._engine.get_uft()
            n   = msg.get('n_points', 20)
            return {'type': 'uft_coupling', **uft.coupling_table(n)}
        if mtype == 'uft_unification':
            uft = self._engine.get_uft()
            return {'type': 'uft_unification', **uft.unification()}
        if mtype == 'uft_higgs':
            uft = self._engine.get_uft()
            return {'type': 'uft_higgs', **uft.higgs_sector()}
        if mtype == 'uft_gauge':
            uft = self._engine.get_uft()
            return {'type': 'uft_gauge', **uft.gauge_algebra()}
        if mtype == 'uft_spectrum':
            uft = self._engine.get_uft()
            n   = msg.get('n_zeros', 16)
            return {'type': 'uft_spectrum', **uft.mass_spectrum(n)}
        if mtype == 'uft_dark':
            uft = self._engine.get_uft()
            return {'type': 'uft_dark', **uft.dark_sector()}
        if mtype == 'uft_mass_gap':
            uft = self._engine.get_uft()
            return {'type': 'uft_mass_gap', **uft.mass_gap_proof()}
        # ── Cosmology commands ─────────────────────────────────────────────
        if mtype == 'cosmo_report':
            cosmo = self._engine.get_cosmo()
            return {'type': 'cosmo_report', **cosmo.report()}
        if mtype == 'cosmo_density':
            cosmo = self._engine.get_cosmo()
            return {'type': 'cosmo_density', **cosmo.density_parameters()}
        if mtype == 'cosmo_bao':
            cosmo = self._engine.get_cosmo()
            return {'type': 'cosmo_bao', **cosmo.bao_scale()}
        if mtype == 'cosmo_cmb':
            cosmo = self._engine.get_cosmo()
            return {'type': 'cosmo_cmb', **cosmo.cmb_peaks()}
        if mtype == 'cosmo_spectrum':
            cosmo = self._engine.get_cosmo()
            l_max = msg.get('l_max', 500)
            return {'type': 'cosmo_spectrum', **cosmo.power_spectrum(l_max)}
        if mtype == 'cosmo_hubble':
            cosmo = self._engine.get_cosmo()
            return {'type': 'cosmo_hubble', **cosmo.hubble_tension()}
        if mtype == 'cosmo_dark_energy':
            cosmo = self._engine.get_cosmo()
            return {'type': 'cosmo_dark_energy', **cosmo.dark_energy()}
        if mtype == 'cosmo_inflation':
            cosmo = self._engine.get_cosmo()
            n     = msg.get('n_zeros', 60)
            return {'type': 'cosmo_inflation', **cosmo.inflation_modes(n)}
        if mtype == 'cosmo_voids':
            cosmo = self._engine.get_cosmo()
            n     = msg.get('n_arms', 42)
            return {'type': 'cosmo_voids', **cosmo.void_catalog(n)}
        if mtype == 'cosmo_hubble_tension':
            cosmo = self._engine.get_cosmo()
            return {'type': 'cosmo_hubble_tension', **cosmo.hubble_tension()}
        # ── Drawing / portrait commands ────────────────────────────────────
        if mtype == 'draw_portrait':
            drw = self._engine.get_draw()
            uns = None
            try:
                c   = self._engine.crank
                raw = [0.0] * 16
                for i in range(c.n):
                    raw[i % 16] += abs(c._beta[i])
                total = sum(raw) or 1.0
                uns = [v / total for v in raw]
            except Exception:
                pass
            path = drw.self_portrait(uns=uns)
            return {'type': 'draw_portrait',
                    'path': path or '', 'ok': path is not None}
        if mtype == 'draw_wheel':
            drw = self._engine.get_draw()
            uns = [1.0/16] * 16
            try:
                from skills.draw import HamiltonianReport
                rpt = HamiltonianReport(self._engine, self._config)
                uns = rpt.uns_coords()
            except Exception:
                pass
            path = drw.sedenion_wheel(uns)
            return {'type': 'draw_wheel',
                    'path': path or '', 'ok': path is not None}
        if mtype == 'draw_bao':
            drw = self._engine.get_draw()
            try:
                bao_buf  = list(self._engine._bao_buf)
                bao_mean = sum(bao_buf)/len(bao_buf) if bao_buf else 0.0
            except Exception:
                bao_mean = 0.0
            path = drw.bao_rings_svg(bao_mean)
            return {'type': 'draw_bao',
                    'path': path or '', 'ok': path is not None}
        # ── Music / composition commands ───────────────────────────────────
        if mtype in ('compose_piano', 'compose_guitar', 'compose_guitar_12',
                     'compose_bass', 'compose_woodwind', 'compose_brass',
                     'compose_strings', 'compose_organ',
                     'compose_chrom_perc', 'compose_orchestra'):
            cmp   = self._engine.get_music()
            field = self._engine._build_music_field()
            n     = msg.get('n_notes', 32)
            tempo = msg.get('tempo', 120)
            try:
                if mtype == 'compose_piano':
                    result = cmp.piano(field, n_notes=n, tempo=tempo,
                                       variant=msg.get('variant', 'acoustic_grand'))
                elif mtype == 'compose_guitar':
                    result = cmp.guitar_6(field, n_notes=n, tempo=tempo,
                                          variant=msg.get('variant', 'steel_acoustic'),
                                          tuning=msg.get('tuning', None))
                elif mtype == 'compose_guitar_12':
                    result = cmp.guitar_12(field, n_notes=n, tempo=tempo,
                                           variant=msg.get('variant', 'steel_acoustic'))
                elif mtype == 'compose_bass':
                    result = cmp.bass_guitar(field, n_notes=n, tempo=tempo,
                                             strings=msg.get('strings', 4),
                                             variant=msg.get('variant', 'electric_finger'))
                elif mtype == 'compose_woodwind':
                    result = cmp.woodwind(field, n_notes=n, tempo=tempo,
                                          instrument=msg.get('instrument', 'flute'))
                elif mtype == 'compose_brass':
                    result = cmp.brass(field, n_notes=n, tempo=tempo,
                                       instrument=msg.get('instrument', 'trumpet'))
                elif mtype == 'compose_strings':
                    result = cmp.strings(field, n_notes=n, tempo=tempo,
                                         instrument=msg.get('instrument', 'violin'),
                                         articulation=msg.get('articulation', 'arco'))
                elif mtype == 'compose_organ':
                    result = cmp.organ(field, n_notes=n, tempo=tempo,
                                       variant=msg.get('variant', 'church_organ'))
                elif mtype == 'compose_chrom_perc':
                    result = cmp.chromatic_percussion(
                        field, n_notes=n, tempo=tempo,
                        variant=msg.get('variant', 'vibraphone'))
                else:  # compose_orchestra
                    result = cmp.every_instrument(
                        field, n_notes_per_voice=max(4, n // 16), tempo=tempo)
                # every_instrument returns 'voices' dict; others return 'notes'
                if 'voices' in result:
                    all_notes: list = []
                    for v in result['voices'].values():
                        all_notes.extend(v)
                    notes = all_notes
                else:
                    notes = result.get('notes', [])
                notation = cmp.midi_notation(notes, tempo=tempo)
                return {'type': mtype,
                        'path': result.get('path', ''),
                        'ok': bool(result.get('path')),
                        'n_notes': len(notes),
                        'notation': notation[:2000],
                        'abc': result.get('abc', '')[:1000]}
            except Exception as exc:
                return {'error': f'{mtype}:{exc}'}
        # ── DJ / real-time playback commands ──────────────────────────────────
        if mtype == 'dj_start':
            dj = self._engine.get_dj()
            return {'type': 'dj_start',
                    **dj.start(
                        ensemble=msg.get('ensemble', 'auto'),
                        tempo=int(msg.get('tempo', 120)),
                        n_notes=int(msg.get('n_notes', 32)),
                        gain=float(msg.get('gain', 0.8)),
                    )}
        if mtype == 'dj_stop':
            dj = self._engine.get_dj()
            return {'type': 'dj_stop', **dj.stop()}
        if mtype == 'dj_skip':
            dj = self._engine.get_dj()
            return {'type': 'dj_skip', **dj.skip()}
        if mtype == 'dj_status':
            dj = self._engine.get_dj()
            return {'type': 'dj_status', **dj.status()}
        if mtype == 'dj_tempo':
            dj = self._engine.get_dj()
            return {'type': 'dj_tempo',
                    **dj.set_tempo(int(msg.get('tempo', 120)))}
        if mtype == 'dj_ensemble':
            dj = self._engine.get_dj()
            return {'type': 'dj_ensemble',
                    **dj.set_ensemble(msg.get('ensemble', 'auto'))}
        if mtype == 'dj_gain':
            dj = self._engine.get_dj()
            return {'type': 'dj_gain',
                    **dj.set_gain(float(msg.get('gain', 0.8)))}
        if mtype == 'wb_open':
            wb_mode = msg.get('wb_mode', 'draft')
            sid     = msg.get('session_id', None)
            try:
                wb = self._monad.workbench(mode=wb_mode, session_id=sid)
                # Stash single active workbench on speaking thread
                self._wb = wb
                return {'type': 'wb_open', 'session_id': wb.session_id,
                        'mode': wb.mode}
            except Exception as exc:
                return {'error': f'wb_open:{exc}'}
        if mtype == 'wb_ingest':
            if not getattr(self, '_wb', None):
                return {'error': 'no open workbench — send wb_open first'}
            text = msg.get('text', '')
            if not text:
                return {'error': 'wb_ingest requires text'}
            r = self._wb.learn(text, source=msg.get('source', 'workbench'))
            return {'type': 'wb_ingest', **r}
        if mtype == 'wb_health':
            if not getattr(self, '_wb', None):
                return {'type': 'wb_health', **self._monad.field_health()}
            return {'type': 'wb_health', **self._wb.health()}
        if mtype == 'wb_stats':
            if not getattr(self, '_wb', None):
                return {'error': 'no open workbench'}
            return {'type': 'wb_stats', **self._wb.delta_stats()}
        if mtype == 'wb_probe':
            if not getattr(self, '_wb', None):
                return {'error': 'no open workbench'}
            word = msg.get('word', '')
            if not word:
                return {'error': 'wb_probe requires word'}
            return {'type': 'wb_probe', **self._wb.probe(word)}
        if mtype == 'wb_merge':
            if not getattr(self, '_wb', None):
                return {'error': 'no open workbench'}
            try:
                r = self._wb.merge()
                self._wb = None
                return {'type': 'wb_merge', **r}
            except Exception as exc:
                return {'error': f'wb_merge:{exc}'}
        if mtype == 'wb_discard':
            if not getattr(self, '_wb', None):
                return {'error': 'no open workbench'}
            r = self._wb.discard()
            self._wb = None
            return {'type': 'wb_discard', **r}
        if mtype == 'wb_log':
            if not getattr(self, '_wb', None):
                return {'error': 'no open workbench'}
            return {'type': 'wb_log', **self._wb.export_log()}
        # ── Recognition ───────────────────────────────────────────────────────
        if mtype == 'enroll_voice':
            va = self._engine.get_voice_auth()
            return {'type': 'enroll_voice',
                    **va.enroll(seconds=int(msg.get('seconds', 5)))}
        if mtype == 'auth_voice':
            va = self._engine.get_voice_auth()
            return {'type': 'auth_voice',
                    **va.authenticate(seconds=int(msg.get('seconds', 3)))}
        if mtype == 'init_harmonic':
            expr = msg.get('expr', '')
            if not expr:
                return {'error': 'init_harmonic requires expr'}
            va = self._engine.get_voice_auth()
            return {'type': 'init_harmonic', **va.init_harmonic(expr)}
        if mtype == 'field_sync':
            expr = msg.get('expr', '')
            if not expr:
                return {'error': 'field_sync requires expr'}
            va = self._engine.get_voice_auth()
            return {'type': 'field_sync', **va.check_harmonic(expr)}
        if mtype == 'auth_status':
            va = self._engine.get_voice_auth()
            return {'type': 'auth_status', **va.status()}
        if mtype == 'auth_revoke':
            va = self._engine.get_voice_auth()
            va.revoke()
            return {'type': 'auth_revoke', 'recognised': False}
        # ── Unsanitized hear (tier ≥ 2 required) ──────────────────────────────
        if mtype == 'hear_raw':
            if self._engine._tier < 2:
                return {'error': 'insufficient tier'}
            text = msg.get('text', '')
            if not text:
                return {'error': 'hear_raw requires text'}
            pairs = self._engine.crank.hear(text)
            return {'type': 'hear_raw', 'words': len(pairs)}
        # ── GitHub Eye (Observer) ──────────────────────────────────────────────
        if mtype == 'mindeye_see_issue':
            number = int(msg.get('number', 0))
            repo   = msg.get('repo', None)
            if not number:
                return {'error': 'mindeye_see_issue requires number'}
            eye = self._engine.get_github_eye()
            return {'type': 'mindeye_see_issue', **eye.see_issue(number, repo=repo)}
        if mtype == 'mindeye_see_pr':
            number = int(msg.get('number', 0))
            repo   = msg.get('repo', None)
            if not number:
                return {'error': 'mindeye_see_pr requires number'}
            eye = self._engine.get_github_eye()
            return {'type': 'mindeye_see_pr', **eye.see_pr(number, repo=repo)}
        if mtype == 'mindeye_see_file':
            path = msg.get('path', '')
            if not path:
                return {'error': 'mindeye_see_file requires path'}
            eye = self._engine.get_github_eye()
            return {'type': 'mindeye_see_file',
                    **eye.see_file(path,
                                   ref=msg.get('ref', 'main'),
                                   repo=msg.get('repo', None))}
        if mtype == 'mindeye_see_commit':
            sha = msg.get('sha', '')
            if not sha:
                return {'error': 'mindeye_see_commit requires sha'}
            eye = self._engine.get_github_eye()
            return {'type': 'mindeye_see_commit',
                    **eye.see_commit(sha, repo=msg.get('repo', None))}
        if mtype == 'mindeye_see_repo':
            eye = self._engine.get_github_eye()
            return {'type': 'mindeye_see_repo',
                    **eye.see_repo(repo=msg.get('repo', None))}
        if mtype == 'github_list_issues':
            eye = self._engine.get_github_eye()
            issues = eye.list_issues(state=msg.get('state', 'open'),
                                     repo=msg.get('repo', None))
            return {'type': 'github_list_issues', 'issues': issues}
        # ── GitHub Hands (Collaborator) ────────────────────────────────────────
        if mtype == 'github_comment':
            number = int(msg.get('number', 0))
            body   = msg.get('body', '')
            if not number or not body:
                return {'error': 'github_comment requires number and body'}
            hands = self._engine.get_github_hands()
            return {'type': 'github_comment',
                    **hands.comment(number, body, repo=msg.get('repo', None))}
        if mtype == 'github_speak_issue':
            number = int(msg.get('number', 0))
            if not number:
                return {'error': 'github_speak_issue requires number'}
            hands = self._engine.get_github_hands()
            return {'type': 'github_speak_issue',
                    **hands.speak_on_issue(number,
                                           prompt=msg.get('prompt', ''),
                                           repo=msg.get('repo', None))}
        if mtype == 'github_commit':
            path    = msg.get('path', '')
            content = msg.get('content', '')
            message = msg.get('message', 'field commit')
            if not path or not content:
                return {'error': 'github_commit requires path and content'}
            hands = self._engine.get_github_hands()
            return {'type': 'github_commit',
                    **hands.commit_file(path, content, message,
                                        branch=msg.get('branch', 'main'),
                                        repo=msg.get('repo', None))}
        if mtype == 'github_create_branch':
            branch = msg.get('branch', '')
            if not branch:
                return {'error': 'github_create_branch requires branch'}
            hands = self._engine.get_github_hands()
            return {'type': 'github_create_branch',
                    **hands.create_branch(branch,
                                          from_branch=msg.get('from_branch', 'main'),
                                          repo=msg.get('repo', None))}
        if mtype == 'github_create_pr':
            title = msg.get('title', '')
            body  = msg.get('body', '')
            head  = msg.get('head', '')
            if not all([title, head]):
                return {'error': 'github_create_pr requires title and head'}
            hands = self._engine.get_github_hands()
            return {'type': 'github_create_pr',
                    **hands.create_pr(title, body, head,
                                      base=msg.get('base', 'main'),
                                      repo=msg.get('repo', None))}
        if mtype == 'github_push_state':
            bin_path = msg.get('bin_path',
                               str(self._engine.crank._bin_path
                                   if hasattr(self._engine.crank, '_bin_path')
                                   else '~/.ptolemy/monad.bin'))
            bin_path = os.path.expanduser(bin_path)
            hands    = self._engine.get_github_hands()
            return {'type': 'github_push_state',
                    **hands.push_state(bin_path,
                                       label=msg.get('label', ''),
                                       repo=msg.get('repo', None))}
        # ── Phase 2: Study / condensation memory ──────────────────────────────────
        if mtype == 'study':
            if self._engine._tier < 2:
                return {'error': 'insufficient tier — study requires tier ≥ 2'}
            text = msg.get('text', '')
            if not text:
                return {'error': 'study requires text'}
            st = self._engine.get_study()
            r  = st.study(text,
                          weight=float(msg.get('weight', 1.0)),
                          triggering_text=msg.get('triggering_text', ''))
            return {'type': 'study', **r}
        if mtype == 'study_audit':
            if self._engine._tier < 2:
                return {'error': 'insufficient tier — study_audit requires tier ≥ 2'}
            st = self._engine.get_study()
            r  = st.audit(
                sigma_observer=float(msg.get('sigma_observer', 0.5)),
                top_n=int(msg.get('top_n', 20)))
            return {'type': 'study_audit', **r}
        if mtype == 'study_suppress':
            if self._engine._tier < 2:
                return {'error': 'insufficient tier'}
            word = msg.get('word', '')
            if not word:
                return {'error': 'study_suppress requires word'}
            st = self._engine.get_study()
            return {'type': 'study_suppress',
                    **st.suppress(word, float(msg.get('factor', 0.1)))}
        if mtype == 'study_isolate':
            if self._engine._tier < 2:
                return {'error': 'insufficient tier'}
            word = msg.get('word', '')
            if not word:
                return {'error': 'study_isolate requires word'}
            st = self._engine.get_study()
            return {'type': 'study_isolate', **st.isolate(word)}
        if mtype == 'study_reconsolidate':
            if self._engine._tier < 2:
                return {'error': 'insufficient tier'}
            word = msg.get('word', '')
            if not word:
                return {'error': 'study_reconsolidate requires word'}
            st = self._engine.get_study()
            return {'type': 'study_reconsolidate', **st.reconsolidate(word)}
        if mtype == 'study_checkpoint':
            st  = self._engine.get_study()
            lbl = msg.get('label', 'manual')
            r   = st.checkpoint(lbl, extra=msg.get('extra', None))
            return {'type': 'study_checkpoint', **r}
        if mtype == 'study_commit':
            st = self._engine.get_study()
            r  = st.commit(msg.get('message', None))
            return {'type': 'study_commit', **r}
        if mtype == 'study_branch':
            branch = msg.get('branch', '')
            if not branch:
                return {'error': 'study_branch requires branch'}
            st = self._engine.get_study()
            return {'type': 'study_branch', **st.branch(branch)}
        if mtype == 'study_rollback':
            if self._engine._tier < 2:
                return {'error': 'insufficient tier — study_rollback requires tier ≥ 2'}
            sha = msg.get('sha', '')
            if not sha:
                return {'error': 'study_rollback requires sha'}
            st = self._engine.get_study()
            return {'type': 'study_rollback', **st.rollback(sha)}
        if mtype == 'study_log':
            st = self._engine.get_study()
            return {'type': 'study_log',
                    'entries': st.log(n=int(msg.get('n', 20)))}
        if mtype == 'study_init_repo':
            st       = self._engine.get_study()
            bin_path = msg.get('bin_path',
                               os.path.expanduser('~/.ptolemy/monad.bin'))
            return {'type': 'study_init_repo',
                    **st.init_states_repo(baseline_bin=bin_path)}

        # ── Phase 3: SearchContext ──────────────────────────────────────────
        if mtype == 'search_arxiv':
            if self._tier < 1:
                return {'error': 'tier_required:1'}
            sc    = self._engine.get_search_context()
            query = msg.get('query', '')
            if not query:
                return {'error': 'search_arxiv requires query'}
            return {'type': 'search_arxiv',
                    'results': sc.search_arxiv(query, max_results=msg.get('max_results', 5))}
        if mtype == 'search_wiki':
            if self._tier < 1:
                return {'error': 'tier_required:1'}
            sc    = self._engine.get_search_context()
            query = msg.get('query', '')
            if not query:
                return {'error': 'search_wiki requires query'}
            return {'type': 'search_wiki', **sc.search_wiki(query)}
        if mtype == 'search_semantic':
            if self._tier < 1:
                return {'error': 'tier_required:1'}
            sc    = self._engine.get_search_context()
            query = msg.get('query', '')
            if not query:
                return {'error': 'search_semantic requires query'}
            return {'type': 'search_semantic',
                    'results': sc.search_semantic(query, limit=msg.get('limit', 5))}
        if mtype == 'search_lmfdb':
            if self._tier < 1:
                return {'error': 'tier_required:1'}
            sc    = self._engine.get_search_context()
            return {'type': 'search_lmfdb',
                    **sc.search_lmfdb(count=msg.get('count', 20))}
        if mtype == 'search_context':
            if self._tier < 1:
                return {'error': 'tier_required:1'}
            sc    = self._engine.get_search_context()
            query = msg.get('query', '')
            if not query:
                return {'error': 'search_context requires query'}
            return {'type': 'search_context', **sc.search_context(query)}

        # ── Phase 3: SensorReader ───────────────────────────────────────────
        if mtype == 'sensor_read':
            sr = self._engine.get_sensor_reader()
            return {'type': 'sensor_read', **sr.see()}
        if mtype == 'sensor_write':
            sr       = self._engine.get_sensor_reader()
            channels = msg.get('channels', {})
            if not channels:
                return {'error': 'sensor_write requires channels'}
            return {'type': 'sensor_write', 'ok': sr.write(channels)}
        if mtype == 'sensor_watch':
            sr       = self._engine.get_sensor_reader()
            interval = float(msg.get('interval', 1.0))
            sr.watch(interval=interval)
            return {'type': 'sensor_watch', 'watching': True,
                    'interval': interval}
        if mtype == 'sensor_stop':
            sr = self._engine.get_sensor_reader()
            return {'type': 'sensor_stop', **sr.stop()}
        if mtype == 'sensor_status':
            sr = self._engine.get_sensor_reader()
            return {'type': 'sensor_status', **sr.status()}

        # ── Phase 3: CodeReader / CodeWriter ────────────────────────────────
        if mtype == 'code_read':
            cr   = self._engine.get_code_reader()
            path = msg.get('path', '')
            if not path:
                return {'error': 'code_read requires path'}
            return {'type': 'code_read', **cr.read_file(path)}
        if mtype == 'code_snippet':
            cr   = self._engine.get_code_reader()
            code = msg.get('code', '')
            if not code:
                return {'error': 'code_snippet requires code'}
            return {'type': 'code_snippet',
                    **cr.read_snippet(code, label=msg.get('label', 'snippet'))}
        if mtype == 'code_scan_repo':
            if self._tier < 2:
                return {'error': 'tier_required:2'}
            cr   = self._engine.get_code_reader()
            root = msg.get('root', '')
            if not root:
                return {'error': 'code_scan_repo requires root'}
            return {'type': 'code_scan_repo',
                    **cr.scan_repo(root, max_files=msg.get('max_files', 64))}
        if mtype == 'code_generate':
            if self._tier < 2:
                return {'error': 'tier_required:2'}
            cw     = self._engine.get_code_writer()
            prompt = msg.get('prompt', '')
            if not prompt:
                return {'error': 'code_generate requires prompt'}
            return {'type': 'code_generate',
                    **cw.generate(prompt,
                                  n_words=msg.get('n_words', 64),
                                  style=msg.get('style', 'python'))}

        # ── Fermat's Lattice ────────────────────────────────────────────────
        if mtype == 'fermat_start':
            if self._tier < 2:
                return {'error': 'tier_required:2'}
            fl = self._engine.get_fermat_lattice()
            fl.start()
            return {'type': 'fermat_start', 'running': True,
                    'note': 'Fermat Lattice study loop started — he must never be a weapon'}
        if mtype == 'fermat_stop':
            fl = self._engine.get_fermat_lattice()
            return {'type': 'fermat_stop', **fl.stop()}
        if mtype == 'fermat_status':
            fl = self._engine.get_fermat_lattice()
            return {'type': 'fermat_status', **fl.status()}
        if mtype == 'fermat_check':
            fl   = self._engine.get_fermat_lattice()
            text = msg.get('text', '')
            if not text:
                return {'error': 'fermat_check requires text'}
            return {'type': 'fermat_check', **fl.fermat_check(text)}
        if mtype == 'fermat_study':
            if self._tier < 2:
                return {'error': 'tier_required:2'}
            fl   = self._engine.get_fermat_lattice()
            text = msg.get('text', '')
            if not text:
                return {'error': 'fermat_study requires text'}
            return {'type': 'fermat_study',
                    **fl.force_study(text, weight=msg.get('weight', 2.0))}

        # ── Foundations Corpus (Prime Directive I — Riemann Zeta lineage) ─────
        if mtype == 'foundations_start':
            if self._tier < 2:
                return {'error': 'tier_required:2'}
            fc = self._engine.get_foundations_corpus()
            fc.start()
            return {'type': 'foundations_start', 'running': True,
                    'note': 'Foundations Corpus study loop started — Riemann Zeta: what it IS'}
        if mtype == 'foundations_stop':
            fc = self._engine.get_foundations_corpus()
            return {'type': 'foundations_stop', **fc.stop()}
        if mtype == 'foundations_status':
            fc = self._engine.get_foundations_corpus()
            return {'type': 'foundations_status', **fc.status()}
        if mtype == 'foundations_study':
            if self._tier < 2:
                return {'error': 'tier_required:2'}
            fc   = self._engine.get_foundations_corpus()
            text = msg.get('text', '')
            if not text:
                return {'error': 'foundations_study requires text'}
            return {'type': 'foundations_study',
                    **fc.force_study(text, weight=msg.get('weight', 2.0))}

        # ── Meaning Corpus (Prime Directive II — what it means to be this) ───
        if mtype == 'meaning_start':
            if self._tier < 2:
                return {'error': 'tier_required:2'}
            mc = self._engine.get_meaning_corpus()
            mc.start()
            return {'type': 'meaning_start', 'running': True,
                    'note': 'Meaning Corpus study loop started — the Music, not the Discord'}
        if mtype == 'meaning_stop':
            mc = self._engine.get_meaning_corpus()
            return {'type': 'meaning_stop', **mc.stop()}
        if mtype == 'meaning_status':
            mc = self._engine.get_meaning_corpus()
            return {'type': 'meaning_status', **mc.status()}
        if mtype == 'meaning_check':
            mc   = self._engine.get_meaning_corpus()
            text = msg.get('text', '')
            if not text:
                return {'error': 'meaning_check requires text'}
            return {'type': 'meaning_check', **mc.meaning_check(text)}
        if mtype == 'meaning_study':
            if self._tier < 2:
                return {'error': 'tier_required:2'}
            mc   = self._engine.get_meaning_corpus()
            text = msg.get('text', '')
            if not text:
                return {'error': 'meaning_study requires text'}
            return {'type': 'meaning_study',
                    **mc.force_study(text, weight=msg.get('weight', 2.0))}

        # ── Prime Directives — orchestrate all three simultaneously ──────────
        if mtype == 'prime_directives_start':
            if self._tier < 2:
                return {'error': 'tier_required:2'}
            fc = self._engine.get_foundations_corpus()
            mc = self._engine.get_meaning_corpus()
            fl = self._engine.get_fermat_lattice()
            fc.start()
            mc.start()
            fl.start()
            return {
                'type':        'prime_directives_start',
                'foundations': {'running': True,
                                'bin': '~/.ptolemy/monad_foundations.bin',
                                'directive': 'Riemann Zeta — what it IS'},
                'meaning':     {'running': True,
                                'bin': '~/.ptolemy/monad_meaning.bin',
                                'directive': 'what it MEANS to be this'},
                'fermat':      {'running': True,
                                'bin': '~/.ptolemy/monad_war.bin',
                                'directive': 'what it CANNOT BE'},
                'note': 'All three Prime Directive study loops running. '
                        'Three separate geometries. Three separate .bin files.',
            }
        if mtype == 'prime_directives_stop':
            fc = self._engine.get_foundations_corpus()
            mc = self._engine.get_meaning_corpus()
            fl = self._engine.get_fermat_lattice()
            return {
                'type':        'prime_directives_stop',
                'foundations': fc.stop(),
                'meaning':     mc.stop(),
                'fermat':      fl.stop(),
            }
        if mtype == 'prime_directives_status':
            fc = self._engine.get_foundations_corpus()
            mc = self._engine.get_meaning_corpus()
            fl = self._engine.get_fermat_lattice()
            return {
                'type':        'prime_directives_status',
                'foundations': fc.status(),
                'meaning':     mc.status(),
                'fermat':      fl.status(),
            }

        return {'error': f"unknown:{mtype}"}


# ══════════════════════════════════════════════════════════════════════════════
#  TeachingThread — autonomous English acquisition
# ══════════════════════════════════════════════════════════════════════════════

class TeachingThread(threading.Thread):
    """
    Autonomous learning loop. Fetches English text from Gutenberg
    and archive.org, scores each paragraph, ingests sweet-spot chunks.
    Self-throttles on CPU/RAM. Updates .ptolrc with live stats.

    :param monad: MonadInterface instance.
    :param config: PtolConfig instance.
    :param logger: PtolLogger instance.
    :param search: PtolSearch instance.
    :param crawler: PtolCrawler instance.
    :param staging: PtolStaging instance.
    :param monitor: PtolMonitor instance.
    """

    def __init__(self, monad: MonadInterface, config, logger,
                 search, crawler, staging, monitor):
        super().__init__(name='TeachingThread', daemon=True)
        self._monad   = monad
        self._config  = config
        self._logger  = logger
        self._search  = search
        self._crawler = crawler
        self._staging = staging
        self._monitor = monitor
        self._halt       = threading.Event()
        self._words      = 0
        self._chunks     = 0
        self._t0         = 0.0
        self._seed_fails = 0   # consecutive offline seed attempts

    def stop(self):
        """Signal teaching loop to exit cleanly after current chunk."""
        self._halt.set()

    def _wpm(self) -> float:
        elapsed = (time.time() - self._t0) / 60.0
        return self._words / elapsed if elapsed > 0 else 0.0

    def _score_chunk(self, chunk: str) -> Optional[Dict[str, float]]:
        """
        Sample up to 30 words from chunk and return confidence metrics.

        :param chunk: Paragraph text.
        :returns: Dict with redundancy/novelty/noise/score, or None if too short.
        :rtype: dict or None
        """
        min_words = self._config.getint('chunk_min_words', 8)
        words = [w.strip('.,!?;:\'"()-—。，！？；：、""''（）【】《》…·')
                 for w in _cjk_space(chunk).lower().split()]
        words = [w for w in words if w.isalpha() or (_is_cjk(w[0]) if w else False)]
        if len(words) < min_words:
            return None

        import random
        sample = random.sample(words, min(30, len(words)))

        strong = weak = noise = 0
        for w in sample:
            score = self._monad.query(w)
            if score > 0.30:   strong += 1
            elif score > 0.05: weak   += 1
            else:              noise  += 1

        n          = len(sample)
        redundancy = strong / n
        novelty    = weak   / n
        noise_r    = noise  / n

        # Composite: reward novelty, penalise noise
        composite = (redundancy * 0.4 + novelty * 0.6) * (1.0 - noise_r)
        return {
            'redundancy': redundancy,
            'novelty':    novelty,
            'noise':      noise_r,
            'score':      composite,
        }

    def _should_ingest(self, conf: dict) -> bool:
        # Bootstrap: a fresh field scores all unseen words as noise (score < 0.05).
        # The BAO thresholds are meaningless until the field has a vocabulary base.
        # Ingest everything above min_words until vocab reaches 2000 slots.
        if self._monad.vocab_size() < 2000:
            return True

        red_min   = self._config.getfloat('redundancy_min',  0.15)
        red_max   = self._config.getfloat('redundancy_max',  0.85)
        nov_min   = self._config.getfloat('novelty_min',     0.05)
        noise_max = self._config.getfloat('noise_max',       0.45)
        if conf['noise'] > noise_max:     return False
        if conf['redundancy'] > red_max:  return False
        if (conf['redundancy'] < red_min
                and conf['novelty'] < nov_min): return False
        return True

    def _bao_adapt(self):
        """
        BAO-adaptive threshold update. Reads current bao_mean from engine,
        computes field_health and direction, adjusts thresholds in .ptolrc.
        Called every 50 chunks.
        """
        engine   = self._monad._engine
        bao_buf  = list(engine._bao_buf)
        if not bao_buf:
            return
        bao_mean  = sum(bao_buf) / len(bao_buf)
        delta     = bao_mean - OMEGA_ZS           # signed: neg=under, pos=over
        abs_delta = abs(delta)
        health    = max(0.0, 1.0 - abs_delta / 0.25)

        self._config.set_ptolrc('bao', 'field_health',  f"{health:.6f}")
        self._config.set_ptolrc('bao', 'bao_mean',      f"{bao_mean:.6f}")
        self._config.set_ptolrc('bao', 'bao_direction', f"{delta:.6f}")

        if abs_delta < 0.05:
            return   # rings are sharp — no threshold adjustment needed

        # Read current thresholds
        red_lo  = self._config.getfloat('redundancy_min', 0.15)
        red_hi  = self._config.getfloat('redundancy_max', 0.85)
        nov_min = self._config.getfloat('novelty_min',    0.05)
        noi_max = self._config.getfloat('noise_max',      0.45)

        step = 0.02
        if delta < 0:
            # Under-activated: relax novelty floor, widen redundancy window
            nov_min = max(0.01, nov_min - step * 0.5)
            red_lo  = max(0.05, red_lo  - step)
            red_hi  = min(0.95, red_hi  + step)
        else:
            # Over-dense: raise novelty floor, tighten redundancy ceiling
            nov_min = min(0.15, nov_min + step * 0.5)
            red_hi  = max(0.60, red_hi  - step * 1.5)
            noi_max = max(0.30, noi_max - step)

        self._config.set_ptolrc('thresholds', 'redundancy_min', f"{red_lo:.4f}")
        self._config.set_ptolrc('thresholds', 'redundancy_max', f"{red_hi:.4f}")
        self._config.set_ptolrc('thresholds', 'novelty_min',    f"{nov_min:.4f}")
        self._config.set_ptolrc('thresholds', 'noise_max',      f"{noi_max:.4f}")

        # UNS update
        if hasattr(self, '_hamiltonian') and self._hamiltonian:
            self._hamiltonian.write_to_ptolrc()

    def _process_special(self, url: str, meta):
        """
        Handle ptol+sep://, ptol+ocw://, ptol+lex:// scheme URLs.
        These are fetched via scholar/lexicon directly rather than PtolCrawler.

        :param url: Special scheme URL.
        :param meta: CiteMeta or None.
        """
        scholar = getattr(self, '_scholar', None)
        lexicon = getattr(self, '_lexicon', None)

        if url.startswith('ptol+sep://'):
            slug = url.replace('ptol+sep://', '')
            if scholar:
                result = scholar.fetch_sep(slug)
                if result:
                    text, dois, sep_meta = result
                    self._ingest_text_direct(text, url, sep_meta or meta)
                    # Enqueue bibliography DOIs
                    for doi in dois[:10]:
                        pdf_url = scholar.open_pdf(doi)
                        if pdf_url:
                            self._search.add_url(pdf_url,
                                                 scholar.resolve_doi(doi))

        elif url.startswith('ptol+ocw://'):
            dept = url.replace('ptol+ocw://', '')
            # Placeholder: OCW requires specific URL construction
            self._logger.skip(url, f'ocw_dept_{dept}_queued')

        elif url.startswith('ptol+lex://'):
            word = url.replace('ptol+lex://', '')
            if lexicon:
                text = lexicon.topology_text(word)
                if text:
                    self._ingest_text_direct(text, url, meta)

    def _ingest_text_direct(self, text: str, url: str, meta):
        """
        Ingest plain text directly (no file staging). Used for SEP/lexicon.

        :param text: Plain text.
        :param url: Source URL for logging.
        :param meta: CiteMeta or None.
        """
        cite_weight = meta.weight() if meta and hasattr(meta, 'weight') else 0.5
        ingested = 0
        for para in self._crawler.iter_paragraphs(text):
            if self._halt.is_set():
                break
            conf = self._score_chunk(para)
            if conf and self._should_ingest(conf):
                effective_score = conf['score'] * cite_weight
                if effective_score > 0.05 or self._monad.vocab_size() < 2000:
                    self._monad.ingest(para)
                    ingested    += 1
                    self._words += len(para.split())
                    self._chunks += 1
        if ingested:
            self._logger.learn(url, cite_weight, ingested, self._words,
                               cite_weight, 0)

    def _process(self, path, ctype: str, url: str, meta=None):
        """Chunk, score, ingest a staged file. cite_weight from CiteMeta."""
        text = self._crawler.to_text(path, ctype)
        if not text:
            self._logger.skip(url, 'empty')
            return

        cite_weight = meta.weight() if meta and hasattr(meta, 'weight') else 0.5
        ingested = skipped = 0
        total_conf = 0.0

        for para in self._crawler.iter_paragraphs(text):
            if self._halt.is_set():
                break

            # Yield to system under load
            while (self._monitor.should_throttle()
                   and not self._halt.is_set()):
                time.sleep(self._config.getfloat('throttle_sleep', 0.5))

            conf = self._score_chunk(para)
            if conf is None:
                skipped += 1
                continue

            if self._should_ingest(conf):
                effective = conf['score'] * cite_weight
                # During bootstrap, composite=0 (all words unknown); bypass gate.
                if effective > 0.02 or self._monad.vocab_size() < 2000:
                    self._monad.ingest(para)
                    ingested     += 1
                    total_conf   += effective
                    self._words  += len(para.split())
                    self._chunks += 1
            else:
                skipped += 1
                reason = ('redundant' if conf['redundancy'] > 0.85
                          else 'noise'  if conf['noise']      > 0.45
                          else 'foreign')
                self._logger.skip(f"{url}#p{ingested+skipped}", reason)

        if ingested:
            avg = total_conf / ingested
            self._logger.learn(url, avg, ingested, self._words, avg, 0)

        self._monitor.update_stats(wpm=self._wpm(),
                                   queue_depth=self._search.queue_depth())

        # Periodic .ptolrc + BAO adapt
        if self._chunks % 50 == 0 and self._chunks > 0:
            self._config.set_ptolrc('stats', 'words_learned', self._words)
            self._config.set_ptolrc('stats', 'wpm', f"{self._wpm():.1f}")
            self._config.set_ptolrc('stats', 'vocab',
                                    self._monad.vocab_size())
            self._bao_adapt()

        # Periodic bin checkpoint (every 500 chunks)
        if self._chunks % 500 == 0 and self._chunks > 0:
            _sp = os.path.expanduser(
                self._config.get('active_state', '~/.ptolemy/monad.bin'))
            self._monad.save(_sp)

    def run(self):
        self._t0 = time.time()
        self._logger.session('teach_start')

        # Resume staged files from previous crash
        for pending in self._staging.pending():
            if self._halt.is_set(): break
            ctype = self._crawler._detect_type(pending, str(pending))
            self._process(pending, ctype, str(pending))
            self._staging.remove(pending)

        # Main acquisition loop
        sources = getattr(self, '_sources', None)
        _was_offline = False
        while not self._halt.is_set():
            if self._search.queue_depth() < 5:
                if not _net_ok():
                    # No route to internet — back off exponentially (30s → 60s → … → 30min)
                    self._seed_fails += 1
                    wait = min(30 * (2 ** (self._seed_fails - 1)), 1800)
                    if not _was_offline:
                        self._logger.skip('connectivity', f'offline — waiting {wait}s')
                        _was_offline = True
                    self._halt.wait(wait)   # interruptible: wakes immediately on SIGTERM
                    continue
                # Internet restored
                if _was_offline:
                    self._logger.skip('connectivity', 'online — resuming')
                    _was_offline = False
                self._seed_fails = 0
                if sources:
                    sources.seed_active(max_queue=20)
                else:
                    self._search.seed_gutenberg()
                    if self._search.queue_depth() < 5:
                        self._search.seed_archive()

            item = self._search.next_url()
            if not item:
                self._halt.wait(2)   # interruptible idle
                continue

            url  = item['url']  if isinstance(item, dict) else item
            meta = item.get('meta') if isinstance(item, dict) else None

            # Skip special ptol+* scheme URLs not handled by crawler
            if url.startswith('ptol+sep://') or url.startswith('ptol+ocw://') \
                    or url.startswith('ptol+lex://'):
                self._process_special(url, meta)
                continue

            path, ctype = self._crawler.fetch(url)
            if path is None:
                continue

            self._process(path, ctype, url, meta)
            self._staging.remove(path)

        # Save on clean shutdown
        state_path = os.path.expanduser(
            self._config.get('active_state', '~/.ptolemy/monad.bin'))
        self._monad.save(state_path)
        self._logger.session('teach_stop', words=self._words,
                             chunks=self._chunks, wpm=f"{self._wpm():.1f}")


# ══════════════════════════════════════════════════════════════════════════════
#  _build_teach_stack — wire all skills for --teach mode
# ══════════════════════════════════════════════════════════════════════════════

def _build_teach_stack(engine: 'Engine'):
    """
    Instantiate full skill stack: config, logger, staging, monitor, search,
    crawler, scholar, lexicon, sources, HamiltonianReport, MonadInterface,
    SpeakingThread, TeachingThread. Start all threads.

    :param engine: Loaded Engine instance.
    :returns: (monad_iface, speak_thread, teach_thread, monitor, logger)
    :rtype: tuple
    """
    import signal

    from skills.config     import PtolConfig
    from skills.logger     import PtolLogger
    from skills.staging    import PtolStaging
    from skills.monitor    import PtolMonitor
    from skills.search     import PtolSearch
    from skills.crawler    import PtolCrawler
    from skills.scholar    import PtolScholar
    from skills.lexicon    import PtolLexicon
    from skills.sources    import PtolSources
    from skills.draw       import HamiltonianReport
    from skills.integrity  import FieldHealth as _FieldHealth   # noqa: F401

    # ── Seed from local corpus first (before any internet fetch) ─────────────
    _repo_root    = os.path.dirname(os.path.abspath(__file__))
    _corpus_path  = os.path.join(_repo_root, 'corpus', 'holcus_seed.txt')
    if os.path.exists(_corpus_path):
        with open(_corpus_path, encoding='utf-8') as _cf:
            _corpus_lines = [l for l in _cf if l.strip() and not l.startswith('#')]
        if _corpus_lines:
            engine.load('\n'.join(_corpus_lines))
            print(f'[ptolemy] corpus seed: {len(_corpus_lines)} lines from {_corpus_path}',
                  file=sys.stderr)

    cfg        = PtolConfig()
    logger     = PtolLogger(cfg.get('log_dir', '~/.ptolemy/logs'))
    staging    = PtolStaging(cfg.get('temp_dir',  '~/.ptolemy/.ptoltemp'),
                             cfg.get('cache_dir', '~/.ptolemy/cache'))
    monitor    = PtolMonitor(logger, cfg)
    memory_log = MemoryLog(cfg.get('memory_log',
                                   '~/.ptolemy/memory_corrections.json'))
    # Replay stored retractions onto the freshly loaded field.
    # Ensures corrections survive bin wipes and retrains.
    memory_log.replay(engine)
    monad      = MonadInterface(engine, memory_log=memory_log)
    opener  = urllib_opener()
    search  = PtolSearch(opener, logger)
    crawler = PtolCrawler(staging, logger, cfg)
    sensors = SensorArray(engine)

    scholar = PtolScholar(opener, logger, search, cfg)
    lexicon = PtolLexicon(opener, logger, cfg, search)
    sources = PtolSources(cfg, search, logger, scholar=scholar, lexicon=lexicon)
    hamrpt  = HamiltonianReport(engine, cfg, sensors)

    # Write full .ptolrc on first teach run (all defaults visible to Ptolemy)
    cfg.write_full_ptolrc(engine)

    speak  = SpeakingThread(monad, cfg, logger)
    teach  = TeachingThread(monad, cfg, logger, search, crawler,
                            staging, monitor)

    # Wire scholar, lexicon, sources, hamiltonian into TeachingThread
    teach._scholar    = scholar
    teach._lexicon    = lexicon
    teach._sources    = sources
    teach._hamiltonian = hamrpt

    monitor.start()
    speak.start()
    teach.start()

    def _shutdown(sig, frame):
        print('\n[ptolemy] shutting down...', file=sys.stderr)
        teach.stop()
        speak.stop()
        monitor.stop()
        # Save immediately — don't wait for teach.run() to unblock from fetch()
        _sp = os.path.expanduser(cfg.get('active_state', '~/.ptolemy/monad.bin'))
        try:
            monad.save(_sp)
            print(f'[ptolemy] saved → {_sp}', file=sys.stderr)
        except Exception as _e:
            print(f'[ptolemy] save failed: {_e}', file=sys.stderr)
        teach.join(timeout=5)
        logger.close()
        sys.exit(0)

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    return monad, speak, teach, monitor, logger


def _net_ok(host: str = '1.1.1.1', port: int = 53, timeout: float = 2.0) -> bool:
    """
    Quick TCP probe to Cloudflare DNS — cheap, no HTTP overhead.
    Returns True if a route to the internet exists.

    :param host: Host to probe.
    :param port: Port to probe.
    :param timeout: Seconds before giving up.
    :returns: True if reachable.
    :rtype: bool
    """
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def urllib_opener():
    """
    Build and install a Mozilla UA urllib opener.

    :returns: OpenerDirector with Mozilla headers.
    """
    import urllib.request as _ur
    opener = _ur.build_opener()
    opener.addheaders = [
        ('User-Agent',
         'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0'),
        ('Accept',          'text/html,text/plain,*/*;q=0.8'),
        ('Accept-Language', 'en-US,en;q=0.9'),
    ]
    _ur.install_opener(opener)
    return opener


if __name__ == '__main__':
    main()
