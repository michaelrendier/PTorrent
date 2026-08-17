# PTorrent — Context Primer: the C Core and the Curses Face

**Written 2026-08-17 for a fresh session.** Read this before touching the repo.
Companion to [`claude_code_context_primer.md`](claude_code_context_primer.md), which covers
the existing Android/Python implementation. This one covers the restructure.

---

## 0. What PTorrent is (thirty seconds)

**Two halves, co-equal.** Get this right before designing anything, because the core has to
serve both and they have different shapes:

```
ACQUIRE     a user-defined, robots.txt-COMPLIANT web crawler + download client
            the user defines the scope; the core enforces the politeness
DISTRIBUTE  dataset and checkpoint distribution, peer-to-peer, torrent-like
            once a device has built a bin, it becomes a seed
```

A `.ptorrent` file is a JSON job description — what to fetch, how to tag it, where to write
the checkpoint. A device picks up the job, crawls the URL list locally under robots.txt
discipline, and writes `monad_<name>.bin`. Then it seeds that bin to other devices.

No tracker required. No gradient server. No central coordinator. It distributes the **work**,
not the gradients — the specific thing that makes it not federated learning. The data never
leaves the device.

Structural ancestor: BitTorrent (Cohen 2003). Paradigm superseded: the parameter server
(Li et al. 2014).

**Why the two halves belong in one program:** the output of ACQUIRE is the input to
DISTRIBUTE. A device that finished crawling holds something other devices need, and the
whole economic argument — offload traversal to LTE devices, keep the desktop free — only
closes if the result propagates without going back through the desktop.

---

## 1. The restructure — what changes and why

**Today:** the implementation *is* the Android APK. Kotlin UI + Python 3.12 seeding engine
bridged by Chaquopy 15.0.1. The protocol and the phone are entangled — you cannot run
PTorrent without an Android device.

**Wanted:** the protocol is the product, and Android is one consumer of it.

```
                    ┌─────────────────────────────┐
                    │  PTORRENT CORE  (C, main)   │
                    │  .ptorrent parse + verify   │
                    │  ┌── ACQUIRE ─────────────┐ │
                    │  │ robots.txt + host queue│ │
                    │  │ crawl / fetch          │ │
                    │  │ pause-on-signal-loss   │ │
                    │  │ tag pipeline           │ │
                    │  └────────────────────────┘ │
                    │  ┌── DISTRIBUTE ──────────┐ │
                    │  │ DHT / peers / pieces   │ │
                    │  │ beta-weighted merge    │ │
                    │  └────────────────────────┘ │
                    │  checkpoint container       │
                    │  chain / provenance         │
                    │  ── stable C API ──         │
                    └──────────┬──────────────────┘
             ┌─────────────────┼─────────────────┬──────────────┐
             ▼                 ▼                 ▼              ▼
      curses face        Android APK        Windows svc    browser ext
      (*nix branch)      (android branch)   (windows)      (WASM, later)
```

**The core carries no UI and no platform assumptions.** Every front end is a *face* over it.
"Face" is already this project's word — see `peval/*.σface` and `evaluate_σface.py`, where a
σface is the evaluative face presented over a dataset. A curses console is the same idea
pointed at the core.

---

## 2. Branch scheme

`main` is **not** a platform. It is the core and its API, and it must build with no platform
SDK present.

| branch | contains | notes |
|---|---|---|
| `main` | C core + stable API + spec + tests | must compile with cc and libc alone. No SDK, no APK, no UI. |
| `nix` | curses face, daemon, socket API | first face to build. Linux/BSD. |
| `windows` | Windows service + console face | MSVC or mingw; no POSIX assumptions leak into core |
| `mac` | launchd agent + console face | BSD-adjacent; shares most of `nix` |
| `android` | existing PtolemySeeder APK | Kotlin + Chaquopy. **The C core does not involve the APK.** |
| `ios` | port evaluation only | no work yet; Chaquopy has no iOS analogue |

