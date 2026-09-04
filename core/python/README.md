# PTorrent Core — Python

The platform-independent **runtime** core. `core/c/libptorrent` is the inner,
ABI-stable parse/classify/expr core; this package is the posix/runtime branch
its README parks: the I/O, orchestration, phonebook, identity, voting, and
custody chain. Every skin — curses, Android, iOS, .NET, browser — binds this
one surface, in-process or over `ptorrentd` (JSON-RPC; method names == the
Python verbs; shapes in `ptorrent_core/schema/v1.json`).

Stdlib only. Python ≥ 3.11. No `monad.py` dependency.

```python
from ptorrent_core import Engine

e = Engine("~/.ptorrent")                       # host injects the roots
r = e.add({                                     # a .ptorrent dict, path, or JSON
    "type": "corpus", "name": "Wave mechanics", "color": "cyan",
    "description": "", "bin": "monad_waves.bin",
    "crawl": {"seeds": [{"tag": "WAVES",
        "url": "https://en.wikipedia.org/wiki/Wave_equation"}]},
}, start=True)

while True:
    snap = e.snapshot()                         # jobs, phonebook, chain, identity
    for ev in e.events(since=seq): ...           # replayable by monotonic seq
```

## What runs today (spine, tested end-to-end)

| Flow | Path |
|---|---|
| find | `phonebook_search` / `phonebook_get` — Alexandrian intake: every `add()` checks the dataset into the library (`PHONEBOOK_ADD`) |
| download | `add(corpus\|dataset)` → api-first resolve (`declared_api → known_api → sitemap → feed → html`) → robots-gated fetch → `BinaryArtifactStore` |
| traverse + evaluate | `add(evaluation)` → row stream → `jexpr` (no `eval()`) → σ-face (`classify`, non-finite ⇒ UNDEFINED) → `.peval` artifact |
| seed | `seed(hash, list_mode)` — `SEED` custody tx always; phonebook `SEED_LISTED` beacon only when opted in and TLP:CLEAR |
| vote | `vote / vote_address / vote_dispute` — immutable cast, VERIFIED-only, no self-vote, down needs a reason |
| identity | `identity_set` (ISO 7064 checksum) → `identity_verify` (pub.orcid.org resolve; OAuth entry points stubbed) |
| access | `request_access → request_clarify ↔ request_respond → grant_access / deny_access` |
| custody | hash-linked chain (`chain.py`); `chain_export("native" | "case" | "stix")` — AFF4 stubbed |
| wizard | `ptorrent_build(answers)` — Step C cybersecurity self-identification → classification / level / `security.labels` |

**Crawler details:** wire UA `Mozilla/5.0 (compatible; PtorrentBot/1.0; +…)`,
robots matched on the bare token `PtorrentBot`; per-host delay clock honours
`Crawl-delay`; `429/503` → `DEFERRED` + backoff; whole-internet loss → block,
never abort; every seed becomes an `Item` with a terminal status — nothing is
dropped.

## Reused from the Android engine (near-verbatim, LGPL-3.0-or-later)

`chain.py` ← `ptorrent_chain.py` · `preflight.py` ← `skills/preflight.py` ·
`keys.py` ← `skills/ptorrent_keys.py` · `evaluate.py` ← `skills/evaluator.py`
math + `.peval` writer.

**Fixed on extraction:** σ non-finite ⇒ `UNDEFINED` (was `∞`); corpus tag regex
`[A-Za-z0-9_]+` + count-don't-drop (was `[A-Z]+` silent skip); `j_expr` is a
recursive-descent parser, never `eval()`.

## Not yet built (deliberate)

`ptorrentd` JSON-RPC transport · full ORCID OAuth token exchange · subprocess
sandbox shim (in-process + import hooks only for now) · AFF4 export · CSAF
export · FITS/HDF5/TAP evaluation adapters · sitemap/feed frontier expansion
(rungs are wired, expansion is a no-op) · libptorrent ctypes binding (pure-
Python `ptfile`/`sigma`/`jexpr`/`corpuslist` stand in).

## Test

```sh
cd core/python && python3 -m pytest tests/ -q
```
