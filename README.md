# PTorrent

> *Anyone who has ever had to both aggregate and then evaluate complex datasets...*
> *This is my present to knowledge acquisition for You All.*

**A protocol and a portable core for finding, fetching, evaluating in situ, and
seeding research datasets — without a tracker, a gradient server, or a central
coordinator of any kind.**

Inspired by BitTorrent (Cohen, 2003). Licensed **LGPL-3.0-or-later** — the core
is a library meant to be embedded in front-ends on every platform, so the weaker
copyleft is deliberate.

*Code compiled and built by [Claude Code](https://claude.ai/code).*

---

## What PTorrent does

A `.ptorrent` file is a declarative job written in plain JSON. Four verbs:

| Verb | `.ptorrent` type | What happens |
|------|------------------|--------------|
| **find** | `phonebook` | records *where a dataset lives* — canonical URL, API, bulk-dump location, license, verification date. Every `add()` of any job also checks its dataset into the phonebook automatically. |
| **fetch** | `corpus` / `dataset` | an api-first, robots-compliant crawl (`declared_api → known_api → sitemap → feed → html`) writes artifacts locally. |
| **evaluate in situ** | `evaluation` | a researcher-defined J-ratio reduction runs against each record as it streams past; the bytes are fetched, reduced, and discarded. Output is a `.peval`. Walk 5 000 images at an API's rate limit without ever storing the 196 GB. |
| **seed** | any | a device that holds an artifact can announce and serve it peer-to-peer. |

Every one of those actions is a transaction on a hash-linked **chain of
custody** — ORCID-attributed, append-only, exportable to CASE/UCO, STIX 2.1, and
AFF4.

---

## Architecture — two cores, many faces

```
                       ┌──────────────── core/c/libptorrent ─────────────────┐
   the inner core:     │  .ptorrent parse + validate   j_expr compile+eval   │
   ABI-stable, no I/O   │  σ-face classify + tally      dependency-free JSON  │
                       │  [TAG] URL list — cursor / dedup                    │
                       └───────────────────────┬────────────────────────────┘
                                               │  (ctypes, or the pure-Python
                                               │   fallbacks in core/python)
                       ┌───────────────────────┴────────────────────────────┐
   the runtime core:    │              core/python/ptorrent_core             │
   the I/O + orchestr.  │  robots-compliant api-first crawler + scheduler    │
                       │  network gate · BinaryArtifactStore · .peval       │
                       │  phonebook (sqlite) · ORCID identity + access gate │
                       │  thumbs voting · hash-linked custody chain         │
                       │  ─────────────── Engine surface ────────────────   │
                       │  snapshot() · events(since_seq) · command verbs    │
                       │            ≡  schema/v1.json (co-equal)            │
                       └───────────────────────┬────────────────────────────┘
                                               │  in-process, or JSON-RPC over ptorrentd
                    ┌──────────┬───────────┬────┴─────┬───────────┬──────────┐
                  curses     Android      iOS       .NET       browser    …
                 (console)    (APK)     (SwiftUI)  (WinUI)      (web)
```

**The core has no GUI.** Every front-end is a *face* over the `Engine` surface
and lives in its own release directory; their docs are linked here as children
later. Nothing below `Engine` knows a face exists.

The C core obeys the hardest target (iOS): C ABI only, opaque handles, no
struct-by-value across the boundary, no callbacks into the caller (progress is
polled), the core never owns the process, no ambient paths. Obeying iOS makes it
embeddable in an Android Service, a Windows service, a .NET GUI, and a
`select()` loop without changing a line. The desktop console and the C core will
each build against the platform's **native curses** (ncurses, PDCurses, …).

---

## Repository layout

```
PTorrent/
├── COPYING  COPYING.LESSER        LGPL-3.0 (GPL-3.0 base + Lesser additional terms)
├── README.md  AUTHORS  ChangeLog  NEWS  INSTALL
│
├── core/
│   ├── c/                         libptorrent — the ABI-stable inner core (C99, no deps)
│   │   ├── include/ptorrent.h     the entire public surface
│   │   ├── src/  tests/  Makefile
│   └── python/                    ptorrent_core — the runtime core (stdlib only, py≥3.11)
│       ├── ptorrent_core/         24 modules — see core/python/README.md
│       ├── ptorrent_core/schema/v1.json   the co-equal API contract
│       └── tests/
│
├── spec/
│   ├── ptorrent-format-v1.md      v1.0 / v1.1 (historical)
│   ├── ptorrent-format-v1.2.md    current — crawl · distribution · security.labels · reductions
│   ├── ptorrent-chain-v1.md       custody chain transaction spec
│   └── evaluation.ptorrent.template
│
├── ptorrents/                     example .ptorrent descriptors
├── peval/                         example .peval evaluation outputs
├── aggregators/medical/           standalone PubMed / ClinicalTrials aggregator
├── wiki/                          Core-Architecture, RDOP, Security-Classification, …
│
└── releases/                     (added later) one directory per face
    ├── curses/   android/   ios/   windows/   web/
```

---

## The `.ptorrent` format

A UTF-8 JSON object. Minimal corpus job:

```json
{
  "ptorrent_version": "1.2",
  "type": "corpus",
  "name": "Wave mechanics",
  "bin": "monad_waves.bin",
  "primary_tags": ["PHYSICS"],
  "color": "cyan",
  "description": "Wave equation, resonance, standing waves.",
  "crawl": {
    "seeds": [ { "tag": "WAVES", "url": "https://en.wikipedia.org/wiki/Wave_equation" } ]
  }
}
```

The full field reference — `crawl`, `distribution`, `security.labels`,
`evaluation` reductions, the J-ratio priority order, and the σ-face table — is
**[`spec/ptorrent-format-v1.2.md`](spec/ptorrent-format-v1.2.md)**. Design
principle unchanged: *modify, don't write from scratch.* Copy an existing file,
change the name, swap the URLs.

---

## Using the core

```python
from ptorrent_core import Engine

e = Engine("~/.ptorrent")                        # the host injects every filesystem root
r = e.add("physics.ptorrent", start=True)        # → {job_id, phonebook_key, quarantine, preflight}

while True:
    snap = e.snapshot()                          # jobs · phonebook · chain · identity
    for ev in e.events(since=seq): ...            # durable, replayable by monotonic seq
```

The same verb names are the JSON-RPC methods `ptorrentd` will expose
(`schema/v1.json`). Module map and the full surface: **[`core/python/README.md`](core/python/README.md)**.

Build the C core:

```sh
cd core/c && make            # static + shared + tests, no deps beyond a C99 compiler
```

---

## Curses GUI

The first face. Native `curses` (ncurses / PDCurses / the platform's own),
stdlib + the core, no other dependencies. Legacy‑BIOS layout — a field ladder on
the left, an *Item Specific Help* panel on the right that grows past ~170 columns
and collapses under 90. All geometry is a percentage of the terminal, so a
maximised window and an 80×24 one lay out from the same numbers. Every on‑screen
string is Unicode so maths reads on one line (`√(pmra² + pmdec²) / max(parallax,
0.001)`, `d⋆ ≤ J < 1`, `Σ|∇I| / Σ I`).

```sh
python3 -m ptorrent_gui [--engine DIR] [--out DIR] [--wizard]
```

Full skin docs: **[`releases/curses/README.md`](releases/curses/README.md)**.

### The shell

```
┌ File ─┬ Settings ─┬ Help ───────────────────────────────────────────────────┐
│                                                                             │
│  ┌ PTorrent ───────────────────────────────────────────────────────────┐    │
│  │                                                                     │    │
│  │   No job open.                                                      │    │
│  │                                                                     │    │
│  │   File ▸ New   —  build a .ptorrent through the four-tab wizard      │    │
│  │   File ▸ Open  —  preview an existing .ptorrent                      │    │
│  │                                                                     │    │
│  │   engine: attached  (~/.ptorrent)                                   │    │
│  │                                                                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│ F1 menu   n new   o open   p preferences   q quit                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

`F1` opens the menu bar; `n` / `o` / `p` are direct hot‑keys. When launched with
`--engine`, the shell polls `snapshot()` / `events()` on the configured interval
and evaluates the section alarms (below).

### File ▸ New — the .ptorrent wizard

Rufus‑style: every option on screen, laddered, split across four tabs —
**Dataset · Crawler options · Cybersecurity · User information**.

```
┌ PTorrent — new .ptorrent ─────────────────────────────────────────────────────┐
│  1 Dataset   2 Crawler options   3 Cybersecurity   4 User information         │
├──────────────────────────────────────────┬───────────────────────────────────┤
│ Crawler options                          │ Item Specific Help                │
│  Resolution ladder ...:  ▸[×]declared_api │ Order tried per seed. Space        │
│                          [×]known_api     │ toggles a rung; the enabled set   │
│                          [ ]sitemap …     │ is tried left → right. 'api first' │
│  Follow links .........: ‹ none ›         │ = keep declared_api / known_api    │
│  Max pages ............: 500              │ on top.                           │
│  User-Agent ...........: Mozilla/5.0 (com…│                                   │
│  ── In-situ evaluation ──                 │ This reduction:                   │
│  Enable in-situ evaluat: [×] yes          │  Σ|∇I| / Σ I — total local        │
│  Algorithm / code block: ‹ img_entropy_r… │  contrast normalised by brightness│
│  fn params ...........: bins=64           │                                   │
│  Max records .........: 5000              │ d⋆ = 0.246   Ω_ZS = 0.56714…      │
│  Methodology .........: texture density   │ σ-face bands (J):                 │
│                                           │   d⋆ ≤ J < 1        ½  causality  │
│                                           │   1 ≤ J < 1/d⋆      1  Yang–Mills │
│                                           │   J ≥ 1/d⋆ + Ω_ZS   ∞  force ext. │
├──────────────────────────────────────────┴───────────────────────────────────┤
│ F8 check   F9 preview   F10 build   Tab section   t tooltips   ▲ 1 warning F8 │
└─────────────────────────────────────────────────────────────────────────────┘
```

The **Cybersecurity** tab self‑identifies what the data is; the answers derive
`classification` / `level` / `TLP` / `security.labels` live (shown in the
sidebar), re‑derived authoritatively by the core on `add()`. It also carries the
**auth‑provenance** table that ties each sensitive source to how it is
authenticated:

```
│ This data / its output …: ▸[×]crypto_exploitable  [ ]exploit_code  [ ]…       │
│ Attacker could build a w: [×] yes                                            │
│ Derived classification                                                      │  ← sidebar:
│ TLP marking (override) .: ‹  ›                                               │  dual-use · level 3 ·
│ Embargo until (YYYY-MM-D: 2027-06-03                                         │  TLP:AMBER+STRICT ·
│ Contact ORCID .........: 0000-0002-1825-0097                                 │  crypto-attack-vector
│ ── Auth provenance bindings ──                                               │
│ Source → provenance ...: [2 row(s)]  (↵ to edit)                            │
│      s3://stpubdata/         institutional   MAST                            │
│      /media/…/Datasets/      orcid-session                                   │
```

### Faults — handled, never fatal

A malformed field, a contradictory choice, an unparseable `j_expr`, a
`.ptorrent` that will not validate — none of it crashes the wizard. `F8` checks
on demand; `F10` checks first and **errors block the write, warnings do not**:

```
┌ ✖ .ptorrent faults — cannot build ──────────────────────────────────────────┐
│ ✖ [Dataset]        name           job name is empty                         │
│ ✖ [Cybersecurity]  embargo_until  Level-3 dual-use requires an embargo date  │
│ ▲ [Crawler]        j_expr_cols    j_expr uses columns not in j_expr_cols: c  │
│ ▲ [Dataset]        seeds          seed 0 URL has no http(s):// scheme        │
│                                                                             │
│ → YYYY-MM-DD                                                                 │
│ ↑↓ select fault    errors block the build — fix them                        │
│            [ Fix selected ]   [ Dismiss ]                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

*Fix selected* jumps straight to the offending tab and field. Each bad row also
carries a `✖` / `▲` marker; in **tooltip mode** (`t`) the field's faults appear
in a popup anchored to it:

```
  j_expr .............: a / c   ⟶  a / c                                       │
                       ┌──────────────────────────────────────────┐            │
                       │ safe arithmetic over column names        │            │
                       │ functions: sqrt abs log log10 exp max min│            │
                       │ ▲ j_expr uses columns not in j_expr_cols │            │
                       └──────────────────────────────────────────┘            │
```

### Settings ▸ Preferences

`Settings ▸ Preferences` (or `p`) opens every user‑adjustable console setting.
Text boxes, on/off toggles, and `‹cycle›` choices (radio‑equivalent) as
appropriate. Persisted to `~/.config/ptorrent/gui.json`.

```
┌ PTorrent — Settings ─────────────────────────────────────────────────────────┐
├──────────────────────────────────────────┬───────────────────────────────────┤
│ Preferences                              │ Item Specific Help                │
│  ── Notifications ──                     │ bell: terminal \a.  desktop:      │
│  Enable notifications .: [×] yes          │ notify-send / kdialog popup.      │
│  Channel .............: ‹ bell ›          │ both: ring and pop. off: neither  │
│  · on job complete ...: [×] yes           │ (status line only).               │
│  · on job error .....: [×] yes            │                                   │
│  · on embargo lifted .: [×] yes           │                                   │
│  · on access request .: [×] yes           │                                   │
│  · on grant received .: [×] yes           │                                   │
│  · on vote received ..: [ ] no            │                                   │
│  · on phonebook stale : [ ] no            │                                   │
│  ── Section alarms (heartbeats) ──        │                                   │
│  Alarm rules .........: [1 rule(s)] (↵)   │                                   │
│  ── Display ──                            │                                   │
│  Theme ...............: ‹ bios-blue ›     │                                   │
│  Help sidebar ........: ‹ auto ›          │                                   │
│  Tooltips on by defaul: [ ] no            │                                   │
│  Confirm on quit .....: [×] yes           │                                   │
│  Unicode glyphs ......: ‹ auto ›          │                                   │
│  ── Defaults for new .ptorrent ──         │                                   │
│  Politeness delay (s) : 1.0               │                                   │
│  User-Agent ..........: Mozilla/5.0 (com… │                                   │
│  ── Paths ──                              │                                   │
│  Output directory ....: .                 │                                   │
│  Engine root .........: ~/.ptorrent       │                                   │
│  Poll interval (s) ...: 1.0               │                                   │
│  [ Reset all to defaults ]                │                                   │
├──────────────────────────────────────────┴───────────────────────────────────┤
│ ↑↓ move   ←→/↵ change   F10 save   Esc back                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Section alarms (heartbeats)

User‑defined periodic / conditional alerts, evaluated against the live
`snapshot()` while the shell is attached to an engine. The shipped rule
**still‑alive ping** dings once every 3 hours for as long as any job is
`RUNNING` — so a 12‑day download keeps reminding you it is still going. `↵` on
*Alarm rules* opens the rule editor:

```
┌ Section alarms   a add · d delete · ↵ edit · Esc back ──────────────────────┐
│ name                on   when                     every     action         │
│ still-alive ping     yes  periodic_while_running   3h        bell           │
│ 12-day crawl watch   yes  job_running_longer_than  6h        desktop        │
│ error storm          yes  error_count_over         30m       desktop        │
└────────────────────────────────────────────────────────────────────────────┘

┌ alarm: still-alive ping   ↵ edit · Esc done ───────────────────────────────┐
│ name            : still-alive ping                                         │
│ enabled         : [×] yes                                                  │
│ when            : ‹ periodic_while_running ›                               │
│ every n         : 3                                                        │
│ every unit      : ‹ hours ›                                                │
│ threshold n     : 1                                                        │
│ threshold unit  : ‹ hours ›                                                │
│ error count     : 5                                                        │
│ scope           : ‹ any_job ›     (any_job | each_job)                     │
│ action          : ‹ bell ›        (bell | desktop | status)                │
│ repeat          : [×] yes                                                  │
│ when → ding every <interval> for as long as any/each job is RUNNING        │
└────────────────────────────────────────────────────────────────────────────┘
```

`when` conditions: `periodic_while_running` · `job_running_longer_than` ·
`job_idle_for` (progress not advancing) · `error_count_over` · `all_done`.
`action` is `bell` (terminal `\a`), `desktop` (`notify-send` / `kdialog`), or
`status` (status‑line only). `scope` fires for `any_job` or `each_job`.

### Keys

`F1` menu · `n` new · `o` open · `p` preferences · `q` quit. In the wizard:
`Tab` / `1`–`4` section · `↑↓` fields · `←→` change · `↵` edit · `Space` toggle ·
`s` sidebar · `t` tooltips · `F8` check · `F9` preview · `F10` build & save ·
`Esc` back.

---

## Dataset Phonebook

A dynamically-current, cross-disciplinary index of *where* public datasets live —
not the data. One `.ptorrent` of type `phonebook` per dataset, machine-readable,
community-maintained, verified on a schedule. It is populated three ways:

1. the manual seed catalogue — `wiki/dataset_phonebook_seed_list.md`, 400+ entries;
2. meta-crawlers (Kaggle, HuggingFace, Zenodo, Figshare, data.gov, OpenAlex, …);
3. **automatically** — every `add()` of any job checks its dataset into the
   library (the "Alexandrian" intake). A peer that syncs the custody chain
   rebuilds the whole phonebook.

Advertising *yourself* as a live seed source for an entry is opt-in
(`distribution.seed_listing`, default `off`).

---

## Responsible Disclosure Open Protocol (RDOP)

PTorrent carries a formally-specified protocol for coordinated disclosure of
security findings made during research. The `.ptorrent` `security` block plus its
`labels` sub-block normalise **TLP 2.0**, **STIX 2.1 data markings**, **CSAF**,
**MITRE CWE / CAPEC / ATLAS**, and **CVSS / EPSS / SSVC** into one marking that
rides every custody transaction and cannot be silently downgraded.

- `CLASSIFY / NOTIFY / ACKNOWLEDGE / DISCLOSE` transaction sequence, ORCID-attributed
- STIX 2.1 bundle auto-generated; TAXII 2.1 submission to CISA AIS
- `embargo_until` enforced in `preflight` as a hard block — surfaced as `E_EMBARGO`
- the "create new `.ptorrent`" wizard's cybersecurity step maps a researcher's
  self-identification to `classification` / `level` / `labels`, re-checked
  authoritatively by the core

See [`wiki/Responsible-Disclosure-Protocol.md`](wiki/Responsible-Disclosure-Protocol.md),
[`wiki/Security-Classification.md`](wiki/Security-Classification.md),
[`wiki/Agency-Interface.md`](wiki/Agency-Interface.md).

**We invite NIST and CISA to evaluate PTorrent as a machine-readable,
ORCID-verified, provenance-tracked researcher disclosure intake channel.**

---

## Contributing

The bar is low and the scope is narrow.

- **C:** the network gate, `Range:` resume, the `.peval` writer, more `tests/`
- **Python:** meta-crawlers under a future `crawlers/`, `known_apis.json` entries,
  evaluation `fn` reductions, the `ptorrentd` JSON-RPC transport, adapters
  (FITS / HDF5 / TAP)
- **Protocol:** `.ptorrent` signing and checksums, a lightweight discovery tracker
- **Curation:** new `phonebook` `.ptorrent` descriptors — simple JSON, lint-checked

Fork, branch, add your name to `AUTHORS`, open a PR describing what and why. All
contributions stay LGPL-3.0-or-later; original attribution is preserved.
*Original code goes with style.*

**Contact:** Cody Michael Allison — <the.wandering.god@gmail.com>

---

## Related projects

| Project | Description |
|---------|-------------|
| [VAPMIP](https://github.com/michaelrendier/VAPMIP) | Ptolemy LSHS engine — the primary consumer of PTorrent bin files |
| [Ainulindale](https://github.com/michaelrendier/Ainulindale) | The mathematical framework (σ-face constants d*, Ω_ZS) |
| [ValaQuenta](https://github.com/michaelrendier/ValaQuenta) | Derivation engine — mathematics, physics, cosmology |

---

## License

PTorrent is free software: you can redistribute it and/or modify it under the
terms of the **GNU Lesser General Public License** as published by the Free
Software Foundation, version 3 of the License, or (at your option) any later
version.

Distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY. See
`COPYING` (GPL-3.0 base) and `COPYING.LESSER` (Lesser additional permissions),
or <https://www.gnu.org/licenses/lgpl-3.0.html>.

**Original author:** Cody Michael Allison <the.wandering.god@gmail.com>
**Original code goes with style.** Attribution is non-negotiable.

---

## References

- Cohen, B. (2003). *Incentives Build Robustness in BitTorrent.* — structural ancestor.
- McMahan et al. (2017). *Communication-Efficient Learning of Deep Networks from
  Decentralized Data.* AISTATS — the federated-learning paradigm PTorrent supersedes.
- Li et al. (2014). *Scaling Distributed Machine Learning with the Parameter Server.*
  OSDI — the architecture PTorrent replaces.
- FIRST. *Traffic Light Protocol (TLP) 2.0.* — the handling label carried in `security.labels`.
- OASIS. *STIX 2.1*, *CSAF 2.0.* — data markings and machine-readable advisories.
- MITRE. *ATLAS* — adversarial-ML taxonomy for poisoned / adversarial datasets.
- LMFDB Collaboration (2024); Baker et al. (2000) — sources of shipped example descriptors.
