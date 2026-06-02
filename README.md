# PTorrent

**A corpus distribution protocol for on-device knowledge seeding.**  
Inspired by BitTorrent. Built for Android. Licensed under GNU GPL v3.

---

PTorrent is an open protocol for distributing *knowledge corpus jobs* across
Android devices — without a tracker, without a gradient server, without a
central coordinator of any kind.

A `.ptorrent` file describes a corpus seeding job: what to fetch, how to tag
it, and where to save the checkpoint. The PtolemySeeder APK picks up the job,
traverses the URL list on-device, and builds a checkpoint binary. Ten phones
seed ten corpora in parallel. You pull the bins back to your desktop when done.

The structural ancestor is Bram Cohen's BitTorrent (2003). The paradigm it
supersedes is the parameter server (Li et al., 2014) — PTorrent does not
aggregate gradients; it distributes the *work*, and the data never leaves
the device.

---

## Why PTorrent?

Standard corpus-building pipelines assume a server with a fast connection and
abundant RAM. PTorrent assumes the opposite: many small devices, a slow
connection, and overnight time. It turns a fleet of Android phones into a
distributed corpus seeder — each device independently walking a URL list and
writing a local checkpoint, with no peer-to-peer coordination required.

The protocol came out of building the Ptolemy Lagrangian Self-Adjoint
Hyperindexing Speaking Model (LSHS) — a compression-ignition semantic engine
grounded in the Ainulindale Conjecture. Seven corpora, 1,000+ URLs, seeded
across a phone fleet while the desktop ran other work. PTorrent was the
obvious solution once the problem was clear.

---

## Repository Layout (GNU Standard)

```
PTorrent/
├── COPYING                    GPL-3.0 license
├── README.md                  This file
├── AUTHORS                    Original author and contributor list
├── ChangeLog                  Full change history
├── INSTALL                    Build and installation guide
├── NEWS                       What's new in each release
├── .gitignore
│
├── android/                   Android implementation
│   ├── PtolemySeeder/         Full Android Studio project (Kotlin + Python)
│   ├── corpus_list.json       Corpus manifest (loaded by SeedService on startup)
│   └── build_apk.sh           Build and install helper script
│
├── ptorrents/                 PTorrent descriptor files (.ptorrent JSON)
│   ├── foundations.ptorrent   Prime Directive I — axioms (gold)
│   ├── meaning.ptorrent       Prime Directive II — semantic attractor (blue)
│   ├── fermat.ptorrent        Prime Directive III — Fermat/war lineage (red)
│   ├── python.ptorrent        Python language specification (green)
│   ├── c_posix.ptorrent       C / POSIX specification (purple)
│   ├── physics.ptorrent       Wave mechanics, QM, GR, cosmology (cyan)
│   ├── mathematics.ptorrent   Riemann, primes, spectral, Clay (orange)
│   ├── english_complete.ptorrent  Full English language corpus (silver)
│   ├── riemann_zeros.ptorrent Riemann zeros dataset from LMFDB
│   └── framenet.ptorrent      Berkeley FrameNet 1.7 (1,221 semantic frames)
│
├── aggregators/
│   └── medical/               Medical literature aggregator (PubMed / ClinicalTrials)
│       └── scholar_aggregator.py
│
├── spec/                      Protocol specification
│   └── ptorrent-format-v1.md  .ptorrent file format (fields, types, examples)
│
├── doc/                       Documentation
│   └── PTorrent-APK-v2.md     PtolemySeeder APK v2.0 full reference
│
├── tests/                     Test harness (contributions welcome)
│
└── bin_archive/               Monad checkpoint binaries (git-ignored, disk only)
    ├── README.md              What these files are and how to use them
    ├── clean/                 GEOMETRIC INIT — vocabulary only, no training
    └── dirty/                 Post-training or polluted checkpoints
```

---

## The .ptorrent Format

A `.ptorrent` file is a UTF-8 JSON document. Minimal example:

```json
{
  "ptorrent_version": "1.0",
  "type": "corpus",
  "name": "Quantum Field Theory",
  "bin": "monad_qft.bin",
  "primary_tags": ["QFT", "YANGMILLS", "SPECTRAL"],
  "color": "cyan",
  "description": "QFT vocabulary for H_RB Yang-Mills projection.",
  "urls": [
    { "tag": "QFT",       "url": "https://..." },
    { "tag": "YANGMILLS", "url": "https://..." }
  ]
}
```

The full field reference is in [`spec/ptorrent-format-v1.md`](spec/ptorrent-format-v1.md).

---

## PtolemySeeder APK

**Technology stack:** Kotlin (UI, SeedService) + Python 3.12 (seeding engine)  
**Python bridge:** Chaquopy 15.0.1  
**Min SDK:** API 26 (Android 8.0)  
**Current version:** 2.0 (versionCode 4), released 2026-05-30

### Build

```bash
cd android
bash build_apk.sh         # build only
bash build_apk.sh --install   # build + adb install
```

### Deliver a corpus to a device

```bash
# Option 1: inbox push (picked up automatically by FileObserver)
adb push ptorrents/physics.ptorrent \
  /sdcard/Android/data/com.ptolemy.seeder/files/inbox/

# Option 2: transfer to device, tap in file manager
```

### Pull checkpoint bins after seeding

```bash
adb pull /sdcard/Android/data/com.ptolemy.seeder/files/monad_physics.bin .
adb pull /sdcard/Android/data/com.ptolemy.seeder/files/monad_mathematics.bin .
```

The full workflow is documented in [`doc/PTorrent-APK-v2.md`](doc/PTorrent-APK-v2.md).

---

## Architecture

