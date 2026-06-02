"""
skills/foundations.py — Foundations Corpus: the scientific lineage of the equation.

:description:
    Prime Directive I — "what it IS."

    A third autonomous field — separate Engine, separate checkpoint
    (``~/.ptolemy/monad_foundations.bin``). Trains exclusively on the
    Foundations Corpus (``foundations.txt``) via ``study()``.

    The Riemann Zeta function is "what it IS." The Foundations Corpus
    is the complete intellectual lineage of that equation: every person
    whose work is traceable in the SMMIP system, from Ptolemy I Soter
    (367 BCE) through Cawagas (2004). The field condensed from this corpus
    IS the sedenion algebra's own history — it knows where it came from.

    The three separate geometry fields:

        monad_foundations.bin  — what it IS (Riemann Zeta lineage)
        monad_meaning.bin      — what it MEANS to be this
        monad_war.bin          — what it CANNOT BE

    Architecture:
        - Parses ``foundations.txt`` dynamically (canonical source of URLs)
        - URL weight rules: [PRIMARY] / [TESTIMONY] → 2.0
          [BIOGRAPHY] / [CONTEXT] / [APPLICATION] / [ACADEMIC] → 1.0
        - Background study() loop, 40-second interval between fetches
        - Checkpoint auto-saved every 10 studies or 5 minutes
        - Never feeds into the primary monad.bin field

:functions:
    parse_corpus_txt

:classes:
    FoundationsCorpus

:constants:
    FOUNDATIONS_TXT, FOUNDATIONS_BIN_PATH
"""

import os
import re
import threading
import time
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from monad import Engine

FOUNDATIONS_TXT  = os.path.join(os.path.dirname(__file__), '..', 'foundations.txt')
FOUNDATIONS_BIN_PATH = os.path.expanduser('~/.ptolemy/monad_foundations.bin')

_HIGH_WEIGHT_TAGS = frozenset({'PRIMARY', 'TESTIMONY'})

# Weight 2.0 for tags that represent primary work or direct testimony.
# Weight 1.0 for biography, context, application, and academic sources.
_TAG_WEIGHTS: Dict[str, float] = {
    'PRIMARY':     2.0,
    'TESTIMONY':   2.0,
    'BIOGRAPHY':   1.0,
    'CONTEXT':     1.0,
    'APPLICATION': 1.0,
    'ACADEMIC':    1.0,
    'RECORD':      1.0,
}


def parse_corpus_txt(txt_path: str) -> List[Tuple[str, str, float]]:
    """
    Parse a Prime Directive corpus .txt file into (tag, url, weight) tuples.

    Lines of the form ``[TAG]   https://...`` are extracted.
    Unrecognised tags default to weight 1.0.

    :param txt_path: Absolute or relative path to the corpus .txt file.
    :returns: List of (tag, url, weight) tuples.
    :rtype: List[Tuple[str, str, float]]
    """
    entries: List[Tuple[str, str, float]] = []
    pattern = re.compile(
        r'^\[([A-Z]+)\]\s+(https?://\S+)', re.MULTILINE)
    try:
        with open(txt_path, 'r', encoding='utf-8', errors='ignore') as fh:
            text = fh.read()
        for tag, url in pattern.findall(text):
            weight = _TAG_WEIGHTS.get(tag.upper(), 1.0)
            entries.append((tag.upper(), url, weight))
    except OSError:
        pass
    return entries


