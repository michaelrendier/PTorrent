# PTorrent Changelog

Each release is a foundational inclusion — full version increment.

---

## v7.0 — 2026-06-03

### Responsible Disclosure Open Protocol (RDOP)

PTorrent formally defines an open protocol for responsible disclosure of
security vulnerabilities discovered during research.

**Chain (ptorrent_chain.py):**
- +7 transaction types: EVALUATE, CLASSIFY, ACKNOWLEDGE, DISCLOSE, REVOKE,
  FLAG, NOTIFY — complete security lifecycle on-chain
- `evaluate()` — Data Transversal result with parallel β-merge semantics
- `classify()` — security classification with embargo enforcement
- `acknowledge()` — warning_hash proof of informed consent
- `disclose()` — embargo lift, classification drop
- `notify()` — agency notification committed BEFORE send (chain is authoritative)
- `flag()` / `is_flagged()` — malicious file block, no override
- `get_classification()` / `is_embargoed()` / `get_evaluations()` / `get_notifications()`

**Disclosure module (skills/disclosure/):**
- `stix_builder.py` — STIX 2.1 vulnerability/CoA/report/bundle (pure Python)
- `notifier.py` — NIST, CISA, MITRE, CERT/CC, NCSC, ENISA dispatch
  - TAXII 2.1 client for CISA AIS machine-readable submission
  - Structured email with STIX bundle attachment
  - `pre_check()` — queries NVD + KEV before filing

**Adapters (skills/adapters/):**
- `nist_nvd_adapter.py` — NVD CVE database query (API key optional)
- `cisa_kev_adapter.py` — CISA KEV catalog (public domain, cached)
- Full scientific adapter stack: FITS, HDF5, MRT, VOTable, Fortran binary,
  COBOL VSAM + EBCDIC, GitHub API, IVOA TAP/ADQL

**Safety (skills/sandbox.py, skills/preflight.py):**
- Python execution sandbox — blocks subprocess/ctypes/system paths
- Pre-flight resource checker — storage/RAM/temp/battery/embargo hard gates
- ThermalMonitor — continuous pause/resume at 48°C/40°C
- doc/ANDROID-SAFETY.md — VBMeta/build.prop protection guide

**Format specs:**
- ptorrent-format-v1.md: +evaluation type, +security block, +resources block,
  +data_model object
- ptorrent-chain-v1.md: +13 new transaction types documented, v1.2

**Documentation:**
- wiki/Responsible-Disclosure-Protocol.md — formal RDOP specification
- wiki/Agency-Interface.md — NIST/CISA/MITRE interface, email templates
- wiki/Security-Classification.md — classification levels, enforcement procedures
- README.md — RDOP section with NIST/CISA invitation

---

## v6.0 — 2026-06-01

### New ptorrents

- **`framenet.ptorrent`** — FrameNet 1.7 corpus (semantic frame database).
- **`riemann_zeros.ptorrent`** — first 100,000 Riemann zeros corpus.
- Updated: english_complete, mathematics, physics, foundations, meaning, python, fermat.

---

## v5.0 — 2026-05-31

### APK
- **PGui color scheme**: red (`#cc2200`) → cyan (`#00ffff`) → blue (`#0055ff`) gradient
  matching PtolemyDesktop window compositor palette. J_pos / critical line / J_neg.
- **Status bar inset fix**: content no longer overlaps Android system UI.
  WindowInsetsCompat applied dynamically at runtime — handles notches, punch-holes,
  foldables correctly.
- **White text + white glow shadow**: `setShadowLayer(3f, 0f, 0f, WHITE)` on all
  TextViews. Single rule, zero overhead, readable on all dark backgrounds.
- **Gradient accent stripe**: horizontal red→cyan→blue stripe at top of each corpus
  card, matching PGui's 6px title bar stroke.
- **Settings screen**: storage directories, MCP server toggle + port, network
  (UA selection, timeout, retry, WiFi-only), seeder (threads, checkpoint interval),
  cloud sync stubs (Google Drive, Dropbox, OneDrive, iCloud, Samsung Cloud),
  API credentials (encrypted), about/ORCID.
- **Settings button** (⚙) added to toolbar row.
- **MCP server stub**: ACTION_MCP_START / ACTION_MCP_STOP wired to SeedService.
  Ktor integration pending.

### Corpus
- **Fermat Bibliography renamed**: `Prime Directive III — War Corpus` →
  `Prime Directive III — Fermat Bibliography`. It is a bibliography, not a war corpus.
  Bin: `monad_war.bin` → `monad_fermat.bin`.
- **Crawler rewrite**: `_fetch_text()` in corpus.py replaced with API-first crawler:
  - Wikipedia/Wiktionary → MediaWiki extracts API (clean plaintext, no HTML)
  - arXiv → structured abstract extraction
  - SSL fallback for institutional servers with cert mismatches
  - robots.txt compliance with per-host cache
  - Mozilla/5.0 UA path for sites that block bot UAs (403 fallback)
- **Corpus save bug fixed**: `GenericCorpus.__init__` used `load_bin()` which added
  the bin path to `_protected_paths`, silently preventing `save_session()` from
  writing. Fixed: `load_checkpoint()` added to Engine (loads state without
  path protection).
- **GEOMETRIC INIT bins cleared from phone**: all previous zero word_count bins
  deleted. Clean restart with corrected crawler.

