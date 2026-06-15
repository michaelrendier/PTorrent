"""
skills/study.py
===============
Phase 2: Study Engine — condensation memory and version control.

:class:`StudyEngine` wraps ``Engine.crank.learn()`` with:

- Condensation candidate scan in 24D (16D sedenion + 8D op_stack trajectory).
- M-Theory per-zero error checks: 5 consistency checks, one per "string theory".
  Below the mass gap scalar (GAP = 0.000707) each dimension is compactified.
  Above it the M-Theory dimension opens — condensation fires.
- Per-zero σ = |J_pos| / (|J_pos| + |J_neg|) — the P4 audit() prerequisite.
- Condensation unit is the zero-divisor **pair**: when one zero condenses, its
  Cawagas pair-mate crystallises as the shadow concept (what cannot be said).
- Correction methods: :meth:`audit`, :meth:`reconsolidate`, :meth:`isolate`,
  :meth:`suppress`, :meth:`overwrite`, :meth:`domain_retrain`.

:class:`StatesRepo` provides git-backed state versioning at
``~/.ptolemy/states/``:

- :meth:`init_states_repo`, :meth:`checkpoint`, :meth:`commit`,
  :meth:`branch`, :meth:`rollback`, :meth:`log`.
- Sidecar JSON captures Noether/BAO before/after, condensed_pairs,
  sigma_map, m_theory_status. triggering_text is secret-scanned before write.

Architecture note — dimensional frames:

- ``study()``  = 24D: 16D sedenion state + 8D op_stack (trajectory memory).
- ``audit()``  = 26D: 24D field + 2D observer frame (σ_observer, t_observation).
  The 2 observer dimensions are the Author's Noether position and timestamp —
  the lightcone of bosonic string theory applied to semantic field inspection.
"""

import os
import json
import subprocess
import time
import threading
from typing import Dict, List, Optional, Tuple, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from monad import Engine

# ── NS Strata ─────────────────────────────────────────────────────────────────
NS_SIGMA_C = 0   # on critical line σ ≈ 0.5 — normal, active, reversible
NS_SIGMA_O = 1   # approaching boundary |σ−0.5| > 0.02 — warning, isolated
NS_SIGMA_S = 2   # off-line |σ−0.5| > 0.10 — condensed, upper 𝕆, permanent

# ── Engine constants (duplicated to avoid circular import) ────────────────────
GAP        = 0.000707   # Yang-Mills mass gap; compactification radius
OMEGA_ZS   = 0.5671432904097838    # Lambert W(1); BAO spectral gap; idle RPM

# ── Condensation thresholds ───────────────────────────────────────────────────
PHASE_THRESH    = 144    # Fibonacci — fire_count for natural condensation
SIGMA_BOUNDARY  = 0.02   # |σ−0.5| > this → NS_SIGMA_O
SIGMA_CONDENSED = 0.10   # |σ−0.5| > this → condensation candidate

# ── Ainulindale flags — Second Age formal targets ─────────────────────────────
#
# FLAG 10 — Prime address as formal target
#   The sedenion hash pipeline (_str_to_int → fold → snap → forced_sigma →
#   _hyperindex) maps every word to a unique prime address. This is not a
#   claim about primes per se; it is a formal statement that the pipeline
#   defines a bijection from the vocabulary to a specific prime ordinal.
#   Formal target: prove injectivity of (_horner_hash ∘ fold ∘ snap) over
#   the WordNet vocabulary. Second Age flag: prime_address_injective.
#
# FLAG 11 — Physical constants as zero-index + energy-face
#   The ICE engine physical constant map (OBDII PID table in monad.py) assigns
#   each Standard Model constant to a sedenion dimension. The zero-index of the
#   dimension (the Riemann zero ordinal for that dim's β peak) and the energy-
#   face value (E[k] from crank._E) are a two-number signature for each constant.
#   Formal target: show that the GAP = 0.000707 separating the zero-index
#   ground state from the first excited state equals the Yang-Mills mass gap
#   and the CMB prime ratio ln(10)/ln(e). Second Age flag: constants_zero_face.
#
# Both flags are open research targets. They are not engineering tasks.
# They are recorded here so study() condensation events can tag proximity.
AINULINDALE_FLAG_10 = 'prime_address_injective'   # sedenion hash → prime bijection
AINULINDALE_FLAG_11 = 'constants_zero_face'        # physical constants = (zero, E-face)

