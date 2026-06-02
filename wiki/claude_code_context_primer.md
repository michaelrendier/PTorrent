# PTorrent — Claude Code Context Primer

**Scope:** Strictly PTorrent. No Ainulindale theory, no SMMIP, no sedenion algebra.
This document tells Claude Code everything it needs to work effectively in this repo.
Keep it updated whenever ChangeLog entries are added.

**Built by:** Claude Code (claude-sonnet-4-6) in collaboration with Cody Michael Allison.
**Last updated:** 2026-06-02 (session 2)

---

## What This Repo Is

PTorrent is two things simultaneously:

1. **A targeted web crawler runtime for non-coders.** A `.ptorrent` file is a
   declarative JSON crawler spec — URL list, tags, output path. The PtolemySeeder
   Android APK is the runtime. Users modify existing `.ptorrent` files rather than
   writing code. A phone or tablet runs the crawl at LTE speeds in the background
   while the desktop keeps working.

2. **A Dataset Phonebook** (in progress, Priority #1). A machine-readable,
   dynamically-verified index of every publicly available dataset — where it lives,
   what format, whether an API or dump exists. Not the data itself. The directory.
   See `wiki/dataset_phonebook_seed_list.md` for the 400+ entry seed catalogue.

The APK uses Kotlin (UI, service layer) + Python 3.12 via Chaquopy (seeding engine).
The protocol is inspired by BitTorrent but currently has no peer-to-peer data
transfer — full BitTorrent seeding of corpus bins is a planned feature (TODO #2).

---

## Repository Layout

```
PTorrent/
├── COPYING                    GPL-3.0 full text
├── README.md                  Main README — dedication, architecture, "What's Being Built"
├── AUTHORS                    Original author. Add contributors here.
├── ChangeLog                  GNU-format changelog. Update with every significant change.
├── INSTALL                    Build and adb workflow reference
├── NEWS                       User-facing what's new per version
├── TODO.md                    Numbered priority list. Phonebook = #1.
├── .gitignore                 Excludes: bin_archive/*.bin, app/build/, .gradle/, __pycache__
│
├── android/
│   ├── build_apk.sh           Build + optional --install via adb
│   ├── corpus_list.json       Corpus manifest loaded by SeedService at startup
│   └── PtolemySeeder/         Full Android Studio project
│       ├── app/build.gradle   versionCode, Chaquopy config, dependencies
│       ├── app/src/main/
│       │   ├── AndroidManifest.xml   Intent filters for .ptorrent files
│       │   ├── java/com/ptolemy/seeder/
│       │   │   ├── MainActivity.kt         Transmission-style UI
│       │   │   ├── SeedService.kt          FileObserver, corpus list, LiveData
│       │   │   ├── CorpusDetailActivity.kt URL-level live status page
│       │   │   └── SettingsActivity.kt     Preferences
│       │   ├── python/
│       │   │   ├── monad.py               Checkpoint load/save (pickle, v1.218+)
│       │   │   ├── seed_runner.py         run_all() + run_one() entry points
│       │   │   └── skills/                Per-corpus seeding logic
│       │   │       ├── corpus.py          GenericCorpus — MediaWiki-aware fetcher
│       │   │       ├── corpus_physics.py
│       │   │       ├── corpus_mathematics.py
│       │   │       ├── corpus_python.py
│       │   │       ├── corpus_c.py
│       │   │       ├── foundations.py
│       │   │       ├── meaning.py
│       │   │       ├── fermat_lattice.py
│       │   │       └── study.py
│       │   └── assets/                    Corpus URL text files + corpus_list.json
│       └── app/build/                     Generated — git-ignored
│
├── ptorrents/                 10 .ptorrent corpus descriptors (JSON)
│   ├── physics.ptorrent
│   ├── mathematics.ptorrent
│   ├── english_complete.ptorrent
│   ├── foundations.ptorrent
│   ├── meaning.ptorrent
│   ├── fermat.ptorrent
│   ├── python.ptorrent
│   ├── c_posix.ptorrent
│   ├── riemann_zeros.ptorrent
│   └── framenet.ptorrent
│
├── aggregators/
│   └── medical/
│       └── scholar_aggregator.py   PubMed + ClinicalTrials cancer drug aggregator
│
├── spec/
│   └── ptorrent-format-v1.md  Definitive .ptorrent format spec (v1.0.1)
│                               Types: corpus, dataset, transfer, phonebook
│
├── doc/
│   └── PTorrent-APK-v2.md     Full APK v2.0 reference (delivery paths, toolbar, adb)
│
├── tests/                     Empty — contributions welcome
│
├── wiki/
│   ├── claude_code_context_primer.md   This file
│   └── dataset_phonebook_seed_list.md  400+ dataset seed catalogue
│
└── bin_archive/               Git-ignored on-disk only
    ├── README.md
    ├── clean/                 GEOMETRIC INIT bins (vocab only, word_count=0)
    └── dirty/                 Post-training or polluted checkpoints
```

---

## Technology Stack

| Layer | Technology | Version | Notes |
|-------|-----------|---------|-------|
| Android UI | Kotlin | 1.9+ | MainActivity, SeedService, CorpusDetailActivity |
| Build system | Gradle | 8.2 | android/PtolemySeeder/gradlew |
| Python bridge | Chaquopy | 15.0.1 | Embeds CPython in APK |
| Python runtime | Python | 3.12 | On-device via Chaquopy |
| Min SDK | Android API | 26 (Android 8.0) | FileObserver constructor varies API 26–29+ |
| Corpus bins | Python pickle | v1.218+ | NOT C binary — eval_checkpoint.py will fail on these |
| License | GPL-3.0 | — | COPYING contains full text |

---

## Build

```bash
# From repo root:
cd android
bash build_apk.sh             # assembleDebug
bash build_apk.sh --install   # assembleDebug + adb install -r

# Manual:
cd android/PtolemySeeder
./gradlew assembleDebug
# Output: app/build/outputs/apk/debug/app-debug.apk
```

**Requirements:** Android Studio (Hedgehog+) or SDK command-line tools, Java 17+,
adb in PATH, Android device/emulator API 26+.

---

## Current APK Version

| Field | Value |
|-------|-------|
| Version name | 2.0 |
| versionCode | 4 |
| Release date | 2026-05-30 |
| Corpora shipped | 7 (Foundations, Meaning, Fermat, Python, C/POSIX, Physics, Mathematics) |
| Chaquopy | 15.0.1 |
| Python | 3.12 |

---

## The .ptorrent Format — Quick Reference

Four types. All UTF-8 JSON with `.ptorrent` extension, MIME `application/x-ptorrent`.

| Type | Purpose |
|------|---------|
| `corpus` | Fetch URLs, extract text, seed monad checkpoint binary |
| `dataset` | Fetch structured data from API, save to file |
| `transfer` | Load `requires_bin` then continue corpus seeding |
| `phonebook` | Record where a dataset lives — address book entry, not the data |

Minimum required fields: `ptorrent_version`, `type`, `name`, `primary_tags`, `color`, `description`.
Full spec: `spec/ptorrent-format-v1.md`.

**phonebook type** (new in v1.0.1) adds a `phonebook` object with:
`dataset_url`, `license` (SPDX), `citation` (DOI), `api{}`, `dumps[]`, `last_verified`.

---

## Delivery Paths (APK)

**a) adb inbox push** — FileObserver watches `extDir()/inbox/` for `CLOSE_WRITE | MOVED_TO`:
```bash
adb push my.ptorrent /sdcard/Android/data/com.ptolemy.seeder/files/inbox/
```

**b) Tap to open** — Three intent filters in AndroidManifest.xml:
`application/x-ptorrent`, `*.ptorrent` via `content://`, `*.ptorrent` via `file://`.