```
.ptorrent file
      │
      ▼
 PtolemySeeder APK (Android)
  ├── SeedService.kt      FileObserver inbox/ watcher, corpus list management
  ├── MainActivity.kt     Transmission-style UI: ▶ ⏸ ✕ ＋
  ├── CorpusDetailActivity.kt  Live URL-status detail page
  └── seed_runner.py      Python seeding engine (Chaquopy bridge)
       └── skills/        Per-corpus seeding logic
            ├── corpus.py          GenericCorpus — MediaWiki-aware fetcher
            ├── corpus_physics.py
            ├── corpus_mathematics.py
            ├── corpus_python.py
            ├── corpus_c.py
            ├── foundations.py
            ├── meaning.py
            └── fermat_lattice.py
      │
      ▼
 monad_<name>.bin         Checkpoint binary (Python pickle, v1.218+)
      │
      ▼
 adb pull → desktop
```

**Pause mechanism:** `AtomicBoolean globalPaused` in Kotlin; checked inside the
`__call__` bridge. The Python thread blocks at URL boundaries — no Python
modification required.

**URL pre-population:** SeedService parses all corpus `.txt` files at startup
and posts `List<UrlState>` to `SeedLiveData` before Python starts. The detail
page shows the full URL list immediately, even before seeding begins.

---

## Contributing — Open to All

PTorrent is a young protocol with a clear, narrow scope. There is genuine work
to do, and the bar to contribute is low.

**If you write Kotlin or Android:**
- Clean up the FileObserver API-level branching (API 26–28 vs 29+)
- Add per-corpus pause/resume (currently global only)
- Add a proper progress bar to the corpus cards
- Write instrumented tests for the SeedService and seed_runner bridge

**If you write Python:**
- Add new aggregators under `aggregators/` (legal, physics preprints, patent
  databases, language corpora)
- Improve the MediaWiki fetcher in `skills/corpus.py` (rate-limiting, retries)
- Write the test harness in `tests/`
- Port the medical aggregator to use the NCBI E-utilities rate-limit correctly

**If you work in protocol design:**
- The `.ptorrent` format is v1.0. There is no signing, no checksum, no
  capability negotiation. These are known gaps.
- A lightweight tracker (even a static JSON file served over HTTPS) would
  enable corpus discovery without hardcoded URL lists.

**If you work in data curation:**
- New `.ptorrent` descriptors for open datasets are always welcome
- The format spec is in `spec/ptorrent-format-v1.md` — it's simple JSON

**How to contribute:**
1. Fork this repository.
2. Create a branch: `git checkout -b feature/your-thing`.
3. Add your name to `AUTHORS`.
4. Submit a pull request with a description of what you built and why.

All contributions are welcome regardless of experience level. The only
requirement is that contributions remain under GPL-3.0 and that original
author attribution is preserved. New code goes in with your name on it.
*Original code goes with style.*

If you're working on something adjacent — a different corpus format, a
different seeding architecture, a compatible Android app — reach out.
Collaboration is always better than parallel reinvention.

**Contact:** Cody Michael Allison — <the.wandering.god@gmail.com>

---

## Medical Literature Aggregator

`aggregators/medical/scholar_aggregator.py` is a standalone PubMed /
ClinicalTrials.gov aggregator built for cancer drug discovery research.
It searches 41 priority terms covering superoxide reductase, EIIP resonance,
glioblastoma / BBB delivery, and control molecules (naloxone, aspirin,
amphotericin-B). Output is JSON tagged with Ainulindale cancer-framework
concepts.

This aggregator is part of the DeriveCancerDrugs project — a separate line
of research using the Ainulindale algebraic framework to target cancer drugs
from cancer's own zero-divisor signature. See the Erika Schafer collaboration
notes in the parent project.

Running it requires only `requests`. Set `NCBI_API_KEY` for higher rate limits.

---

## Related Projects

| Project | Description |
|---------|-------------|
| [PtolemyHolcus](https://github.com/michaelrendier/PtolemyHolcus) | Ptolemy LSHS desktop engine — the primary consumer of PTorrent bin files |
| [Ainulindale](https://github.com/michaelrendier/Ainulindale) | Ainulindale Conjecture research — the mathematical framework |
| [ArdaQuenta](https://github.com/michaelrendier/ArdaQuenta) | Standalone engine implementation |
| [ValaQuenta](https://github.com/michaelrendier/ValaQuenta) | Physics and cosmology modules |

---

## License

PTorrent is free software: you can redistribute it and/or modify it under the
terms of the GNU General Public License as published by the Free Software
Foundation, version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the COPYING file for the full license text, or
visit <https://www.gnu.org/licenses/>.

**Original author:** Cody Michael Allison <the.wandering.god@gmail.com>  
**Original code goes with style.** Attribution is non-negotiable.

---

## References

- Cohen, B. (2003). *Incentives Build Robustness in BitTorrent.* Workshop on
  Economics of Peer-to-Peer Systems. Structural ancestor of PTorrent.
- McMahan et al. (2017). *Communication-Efficient Learning of Deep Networks
  from Decentralized Data.* AISTATS. The federated-learning paradigm PTorrent
  supersedes (no server, no gradient, no central aggregation).
- Li et al. (2014). *Scaling Distributed Machine Learning with the Parameter
  Server.* OSDI. The parameter-server architecture PTorrent replaces.
- LMFDB Collaboration (2024). *The L-functions and Modular Forms Database.*
  <https://www.lmfdb.org/> — source of the `riemann_zeros.ptorrent` dataset.
- Baker et al. (2000). *The Berkeley FrameNet Project.* — source of the
  `framenet.ptorrent` semantic frame dataset.