### Engine (monad.py)
- **Mind's Eye speak routing**: `generate` dispatch routes through
  `_speak_depth()` → `contemplate()` → `mind_eye.describe()` instead of
  bare `engine.generate()`. Callosum geometry informs word selection.
- **`see_text()`**: encodes text prompt into second 𝕆 (psi2) via spectral
  analysis — mean E, spread, depth, β mean, vocabulary coverage, BAO proximity.
- **`contemplate(depth)`**: multi-pass psi2 settling before callosum crossing.
  Depth 1 for casual speech, 5+ for mathematical reasoning.
- **`describe(n_words)`**: n_words parameter added (was hardcoded 8).
- **`load_checkpoint()`**: loads pickle state without path protection —
  for corpus bins that need both load and save to the same path.

### daemon.c (PtolC)
- `monad_speak_oct()` identified as C-side callosum approximation (interference
  score: content × observer beat frequency). Wired as default in daemon.c
  HEAR handler (replaces bare `monad_speak()`).

---

## v4.0 — 2026-05-30

**Android APK v2.0 — PTorrent Protocol + Corpus Detail Pages**

Physics and Mathematics corpora operational. Full Android APK v2.0 released.

### Android APK v2.0 — `android/PtolemySeeder/`

- **PTorrent format** — `.ptorrent` JSON file is the distribution unit for new corpora.
  Two delivery paths: `adb push` to `inbox/` (FileObserver auto-picks up) or tap-to-open
  via intent filter (`application/x-ptorrent`, `*.ptorrent`).
- **Corpus detail page** — tap any card → `CorpusDetailActivity`: header (name, status, description,
  primary tag chips, bin path), live stats grid (Total / Studied / Skipped / Success Rate),
  full URL list with per-URL status icons (○ PENDING ▶ ACTIVE ✓ STUDIED ✗ SKIPPED).
  Incremental list update — only changed rows are redrawn.
- **Transmission toolbar** — ▶ Resume All · ⏸ Pause All · ✕ Clear Done · ＋ PTorrent picker.
  Pause blocks Python fetch threads at URL granularity via `AtomicBoolean` in Kotlin bridge.
- **URL pre-population** — SeedService parses all `.txt` corpora at startup; full URL lists
  are visible in detail pages before seeding begins.
- **FileObserver inbox** — watches `extDir()/inbox/` for `.ptorrent` drops (CLOSE_WRITE | MOVED_TO).
  API-safe: File-based constructor on API 29+, deprecated path-based on API 26–28.
- **seed_runner.py** — new `run_one(entry, ...)` function for single-corpus PTorrent seeding.
  `_seed_one` extracted as shared helper.
- **Notification** — Pause/Resume toggle action in notification drawer.
- **versionCode 4, versionName "2.0"**

### New Corpora

- **`physics_corpus.txt`** — ~130 URLs across 10 parts.
  Tags: FOUNDATIONS, WAVES, RESONANCE, QM, GR, COSMOLOGY, DARKMATTER, YANGMILLS,
  FLUIDMECH, SPECTRAL, GRAVITY, CONTEXT.
- **`mathematics_corpus.txt`** — ~130 URLs across 12 parts.
  Tags: PRIMES, RIEMANN, SPECTRAL, MODULAR, HARMONIC, GEOMETRY, ALGEBRA, ANALYSIS,
  NUMBERTHEORY, CLAY, CONTEXT.

### Wiki

- **`wiki/PTorrent-APK-v2.md`** — full v2.0 reference: PTorrent format, adb workflow,
  pause architecture, corpus colours, version history.

---

## v3.0 — 2026-05-30

**Android APK v1.0 — Torrent Architecture**

Dynamic corpus manifest. Any corpus can be added by pushing an updated
`corpus_list.json` via adb — no APK rebuild required.

### Android — `android/PtolemySeeder/`

- **`corpus_list.json`** — torrent manifest: name, bin, txt, primary_tags, color per entry.
- **`SeedService.kt`** — rewritten: dynamic `Map<String,CorpusState>` LiveData,
  one thread per manifest entry, `loadCorpusOrder()` parses JSON at launch.
- **`MainActivity.kt`** — rewritten: fully programmatic layout, one card per corpus,
  color-coded by manifest entry (gold/blue/red/green/purple).
- **`seed_runner.py`** — rewritten: reads `corpus_list.json`, spawns one thread
  per entry, returns when all exhausted.
- Assets: `foundations.txt`, `meaning.txt`, `war_corpus.txt`, `python_corpus.txt`,
  `c_corpus.txt`, `corpus_list.json` all bundled and extractable.

### Tool — `android/build_apk.sh`

Syncs Python sources and corpus assets from repo root into the Android project,
then runs `./gradlew assembleDebug`. Optional `--install` flag runs `adb install -r`.

```bash
bash android/build_apk.sh           # build only
bash android/build_apk.sh --install # build + install on attached phone
```

### Acquisition run — 2026-05-29/30

All five corpora acquired on Moto G 5G 2024, unlimited LTE, unattended:

| Corpus | Size | Time |
|---|---|---|
| monad_foundations.bin | 676 KB | ~5 min |
| monad_meaning.bin | 138 KB | ~3 min |
| monad_war.bin | 84 KB | < 1 min |
| monad_python.bin | 5.4 MB | ~90 min |
| monad_c.bin | 1.4 MB | ~90 min |

---

## v2.0 — 2026-05-19

- Initial sedenion corpus seeder APK
- Chaquopy Python runtime (3.12)
- Eight corpus types defined in corpus_list.json
- Prime Directive I, II, III seeding