---

## Architecture — Key Invariants

- **Pause:** `AtomicBoolean globalPaused` in Kotlin, checked inside the `__call__`
  bridge. Blocks Python at URL boundaries. No Python modification needed.

- **URL pre-population:** SeedService parses all `.txt` corpus files at startup and
  posts `List<UrlState>` to `SeedLiveData` before Python starts. Detail pages show
  the full URL list immediately.

- **Bin format:** Python pickle (Chaquopy 15.0.1 / Python 3.12). Load via
  `Engine.load_checkpoint(path)` in `monad.py`. Do NOT use `load_bin()` for corpus
  bins — silent save bug. Do NOT pass to `eval_checkpoint.py` — that tool expects
  C binary format and will error on pickle with "Bad magic number".

- **FileObserver API split:** API 29+ uses `File`-based constructor;
  API 26–28 uses deprecated path-based constructor. Both branches must be maintained.

- **Corpus card colors** are resolved in the UI from the `color` string field in
  `.ptorrent`. See `spec/ptorrent-format-v1.md` Color Table for hex values.

---

## Priority TODO (as of 2026-06-02)

Full list: `TODO.md`. Summary:

1. **Dataset Phonebook** — meta-crawlers for Kaggle/HF/Zenodo/data.gov/OpenAlex +
   specialty crawlers + standards corpus (IETF RFCs, W3C, PEPs, NIST, POSIX,
   Unicode, OASIS, HL7 FHIR, DICOM, ASOP, SAE, etc.) + verification crawler +
   phonebook APK browser + phonebook distribution via PTorrent itself.