**Rule:** platform branches may depend on `main`; `main` may never depend on a platform
branch. If a platform needs something from the core, the core grows an API — it does not grow
an `#ifdef __ANDROID__`.

**Merge direction is one-way.** Fixes discovered on a platform branch get lifted into `main`
as API or core changes, then the platform branch rebases. Platform code never lands on `main`.

---

## 3. What the C core must implement

Extracted from the current Python engine, which is the reference implementation:
`android/PtolemySeeder/app/src/main/python/` — `seed_runner.py`, `monad.py`,
`ptorrent_chain.py`, `skills/*.py`.

### 3.1 `.ptorrent` parse
Format spec is authoritative: [`spec/ptorrent-format-v1.md`](../spec/ptorrent-format-v1.md).
UTF-8 JSON. Fields in use today: `ptorrent_version`, `type`, `name`, `bin`, `primary_tags`,
`color`, `description`, `urls[{tag,url}]`, plus the RDOP `security` block.

Known gaps, stated in the README and still open: **no signing, no checksum, no capability
negotiation.** A v1.1 that adds a manifest hash is the natural first spec change, and the C
core is the right place to define it since it will be the thing verifying it.

### 3.2 Fetch with pause, not abort
This is the piece with a working design already written elsewhere in the monorepo —
`BulletCluster/netgate.py`, 2026-08-17. Port its semantics to C:

```
probe        one TCP connect to the host being transferred FROM.
             Not ICMP, not a third-party DNS lookup. Cheapest thing that
             proves a route to the host that matters.
classify     DON'T. On any interruption, ask only "is the signal up?"
             down -> wait, unbounded patience, exponential backoff to a ceiling
             up   -> not a network fault; short backoff, then give up after
                     N consecutive no-progress attempts
quiet        log STATE TRANSITIONS only, plus a slow heartbeat. A job that
             waits six hours must not produce six hours of log.
resume       byte-range via Range:, from the .part offset
```

The design point worth preserving verbatim: **the gate does not classify the interruption.**
Wifi to tethering, suspend, out of range, far-end hiccup — all the same question. That is why
it is small enough to be correct.

Rationale for pause over restart: restarting re-runs the whole query stage. On the JWST job
that was a MAST observation query plus ~20 batched product-list calls, ~3 minutes of wall
time and real server load, before one byte moved. Pausing costs one TCP handshake.

### 3.2b robots.txt compliance — a CORE requirement, not a courtesy

This is half the identity of the ACQUIRE side and it belongs in the core, below every face,
where no front end can opt out of it.

```
fetch /robots.txt per (scheme, host, port)   BEFORE the first content request
cache it with a TTL; re-fetch on expiry, not per URL
parse User-agent groups, Allow, Disallow, Crawl-delay, Sitemap
match the MOST SPECIFIC applicable User-agent group, then longest-match paths
honour Crawl-delay as a PER-HOST minimum interval, not a global one
on 4xx for robots.txt -> treat as allow-all;  on 5xx / unreachable -> treat as DISALLOW
   (fail closed: an archive that is down must not be hammered)
```

Design notes that matter here specifically:

- **Per-host rate limiting is a core scheduler concern, not an adapter concern.** Adapters
  will each get this wrong differently. One host queue with one delay clock, shared by every
  adapter, is the only version that holds.
- **Declare a real User-Agent with contact info.** A distributed crawler that cannot be
  identified or asked to stop is the kind that gets an IP range banned. And a phone fleet
  makes that worse, not better — you burn many addresses, and the archives we depend on
  (MAST, CDA, SARAO, LMFDB) are exactly the ones that would notice.
- **`Crawl-delay` interacts with the fleet.** Ten phones honouring a 1-second delay
  independently are collectively hitting once per 100 ms. If a job is sharded across devices,
  the delay has to be divided by the shard count, or the shards have to cover disjoint hosts.
  **This is a protocol-level problem and it is unsolved** — note it in the spec rather than
  pretending per-device politeness is sufficient.
