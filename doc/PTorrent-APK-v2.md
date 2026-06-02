# Ptolemy Seeder — APK v2.0

**Release:** v2.0 — 2026-05-30  
**APK:** `android/PtolemySeeder/app/build/outputs/apk/debug/app-debug.apk`  
**versionCode:** 4  
**Corpora:** 7 (Physics + Mathematics added)

---

## What's New in v2.0

### PTorrent File Format

A `.ptorrent` file is a self-contained JSON descriptor for one corpus seeding job.
It is the distribution unit for new corpora — analogous to a `.torrent` file.

```json
{
  "name": "Quantum Field Theory",
  "bin":  "monad_qft.bin",
  "txt":  "qft_corpus.txt",
  "primary_tags": ["QFT", "SPECTRAL", "YANGMILLS"],
  "color": "cyan",
  "description": "One-sentence description of what this corpus teaches Holcus.",
  "urls": [
    { "tag": "QFT",      "url": "https://..." },
    { "tag": "SPECTRAL", "url": "https://..." }
  ]
}
```

The `urls` array is optional — if present it embeds all URLs directly (no separate `.txt` file needed).

#### Two delivery paths

**a) adb push to inbox/**
```bash
adb push quantum_field_theory.ptorrent \
  /sdcard/Android/data/com.ptolemy.seeder/files/inbox/
```
A `FileObserver` watches `inbox/` — the file is picked up automatically, added to
`corpus_list.json` on device, and the URL list is pre-populated in the UI.

**b) Tap to open**
`.ptorrent` files are registered in the manifest (`application/x-ptorrent`, `*.ptorrent`).
Tapping a `.ptorrent` file in any file manager opens the Seeder and queues it.

---

### Corpus Detail Page

Tap any corpus card → full-screen detail view:

| Section | Contents |
|---|---|
| **Header** | Name, status chip, description, primary tag chips, bin output path |
| **Stats** | Total URLs · Studied · Skipped · Success Rate (2×2 grid, live) |
| **URL List** | Every URL in the corpus with status icons — live updates as seeding runs |

URL status icons:
- `○` PENDING (dim)
- `▶` ACTIVE (gold, currently being fetched)
- `✓` STUDIED (green)
- `✗` SKIPPED (red, fetch failed or too short)

The URL list updates incrementally (only changed rows redrawn) — efficient for 130+ URL corpora.

---

### Transmission-Style Toolbar

The main screen now has a control bar above the corpus cards:

| Button | Action |
|---|---|
| `▶` | Resume all — clears global pause flag |
| `⏸` | Pause all — blocks Python fetch threads at URL boundary |
| `✕ Done` | Clear completed corpus cards from view |
| `＋ PTorrent` | System file picker — select a `.ptorrent` file to import |

Pause is implemented by blocking the Python `on_progress` callback inside the
Kotlin bridge — the Python `corpus.seed()` loop naturally holds at URL boundaries.

---

### Physics and Mathematics Corpora

Two new corpus entries (v1.1 code, shipped in v2.0 APK):

| Corpus | Color | URLs | Primary Tags |
|---|---|---|---|
| Physics | cyan | ~130 | WAVES, RESONANCE, QM, GR, COSMOLOGY, DARKMATTER, YANGMILLS, SPECTRAL |
| Mathematics | orange | ~130 | RIEMANN, PRIMES, SPECTRAL, MODULAR, CLAY, HARMONIC, NUMBERTHEORY |

Physics covers: wave mechanics, Schumann resonances, Chladni geometry, quantum mechanics (Berry-Keating, GUE), general relativity, cosmology/BAO, dark matter (SPARC-relevant), Yang-Mills/mass gap, Navier-Stokes, Feynman Lectures, LIGO, history.

Mathematics covers: prime number theory, Riemann zeta/hypothesis, random matrix theory/GUE, modular forms/L-functions/LMFDB, harmonic analysis/spherical harmonics, differential geometry/gauge theory, Lie groups/Leech lattice/Sedenion, functional analysis/Hilbert space, analytic number theory, Clay problems, DLMF special functions.

Checkpoints: `~/.ptolemy/monad_physics.bin` and `~/.ptolemy/monad_mathematics.bin`

---

## Corpus Colors

| Corpus | Color | Hex |
|---|---|---|
| Prime Directive I — Foundations | gold | `#C9A84C` |
| Prime Directive II — Meaning | blue | `#6EA8D4` |
| Prime Directive III — Fermat | red | `#B05050` |
| Python Language | green | `#6EAD7A` |
| C / POSIX | purple | `#9B7DC8` |
| Physics | cyan | `#4EC9C9` |
| Mathematics | orange | `#D4915A` |

---

## Installation

```bash
# Build
bash android/build_apk.sh

# Install
bash android/build_apk.sh --install

# Or manual
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

After seeding, pull results to the desktop machine:
```bash
adb pull /sdcard/Android/data/com.ptolemy.seeder/files/monad_physics.bin     ~/.ptolemy/
adb pull /sdcard/Android/data/com.ptolemy.seeder/files/monad_mathematics.bin ~/.ptolemy/
# ...and the other 5 bin files
```

---

## adb Workflow Reference

| Task | Command |
|---|---|
| Push updated corpus manifest | `adb push corpus_list.json /sdcard/Android/data/com.ptolemy.seeder/files/` |
| Add a new PTorrent | `adb push my.ptorrent /sdcard/Android/data/com.ptolemy.seeder/files/inbox/` |
| Pull all bin files | `adb pull /sdcard/Android/data/com.ptolemy.seeder/files/ ~/ptolemy_bins/` |
| Pause seeder | `adb shell am startservice -n com.ptolemy.seeder.debug/.SeedService --ea action pause` |

---

## Architecture Notes

- **Python bridge:** Chaquopy 15.0.1, Python 3.12 embedded in APK
- **Pause mechanism:** `AtomicBoolean globalPaused` checked inside the Kotlin `__call__` bridge method; blocks the Python thread at URL granularity — no Python-side modification required
- **FileObserver:** watches `extDir()/inbox/` for `.ptorrent` files via `CLOSE_WRITE | MOVED_TO`; API-level-safe (uses `File`-based constructor on API 29+, deprecated path-based on API 26–28)
- **URL pre-population:** SeedService parses all `.txt` corpus files at startup and posts `List<UrlState>` to `SeedLiveData.urlStates` before Python starts — detail pages show the full URL list immediately
- **seed_runner.py:** now exports `run_one(entry, ...)` for single-corpus seeding of PTorrent inbox additions

---

## Version History

| Version | versionCode | Date | Description |
|---|---|---|---|
| 1.0 | 1 | 2026-05-26 | Initial release — 5 corpora, parallel seeder |
| 1.1 | 3 | 2026-05-30 | Physics + Mathematics corpora added |
| 2.0 | 4 | 2026-05-30 | PTorrent format, detail page, transmission toolbar, pause/resume |