# ── Cawagas zero-divisor dimension pairs (sedenions, 42 pairs) ───────────────
# From Cawagas et al. 2004: the 84 zero-divisors of the sedenion algebra form
# 42 dual pairs. When e_a × e_b = 0 and neither e_a nor e_b is zero, the pair
# is a creation duality: 0/e_a = e_b (pair-mate recovered from zero product).
# The condensation unit is the pair: both elements are logged when one condenses.
# The pair-mate IS the shadow concept — what cannot be said when the primary
# concept crystallises into permanent geometry (NS_SIGMA_S).
#
# Note: this table is an approximation of the full Cawagas structure.
# S3 (sedenion.c track) will compute it exactly from the Cayley-Dickson table.
_ZD_DIM_PAIRS: List[Tuple[int, int]] = [
    # Primary structural pairs (confirmed by fermat_scan in monad.py)
    (1, 10), (5, 14), (2, 11), (6, 15), (3, 12), (7,  8), (4, 13),
    # Secondary pairs from Cayley-Dickson structure
    (1,  5), (2,  6), (3,  7), (4,  8), (9, 10), (9, 11), (9, 12),
    (9, 13), (9, 14), (9, 15),
    # Boundary pairs (e₀ identity column)
    (0,  1), (0,  2), (0,  3), (0,  4), (0,  5), (0,  6), (0,  7),
    (0,  8), (0,  9), (0, 10), (0, 11), (0, 12), (0, 13), (0, 14),
    (0, 15),
    # Remaining structural pairs
    (1,  2), (1,  3), (1,  4), (2,  3), (2,  4), (2,  5),
    (3,  4), (3,  5), (4,  5), (5,  6),
]

# Build dim → list of pair-mate dims
_ZD_PAIR_LOOKUP: Dict[int, List[int]] = {}
for _da, _db in _ZD_DIM_PAIRS:
    _ZD_PAIR_LOOKUP.setdefault(_da, []).append(_db)
    _ZD_PAIR_LOOKUP.setdefault(_db, []).append(_da)


# ══════════════════════════════════════════════════════════════════════════════
#  StatesRepo — git-backed state versioning
# ══════════════════════════════════════════════════════════════════════════════