2. **Full BitTorrent seeding** — libtorrent via Chaquopy on ARM64, DHT,
   multi-peer bin merge (β-weighted A-matrix union).

3. **Corpus & crawler** — NASA ADS, TAP/ADQL (VizieR/Gaia), Fortran parser,
   psi2 language geometry, full standards specifications corpus.

4. **Dataset traversal** — source adapter dispatch, output formats (FITS/HDF5/Parquet),
   model hooks (Anthropic API, OpenAI-compatible, MCP).

5. **APK features** — MCP server (Ktor, JSON-RPC 2.0), cloud sync, SD card,
   encrypted credentials, gradient progress bars.

6. **Platforms** — desktop CLI, PTorrent daemon, iOS evaluation.

---

## What's in bin_archive/

Git-ignored. On-disk only. Do not commit `.bin` files.

- `clean/` — GEOMETRIC INIT state (vocab + E-values built, word_count=0, no training)
- `dirty/` — post-training checkpoints, polluted bins, dated snapshots

Prefixes: `holcus_` = from PtolemyHolcus working dir, `phone_` = pulled from device,
`phone_20260601_` = phone snapshot 2026-06-01 (post-seeding, treat as dirty).

---

## PTorrent Chain Engine

`android/PtolemySeeder/app/src/main/python/ptorrent_chain.py` — stdlib only, Chaquopy-safe.

**7 transaction types:** `GENESIS`, `ANNOUNCE`, `UPDATE`, `RETIRE`, `SEED`, `UNSEED`, `MERGE`

**Key invariants:**
- `tx_hash` is recomputed on deserialisation and verified — any mismatch raises `ValueError`
- `UPDATE` always auto-stages a `RETIRE` first — never call them separately
- `commit()` mines pending transactions into a block (PoW difficulty=2, ~256 SHA-256 hashes avg)
- Chain file written atomically: `.tmp` → `os.replace()` — safe on Android
- `.ptorrent` files hashed via canonical JSON (keys sorted, no whitespace) — stable across reformatting
- `all_files()` returns only files whose current hash is NOT retired

**CLI:** `python ptorrent_chain.py [announce|update|seed|unseed|merge|seeders|latest|history|verify|hash|blocks|summary]`

**Env:** `PTORRENT_CHAIN=/path/to/chain.json` (default: `./ptorrent_chain.json`)

**Spec:** `spec/ptorrent-chain-v1.md`

---

## Gotchas

- **Do not commit bin files.** `.gitignore` covers `bin_archive/**/*.bin` but not
  bins dropped anywhere else in the tree — check before staging.

- **Chaquopy version pinning.** Chaquopy 15.0.1 + Python 3.12. Do not upgrade
  without testing the bridge — Chaquopy minor versions sometimes break the
  `__call__` interface used by the pause mechanism.

- **versionCode must be incremented manually** in `app/build.gradle` before every
  `adb install`. The user defines all version numbers — never auto-increment.

- **corpus_list.json** exists in two places: `android/corpus_list.json` (source)
  and `android/PtolemySeeder/app/src/main/assets/corpus_list.json` (APK asset).
  Keep them in sync. The APK asset is the one loaded at runtime.

- **MediaWiki fetcher** in `skills/corpus.py` routes Wikipedia/Wiktionary through
  the MediaWiki extracts API (`action=query&prop=extracts&explaintext=1`). This
  returns clean plaintext — do not revert to HTML parsing.

- **run_one() vs run_all()** in `seed_runner.py`: `run_one(entry, ...)` handles
  a single inbox PTorrent addition; `run_all(files_dir, on_progress, ...)` runs
  all corpora in parallel. The pause bridge wraps both.

- **The phonebook type** was added to the spec in v1.0.1 (2026-06-02). The APK
  does not yet implement a phonebook runner — it is specced but not built.

---

## ChangeLog — PTorrent Session History

### 2026-06-02 session 2 (Claude Code — claude-sonnet-4-6)

- Created PTorrent blockchain engine: `android/PtolemySeeder/app/src/main/python/ptorrent_chain.py`
  - 7 transaction types: GENESIS, ANNOUNCE, UPDATE, RETIRE, SEED, UNSEED, MERGE
  - Merkle tree over tx_hash values (binary, odd-duplicate, SHA-256)
  - Lightweight PoW (difficulty=2, ~256 hashes avg, ARM64-safe)
  - Full query API: get_seeders(), get_latest(), get_history(), get_by_hash(),
    is_retired(), all_files(), merge_chain(), is_valid_chain()
  - File hashing utilities: hash_file(), hash_ptorrent(), hash_bytes()
  - Atomic JSON persistence (tmp + os.replace)
  - CLI: announce/update/seed/unseed/merge/seeders/latest/history/verify/hash/blocks/summary
  - Stdlib only — Chaquopy 15.0.1 / Python 3.12 / ARM64 compatible
