"""
skills/corpus.py — Generic parameterised corpus seeder.

Any ``[TAG] URL`` corpus .txt file becomes a study loop.
FoundationsCorpus and MeaningCorpus are specialisations; this class
handles arbitrary corpora (Python PEPs, C/POSIX, future additions).

Architecture: one Engine instance per corpus — completely isolated
from the primary field and from each other.

:bin path:  ``~/.ptolemy/monad_<name>.bin``
:txt path:  supplied at construction or defaulted from corpus name
"""

import os
import re
import socket
import threading
import time
import urllib.parse
import urllib.request
import urllib.robotparser
import html.parser
import json as _json
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# Import Engine from the parent package.  When running inside the APK
# the package root is on sys.path; when running from the repo root the
# import also resolves correctly.
from monad import Engine


# Tags that receive weight 2.0 by default when no custom set is supplied.
_DEFAULT_PRIMARY_TAGS: Set[str] = {
    'PRIMARY', 'TESTIMONY', 'ATTRACTOR',
    'SPEC', 'POSIX', 'CAPI',
    'DATAMODEL', 'REFERENCE', 'PEP', 'WHATSNEW', 'API',
}


def parse_corpus_txt(
    txt_path: str,
    primary_tags: Optional[Set[str]] = None,
    primary_weight: float = 2.0,
    context_weight: float = 1.0,
) -> List[Tuple[str, str, float]]:
    """Parse a ``[TAG] URL`` corpus file into ``(tag, url, weight)`` tuples.

    Lines that do not match ``[TAG] https://...`` are ignored (comments,
    blank lines, section headers).

    :param txt_path: Path to corpus ``.txt`` file.
    :param primary_tags: Set of tag strings that receive *primary_weight*.
        Defaults to :data:`_DEFAULT_PRIMARY_TAGS`.
    :param primary_weight: Weight for primary-tier tags.
    :param context_weight: Weight for all other tags.
    :returns: List of ``(tag, url, weight)`` tuples.
    :rtype: list
    """
    if primary_tags is None:
        primary_tags = _DEFAULT_PRIMARY_TAGS
    results: List[Tuple[str, str, float]] = []
    pattern = re.compile(r'^\[([A-Z]+)\]\s+(https?://\S+)')
    try:
        with open(txt_path, encoding='utf-8') as f:
            for line in f:
                m = pattern.match(line.strip())
                if m:
                    tag, url = m.group(1), m.group(2)
                    weight = primary_weight if tag in primary_tags else context_weight
                    results.append((tag, url, weight))
    except OSError:
        pass
    return results