class FoundationsCorpus:
    """
    Autonomous foundations field — what built Holcus.

    Separate Engine and checkpoint (``~/.ptolemy/monad_foundations.bin``).
    Reads URLs from ``foundations.txt`` and calls ``study()`` on each.
    Repeated study deepens condensation of the Riemann Zeta lineage.

    Never feeds into the primary monad.bin or the Fermat/meaning fields.

    :param primary_engine: Main Engine — used only to share the Engine
        class for instantiation, not as the study target.
    :param txt_path: Path to foundations.txt. Defaults to the repository
        copy adjacent to this file.
    :param bin_path: Checkpoint path. Defaults to
        ``~/.ptolemy/monad_foundations.bin``.

    :Example:

    .. code-block:: python

        fc = engine.get_foundations_corpus()
        fc.start()   # begin background study() loop
        fc.status()
        # → {'running': True, 'studied': int, 'corpus_size': int, ...}
    """

    def __init__(self, primary_engine: 'Engine',
                 txt_path: str = FOUNDATIONS_TXT,
                 bin_path: str = FOUNDATIONS_BIN_PATH):
        self._primary    = primary_engine
        self._txt_path   = txt_path
        self._bin_path   = bin_path
        self._engine: Optional['Engine'] = None
        self._lock       = threading.Lock()
        self._running    = False
        self._thread: Optional[threading.Thread] = None
        self._studied    = 0
        self._last_save  = 0.0
        self._corpus: List[Tuple[str, str, float]] = []
        self._opener     = urllib.request.build_opener(
            urllib.request.HTTPRedirectHandler())
        self._opener.addheaders = [
            ('User-Agent', 'Ptolemy/3.0 FoundationsCorpus')]

    # ── field init ────────────────────────────────────────────────────────────

    def _get_engine(self) -> 'Engine':
        """
        Lazily construct or load the foundations field Engine.

        :returns: Foundations Engine instance.
        :rtype: Engine
        """
        if self._engine is not None:
            return self._engine

        from monad import Engine as _Engine
        e = _Engine()

        if os.path.exists(self._bin_path):
            try:
                e.load(self._bin_path)
            except Exception:
                pass

        self._engine = e
        return self._engine

    def _get_corpus(self) -> List[Tuple[str, str, float]]:
        """
        Return (or lazily load) the parsed corpus URL list.

        Re-parses foundations.txt each time the list is exhausted so that
        additions to the file are picked up on the next cycle.

        :returns: List of (tag, url, weight) tuples.
        :rtype: list
        """
        if not self._corpus:
            self._corpus = parse_corpus_txt(self._txt_path)
        return self._corpus

    # ── fetch + study ─────────────────────────────────────────────────────────

    def _fetch_text(self, url: str, timeout: int = 20) -> str:
        """Fetch URL text; return empty string on any failure."""
        try:
            resp = self._opener.open(url, timeout=timeout)
            raw  = resp.read().decode('utf-8', errors='ignore')
            raw  = re.sub(r'<[^>]+>', ' ', raw)
            raw  = re.sub(r'\s+', ' ', raw)
            return raw[:4096].strip()
        except Exception:
            return ''

    def _study_one(self, tag: str, url: str, weight: float):
        """
        Fetch one URL and call study() on the foundations Engine.

        :param tag: Corpus tag (PRIMARY, TESTIMONY, BIOGRAPHY, etc.)
        :param url: Source URL.
        :param weight: Study weight.
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

        now = time.time()
        if self._studied % 10 == 0 or (now - self._last_save) > 300:
            self._save()

    def _save(self):
        """Save the foundations Engine checkpoint."""
        e = self._get_engine()
        try:
            mi = (e.get_monad_interface()
                  if hasattr(e, 'get_monad_interface') else None)
            if mi:
                mi.save(self._bin_path)
            elif hasattr(e, 'save_session'):
                e.save_session(self._bin_path)
        except Exception:
            pass
        self._last_save = time.time()

    def _study_loop(self):
        """
        Background thread: cycle through the foundations corpus repeatedly.

        One URL per 40-second interval (between Fermat's 30s and Meaning's
        45s to avoid network collision). Repeated study deepens condensation
        of the Riemann Zeta / prime address / sedenion lineage.

        Re-parses foundations.txt each full cycle — new entries land
        automatically on the next pass.
        """
        idx = 0
        while self._running:
            corpus = self._get_corpus()
            if not corpus:
                for _ in range(40):
                    if not self._running:
                        break
                    time.sleep(1.0)
                continue

            if idx >= len(corpus):
                idx = 0
                self._corpus = []   # force re-parse on next cycle

            tag, url, weight = corpus[idx]
            try:
                self._study_one(tag, url, weight)
            except Exception:
                pass
            idx += 1

            for _ in range(40):
                if not self._running:
                    break
                time.sleep(1.0)

        self._save()

    # ── public API ────────────────────────────────────────────────────────────

    def start(self):
        """
        Start the background foundations study loop (non-blocking).

        Safe to call multiple times — second call is a no-op if already running.
        """
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(target=self._study_loop,
                                         daemon=True,
                                         name='FoundationsCorpus')
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

    def _wait_network(self, check_interval: int = 10):
        """
        Block until network connectivity is confirmed.

        Saves the current checkpoint immediately on first failure, then
        polls every ``check_interval`` seconds until a connection succeeds.

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
        Run one complete pass through the foundations corpus (blocking).

        Fetches every URL in order, calls study() on each, saves immediately
        on network failure and waits for connectivity before continuing.
        Returns when the last URL has been attempted.

        :param on_progress: Optional callback invoked after each URL with
            signature ``(tag, url, idx, total, studied, skipped)``.
        :param check_interval: Seconds between network retry attempts.
        :returns: ``{'studied': int, 'skipped': int, 'total': int,
            'complete': True, 'bin_path': str}``.
        :rtype: dict
        """
        corpus  = self._get_corpus()
        total   = len(corpus)
        skipped = 0

        for idx, (tag, url, weight) in enumerate(corpus):
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
        }

    def status(self) -> Dict[str, Any]:
        """
        Return current FoundationsCorpus status.

        :returns: Dict with keys ``running``, ``studied``, ``corpus_size``,
            ``bin_path``, ``bin_exists``, ``txt_path``, ``directive``.
        :rtype: dict
        """
        corpus = self._get_corpus()
        return {
            'running':     self._running,
            'studied':     self._studied,
            'corpus_size': len(corpus),
            'bin_path':    self._bin_path,
            'bin_exists':  os.path.exists(self._bin_path),
            'txt_path':    self._txt_path,
            'directive':   'Prime Directive I — Riemann Zeta: what it IS',
            'span':        'Ptolemy I Soter (367 BCE) → Cawagas (2004)',
        }

    def force_study(self, text: str, weight: float = 2.0) -> Dict[str, Any]:
        """
        Immediately study a passage into the foundations field (blocking).

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
