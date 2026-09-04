# PTorrent Core Architecture

**License:** LGPL-3.0-or-later (the core is a library embedded in front-ends on
every platform — weaker copyleft is deliberate).

The core has **no GUI**. Every front-end is a *face* over one surface and lives
in its own `releases/<face>/` directory; nothing below the surface knows a face
exists.

```
core/c/libptorrent          the ABI-stable inner core — parse, classify, express. No I/O.
        │  ctypes  (or the pure-Python fallbacks: ptfile, sigma, jexpr, corpuslist)
core/python/ptorrent_core    the runtime core — I/O, orchestration, provenance
        │  Engine.snapshot() / events(since_seq) / command verbs   ≡  schema/v1.json
faces   curses · Android · iOS · .NET · browser        in-process, or JSON-RPC via ptorrentd
```

---

## 1. `core/c/libptorrent` — the inner core

C99, no dependencies. The whole public surface is `include/ptorrent.h`
(78 exported `pt_*` symbols). Obeys the hardest target, iOS:

1. C ABI only (name mangling is not portable)
2. opaque handles — callers hold pointers, never layouts
3. no struct-by-value across the boundary
4. no callbacks into the caller — progress is **polled**
5. the core never owns the process — no daemon, no `fork`, no signal handlers
6. no ambient paths — every filesystem root is injected by the host
7. cooperative flag-based cancellation, never signals
8. UTF-8 everywhere

Provides: `.ptorrent` parse + validate · `j_expr` compile + evaluate (whitelisted
arithmetic, no `eval`) · σ-face classify + tally · a dependency-free JSON DOM ·
the `[TAG] URL` acquisition list with a cursor / dedup record model.

Parked here by design (all of it is I/O): robots.txt, the per-host queue, HTTP
adapters, `Range:` resume, the `.peval` writer, the daemon socket API. **That is
what `core/python` is.**

---

## 2. `core/python/ptorrent_core` — the runtime core

Stdlib only, Python ≥ 3.11, no `monad.py` dependency.

| Module | Responsibility |
|--------|----------------|
| `engine.py` | the façade — owns a worker pool + the per-host crawl scheduler; `snapshot()` / `events(since_seq)`; all command verbs |
| `ptfile.py` | `.ptorrent` v1.2 parse/validate, fail-closed; `crawl` / `distribution` / `security.labels` blocks |
| `sigma.py` | σ-face classify + tally — non-finite J ⇒ `undefined`, never `∞` |
| `jexpr.py` | `j_expr` — recursive-descent, **never `eval()`** |
| `corpuslist.py` | `[TAG] URL` list — tag regex `[A-Za-z0-9_]+`, count-don't-drop |
| `net.py` | `RobotsCache` (token-matched), `HostQueue` delay clock + backoff, gzip/conditional/Range HTTP, `NetworkGate` (never aborts) |
| `resolve.py` + `crawl.py` | api-first ladder; every seed → an `Item` with a terminal status |
| `artifacts.py` | `BinaryArtifactStore` + the artifact-before-stream invariant |
| `evaluate.py` + `reductions.py` | in-situ σ-face; tabular and binary/image `fn` reductions |
| `chain.py` + `custody.py` | hash-linked custody chain; `marking` on every tx; CASE/UCO · STIX 2.1 · AFF4 exporters |
| `phonebook.py` | Alexandrian intake, dedup key, FTS5 search, opt-in seed listing |
| `identity.py` | ORCID `ANONYMOUS → CLAIMED → VERIFIED`; capability gate |
| `access.py` | `request → clarify ↔ respond → grant / deny`; TLP-gated, non-transitive strict grants |
| `votes.py` | thumbs — immutable cast, VERIFIED-only, no self-vote; `vote_address` / `vote_dispute` |
| `labels.py` | TLP 2.0 + CWE/CAPEC/ATLAS/CVSS/SSVC vocab + validation; `labels_hash`; TLP→capability |
| `wizard.py` | `ptorrent_build(answers)` — the "create new `.ptorrent`" decision tree |
| `preflight.py` `keys.py` | resource + security gate; key store — reused from the Android engine |
| `db.py` | one sqlite file: events (replayable by `seq`), jobs, items, artifacts, phonebook, etag cache, votes, requests |
| `errors.py` | `PtErr` — mirrors libptorrent `pt_err`, plus `E_IDENTITY`, `E_SELF_VOTE`, `E_DUP_VOTE`, `E_EMBARGO`, `E_ROBOTS`, `E_QUARANTINE`, `E_ACCESS`, `E_MARKING_DOWNGRADE` |

### Design decisions

- **Co-equal Python API + JSON schema.** Every verb is defined once in
  `schema/v1.json` and has an identical-semantics Python binding.
- **The core owns threads.** Jobs run autonomously once started; faces poll.
- **In-process execution for all jobs**, under import-hook restrictions. A
  subprocess-sandbox shim triggers only on `security.level ≥ 3`, a chain `FLAG`,
  or an explicit `"sandbox": true`.
- **Durable, replayable events** (sqlite). The custody chain is a separate
  append-only evidentiary substrate; every custody transaction also lands as an
  event with `kind: "CUSTODY"`.
- **Artifact-before-stream invariant.** For any stream S derived from bytes B:
  write B → hash → `ACQUIRE` tx, *before* the first event of S. Every stream
  event carries `parent_hash = h(B)`. Un-retained bytes still get an `ACQUIRE`
  with `retained: false` + `source_url` — lineage without the bytes.

---

## 3. Two-tier ledger

| Tier | Store | Contains |
|------|-------|----------|
| Event stream | sqlite, monotonic `seq` | high-frequency operational events; replayable across restart via `events(since_seq)` |
| Custody chain | `custody_chain.json` | append-only, `prev_hash`-linked, Merkle-rooted, light-PoW; `ACQUIRE` `ANNOUNCE` `EVALUATE` `SEED` `PHONEBOOK_ADD` `CLASSIFY` `ACKNOWLEDGE` `REQUEST/GRANT/DENY` `VOTE/VOTE_ADDRESSED/VOTE_DISPUTED` `DISCLOSE` `FLAG` … |

Each custody transaction carries `actor` (ORCID-attributed `peer_id`),
`object_hash`, `parent_hash`, `marking` `{tlp, level, labels_hash}`, UTC
`timestamp`, `tx_hash`, optional `sig`. `chain_export(fmt)` projects to `native`
(authoritative), `case` (CASE/UCO — canonical evidentiary form), `stix`
(disclosure subset), `aff4` (container, not yet implemented).

---

## 4. What is not built yet

`ptorrentd` JSON-RPC transport · full ORCID OAuth token exchange · the
subprocess-sandbox shim · AFF4 / CSAF export · FITS / HDF5 / TAP evaluation
adapters · sitemap / feed frontier expansion (rungs are wired, expansion is a
no-op) · the libptorrent ctypes binding (pure-Python `ptfile` / `sigma` /
`jexpr` / `corpuslist` stand in).

Front-ends (curses, Android, …) are tracked under `releases/` and linked from
the top-level `README.md` as they land.