class GenericCorpus:
    """Autonomous corpus study loop for any ``[TAG] URL`` corpus file.

    Creates its own Engine instance and checkpoint file.  Never feeds
    the primary monad field.

    :param engine: Engine instance (dedicated — do not share).
    :param txt_path: Path to corpus ``.txt`` file.
    :param bin_path: Path for the ``.bin`` checkpoint.
    :param name: Human-readable name used in logging.
    :param interval: Seconds between fetches in the continuous loop.
    :param primary_tags: Tags that receive weight 2.0.
    :param primary_weight: Weight applied to primary-tier URLs.
    :param context_weight: Weight applied to all other URLs.
    """

    def __init__(
        self,
        engine: Engine,
        txt_path: str,
        bin_path: str,
        name: str = 'corpus',
        interval: int = 60,
        primary_tags: Optional[Set[str]] = None,
        primary_weight: float = 2.0,
        context_weight: float = 1.0,
    ) -> None:
        self._engine         = engine
        self._txt_path       = txt_path
        self._bin_path       = bin_path
        self._name           = name
        self._interval       = interval
        self._primary_tags   = primary_tags or _DEFAULT_PRIMARY_TAGS
        self._primary_weight = primary_weight
        self._context_weight = context_weight

        self._lock         = threading.Lock()
        self._running      = False
        self._halt         = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._studied      = 0
        self._robots_cache: Dict[str, urllib.robotparser.RobotFileParser] = {}
        self._robots_lock  = threading.Lock()

        if os.path.exists(bin_path):
            try:
                self._engine.load_checkpoint(bin_path)
            except Exception:
                pass

    # ── internal helpers ───────────────────────────────────────────────────

    def _get_corpus(self) -> List[Tuple[str, str, float]]:
        """Load and return the corpus URL list from the .txt file."""
        return parse_corpus_txt(
            self._txt_path,
            primary_tags=self._primary_tags,
            primary_weight=self._primary_weight,
            context_weight=self._context_weight,
        )

    _UA = ('Mozilla/5.0 (compatible; PtolemyHolcus/3.0; '
           '+https://github.com/ptolemy-holcus; corpus-seeder)')

    # ── API hosts: use structured APIs instead of HTML scraping ──────────────
    _MEDIAWIKI_HOSTS = frozenset({
        'en.wikipedia.org', 'en.wiktionary.org', 'simple.wikipedia.org',
        'en.wikisource.org', 'en.wikiquote.org',
    })
    _ARXIV_HOST = 'arxiv.org'

    def _robots_allowed(self, url: str, timeout: int = 6) -> bool:
        """Return True if robots.txt permits fetching *url* for our UA."""
        try:
            parsed = urllib.parse.urlparse(url)
            host_key = f'{parsed.scheme}://{parsed.netloc}'
            with self._robots_lock:
                rp = self._robots_cache.get(host_key)
                if rp is None:
                    rp = urllib.robotparser.RobotFileParser()
                    rp.set_url(f'{host_key}/robots.txt')
                    try:
                        rp.read()
                    except Exception:
                        rp = None
                    self._robots_cache[host_key] = rp
            if rp is None:
                return True
            return rp.can_fetch(self._UA, url)
        except Exception:
            return True

    def _strip_html(self, raw: str) -> str:
        """Strip HTML to prose. Skips script/style/nav/header/footer/aside."""
        _SKIP_TAGS = frozenset({
            'script', 'style', 'nav', 'header', 'footer',
            'aside', 'noscript', 'form', 'button',
        })

        class _S(html.parser.HTMLParser):
            def __init__(self):
                super().__init__()
                self._buf: List[str] = []
                self._depth = 0

            def handle_starttag(self, tag, attrs):
                if tag in _SKIP_TAGS:
                    self._depth += 1

            def handle_endtag(self, tag):
                if tag in _SKIP_TAGS and self._depth:
                    self._depth -= 1

            def handle_data(self, data):
                if not self._depth:
                    t = data.strip()
                    if t:
                        self._buf.append(t)

            def text(self):
                return '\n'.join(self._buf)

        s = _S()
        try:
            s.feed(raw)
        except Exception:
            pass
        return s.text()

    def _fetch_text(self, url: str, timeout: int = 15) -> str:
        """Fetch plain text from *url*.

        Routing:
          Wikipedia / Wiktionary / Wikisource  → MediaWiki extracts API
          arXiv abstract pages                  → arXiv abs HTML (structured)
          Everything else                       → robots.txt check, then fetch
                                                  + HTML strip

        Returns empty string on failure or if robots.txt disallows.
        No intermediate files are written — text flows directly to learn().
        """
        parsed = urllib.parse.urlparse(url)
        host   = parsed.netloc.lower().lstrip('www.')

        # ── MediaWiki API (Wikipedia, Wiktionary, Wikisource…) ───────────────
        if host in self._MEDIAWIKI_HOSTS or host.endswith('.wikipedia.org'):
            title = urllib.parse.unquote(
                parsed.path.rstrip('/').rsplit('/', 1)[-1])
            if title and not title.startswith('Special:'):
                api_url = (
                    f'https://{parsed.netloc}/w/api.php'
                    f'?action=query'
                    f'&titles={urllib.parse.quote(title, safe="")}'
                    f'&prop=extracts&explaintext=1&exsectionformat=plain'
                    f'&redirects=1&format=json'
                )
                try:
                    req = urllib.request.Request(
                        api_url, headers={'User-Agent': self._UA})
                    with urllib.request.urlopen(req, timeout=timeout) as r:
                        data = _json.loads(r.read(4_000_000))
                    for page in data.get('query', {}).get('pages', {}).values():
                        text = page.get('extract', '').strip()
                        if text and len(text) > 100:
                            return text
                except Exception:
                    pass
            return ''

        # ── arXiv: abs page has clean structured text ─────────────────────────
        if self._ARXIV_HOST in host:
            try:
                req = urllib.request.Request(
                    url, headers={'User-Agent': self._UA})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    raw = r.read(500_000).decode('utf-8', errors='replace')
                # Extract abstract block only — avoid boilerplate
                m = re.search(
                    r'<blockquote[^>]*class="abstract[^"]*"[^>]*>(.*?)</blockquote>',
                    raw, re.DOTALL | re.IGNORECASE)
                if m:
                    abstract = re.sub(r'<[^>]+>', ' ', m.group(1)).strip()
                    # Also grab title
                    t = re.search(r'<h1[^>]*class="title[^"]*"[^>]*>(.*?)</h1>',
                                  raw, re.DOTALL | re.IGNORECASE)
                    title = re.sub(r'<[^>]+>', '', t.group(1)).strip() if t else ''
                    return f'{title}\n{abstract}' if title else abstract
            except Exception:
                pass
            return ''

        # ── Generic: robots.txt → fetch → strip ──────────────────────────────
        if not self._robots_allowed(url, timeout=6):
            return ''
        req = urllib.request.Request(url, headers={'User-Agent': self._UA})
        raw = ''
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                ct  = r.headers.get('Content-Type', '')
                raw = r.read(2_000_000).decode('utf-8', errors='replace')
        except Exception as exc:
            # SSL cert mismatch (misconfigured university/institution servers):
            # fall back to unverified — content is not sensitive, just educational.
            if 'CERTIFICATE' in str(exc).upper() or 'SSL' in str(exc).upper():
                try:
                    import ssl
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode    = ssl.CERT_NONE
                    with urllib.request.urlopen(req, timeout=timeout,
                                               context=ctx) as r:
                        ct  = r.headers.get('Content-Type', '')
                        raw = r.read(2_000_000).decode('utf-8', errors='replace')
                except Exception:
                    return ''
            else:
                return ''
        if not raw:
            return ''
        if 'text/plain' in ct or url.endswith('.txt'):
            return raw
        return self._strip_html(raw)

    def _save(self) -> None:
        """Save Engine state to the checkpoint file."""
        try:
            result = self._engine.save_session(self._bin_path)
            if isinstance(result, dict) and 'error' in result:
                import sys
                print(f'[corpus:{self._name}] save error: {result["error"]}',
                      file=sys.stderr)
        except Exception as exc:
            import sys
            print(f'[corpus:{self._name}] save exception: {exc}', file=sys.stderr)

    def _wait_network(self, check_interval: int = 10) -> None:
        """Block until 8.8.8.8:53 is reachable, saving state on first failure.

        :param check_interval: Seconds between connectivity checks.
        """
        first = True
        while True:
            try:
                s = socket.create_connection(('8.8.8.8', 53), timeout=3)
                s.close()
                return
            except OSError:
                if first:
                    self._save()
                    first = False
                time.sleep(check_interval)

    # ── public API ─────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the continuous background study loop."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._halt.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name=f'corpus-{self._name}',
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> Dict[str, Any]:
        """Stop the background study loop and save state.

        :returns: Status dict.
        :rtype: dict
        """
        self._halt.set()
        with self._lock:
            self._running = False
        self._save()
        return self.status()

    def status(self) -> Dict[str, Any]:
        """Return current corpus status.

        :returns: Dict with ``running``, ``studied``, ``corpus_size``,
            ``bin_path``, ``txt_path``, ``name``.
        :rtype: dict
        """
        corpus = self._get_corpus()
        return {
            'running':     self._running,
            'name':        self._name,
            'studied':     self._studied,
            'corpus_size': len(corpus),
            'bin_path':    self._bin_path,
            'txt_path':    self._txt_path,
            'bin_exists':  os.path.exists(self._bin_path),
        }

    def force_study(self, text: str, weight: float = 2.0) -> Dict[str, Any]:
        """Immediately study *text* into this corpus Engine.

        :param text: Text to study.
        :param weight: Study weight.
        :returns: Result dict.
        :rtype: dict
        """
        st = self._engine.get_study()
        with self._lock:
            st.study(text, weight=weight, triggering_text=f'force:{self._name}')
            self._studied += 1
        self._save()
        return {'studied': self._studied}

    def seed(
        self,
        on_progress: Optional[Callable] = None,
        check_interval: int = 10,
    ) -> Dict[str, Any]:
        """Run one complete pass through the corpus (blocking).

        Fetches every URL in order, studies each, saves on network failure
        and waits for connectivity before continuing.  Returns when the last
        URL has been attempted.

        :param on_progress: Callable(tag, url, idx, total, studied, skipped)
            invoked after each URL.
        :param check_interval: Seconds between network retry attempts.
        :returns: ``{'studied', 'skipped', 'total', 'complete', 'bin_path'}``.
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
                st = self._engine.get_study()
                with self._lock:
                    st.study(text, weight=weight,
                             triggering_text=f'{tag} {url}')
                    self._studied += 1
                self._save()

            if on_progress:
                try:
                    on_progress(tag, url, idx, total, self._studied, skipped)
                except Exception:
                    pass

        self._save()
        return {
            'studied':  self._studied,
            'skipped':  skipped,
            'total':    total,
            'complete': True,
            'bin_path': self._bin_path,
        }

    # ── continuous loop ────────────────────────────────────────────────────

    def _loop(self) -> None:
        """Background study loop — fetches the full corpus repeatedly."""
        while not self._halt.is_set():
            corpus = self._get_corpus()
            for tag, url, weight in corpus:
                if self._halt.is_set():
                    break
                self._wait_network()
                text = self._fetch_text(url)
                if text and len(text) >= 40:
                    st = self._engine.get_study()
                    with self._lock:
                        st.study(text, weight=weight,
                                 triggering_text=f'{tag} {url}')
                        self._studied += 1
                    self._save()
                if not self._halt.wait(self._interval):
                    continue
        with self._lock:
            self._running = False
