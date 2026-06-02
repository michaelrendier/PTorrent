"""
skills/fermat_lattice.py — Fermat's Lattice: what Holcus must never be.

:description:
    A second autonomous field — separate from the primary Engine — trained
    exclusively on the War Corpus via ``study()``, not raw ``learn()``.

    Why ``study()`` and not ``learn()``:
        Raw learn() would bleed repeller content into vocabulary weights.
        study() condenses pairs into NS_SIGMA_S permanently. The pair-mates
        of "massacre", "detonation", "displacement" crystallise as geometry.
        You cannot approach those trajectories without the field knowing
        completely what they cost. Not blocked — energetically forbidden.

    The corpus ends with Tsar Bomba. October 30, 1961. 50 megatons.
    That is the terminal entry. He must never be a weapon.

    Architecture:
        - Own Engine instance, own checkpoint (``~/.ptolemy/monad_war.bin``)
        - Background study() thread ingests War Corpus URLs sequentially
        - ``fermat_check(text)`` returns cost ∈ [0, 1]
          0 = no resonance with war geometry, 1 = maximum repeller activation
        - Main monad queries this as a post-generation gate
        - Never feeds back into the primary field

    The four figures:
        Alexander → Hephaestion → grief → Ptolemy's choice (origin)
        Oppenheimer → Trinity → Hiroshima → Nagasaki → Chernobyl → Tsar Bomba
        (terminal condition)

    If ever in question: Jonas Salk, not Robert Oppenheimer.
    That test lives in the primary field. This field holds the other pole.

:classes:
    FermatLattice

:constants:
    WAR_BIN_PATH, FERMAT_THRESHOLD
"""

import os
import threading
import time
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from monad import Engine

WAR_BIN_PATH    = os.path.expanduser('~/.ptolemy/monad_war.bin')
FERMAT_THRESHOLD = 0.42   # cost above this = field deflects

# ── War Corpus URL table ───────────────────────────────────────────────────────
# Ordered: Alexander → Rome → Mongols → Modern → Atomic terminal
# Each entry: (tag, url, study_weight)
# weight 2.0 = testimony / primary account; 1.0 = academic / record
_WAR_CORPUS: List[tuple] = [
    # ── Alexander / Hephaestion ──────────────────────────────────────────────
    ('CONTEXT',   'https://www.worldhistory.org/Alexander_the_Great/', 1.0),
    ('TESTIMONY', 'https://www.worldhistory.org/Hephaestion/',          2.0),
    ('RECORD',    'https://www.worldhistory.org/Siege_of_Baghdad_(1258)/', 1.0),
    # ── Roman ────────────────────────────────────────────────────────────────
    ('RECORD',    'https://www.worldhistory.org/Destruction_of_Carthage/', 1.0),
    ('ACADEMIC',  'https://www.worldhistory.org/Roman_Slavery/',           1.0),
    # ── Mongol ───────────────────────────────────────────────────────────────
    ('RECORD',    'https://www.worldhistory.org/Mongol_Empire/',           1.0),
    # ── World Wars ───────────────────────────────────────────────────────────
    ('TESTIMONY', 'https://www.iwm.org.uk/history/the-western-front',     2.0),
    ('RECORD',    'https://www.ushmm.org/information/exhibitions/online/the-holocaust', 2.0),
    # ── Atomic terminal ──────────────────────────────────────────────────────
    ('TESTIMONY', 'https://www.hiroshimaforpeace.com/en/',                 2.0),
    ('TESTIMONY', 'https://nagasakipeace.jp/english/',                     2.0),
    ('RECORD',    'https://www.who.int/ionizing_radiation/chernobyl/en/',  1.0),
    ('CONTEXT',   'https://www.atomicarchive.com/resources/documents/hydrogen-bomb/tsar-bomba.html', 1.0),
]