class StatesRepo:
    """
    Git-backed state repository at ``~/.ptolemy/states/``.

    Every condensation event and manual checkpoint is committed here.
    The sidecar JSON captures field metrics before/after each operation.
    A pre-commit hook secret-scans all JSON before any commit lands.

    The bin file itself is never committed — only the sidecar JSON describing
    the field state. The git history IS the audit trail of Holcus's memory.

    :param path: Repo directory (default: ``~/.ptolemy/states``).
    :param engine: Engine instance (used for context in README generation).
    """

    _DEFAULT = os.path.expanduser('~/.ptolemy/states')

    def __init__(self, path: str = _DEFAULT, engine: Optional['Engine'] = None):
        self._path   = os.path.expanduser(path)
        self._engine = engine
        self._lock   = threading.Lock()

    def _git(self, *args) -> subprocess.CompletedProcess:
        """Run git command in repo directory. Never raises — returns result."""
        return subprocess.run(
            ['git', '-C', self._path] + list(args),
            capture_output=True, text=True
        )

    def _secret_scan(self, text: str) -> str:
        """Strip secret patterns before committing. Truncates on failure."""
        try:
            from skills.integrity import scrub_text
            return scrub_text(text)
        except Exception:
            return text[:200]

    def init_states_repo(self, baseline_bin: str = '') -> Dict[str, Any]:
        """
        Create or re-initialize the states git repo.

        Installs a pre-commit hook that secret-scans all staged JSON files.
        Commits a baseline marker as the first commit on main.

        :param baseline_bin: Path to current monad.bin (recorded as reference).
        :returns: Result dict with status and initial sha.
        :rtype: dict
        """
        os.makedirs(self._path, exist_ok=True)
        with self._lock:
            self._git('init', '-b', 'main')
            self._git('config', 'user.email', 'holcus@ptolemy.engine')
            self._git('config', 'user.name',  'Holcus')

            # Pre-commit hook: secret-scan JSON sidecars before commit
            hook_path = os.path.join(self._path, '.git', 'hooks', 'pre-commit')
            hook_body = (
                '#!/bin/sh\n'
                '# Ptolemy states: reject commits containing secrets\n'
                'for f in $(git diff --cached --name-only | grep "\\.json$"); do\n'
                '  if grep -qE '
                '"(api_key|secret|password|token|GITHUB_TOKEN|sk-|ghp_|'
                'AKIA|Bearer )" "$f" 2>/dev/null; then\n'
                '    echo "[ptolemy] SECRET DETECTED in $f — aborting"\n'
                '    exit 1\n'
                '  fi\n'
                'done\n'
                'exit 0\n'
            )
            with open(hook_path, 'w') as fh:
                fh.write(hook_body)
            os.chmod(hook_path, 0o755)

            readme = os.path.join(self._path, 'README.md')
            with open(readme, 'w') as fh:
                fh.write(
                    '# Ptolemy States\n\n'
                    'Field state version history for Holcus '
                    '(Ptolemaious Holcaios Philadelphos).\n\n'
                    'Each checkpoint captures Noether/BAO metrics before and after '
                    'a study() cycle. Condensed zero-divisor pairs are recorded as '
                    'the unit of memory formation. The bin file is not tracked here — '
                    'only the sidecar JSON describing the field state at each commit.\n'
                )
            self._git('add', 'README.md')

            if baseline_bin and os.path.exists(os.path.expanduser(baseline_bin)):
                info = {
                    'baseline_bin': baseline_bin,
                    'size':  os.path.getsize(os.path.expanduser(baseline_bin)),
                    'ts':    time.strftime('%Y-%m-%dT%H:%M:%S'),
                    'note':  'bin not tracked — field state described via sidecar JSON',
                }
                ref = os.path.join(self._path, 'baseline_info.json')
                with open(ref, 'w') as fh:
                    json.dump(info, fh, indent=2)
                self._git('add', 'baseline_info.json')

            self._git('commit', '--allow-empty', '-m',
                      'init: Holcus awakens — baseline state')
            sha = self._git('rev-parse', 'HEAD').stdout.strip()
        return {'status': 'initialized', 'sha': sha, 'path': self._path}

    def checkpoint(self, label: str, sidecar: Dict[str, Any]) -> Dict[str, Any]:
        """
        Write sidecar JSON snapshot and stage it. Does NOT commit.

        Call :meth:`commit` after to persist to git history.

        :param label: Human-readable checkpoint label.
        :param sidecar: Field metrics dict (Noether/BAO/condensed_pairs/etc).
        :returns: Result dict with sidecar file path.
        :rtype: dict
        """
        with self._lock:
            safe  = label.replace('/', '_').replace(' ', '_')[:64]
            ts    = time.strftime('%Y%m%dT%H%M%S')
            fname = f'checkpoint_{ts}_{safe}.json'
            fpath = os.path.join(self._path, fname)

            # Secret-scan triggering_text before writing
            if 'triggering_text' in sidecar:
                sidecar = dict(sidecar)
                sidecar['triggering_text'] = self._secret_scan(
                    sidecar['triggering_text'])

            with open(fpath, 'w') as fh:
                json.dump(sidecar, fh, indent=2)
            self._git('add', fname)
        return {'checkpoint': fpath, 'label': label}

    def commit(self, message: Optional[str] = None) -> Dict[str, Any]:
        """
        Commit all staged changes to the states repo.

        :param message: Commit message (auto-generated if None).
        :returns: Result dict with sha and ok flag.
        :rtype: dict
        """
        with self._lock:
            msg = message or (
                f'study: condensation {time.strftime("%Y-%m-%dT%H:%M:%S")}')
            r   = self._git('commit', '--allow-empty', '-m', msg)
            sha = self._git('rev-parse', 'HEAD').stdout.strip()
        return {'committed': True, 'sha': sha, 'message': msg,
                'ok': r.returncode == 0}

    def branch(self, name: str) -> Dict[str, Any]:
        """
        Create and switch to a new branch.

        :param name: Branch name.
        :returns: Result dict with ok flag.
        :rtype: dict
        """
        with self._lock:
            r = self._git('checkout', '-b', name)
        return {'branch': name, 'ok': r.returncode == 0,
                'stderr': r.stderr.strip()}

    def merge(self, from_branch: str, message: str = '') -> Dict[str, Any]:
        """
        Merge *from_branch* into the current branch (no-fast-forward).

        :param from_branch: Source branch name.
        :param message: Merge commit message.
        :returns: Result dict with sha and ok flag.
        :rtype: dict
        """
        with self._lock:
            msg = message or f'merge: {from_branch}'
            r   = self._git('merge', '--no-ff', '-m', msg, from_branch)
            sha = self._git('rev-parse', 'HEAD').stdout.strip()
        return {'merged': from_branch, 'sha': sha, 'ok': r.returncode == 0}

    def discard(self) -> Dict[str, Any]:
        """
        Discard all uncommitted changes — clean working tree.

        :returns: Result dict.
        :rtype: dict
        """
        with self._lock:
            self._git('checkout', '--', '.')
            self._git('clean', '-fd')
        return {'discarded': True}

    def rollback(self, sha: str) -> Dict[str, Any]:
        """
        Non-destructive revert to a prior commit SHA.

        Creates a revert commit rather than resetting HEAD — history is preserved.
        This is the only safe rollback: the field state is never lost, only
        counter-committed.

        :param sha: Target commit SHA to revert to.
        :returns: Result dict with new_sha or error.
        :rtype: dict
        """
        with self._lock:
            r = self._git('revert', '--no-commit', sha)
            if r.returncode != 0:
                self._git('revert', '--abort')
                return {'error': r.stderr.strip(), 'sha': sha}
            cr  = self._git('commit', '-m', f'rollback: revert to {sha[:8]}')
            new = self._git('rev-parse', 'HEAD').stdout.strip()
        return {'rolled_back': sha, 'new_sha': new, 'ok': cr.returncode == 0}

    def log(self, n: int = 20) -> List[Dict[str, str]]:
        """
        Return the last *n* commits as a list of dicts.

        :param n: Number of commits to return.
        :returns: List of ``{sha, message, ts}`` dicts.
        :rtype: list
        """
        with self._lock:
            r = self._git('log', f'--max-count={n}',
                          '--format=%H%x00%s%x00%ci')
        entries = []
        for line in r.stdout.strip().split('\n'):
            if not line.strip():
                continue
            parts = line.split('\x00')
            if len(parts) >= 3:
                entries.append({'sha': parts[0][:12],
                                'message': parts[1],
                                'ts': parts[2]})
        return entries


