# PTorrent Changelog

## v4.0 — 2026-06-03

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

## v3.0 — 2026-05-31

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

## v2.0 — 2026-05-19 (PtolemyHolcus release)

- Initial sedenion corpus seeder APK
- Chaquopy Python runtime (3.12)
- Eight corpus types defined in corpus_list.json
- Prime Directive I, II, III seeding
