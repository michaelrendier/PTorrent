"""The api-first resolution ladder.

Per seed URL, tried in the declared order; the first rung that yields content
wins and the item records `resolved_via`:

  declared_api  the .ptorrent's own `source` / phonebook `api` block
  known_api     host -> structured API (MediaWiki extracts, arXiv Atom, ...)
  sitemap       robots.txt Sitemap: entries / /sitemap.xml, filtered by scope
  feed          <link rel=alternate> Atom/RSS discovery
  html          robots-gated GET -> content-type dispatch -> strip to prose
"""
from __future__ import annotations

import html.parser
import json
import re
import urllib.parse

from .net import HttpClient

# ── HTML -> prose ──────────────────────────────────────────────────────────

class _Strip(html.parser.HTMLParser):
    def __init__(self, skip: set[str]):
        super().__init__()
        self._skip = skip
        self._depth = 0
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self._skip:
            self._depth += 1

    def handle_endtag(self, tag):
        if tag in self._skip and self._depth:
            self._depth -= 1

    def handle_data(self, data):
        if not self._depth:
            t = data.strip()
            if t:
                self._buf.append(t)

    def text(self) -> str:
        return "\n".join(self._buf)


def strip_html(raw: str, skip: list[str]) -> str:
    s = _Strip(set(skip))
    try:
        s.feed(raw)
    except Exception:
        pass
    return s.text()


def json_pointer(obj, pointer: str | None):
    if not pointer:
        return obj
    cur = obj
    for part in pointer.strip("/").split("/"):
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list) and part.isdigit():
            cur = cur[int(part)] if int(part) < len(cur) else None
        else:
            return None
    return cur


# ── known_api registry ─────────────────────────────────────────────────────
# A tiny built-in registry; a real deployment refreshes known_apis.json the way
# the phonebook is community-maintained.

_MEDIAWIKI_HOSTS = re.compile(
    r"(^|\.)(wikipedia|wiktionary|wikisource|wikiquote|wikibooks)\.org$")


def _known_mediawiki(url: str, http: HttpClient) -> str | None:
    p = urllib.parse.urlparse(url)
    if not _MEDIAWIKI_HOSTS.search(p.netloc.lower()):
        return None
    title = urllib.parse.unquote(p.path.rstrip("/").rsplit("/", 1)[-1])
    if not title or title.startswith("Special:"):
        return None
    api = (f"{p.scheme}://{p.netloc}/w/api.php?action=query&titles="
           f"{urllib.parse.quote(title, safe='')}"
           f"&prop=extracts&explaintext=1&exsectionformat=plain&redirects=1&format=json")
    r = http.get(api, accept=["application/json"])
    if r.status != 200:
        return None
    try:
        data = json.loads(r.body.decode("utf-8", "replace"))
        for page in data.get("query", {}).get("pages", {}).values():
            text = (page.get("extract") or "").strip()
            if len(text) > 100:
                return text
    except Exception:
        return None
    return None


def _known_arxiv(url: str, http: HttpClient) -> str | None:
    p = urllib.parse.urlparse(url)
    if "arxiv.org" not in p.netloc.lower():
        return None
    m = re.search(r"/abs/([^/?#]+)", p.path)
    if not m:
        return None
    api = f"http://export.arxiv.org/api/query?id_list={m.group(1)}"
    r = http.get(api, accept=["application/atom+xml", "application/xml"])
    if r.status != 200:
        return None
    body = r.body.decode("utf-8", "replace")
    title = re.search(r"<title>(.*?)</title>", body, re.S)
    summ = re.search(r"<summary>(.*?)</summary>", body, re.S)
    parts = [re.sub(r"\s+", " ", x.group(1)).strip() for x in (title, summ) if x]
    return "\n".join(parts) if parts else None


_KNOWN = [_known_mediawiki, _known_arxiv]


# ── the ladder ─────────────────────────────────────────────────────────────

class Resolved:
    __slots__ = ("via", "text", "rows", "status", "sha256", "sitemaps")

    def __init__(self, via, text=None, rows=None, status=200, sha256="", sitemaps=None):
        self.via = via
        self.text = text
        self.rows = rows
        self.status = status
        self.sha256 = sha256
        self.sitemaps = sitemaps or []


def resolve(url: str, *, order: list[str], http: HttpClient, robots,
            robots_ua: str, on_unreachable: str, extract: dict,
            source: dict | None = None, api: dict | None = None) -> Resolved:
    for rung in order:
        if rung == "declared_api":
            got = _declared_api(url, http, source, api, extract)
            if got:
                return got
        elif rung == "known_api":
            for fn in _KNOWN:
                try:
                    text = fn(url, http)
                except Exception:
                    text = None
                if text:
                    return Resolved("known_api", text=text)
        elif rung in ("sitemap", "feed"):
            # discovery rungs only expand the frontier; handled by crawl.py
            continue
        elif rung == "html":
            allowed, rstate = robots.can_fetch(robots_ua, url, on_unreachable)
            if not allowed:
                return Resolved("none", status=-1)   # crawl.py maps to ROBOTS_DENIED
            r = http.get(url, accept=extract.get("_accept") or
                         ["text/html", "application/json", "text/plain"])
            if r.from_cache:
                return Resolved("html", text=None, status=304, sha256=r.sha256)
            if r.status != 200 or not r.body:
                return Resolved("html", status=r.status, sha256=r.sha256)
            ctype = r.headers.get("Content-Type", "")
            body = r.body.decode("utf-8", "replace")
            if "application/json" in ctype:
                try:
                    data = json.loads(body)
                    rows = json_pointer(data, (extract.get("json") or {}).get("pointer"))
                    if isinstance(rows, list):
                        return Resolved("html", rows=rows, status=200, sha256=r.sha256)
                except Exception:
                    pass
                return Resolved("html", text=body, status=200, sha256=r.sha256)
            if "text/plain" in ctype or url.endswith(".txt"):
                return Resolved("html", text=body, status=200, sha256=r.sha256)
            skip = (extract.get("html") or {}).get(
                "strip", ["script", "style", "nav", "header", "footer", "aside"])
            return Resolved("html", text=strip_html(body, skip), status=200, sha256=r.sha256)
    return Resolved("none", status=0)


def _declared_api(url, http, source, api, extract) -> Resolved | None:
    block = api or source
    if not block:
        return None
    mode = (block.get("mode") or block.get("type") or "").lower()
    endpoint = block.get("endpoint") or block.get("url") or url
    if mode in ("rest", "", "json"):
        try:
            r = http.get(endpoint, accept=["application/json"])
        except Exception:
            return None
        if r.status != 200:
            return None
        try:
            data = json.loads(r.body.decode("utf-8", "replace"))
        except Exception:
            return Resolved("declared_api", text=r.body.decode("utf-8", "replace"),
                            sha256=r.sha256)
        rows = json_pointer(data, (extract.get("json") or {}).get("pointer"))
        if isinstance(rows, list):
            return Resolved("declared_api", rows=rows, sha256=r.sha256)
        return Resolved("declared_api", text=json.dumps(data), sha256=r.sha256)
    # tap_adql / fits / hdf5 etc. are handled by evaluate.py adapters, not here.
    return None