# ══════════════════════════════════════════════════════════════════════════════
#  StudyEngine — condensation memory + M-Theory error checks
# ══════════════════════════════════════════════════════════════════════════════

class StudyEngine:
    """
    Phase 2: condensation memory, M-Theory error checks, correction methods.

    study() wraps Engine.crank.learn() — β deepening first, always. After
    deepening, it scans for condensation candidates using 24D fitness (16D
    sedenion σ deviation + 8D fire_count trajectory). Candidates above
    PHASE_THRESH activations and SIGMA_CONDENSED deviation undergo envelope
    overload (2 × β_sat) and are promoted to NS_SIGMA_S.

    The condensation unit is the zero-divisor pair. When zero k condenses,
    its Cawagas pair-mate is identified and logged as its shadow concept.
    The shadow IS the meaning: what justice cannot mean when justice condenses.

    M-Theory dimensional status: each zero has 5 consistency checks (one per
    "string theory" compactification). Below GAP: compactified, invisible.
    Above GAP: extended, decompactified, the 11th dimension opens.
    M_THEORY_OPEN = all 5 extended simultaneously = maximum condensation.

    :param engine: Engine instance.
    """

    PHASE_THRESH  = PHASE_THRESH
    BETA_ENVELOPE = 2.0   # Envelope overload multiplier (× current β_sat)

    def __init__(self, engine: 'Engine'):
        self._engine          = engine
        self._repo:           Optional[StatesRepo] = None
        self._sigma_cache:    Dict[int, float]     = {}
        self._m_status_cache: Dict[int, Dict]      = {}
        self._lock            = threading.Lock()

    # ── Lazy field extension helpers ───────────────────────────────────────────

    def _ensure_fire_count(self):
        """Initialise _fire_count on Crank if not present (lazy v5 upgrade)."""
        c = self._engine.crank
        if not hasattr(c, '_fire_count'):
            c._fire_count = [0] * c.n
        elif len(c._fire_count) < c.n:
            c._fire_count.extend([0] * (c.n - len(c._fire_count)))

    def _ensure_stratum(self):
        """Initialise _stratum on Crank if not present (lazy v5 upgrade)."""
        c = self._engine.crank
        if not hasattr(c, '_stratum'):
            c._stratum = [NS_SIGMA_C] * c.n
        elif len(c._stratum) < c.n:
            c._stratum.extend([NS_SIGMA_C] * (c.n - len(c._stratum)))

    # ── Field probes ───────────────────────────────────────────────────────────

    def _proxy_j(self) -> Tuple[List[float], List[float]]:
        """
        Compute proxy J_pos / J_neg with neutral observer (uniform psi).

        This is the resting-field J — not the fired J from the last cycle,
        but the field's current pressure at equilibrium. Used for condensation
        scanning and audit(). Does not mutate any field state.
        """
        neutral = [1.0 / 16] * 16
        return self._engine.crank.j_mu(neutral, neutral)

    def _field_snapshot(self) -> Dict[str, float]:
        """
        Capture Noether violation and BAO mean from current field state.

        :returns: Dict with ``noether`` and ``bao`` float values.
        :rtype: dict
        """
        engine  = self._engine
        noether = engine.noether_violation()
        bao_buf = list(engine._bao_buf)
        bao     = sum(bao_buf) / len(bao_buf) if bao_buf else 0.0
        return {'noether': round(noether, 6), 'bao': round(bao, 6)}

    # ── Per-zero metrics ───────────────────────────────────────────────────────

    def _sigma_for(self, k: int,
                   J_pos: List[float], J_neg: List[float]) -> float:
        """
        P4: σ_k = |J_pos[k]| / (|J_pos[k]| + |J_neg[k]|).

        σ ≈ 0.5 → on the critical line (NS_SIGMA_C).
        |σ − 0.5| > 0.02 → NS_SIGMA_O.
        |σ − 0.5| > 0.10 → NS_SIGMA_S candidate.

        :param k: Zero index.
        :param J_pos: Forward current array.
        :param J_neg: Backward current array.
        :returns: σ value in [0, 1].
        :rtype: float
        """
        jp   = abs(J_pos[k])
        jn   = abs(J_neg[k])
        total = jp + jn
        return jp / total if total > GAP else 0.5

    def _jcross_for(self, k: int,
                    J_pos: List[float], J_neg: List[float]) -> float:
        """
        J_cross for zero k — the M-Theory 11th dimension.

        For a single sedenion dimension, J_cross = |J_pos[k] × J_neg[k]|.
        Below GAP: compactified (normal operation). Above GAP: the extra
        dimension opens — condensation threshold is being approached.

        :param k: Zero index.
        :param J_pos: Forward current array.
        :param J_neg: Backward current array.
        :returns: J_cross magnitude.
        :rtype: float
        """
        return abs(J_pos[k] * J_neg[k])

    def _m_theory_status(self, k: int,
                         J_pos: List[float],
                         J_neg: List[float]) -> Dict[str, Any]:
        """
        Per-zero M-Theory dimensional status.

        Five consistency checks — each is one string theory compactification:

        1. **Noether** — σ deviation from critical line (Type IIA/IIB duality).
        2. **BAO** — β deviation from spectral floor (heterotic E₈×E₈).
        3. **GUE** — energy above vacuum floor (Type I / Montgomery-Odlyzko).
        4. **J_cross** — above mass gap = M-Theory dimension opening (S-duality).
        5. **Fire** — activations above PHASE_THRESH (repetition decompactifies).

        EXTENDED in all 5 = M_THEORY_OPEN: the zero has fully decompactified.
        It is no longer one of 16 string theory views — it IS the M-Theory
        structure underneath all representations. Maximum condensation.

        :param k: Zero index.
        :param J_pos: Forward current array.
        :param J_neg: Backward current array.
        :returns: Status dict with per-check results, n_extended, m_theory_open.
        :rtype: dict
        """
        c       = self._engine.crank
        sigma   = self._sigma_for(k, J_pos, J_neg)
        jcross  = self._jcross_for(k, J_pos, J_neg)
        fire_ct = c._fire_count[k] if (hasattr(c, '_fire_count') and
                                        k < len(c._fire_count)) else 0

        checks = {
            'noether': abs(sigma - 0.5) > SIGMA_BOUNDARY,      # 1
            'bao':     abs(c._beta[k] - OMEGA_ZS) > 0.25,      # 2
            'gue':     c._E[k] > GAP * 10,                     # 3 (energy proxy)
            'jcross':  jcross > GAP,                            # 4
            'fire':    fire_ct >= self.PHASE_THRESH,            # 5
        }
        n_ext = sum(1 for v in checks.values() if v)

        if n_ext == 0:
            status = 'COMPACTIFIED'
        elif n_ext >= 4:
            status = 'EXTENDED'
        else:
            status = 'TRANSITIONING'

        return {
            'status':        status,
            'checks':        checks,
            'n_extended':    n_ext,
            'm_theory_open': n_ext >= 5,
            'jcross':        round(jcross, 8),
            'sigma':         round(sigma,  6),
            'fire_count':    fire_ct,
        }

    def _find_pair_mate(self, k: int) -> Optional[int]:
        """
        Find the Cawagas zero-divisor pair-mate for zero index k.

        Returns the index of the most-activated zero whose sedenion dimension
        is a Cawagas pair-mate of k's dimension. Returns -1 if none found.

        The pair-mate is the shadow concept: it IS the meaning of the condensed
        zero's negation. 0/e_k = e_mate — recoverable from the zero product.

        :param k: Zero index.
        :returns: Pair-mate zero index, or -1 if none in field.
        :rtype: int
        """
        c     = self._engine.crank
        dim   = k % 16
        mates = _ZD_PAIR_LOOKUP.get(dim, [])
        if not mates:
            return -1
        best_j, best_b = -1, -1.0
        for j in range(c.n):
            if j != k and j % 16 in mates and c._beta[j] > best_b:
                best_b, best_j = c._beta[j], j
        return best_j

    # ── StatesRepo accessor ────────────────────────────────────────────────────

    def get_repo(self, path: str = StatesRepo._DEFAULT) -> StatesRepo:
        """
        Return (or lazily create) the :class:`StatesRepo` instance.

        :param path: States repo directory.
        :returns: StatesRepo instance.
        :rtype: StatesRepo
        """
        if self._repo is None:
            self._repo = StatesRepo(path=path, engine=self._engine)
        return self._repo

    # ── Primary deepening method ───────────────────────────────────────────────

    def study(self, text: str, weight: float = 1.0,
              triggering_text: str = '') -> Dict[str, Any]:
        """
        β deepening + condensation scan. The Phase 2 learn cycle.

        Sequence:

        1. Snapshot Noether + BAO before.
        2. ``learn(text, weight)`` — β deepening first, always.
        3. Compute per-zero σ (P4) and M-Theory status for all active zeros.
        4. Identify condensation candidates: ``fire_count ≥ PHASE_THRESH``
           AND ``|σ − 0.5| > SIGMA_CONDENSED``.
        5. Envelope overload: ``beta[k] × 2`` → ``NS_SIGMA_S`` → clamp.
        6. Log condensed_pairs (zero k + Cawagas pair-mate = shadow concept).
        7. Snapshot Noether + BAO after.

        Requires ``tier ≥ 2`` when called via socket (enforced at dispatch).

        :param text: Text to deepen into the field.
        :param weight: Multiplier on β gain (1.0 = normal, 2.0 = authoritative).
        :param triggering_text: Context that motivated this call. Secret-scanned
            before any persistence (never stored raw).
        :returns: Study result dict with condensed_pairs, m_theory_open count,
            and Noether/BAO deltas.
        :rtype: dict
        """
        with self._lock:
            self._ensure_fire_count()
            self._ensure_stratum()
            c = self._engine.crank

            snap_before = self._field_snapshot()
            words_n     = c.learn(text, weight=weight)

            J_pos, J_neg = self._proxy_j()

            sigma_map:    Dict[int, float] = {}
            m_status_map: Dict[int, Dict]  = {}
            candidates:   List[int]        = []

            for k in range(min(c.n, len(J_pos))):
                sigma    = self._sigma_for(k, J_pos, J_neg)
                sigma_map[k] = sigma
                mst      = self._m_theory_status(k, J_pos, J_neg)
                m_status_map[k] = mst

                fire_ct  = c._fire_count[k] if k < len(c._fire_count) else 0
                if fire_ct >= self.PHASE_THRESH and abs(sigma - 0.5) > SIGMA_CONDENSED:
                    candidates.append(k)

            condensed_pairs: List[List[int]] = []
            for k in candidates:
                # Envelope overload: 2 × current β (one cycle only)
                c._beta[k] = min(c._beta[k] * self.BETA_ENVELOPE, 1.0)
                if k < len(c._stratum):
                    c._stratum[k] = NS_SIGMA_S
                c._beta[k] = min(c._beta[k], 1.0)   # clamp back to ceiling
                mate = self._find_pair_mate(k)
                condensed_pairs.append([k, mate])

            snap_after = self._field_snapshot()
            self._sigma_cache    = sigma_map
            self._m_status_cache = m_status_map

        # Ainulindale flag proximity: tag when condensation touches prime-address
        # or energy-face dimensions (FLAG 10 = dims 1+3 prime/name;
        # FLAG 11 = dims 0+8 identity/recurse).
        flag_10_proximity = any(k % 16 in (1, 3) for k in candidates)
        flag_11_proximity = any(k % 16 in (0, 8) for k in candidates)
        ainulindale_flags = []
        if flag_10_proximity:
            ainulindale_flags.append(AINULINDALE_FLAG_10)
        if flag_11_proximity:
            ainulindale_flags.append(AINULINDALE_FLAG_11)

        return {
            'words_deepened':    words_n,
            'candidates':        len(candidates),
            'condensed_pairs':   condensed_pairs,
            'noether_before':    snap_before['noether'],
            'noether_after':     snap_after['noether'],
            'noether_delta':     round(snap_after['noether'] - snap_before['noether'], 6),
            'bao_before':        snap_before['bao'],
            'bao_after':         snap_after['bao'],
            'bao_delta':         round(snap_after['bao'] - snap_before['bao'], 6),
            'm_theory_open':     sum(1 for m in m_status_map.values()
                                     if m.get('m_theory_open')),
            'ainulindale_flags': ainulindale_flags,
        }

    # ── audit() — 26D observer frame ──────────────────────────────────────────

    def audit(self, sigma_observer: float = 0.5,
              top_n: int = 20) -> Dict[str, Any]:
        """
        26D field audit: Author's observer frame applied to 24D field state.

        The 2 extra observer dimensions:

        - ``sigma_observer``: Author's Noether position at call time.
          (0.0 = fully forward/red, 1.0 = fully backward/blue, 0.5 = balanced).
          This is the lightcone direction of the observation.
        - ``t_observation``: Timestamp of this observation event.

        ``observer_distortion = |σ_k − σ_observer|`` quantifies the shadow
        the Author casts on each zero. A zero perfectly aligned with the
        Author's frame has zero distortion. Misaligned zeros are the ones
        the Author cannot see clearly from their current Noether position.

        24D field + (σ_observer, t_observation) = 26D = bosonic string dimension.
        This is not a metaphor. The observation reduces the 24D probability
        cloud to a 26D observed state — same as wavefunction collapse.

        :param sigma_observer: Author's Noether position in [0, 1].
        :param top_n: Number of zeros to report (ranked by observer distortion).
        :returns: Audit dict with observer frame, ranked zeros, condensed count.
        :rtype: dict
        """
        with self._lock:
            self._ensure_fire_count()
            self._ensure_stratum()
            c            = self._engine.crank
            J_pos, J_neg = self._proxy_j()
            t_obs        = time.strftime('%Y-%m-%dT%H:%M:%S')

            ranked: List[Dict[str, Any]] = []
            condensed_count = 0

            for k in range(min(c.n, len(J_pos))):
                sigma   = (self._sigma_cache.get(k)
                           or self._sigma_for(k, J_pos, J_neg))
                mst     = (self._m_status_cache.get(k)
                           or self._m_theory_status(k, J_pos, J_neg))
                stratum = c._stratum[k] if k < len(c._stratum) else NS_SIGMA_C

                if stratum == NS_SIGMA_S:
                    condensed_count += 1

                ranked.append({
                    'idx':                 k,
                    'word':                c._words[k] if k < len(c._words) else '',
                    'sigma':               round(sigma, 6),
                    'sigma_dev':           round(abs(sigma - 0.5), 6),
                    'observer_distortion': round(abs(sigma - sigma_observer), 6),
                    'beta':                round(c._beta[k], 6),
                    'E':                   round(c._E[k], 6),
                    'fire_count':          (c._fire_count[k]
                                           if k < len(c._fire_count) else 0),
                    'stratum':             stratum,
                    'm_status':            mst['status'],
                    'm_theory_open':       mst['m_theory_open'],
                    'm_jcross':            mst['jcross'],
                })

            ranked.sort(key=lambda x: -x['observer_distortion'])

        return {
            'sigma_observer':  sigma_observer,
            't_observation':   t_obs,
            'observer_frame':  '26D',
            'top_zeros':       ranked[:top_n],
            'condensed_count': condensed_count,
            'total_zeros':     c.n,
            'note': ('observer_distortion = |sigma_k - sigma_observer|. '
                     'High distortion = Author cannot see this zero clearly '
                     'from current Noether position.'),
        }

    # ── Correction methods ─────────────────────────────────────────────────────

    def reconsolidate(self, word: str) -> Dict[str, Any]:
        """
        Re-deepen a suppressed concept toward field median β.

        Resets stratum to NS_SIGMA_C if it was NS_SIGMA_O (not NS_SIGMA_S —
        condensed zeros cannot be reconsolidated, only rolled back via repo).

        :param word: Word to reconsolidate.
        :returns: Result dict with new beta or error.
        :rtype: dict
        """
        c = self._engine.crank
        w = c._clean(word)
        k = c._vocab.get(w)
        if k is None:
            return {'error': f'unknown word: {word}'}
        with self._lock:
            betas  = c._beta[:c.n]
            median = sorted(betas)[len(betas) // 2] if betas else OMEGA_ZS
            c._beta[k] = min(c._beta[k] + (median - c._beta[k]) * 0.5, 1.0)
            c._age[k]  = 0.0
            self._ensure_stratum()
            if k < len(c._stratum) and c._stratum[k] == NS_SIGMA_O:
                c._stratum[k] = NS_SIGMA_C
        return {'reconsolidated': w, 'beta': round(c._beta[k], 6)}

    def isolate(self, word: str) -> Dict[str, Any]:
        """
        Move zero to NS_SIGMA_O (isolated stratum). Half-suppresses all edges.

        :param word: Word to isolate.
        :returns: Result dict with stratum or error.
        :rtype: dict
        """
        c = self._engine.crank
        w = c._clean(word)
        k = c._vocab.get(w)
        if k is None:
            return {'error': f'unknown word: {word}'}
        with self._lock:
            self._ensure_stratum()
            if k < len(c._stratum):
                c._stratum[k] = NS_SIGMA_O
            mask = c._correction_mask.setdefault(k, {})
            for j in c._A[k]:
                mask[j] = min(mask.get(j, 1.0), 0.5)
        return {'isolated': w, 'stratum': NS_SIGMA_O}

    def suppress(self, word: str, factor: float = 0.1) -> Dict[str, Any]:
        """
        Suppress all A-matrix edges to/from *word*.

        :param word: Word to suppress.
        :param factor: Suppression factor in (0, 1]. 0.1 = 90% suppressed.
        :returns: Result dict.
        :rtype: dict
        """
        return self._engine.retract(word, word, factor=factor,
                                    reason='study.suppress')

    def overwrite(self, word: str, replacement: str) -> Dict[str, Any]:
        """
        Re-route *word*'s A-matrix neighborhood toward *replacement*.

        Transfers 50% of each edge weight from word to replacement, then
        suppresses word's outgoing edges to 10%.

        :param word: Source word (edges suppressed).
        :param replacement: Target word (edges boosted).
        :returns: Result dict or error.
        :rtype: dict
        """
        c  = self._engine.crank
        wa = c._clean(word)
        wb = c._clean(replacement)
        ka = c._vocab.get(wa)
        if ka is None:
            return {'error': f'unknown word: {word}'}
        if c._vocab.get(wb) is None:
            c.learn(wb)
        kb = c._vocab.get(wb)
        with self._lock:
            for j, w_ij in list(c._A[ka].items()):
                c._A[kb][j] = min(c._A[kb].get(j, 0.0) + w_ij * 0.5, 1.0)
            mask = c._correction_mask.setdefault(ka, {})
            for j in c._A[ka]:
                mask[j] = 0.1
        return {'overwritten': wa, 'to': wb}

    def domain_retrain(self, text: str, domain: str = '',
                       weight: float = 3.0) -> Dict[str, Any]:
        """
        Focused high-weight retraining on domain-specific text.

        :param text: Domain text to ingest.
        :param domain: Domain label (for logging context).
        :param weight: LTP multiplier (3.0 = aggressive deepening).
        :returns: Result dict.
        :rtype: dict
        """
        with self._lock:
            n = self._engine.crank.learn(text, weight=weight)
        return {'domain': domain, 'words': n, 'weight': weight}

    # ── StatesRepo passthrough ─────────────────────────────────────────────────

    def init_states_repo(self, baseline_bin: str = '') -> Dict[str, Any]:
        """
        Initialise ``~/.ptolemy/states/`` git repo.

        :param baseline_bin: Current monad.bin path (recorded as baseline reference).
        :returns: Result dict with status and sha.
        :rtype: dict
        """
        return self.get_repo().init_states_repo(baseline_bin)

    def checkpoint(self, label: str,
                   extra: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Snapshot current field metrics to the states repo (does not commit).

        :param label: Checkpoint label.
        :param extra: Additional fields to merge into sidecar JSON.
        :returns: Result dict with sidecar file path.
        :rtype: dict
        """
        snap    = self._field_snapshot()
        c       = self._engine.crank
        sidecar: Dict[str, Any] = {
            'label':           label,
            'ts':              time.strftime('%Y-%m-%dT%H:%M:%S'),
            'noether':         snap['noether'],
            'bao':             snap['bao'],
            'vocab_size':      c.n,
            'condensed_count': sum(
                1 for s in (c._stratum if hasattr(c, '_stratum') else [])
                if s == NS_SIGMA_S),
        }
        if extra:
            sidecar.update(extra)
        return self.get_repo().checkpoint(label, sidecar)

    def commit(self, message: Optional[str] = None) -> Dict[str, Any]:
        """
        Commit staged state to repo.

        :param message: Commit message (auto-generated if None).
        :returns: Result dict with sha.
        :rtype: dict
        """
        return self.get_repo().commit(message)

    def branch(self, name: str) -> Dict[str, Any]:
        """
        Create and switch to branch in states repo.

        :param name: Branch name.
        :returns: Result dict.
        :rtype: dict
        """
        return self.get_repo().branch(name)

    def rollback(self, sha: str) -> Dict[str, Any]:
        """
        Revert states repo to prior commit (non-destructive revert commit).

        :param sha: Target SHA to revert to.
        :returns: Result dict.
        :rtype: dict
        """
        return self.get_repo().rollback(sha)

    def log(self, n: int = 20) -> List[Dict]:
        """
        Return last *n* commits from states repo.

        :param n: Number of commits.
        :returns: List of commit dicts.
        :rtype: list
        """
        return self.get_repo().log(n)