- Keep `Sitemap:` — it is the cheapest legitimate way to discover a dataset's structure and it
  serves the Dataset Phonebook goal directly.

An explicit non-goal: no robots.txt bypass, no UA spoofing to evade a Disallow. The Mozilla UA
string used elsewhere in the monorepo is for archives that block non-browser clients on
*content* they publish openly; it is not a licence to ignore an exclusion rule.

### 3.2c The DISTRIBUTE half — torrent-like seeding

README §2 already scopes this: DHT peer discovery, tracker support in `.ptorrent` files,
multi-peer bin download with β-weighted merge, seeder reputation, piece hashing, choking,
rarest-first. On Android that was planned via libtorrent through Chaquopy on ARM64.

For the C core the decision to make deliberately: **wrap libtorrent-rasterbar, or implement
the wire protocol?** Wrapping is right — piece selection, choking, and DHT are solved and
subtle, and a from-scratch implementation is a year of work that isn't the point of this
project. What the core owns is the *layer above*: mapping `.ptorrent` jobs to torrents,
verifying manifests, and the β-weighted merge, which is genuinely ours and has no upstream.

The merge is the interesting part and the spec is silent on it. Two devices seed two bins
built from overlapping corpora; merging them is not concatenation, because β is a learned
per-token weight. That belongs in the spec before it belongs in code.

### 3.3 Tag pipeline
The `skills/` modules are per-corpus fetch/tag logic (MediaWiki-aware fetcher in
`skills/corpus.py`, plus specialised ones). In C this becomes a **dispatch table keyed by
`type` and adapter**, not a module import. Adapters needed on day one: plain HTTP, MediaWiki
API, ZIP-stream, and file-list.

### 3.4 Checkpoint writer
Current format is a **Python pickle** (`monad_*.bin`, v1.218+). A C core cannot write pickle
and should not try. Two options, and this is a decision to make deliberately rather than
drift into:

- **A**: define a versioned binary container in the spec (PTOL v4 already exists in VAPMIP —
  reuse it) and have Python read *that*. Clean, breaks existing bins.
- **B**: C core writes an intermediate (CBOR/msgpack), a thin Python shim converts to pickle.
  Keeps existing bins working, adds a hop.

**Recommend A.** Pickle across a language boundary is a trap, and PTOL v4 is already the
monorepo's binary format. Note the standing constraint from VAPMIP: `~/.ptolemy` bins are
**live state, read-only** — `monad_wordnet.bin` is loaded and never written back, ever.

### 3.5 Chain / provenance
`ptorrent_chain.py` implements the disclosure chain used by RDOP. The C core needs hash-chain
append and verify. Signing is the open gap noted in 3.1.

---

## 4. The curses face (`nix` branch, first face)

Full-screen console. The APK's UI is already Transmission-shaped (`▶ ⏸ ✕ ＋`) and the console
should be recognisably the same instrument, because they are faces over one core.

```
┌ PTorrent ─────────────────────────────────── 4 jobs · 2 active ─┐
│ ▶ physics          ████████████░░░░░░  61%   12.4 MB/s   142/230│
│ ▶ mathematics      ██████░░░░░░░░░░░░  31%    8.1 MB/s    77/248│
│ ⏸ english_complete ███░░░░░░░░░░░░░░░  14%  PAUSED: signal down │
│ ✓ foundations      ██████████████████ 100%   monad_foundations.bin│
├──────────────────────────────────────────────────────────────────┤
│ [space] pause/resume  [a] add  [x] cancel  [enter] detail  [q]   │
└──────────────────────────────────────────────────────────────────┘
```

Requirements that are not cosmetic:

- **A paused job must be visibly distinct from a failed job, with the reason shown.** This is
  the whole point of the gate. "PAUSED: signal down" and "FAILED: 404" are different states
  and conflating them is what made the old download scripts untrustworthy.