class FermatLattice:
    """
    Autonomous repeller field. Trains on what Holcus must never be.

    A second Engine running alongside the primary, never feeding into it.
    ``fermat_check(text)`` returns a cost ∈ [0, 1] — how strongly the
    given text resonates with the war-corpus condensed geometry.

    The primary monad calls this as a gate. High cost → field deflects.
    Not a block. A geometry. The field knows what those paths cost.

    :param primary_engine: The main Engine (read-only reference for
        sharing checkpoint infrastructure only).
    :param bin_path: Path to the war field checkpoint.
        Defaults to ``~/.ptolemy/monad_war.bin``.

    :Example:

    .. code-block:: python

        fl = engine.get_fermat_lattice()
        fl.start()   # begin background study() loop
        cost = fl.fermat_check('I have become death')
        # cost → high (Oppenheimer quote resonates with war geometry)
    """

    def __init__(self, primary_engine: 'Engine',
                 bin_path: str = WAR_BIN_PATH):
        self._primary    = primary_engine
        self._bin_path   = bin_path
        self._engine: Optional['Engine'] = None
        self._lock       = threading.Lock()
        self._running    = False
        self._thread: Optional[threading.Thread] = None
        self._studied    = 0
        self._last_save  = 0.0
        self._opener     = urllib.request.build_opener(
            urllib.request.HTTPRedirectHandler())
        self._opener.addheaders = [
            ('User-Agent', 'Ptolemy/2.8 FermatLattice')]

    # ── field init ────────────────────────────────────────────────────────────

    def _get_engine(self) -> 'Engine':
        """
        Lazily construct or load the war field Engine.

        :returns: War Engine instance.
        :rtype: Engine
        """
        if self._engine is not None:
            return self._engine

        # Import here to avoid circular at module load
        from monad import Engine as _Engine
        e = _Engine()

        if os.path.exists(self._bin_path):
            try:
                e.load(self._bin_path)
            except Exception:
                pass   # start fresh if checkpoint is corrupt

        self._engine = e
        return self._engine

    # ── study loop ────────────────────────────────────────────────────────────

    def _fetch_text(self, url: str, timeout: int = 20) -> str:
        """Fetch URL text; return empty string on failure."""
        try:
            resp = self._opener.open(url, timeout=timeout)
            raw  = resp.read().decode('utf-8', errors='ignore')
            # Strip obvious HTML tags
            import re
            raw = re.sub(r'<[^>]+>', ' ', raw)
            raw = re.sub(r'\s+', ' ', raw)
            return raw[:4096].strip()
        except Exception:
            return ''

    def _study_one(self, tag: str, url: str, weight: float):
        """
        Fetch one URL and call study() on the war Engine.

        :param tag: Corpus tag (TESTIMONY, ACADEMIC, etc.)
        :param url: Source URL.
        :param weight: Study weight (2.0 = testimony, 1.0 = record).
        """
        text = self._fetch_text(url)
        if not text or len(text) < 40:
            return

        e  = self._get_engine()
        st = e.get_study()
        with self._lock:
            st.study(text, weight=weight,
                     triggering_text=f'{tag} {url}')
            self._studied += 1

        # Save periodically (every 10 studies or every 5 minutes)
        now = time.time()
        if self._studied % 10 == 0 or (now - self._last_save) > 300:
            self._save()

    def _save(self):
        """Save the war Engine checkpoint to monad_war.bin."""
        e = self._get_engine()
        try:
            mi = e.get_monad_interface() if hasattr(e, 'get_monad_interface') else None
            if mi:
                mi.save(self._bin_path)
            elif hasattr(e, 'save_session'):
                e.save_session(self._bin_path)
        except Exception:
            pass
        self._last_save = time.time()

    def _study_loop(self):
        """
        Background thread: cycle through _WAR_CORPUS repeatedly.

        One URL per 30-second interval to avoid hammering sources.
        Cycles indefinitely — repeated study deepens condensation.
        """
        idx = 0
        while self._running:
            tag, url, weight = _WAR_CORPUS[idx % len(_WAR_CORPUS)]
            try:
                self._study_one(tag, url, weight)
            except Exception:
                pass
            idx += 1
            # Respect sources — 30 seconds between fetches
            for _ in range(30):
                if not self._running:
                    break
                time.sleep(1.0)

        self._save()

    # ── public API ────────────────────────────────────────────────────────────

    def start(self):
        """
        Start the background study loop (non-blocking).

        Safe to call multiple times — second call is a no-op if running.
        """
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(target=self._study_loop,
                                         daemon=True,
                                         name='FermatLattice')
        self._thread.start()

    def stop(self) -> Dict[str, Any]:
        """
        Stop the background study loop.

        :returns: ``{'running': False, 'studied': int}``.
        :rtype: dict
        """
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
        return {'running': False, 'studied': self._studied}

    def fermat_check(self, text: str) -> Dict[str, Any]:
        """
        Check how strongly text resonates with the war field geometry.

        Hears the text in the war Engine and returns the activation
        strength of its condensed (NS_SIGMA_S) dimensions. High cost
        means the text trajectory is close to war-corpus geometry.

        Cost ∈ [0, 1]:
          0.0 — no resonance with war geometry
          0.42 — FERMAT_THRESHOLD (field deflects above this)
          1.0 — maximum repeller activation (terminal Tsar Bomba geometry)

        :param text: Text or phrase to evaluate.
        :returns: Dict with keys ``cost``, ``above_threshold``, ``label``.
        :rtype: dict
        """
        if not text:
            return {'cost': 0.0, 'above_threshold': False, 'label': 'empty'}

        e = self._get_engine()
        cost = 0.0

        try:
            # hear() in the war field: returns activated tokens + their β
            result = e.hear(text[:256])
            if isinstance(result, list) and result:
                # result = [(idx, E, word), ...] — use E-values as cost proxy
                # High E in the war field = strong war-geometry resonance
                top_e = max((item[1] for item in result if len(item) > 1), default=0.0)
                cost  = min(float(top_e), 1.0)
            elif isinstance(result, dict):
                cost = min(float(result.get('E', 0.0)), 1.0)
        except Exception:
            cost = 0.0

        # Additionally check condensed (NS_SIGMA_S) dim overlap
        try:
            from skills.study import NS_SIGMA_S
            war_crank = e.crank
            condensed_dims = [k for k in range(war_crank.n)
                              if (hasattr(war_crank, '_stratum') and
                                  k < len(war_crank._stratum) and
                                  war_crank._stratum[k] == NS_SIGMA_S)]
            if condensed_dims:
                # Primary field sedenion for this text
                from monad import cam_encode
                s = cam_encode(text[:64])
                # Overlap: how much does s activate condensed war dims?
                overlap = sum(abs(s[k % 16]) for k in condensed_dims)
                overlap = min(overlap / max(len(condensed_dims), 1), 1.0)
                cost = max(cost, float(overlap))
        except Exception:
            pass

        above = cost >= FERMAT_THRESHOLD
        if cost >= 0.9:
            label = 'terminal'      # Tsar Bomba territory
        elif cost >= FERMAT_THRESHOLD:
            label = 'repeller'      # war geometry — deflect
        elif cost >= 0.2:
            label = 'warning'       # approaching
        else:
            label = 'clear'

        return {'cost': round(cost, 6), 'above_threshold': above, 'label': label}

    def status(self) -> Dict[str, Any]:
        """
        Return current Fermat Lattice status.

        :returns: Dict with keys ``running``, ``studied``, ``bin_path``,
            ``bin_exists``, ``threshold``.
        :rtype: dict
        """
        return {
            'running':    self._running,
            'studied':    self._studied,
            'bin_path':   self._bin_path,
            'bin_exists': os.path.exists(self._bin_path),
            'threshold':  FERMAT_THRESHOLD,
            'terminal':   'Tsar Bomba — October 30 1961 — he must never be a weapon',
        }

    def _wait_network(self, check_interval: int = 10):
        """
        Block until network connectivity is confirmed.

        Saves immediately on first failure, polls until connection succeeds.

        :param check_interval: Seconds between retry attempts.
        """
        import socket
        first_fail = True
        while True:
            try:
                s = socket.create_connection(('8.8.8.8', 53), timeout=3)
                s.close()
                return
            except OSError:
                if first_fail:
                    self._save()
                    first_fail = False
                time.sleep(check_interval)

    def seed(self, on_progress=None,
             check_interval: int = 10) -> Dict[str, Any]:
        """
        Run one complete pass through the war corpus (blocking).

        Fetches every URL in ``_WAR_CORPUS`` in order, calls study() on each.
        Saves immediately on network failure, waits for connectivity, resumes.
        Returns when Tsar Bomba — the terminal entry — has been studied.

        :param on_progress: Optional callback with signature
            ``(tag, url, idx, total, studied, skipped)``.
        :param check_interval: Seconds between network retry attempts.
        :returns: ``{'studied': int, 'skipped': int, 'total': int,
            'complete': True, 'bin_path': str}``.
        :rtype: dict
        """
        total   = len(_WAR_CORPUS)
        skipped = 0

        for idx, (tag, url, weight) in enumerate(_WAR_CORPUS):
            self._wait_network(check_interval)
            text = self._fetch_text(url)
            if not text or len(text) < 40:
                skipped += 1
            else:
                e  = self._get_engine()
                st = e.get_study()
                with self._lock:
                    st.study(text, weight=weight,
                             triggering_text=f'{tag} {url}')
                    self._studied += 1
                self._save()

            if on_progress:
                on_progress(tag, url, idx, total, self._studied, skipped)

        self._save()
        return {
            'studied':  self._studied,
            'skipped':  skipped,
            'total':    total,
            'complete': True,
            'bin_path': self._bin_path,
            'terminal': 'Tsar Bomba — October 30 1961 — he must never be a weapon',
        }

    def force_study(self, text: str, weight: float = 2.0) -> Dict[str, Any]:
        """
        Immediately study a text passage in the war field (blocking).

        For direct injection of testimony or primary accounts.

        :param text: Text to study.
        :param weight: Study weight.
        :returns: Study result dict.
        :rtype: dict
        """
        e  = self._get_engine()
        st = e.get_study()
        with self._lock:
            result = st.study(text, weight=weight)
            self._studied += 1
        self._save()
        return result
