# PTorrent Format Specification — v1.0

**Author:** Cody Michael Allison  
**Status:** Stable  
**MIME type:** `application/x-ptorrent`  
**File extension:** `.ptorrent`

---

## Overview

A `.ptorrent` file is a UTF-8 JSON document that fully describes one corpus
seeding job. It is the distribution unit of the PTorrent protocol — analogous
to a `.torrent` file in BitTorrent, but purpose-built for knowledge corpus
distribution across Android devices running the PtolemySeeder APK.

Unlike BitTorrent, PTorrent has no tracker, no DHT, no peer exchange, and no
block-level checksumming. The "torrent" is a description of *what to fetch
from the open web*, not a description of pieces held by peers. PTorrent
distributes the *job*, not the *data* — each device independently traverses
the URL list and builds its own checkpoint binary.

---

## Root Object Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ptorrent_version` | string | yes | Format version. Currently `"1.0"`. |
| `type` | string | yes | Job type. See Types below. |
| `name` | string | yes | Human-readable corpus name. |
| `bin` | string | yes* | Output checkpoint filename (e.g. `monad_physics.bin`). Required unless `type` is `"dataset"`. |
| `txt` | string | no | Corpus URL list filename. Optional if `urls` is embedded. |
| `requires_bin` | string | no | Bin file that must be loaded before seeding begins. Used for transfer-learning chains. |
| `primary_tags` | string[] | yes | Semantic domain tags. Used for corpus card display and monad weighting. |
| `primary_weight` | float | no | Weight multiplier for primary-tagged words (default 1.0). |
| `context_weight` | float | no | Weight multiplier for context words (default 1.0). |
| `color` | string | yes | Card accent color name. See Color Table. |
| `description` | string | yes | One-sentence description of what this corpus teaches. |
| `ua` | string | no | User-agent hint for HTTP requests. Default `"ptolemy"`. |
| `urls` | object[] | no | Embedded URL list. If present, no `.txt` file is needed. |
| `source` | object | no | External data source descriptor (REST, NLTK, stream). |
| `test` | string | no | Name of test function to run after seeding. |
| `test_params` | object | no | Parameters passed to the test function. |
| `output` | string | no | Output JSON filename for dataset jobs. |
| `output_format` | string | no | Output format: `"json"`. |
| `output_top_n` | int | no | Limit output to top N results. |
| `checkpoint_every` | int | no | Save checkpoint every N URLs (default 10). |
| `model_hook` | string | null | Reserved for future model hook integration. |

---

## Types

| Type | Description |
|------|-------------|
| `corpus` | Standard corpus job — fetches URLs and seeds a monad checkpoint. |
| `dataset` | Data retrieval job — fetches structured data from a source API. |
| `transfer` | Transfer-learning job — loads `requires_bin` then continues seeding. |

---

## `urls` Array

Each element of the embedded URL list:

```json
{
  "tag":  "WAVES",
  "url":  "https://example.com/wave-mechanics"
}
```

`tag` must be one of the values in `primary_tags` or a sub-tag. Used to
categorize URL status in the corpus detail page.

---

## `source` Object

For `"dataset"` type jobs that pull from an API:

```json
{
  "mode":         "rest",
  "endpoint":     "https://api.example.com/data",
  "format":       "json",
  "pagination":   true,
  "total_known":  100000
}
```

| Field | Values | Description |
|-------|--------|-------------|
| `mode` | `"rest"`, `"nltk"`, `"stream"` | Fetch mode |
| `endpoint` | URL string | API endpoint |
| `format` | `"json"`, `"xml"`, `"plain_floats"` | Response format |
| `pagination` | bool | Whether to page through results |
| `total_known` | int | Expected total record count |

---

## Color Table

Colors are resolved to hex in the PtolemySeeder UI:

| Name | Hex | Used By |
|------|-----|---------|
| `gold` | `#C9A84C` | Prime Directive I — Foundations |
| `blue` | `#6EA8D4` | Prime Directive II — Meaning |
| `red` | `#B05050` | Prime Directive III — Fermat |
| `green` | `#6EAD7A` | Python Language |
| `purple` | `#9B7DC8` | C / POSIX |
| `cyan` | `#4EC9C9` | Physics |
| `orange` | `#D4915A` | Mathematics |
| `silver` | `#A8A8A8` | English Language (complete) |

---

## Minimal Example — Corpus Type

```json
{
  "ptorrent_version": "1.0",
  "type": "corpus",
  "name": "Quantum Field Theory",
  "bin": "monad_qft.bin",
  "primary_tags": ["QFT", "YANGMILLS", "SPECTRAL"],
  "color": "cyan",
  "description": "Quantum field theory vocabulary for H_RB Yang-Mills projection.",
  "urls": [
    { "tag": "QFT",      "url": "https://..." },
    { "tag": "YANGMILLS","url": "https://..." }
  ]
}
```

## Dataset Example — Riemann Zeros

```json
{
  "ptorrent_version": "1.0",
  "type": "dataset",
  "name": "Riemann Zeros — first 100,000",
  "primary_tags": ["RIEMANN", "ZEROS", "SPECTRAL"],
  "color": "orange",
  "description": "First 100,000 non-trivial Riemann zeros from LMFDB.",
  "source": {
    "mode": "rest",
    "endpoint": "https://www.lmfdb.org/api/zeros/zeta/",
    "format": "json",
    "pagination": true,
    "total_known": 100000
  },
  "output": "riemann_zeros.json",
  "output_format": "json",
  "output_top_n": 100000
}
```

---

## Delivery Paths

### a) adb inbox push (FileObserver)

```bash
adb push my_corpus.ptorrent \
  /sdcard/Android/data/com.ptolemy.seeder/files/inbox/
```

The `SeedService` FileObserver watches `inbox/` for `CLOSE_WRITE | MOVED_TO`
events. The file is picked up automatically, parsed, added to
`corpus_list.json` on-device, and the URL list is pre-populated in the UI.

### b) Tap to open (Intent)

`.ptorrent` files are registered in `AndroidManifest.xml` via three intent
filters: `application/x-ptorrent` MIME type, `*.ptorrent` via `content://`
scheme, and `*.ptorrent` via `file://` scheme. Tapping in any file manager
opens PtolemySeeder and queues the job.

---

## Implementation Notes

- All `.ptorrent` files must be valid UTF-8 JSON.
- The `bin` field value is used as the output filename on the device at
  `/sdcard/Android/data/com.ptolemy.seeder/files/<bin>`.
- If both `txt` and `urls` are absent, the corpus job will fail silently —
  always provide one or the other.
- `requires_bin` is checked at job start; if the required bin is not present
  on device, the job is queued but not started.
- `checkpoint_every` defaults to 10 URLs. Lower values increase write
  overhead; higher values risk losing progress on interruption.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-05-30 | Initial format. Corpus and dataset types. Embedded URL list. FileObserver delivery. |