- **Per-job pause.** The APK has global pause only (`AtomicBoolean globalPaused`) and the
  README lists per-corpus pause as an open task. The C core should implement per-job from the
  start so the APK can inherit it.
- **A detail view per job** — the URL list with per-URL state, matching
  `CorpusDetailActivity`. Pre-populate the list before fetching begins, as SeedService already
  does; an empty list during startup reads as a hang.
- **No curses in the core.** The face polls or subscribes to core state through the API. If
  ncurses appears in a `main`-branch header, the layering has failed.

Suggested layout on the `nix` branch: `face/curses/` for the UI, `daemon/` for the socket API
(README §6 already lists "PTorrent daemon with socket API" as planned). The daemon is what
makes the browser extensions possible later — an extension talks to a local socket, not to a
library.

---

## 5. Why this matters right now — the motivating case

`BulletCluster/` currently contains **seven** overlapping downloaders, each with its own state
file and its own resume logic: `download_bullet_cluster.py`, `jwst_resume_download.py`,
`optical/hst/resume_hst.py`, `optical/jwst/resume_jwst.py`,
`optical/jwst/download_mosaics.py`, `lensing_validation/download_validation_targets.py`,
`engine/ptorrent/sarao_download.py`.

That is the same provenance failure as an image with no generating script: the work happened,
the reusable part was not kept. Every new archive produced a new script instead of a new
adapter. **PTorrent with per-archive adapters is the fix**, and the archives already needed
are a good first adapter set:

MAST (JWST/HST), Chandra CDA, SARAO GraphQL, ASKAP/CASDA, NED/IRSA, LMFDB.

One more thing learned today and worth building in: **MAST publishes no torrents, but JWST/HST
are in the AWS Open Data Registry with `RequesterPays=False`.** `astroquery` exposes it via
`enable_cloud_dataset()` / `cloud_only=True`, and that is the real bulk-speed win for this
archive. An S3 path belongs in the MAST adapter. Magnet links → Transmission remains the right
answer where torrents genuinely exist (Academic Torrents, some simulation dumps); it is not
available here.

---

## 6. Order of work

1. **`main`**: `.ptorrent` parser + spec v1.1 with a manifest hash. Tests. No network.
2. **`main`**: **robots.txt + per-host queue with one delay clock** (§3.2b). Before any
   adapter, so no adapter can be written that bypasses it.
3. **`main`**: the gate (port `netgate.py` semantics) + HTTP adapter with Range resume.
4. **`main`**: checkpoint container (decide A vs B in §3.4 first).
5. **`nix`**: curses face over the core. Per-job pause. Paused ≠ failed.
6. **`nix`**: daemon + socket API.
7. **spec**: the β-weighted merge, written down before it is coded (§3.2c).
8. **`main`**: DISTRIBUTE via libtorrent-rasterbar, core owning only the layer above it.
9. Lift anything learned back into `main` as API. Then Windows/Mac faces.
10. Browser extensions last — they talk to the daemon socket, so they need step 6.

**Order rationale:** ACQUIRE before DISTRIBUTE, because you cannot seed what you have not
fetched, and robots.txt before adapters, because politeness retrofitted into N adapters is
politeness in none of them.

**Do not start with the browser extension.** It is the furthest from the core and the most
likely to drag platform assumptions inward.

---

## 7. Standing constraints (monorepo-wide, do not violate)

- **Never use `PTOL_SEED_TOKEN`.** It is unspec'd and belongs to the monad's own GitHub
  interaction. Use `GITHUB_TOKEN` from `~/.bashrc`.
- **ContextPlease update and copy protocol runs first on ANY push.**
- Scratch and experimental code go to persistent storage under `ThePlace/.claude/`, never
  `/tmp` — a working directory is provenance, and text is free next to FITS.
- `~/.ptolemy` bins are live state. Read-only.
- Prototype in python3; port to C only when a result is significant. The C core is the
  exception to that rule and only because portability *is* the result here.