- Created chain specification: `spec/ptorrent-chain-v1.md`
  - Full data structure docs, Merkle algorithm, PoW algorithm, query semantics,
    file hashing rules, Android integration notes, CLI reference, future extensions
- Updated `wiki/claude_code_context_primer.md` with chain engine section

### 2026-06-02 session 1 (Claude Code — claude-sonnet-4-6)

- Centralized all PTorrent development into this repository (moved from PtolemyHolcus, DeriveCancerDrugs).
- Moved PtolemySeeder Android APK source → `android/PtolemySeeder/`.
- Moved all `.ptorrent` corpus descriptors → `ptorrents/`.
- Moved medical literature aggregator → `aggregators/medical/`.
- Moved and organized all monad bin files → `bin_archive/clean/` and `bin_archive/dirty/`.
- Adopted GNU project structure: `COPYING` (GPL-3.0), `AUTHORS`, `ChangeLog`, `INSTALL`, `NEWS`.
- Added `.ptorrent` format specification v1.0 → `spec/ptorrent-format-v1.md`.
- Added `phonebook` type to format spec (v1.0.1): `phonebook{}` object, `api{}`, `dumps[]`, `last_verified`.
- Added `trackers[]` field to format spec for future peer-seeded bin distribution.
- Reframed spec overview: PTorrent as accessible web crawler for non-coders.
- Added Dataset Phonebook as Priority #1 to `TODO.md`.
- Added full BitTorrent seeding (libtorrent, DHT, merge) to `TODO.md`.
- Added standards & specifications corpus section to `TODO.md` (IETF RFCs, W3C, ECMA, PEPs, NIST, POSIX, Unicode, OASIS, OGC, HL7 FHIR, DICOM, SAE, ASHRAE, ASOP, and more).
- Wrote `wiki/dataset_phonebook_seed_list.md` — 400+ datasets and 80+ standards manually catalogued across all disciplines with API/dump status.
- Embedded TODO as final README section "What's Being Built" (not linked — inline).
- Added dedication to README top: *Anyone who has ever had to both aggregate and then evaluate complex datasets...*
- Added Claude Code notation to README with link to this primer.
- Wrote this context primer.
- GitHub: GPL-3.0 license set on repo. All changes pushed to `main`.
- Repo state: `main` at `a8aeec7` (pre this commit).

### 2026-05-30 (Cody Michael Allison)

- PtolemySeeder APK v2.0 (versionCode 4).
- PTorrent file format defined — `.ptorrent` JSON descriptor.
- Corpus detail page with live URL-level status tracking.
- Transmission-style toolbar: ▶ Resume / ⏸ Pause / ✕ Clear Done / ＋ Add PTorrent.
- FileObserver inbox/ watcher for adb-push delivery path.
- `seed_runner.py` exports `run_one(entry, ...)` for inbox additions.
- Pause via `AtomicBoolean globalPaused` — URL-granular, no Python modification.
- Physics corpus (~130 URLs), Mathematics corpus (~130 URLs) added.
- Chaquopy 15.0.1, Python 3.12 embedded in APK.
- Two intent filters: `application/x-ptorrent`, `*.ptorrent` (content:// and file://).

### 2026-05-26 (Cody Michael Allison)

- PtolemySeeder APK v1.0 — initial release.
- Five corpora: Foundations, Meaning, Fermat, Python, C/POSIX.
- Parallel seeder architecture with Kotlin/Python bridge.
- SeedLiveData with URL pre-population before seeding begins.
- adb pull workflow for bin file retrieval.

### 2026-05-16 (Cody Michael Allison)

- PTorrent protocol concept established.
- `.ptorrent` format drafted — JSON corpus descriptor analogous to `.torrent`.
- Intent filters registered: `application/x-ptorrent`, `*.ptorrent`.
- Corpus manifest: `corpus_list.json`.

---

## How to Update This File

When making changes to PTorrent in a Claude Code session:

1. Add a new dated entry to the **ChangeLog** section above.
2. Update **Current APK Version** table if `versionCode` changes.
3. Update **Priority TODO** summary if `TODO.md` changes.
4. Add to **Gotchas** if a non-obvious invariant is discovered.
5. Update the `Last updated` date at the top of this file.

Keep entries factual and terse. This file is a technical briefing, not a narrative.
