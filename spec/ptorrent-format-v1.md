# PTorrent Format Specification — v1.0

**Author:** Cody Michael Allison  
**Status:** Stable  
**MIME type:** `application/x-ptorrent`  
**File extension:** `.ptorrent`

---

## What PTorrent Is

PTorrent is targeted web crawler access for people who don't write web crawlers.

A `.ptorrent` file is a declarative crawler specification written in plain JSON.
You describe *what to fetch, how to tag it, and where to save the result*. The
PtolemySeeder APK is the runtime — it reads the file, traverses the URL list or
API, and builds the output. No Python. No HTTP libraries. No scraping boilerplate.

The design principle: **modify, don't write from scratch.** Copy an existing
`.ptorrent`, change the name, swap the URLs, adjust the tags. That's all it takes
to redirect the crawler at a new dataset or web source. The format is intentionally
minimal so that modification is the primary user action.

PTorrent distributes the *job*, not the *data*. Each device independently
traverses the source and builds its own output — analogous to how BitTorrent peers
independently verify and store pieces, but applied to knowledge acquisition
rather than file transfer.

---

## Three Uses of a .ptorrent File

### 1. Corpus crawler
Fetch web pages, extract text, seed a monad checkpoint binary.
Users who want to train a Ptolemy LSHS on a new domain write or modify a corpus
`.ptorrent`. The PtolemySeeder APK does the rest overnight.

### 2. Dataset retrieval
Pull structured data from a REST API, paginate through results, save as JSON/CSV.
Users who want a local copy of a public dataset (Riemann zeros, SPARC rotation
curves, PubMed abstracts) point a dataset `.ptorrent` at the API.

### 3. Dataset Phonebook entry
Record *where a dataset lives* — not the data itself, but its address, format,
API details, and dump availability. A phonebook `.ptorrent` is a structured
citation for a public dataset: canonical URL, API endpoint, bulk dump location,
license, and verification timestamp. The goal is a single machine-readable,
dynamically-maintained index of all publicly available datasets — across all
disciplines, for all researchers. See the Dataset Phonebook section below.

---

## Root Object Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ptorrent_version` | string | yes | Format version. Currently `"1.0"`. |
| `type` | string | yes | Job type: `corpus`, `dataset`, `transfer`, `phonebook`, `evaluation`. |
| `name` | string | yes | Human-readable name. |
| `bin` | string | yes* | Output checkpoint filename. Required for `corpus` and `transfer` types. |
| `txt` | string | no | Corpus URL list filename. Optional if `urls` is embedded. |
| `requires_bin` | string | no | Bin file that must be loaded before seeding. Used for transfer-learning chains. |
| `primary_tags` | string[] | yes | Semantic domain tags. Used for display and monad weighting. |
| `primary_weight` | float | no | Weight multiplier for primary-tagged words (default 1.0). |
| `context_weight` | float | no | Weight multiplier for context words (default 1.0). |
| `color` | string | yes | Card accent color name. See Color Table. |
| `description` | string | yes | One-sentence description of what this file does or describes. |
| `ua` | string | no | User-agent hint for HTTP requests. Default `"ptolemy"`. |
| `urls` | object[] | no | Embedded URL list. If present, no `.txt` file is needed. |
| `source` | object | no | External data source descriptor (REST, NLTK, stream). |
| `phonebook` | object | no | Dataset Phonebook entry. Present when `type` is `"phonebook"`. |
| `test` | string | no | Name of test function to run after seeding. |
| `test_params` | object | no | Parameters passed to the test function. |
| `output` | string | no | Output filename for dataset jobs. |
| `output_format` | string | no | Output format: `"json"`, `"csv"`, `"fits"`, `"hdf5"`, `"peval"`. |
| `output_top_n` | int | no | Limit output to top N results. |
| `checkpoint_every` | int | no | Save checkpoint every N URLs (default 10). |
| `model_hook` | string | null | Reserved for future model hook integration. |
| `trackers` | string[] | no | BitTorrent tracker URLs for peer-seeded bin distribution. |
| `security` | object | no | Security classification. Required for any dual-use, sensitive, or embargoed data. |
| `resources` | object | no | Resource requirements and warnings. Required for jobs exceeding 1 GB or 1 hour. |
| `discover` | bool | no | `true` = run auto-probe before execution to detect `data_model` fields. |
| `data_model` | object | no | Structured description of the dataset geometry (type, dimensions, units, access). |
| `evaluation` | object | no | Evaluation terms and method. Present when `type` is `"evaluation"`. |

---

## Types

| Type | Description |
|------|-------------|
| `corpus` | Fetch URLs, extract text, seed a monad checkpoint binary. |
| `dataset` | Fetch structured data from a source API and save to file. |
| `transfer` | Load `requires_bin` then continue seeding additional corpus text. |
| `phonebook` | Dataset Phonebook entry — records where a dataset lives, not the data itself. |
| `evaluation` | Data Transversal — apply evaluation terms (bin) to a structured dataset in situ. Output is a `.peval` file announced to the chain with `EVALUATE` transaction. |

---

## `security` Object

Required whenever `security.level >= 1`. The APK enforces all constraints before
allowing any seeding to begin.

```json
{
  "classification":       "dual-use",
  "level":                3,
  "warning":              "Full warning text displayed to researcher before access.",
  "embargo_until":        "2027-06-03",
  "requires_credential":  "security_researcher",
  "disclosure_ref":       "NIST-PRE-DISCLOSURE-2026-AINULINDALE-UDEO",
  "contact_orcid":        "0000-0001-2345-6789",
  "acknowledge_required": true
}
```

| Field | Description |
|-------|-------------|
| `classification` | `"public"` \| `"sensitive"` \| `"restricted"` \| `"dual-use"` |
| `level` | 0 = public, 1 = sensitive, 2 = restricted, 3 = dual-use |
| `warning` | Full text of the warning displayed to the researcher |
| `embargo_until` | ISO date `"YYYY-MM-DD"` — seeding blocked before this date |
| `requires_credential` | ORCID credential type required for access |
| `disclosure_ref` | External reference (NIST advisory, CVE, etc.) |
| `contact_orcid` | ORCID of the responsible researcher (mandatory for level >= 2) |
| `acknowledge_required` | `true` = researcher must enter ORCID to confirm they read the warning |

The `embargo_until` check is enforced by `preflight.py` and `PreFlightCheck.kt`.
Seeding before the embargo date is a hard block — no override.

---

## `resources` Object

Required for any job that may exceed 1 GB storage or run longer than 1 hour.
All fields are checked by `preflight.py` before the job starts.

```json
{
  "storage_gb":           12.5,
  "ram_peak_gb":          3.2,
  "duration_hours":       8,
  "thermal_risk":         "high",
  "battery_drain_pct_hr": 15,
  "requires_charging":    true,
  "requires_wifi":        true,
  "min_free_storage_gb":  15,
  "min_ram_gb":           4,
  "warning":              "Human-readable resource warning shown before start.",
  "safe_to_pause":        true,
  "checkpoint_every_urls": 5
}
```

| Field | Type | Description |
|-------|------|-------------|
| `storage_gb` | float | Estimated output storage required |
| `ram_peak_gb` | float | Peak RAM during evaluation |
| `duration_hours` | float | Estimated runtime |
| `thermal_risk` | string | `"low"` \| `"medium"` \| `"high"` |
| `battery_drain_pct_hr` | float | Estimated battery drain per hour |
| `requires_charging` | bool | Hard block if not charging |
| `requires_wifi` | bool | Hard block if not on WiFi |
| `min_free_storage_gb` | float | Hard block if less free space |
| `min_ram_gb` | float | Hard block if less RAM available |
| `warning` | string | Human-readable summary shown before start |
| `safe_to_pause` | bool | Whether the job can be safely paused mid-run |
| `checkpoint_every_urls` | int | Override global checkpoint interval |

`preflight.py` enforces all `min_*` and `requires_*` fields as hard stops.
The job does not start if any check fails. Failure reasons are displayed
explicitly (field, required value, available value, human message).

---

## `data_model` Object

Describes the geometric structure of the source dataset.
Auto-populated by Discovery Mode (`"discover": true`).
Can be written manually for known formats.

```json
{
  "type":       "spectral_cube",
  "dimensions": ["ra", "dec", "wavelength"],
  "units":      {"flux": "MJy/sr", "wavelength": "micron", "pos": "deg"},
  "layers":     ["F090W", "F150W", "F200W", "F277W", "F356W", "F444W"],
  "native_format": "FITS",
  "wcs":        true,
  "access": {
    "mode":    "s3_fits",
    "bucket":  "stpubdata",
    "prefix":  "jwst/public/jw02114/"
  }
}
```

Supported `type` values: `spectral_cube`, `image_2d`, `simulation_snapshot`,
`multiband_catalog`, `rotation_curve`, `time_series`, `spectral_1d`,
`financial_records`, `code_corpus`, `tap_catalog`, `catalog`.

Supported adapter `mode` values: `fits`, `fits_table`, `hdf5_snapshot`, `hdf5`,
`votable`, `tap_adql`, `mrt`, `fortran_binary`, `cobol_vsam`, `cobol_fixed`,
`github_repo`, `github_dataset`, `s3_fits`.

---

## `evaluation` Object — Researcher-Defined σ-Face Methodology

Present when `type` is `"evaluation"`. The researcher defines how to view their
dataset through the Ainulindale σ-face lens. The computation travels to the data;
the data never moves here.

The most important field is `methodology`: your plain-language statement of what
you are measuring and why. The `j_expr` is the machine-executable form of that
choice. Together they make every ptorrent self-describing — anyone reading the
file can understand what the evaluation does without looking at external code.

---

### J-Ratio Extraction — Priority Order

The evaluator extracts a **J-ratio** (dimensionless buoyancy ratio) from each row.
It tries each method in sequence and uses the first that succeeds:

| Priority | Field | Description |
|----------|-------|-------------|
| 1 | `j_col` | A single column that is already the J-ratio |
| 2 | `j_num_col` / `j_den_col` | Two columns: J = numerator / denominator |
| 3 | `j_expr` | Researcher-defined arithmetic expression over column names |
| 4 | `fn` | Named built-in function (complex logic: sedenion energy, spectral entropy) |
| 5 | *(fallback)* | Adapter's primary `value_col` measurement used as J directly |

`j_expr` is the recommended method for any evaluation expressible as a ratio or
simple arithmetic. It is portable, auditable, and lives entirely in the ptorrent file.

---

### `j_expr` Expression Syntax

A safe arithmetic expression over dataset column names. Column values from the
current row are bound by name as variables.

**Allowed operations:** `+  -  *  /  **` (power)  
**Allowed functions:** `sqrt  abs  max  min  log  log10  exp`  
**Allowed constants:** `pi  e`

```
"D_M / r_drag"
"sqrt(pmra ** 2 + pmdec ** 2) / max(parallax, 0.001)"
"10 ** (power_dB / 10)"
"abs(C_l) / sigma_C_l"
"10 ** ((k_m - j_m) / 2.5)"
```

Declare the columns used in `j_expr_cols`. For TAP sources, this is used to
request only the needed columns — minimum data movement.

---

### σ-Face Assignment

Given a J-ratio, the σ-face is assigned using two constants:
`d* = 0.246` (spectral ground state), `Ω_ZS = 0.5671432904097838` (Lambert W(1)).

| J range | σ-face | Semantic |
|---------|--------|----------|
| J < d* | ∞ | BH interior — compressible limit |
| d* ≤ J < 1 | ½ | Causality — Riemann critical line |
| 1 ≤ J < 1/d* | 1 | Yang-Mills — mass assembly |
| 1/d* ≤ J < 1/d* + Ω_ZS | 2 | Gravity — force regime |
| J ≥ 1/d* + Ω_ZS | ∞ | BH interior — force extreme |

These thresholds are fixed constants — not fit parameters. Do not adjust them.

---

### `evaluation` Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `methodology` | string | **recommended** | Your statement: what you are measuring and why. Human-readable. Shown in ptorrent status. |
| `j_expr` | string | recommended | Arithmetic expression for J using column names from the row. |
| `j_expr_cols` | string[] | recommended | Columns needed by `j_expr`. Used for TAP minimum-column selection. |
| `j_col` | string | no | Column name that is already the J-ratio (use instead of `j_expr` when one column suffices). |
| `j_num_col` | string | no | Numerator column for J = num/den. |
| `j_den_col` | string | no | Denominator column for J = num/den. |
| `fn` | string | no | Named built-in handler for datasets that require complex logic. |
| `prediction` | string | recommended | Testable prediction: what σ-face distribution you expect and why. |
| `J_ambient` | string | no | One-line physical description of the J-ratio. |
| `σ_table` | object | no | σ-face semantic labels. Use the canonical table below. |
| `bin_hash` | string | no | SHA-256 of `requires_bin` for chain reproducibility. |

### Canonical σ-Table (do not modify)

```json
"σ_table": { "½": "causality", "1": "Yang-Mills", "2": "gravity", "∞": "BH interior" }
```

---

### Minimum Viable `evaluation` Block

```json
"evaluation": {
  "j_expr":      "column_a / column_b",
  "j_expr_cols": ["column_a", "column_b"],
  "methodology": "I am measuring [column_a] normalized to [column_b]. I expect to find σ=½ where [physical condition].",
  "prediction":  "What σ-face distribution I expect to find and why."
}
```

### Complete Example — BAO Distance Ratio

```json
"evaluation": {
  "methodology": "I am measuring angular diameter distance D_M normalized to the BAO sound horizon r_drag. I am looking for the Ainulindale constants d*=0.246 and Ω_ZS=0.5671 in the residual after ΛCDM accounting. These are not fitted — they are predicted from H_hat_RB geometry.",
  "j_expr":      "D_M / r_drag",
  "j_expr_cols": ["D_M", "r_drag"],
  "prediction":  "Residual clusters at d*=0.24600 and/or Ω_ZS=0.56714. Paper: D15 Noether-Wiles.",
  "fn":          "σ_face_bao_residual",
  "bin_hash":    "",
  "σ_table":     { "½": "causality", "1": "Yang-Mills", "2": "gravity", "∞": "BH interior" },
  "J_ambient":   "D_M(z)/r_drag normalized — residual after ΛCDM subtraction"
}
```

The `bin_hash` field is the terms hash in the chain's `EVALUATE` transaction.
Two evaluations with the same `bin_hash` and same `data_model` are β-mergeable.

See `spec/evaluation.ptorrent.template` for a skeleton evaluation ptorrent
with all fields annotated.

---

## `urls` Array

Each element of the embedded URL list:

```json
{ "tag": "WAVES", "url": "https://example.com/wave-mechanics" }
```

`tag` must be one of the values in `primary_tags` or a sub-tag. Used to
categorize URL status in the corpus detail page.

---

## `source` Object

For `dataset` type jobs pulling from an API:

```json
{
  "mode":        "rest",
  "endpoint":    "https://api.example.com/data",
  "format":      "json",
  "pagination":  true,
  "total_known": 100000
}
```

| Field | Values | Description |
|-------|--------|-------------|
| `mode` | `"rest"`, `"nltk"`, `"stream"` | Fetch mode |
| `endpoint` | URL string | API endpoint |
| `format` | `"json"`, `"xml"`, `"plain_floats"`, `"csv"` | Response format |
| `pagination` | bool | Whether to page through results |
| `total_known` | int | Expected total record count |

---

## `phonebook` Object — Dataset Phonebook Entry

A `phonebook` entry records the metadata needed to *find and access* a public
dataset — not the data itself. It is a structured, machine-readable citation
that answers: where is it, what format, is there an API, is there a bulk dump,
is it still alive?

```json
{
  "dataset_url": "https://canonical.home/of/dataset",
  "license": "CC-BY-4.0",
  "citation": "10.1234/doi.or.bibtex.key",
  "maintainer": "Institution or person name",
  "last_dataset_update": "2025-01",
  "last_verified": "2026-06-02",
  "size_records": 1000000,
  "size_gb": 42.5,
  "api": {
    "available": true,
    "type": "REST",
    "endpoint": "https://api.example.com/v1/",
    "auth": "none",
    "rate_limit": "1000/day",
    "docs_url": "https://api.example.com/docs"
  },
  "dumps": [
    {
      "url": "https://example.com/dumps/dataset-2025.tar.gz",
      "format": "CSV",
      "size_gb": 42.5,
      "update_freq": "annual",
      "last_verified": "2026-06-02"
    }
  ]
}
```

### `phonebook` Fields

| Field | Type | Description |
|-------|------|-------------|
| `dataset_url` | string | Canonical home page for the dataset |
| `license` | string | SPDX license identifier (e.g. `"CC-BY-4.0"`, `"ODbL-1.0"`, `"public domain"`) |
| `citation` | string | DOI or BibTeX key for citing this dataset |
| `maintainer` | string | Institution or person responsible for the dataset |
| `last_dataset_update` | string | When the dataset was last updated by its maintainer |
| `last_verified` | string | ISO date when PTorrent last confirmed this entry is live |
| `size_records` | int | Approximate number of records |
| `size_gb` | float | Approximate total size in gigabytes |
| `api.available` | bool | Whether a programmatic API exists |
| `api.type` | string | API type: `"REST"`, `"GraphQL"`, `"SPARQL"`, `"FTP"`, `"JDBC"` |
| `api.endpoint` | string | Primary API endpoint URL |
| `api.auth` | string | Auth required: `"none"`, `"api_key"`, `"oauth2"`, `"institutional"` |
| `api.rate_limit` | string | Rate limit description (e.g. `"1000/day"`, `"3/second"`) |
| `api.docs_url` | string | URL for API documentation |
| `dumps[].url` | string | Direct download URL for a bulk dump |
| `dumps[].format` | string | File format: `"CSV"`, `"JSON"`, `"XML"`, `"HDF5"`, `"FITS"`, `"Parquet"`, `"tar.gz"` |
| `dumps[].size_gb` | float | Size of this dump in gigabytes |
| `dumps[].update_freq` | string | How often dumps are released: `"daily"`, `"monthly"`, `"annual"`, `"static"` |
| `dumps[].last_verified` | string | ISO date when this dump URL was last confirmed live |

### Phonebook Example — SPARC Galaxy Rotation Curves

```json
{
  "ptorrent_version": "1.0",
  "type": "phonebook",
  "name": "SPARC — Spitzer Photometry and Accurate Rotation Curves",
  "primary_tags": ["ASTROPHYSICS", "DARK_MATTER", "ROTATION_CURVES", "GALAXIES"],
  "color": "cyan",
  "description": "175 late-type galaxies with high-quality rotation curves and Spitzer 3.6μm photometry.",
  "phonebook": {
    "dataset_url": "http://astroweb.cwru.edu/SPARC/",
    "license": "public domain",
    "citation": "Lelli et al. 2016, AJ, 152, 157",
    "maintainer": "Federico Lelli, Case Western Reserve University",
    "last_dataset_update": "2016-10",
    "last_verified": "2026-06-02",
    "size_records": 175,
    "size_gb": 0.01,
    "api": {
      "available": false
    },
    "dumps": [
      {
        "url": "http://astroweb.cwru.edu/SPARC/SPARC_Lelli2016c.mrt",
        "format": "MRT",
        "size_gb": 0.01,
        "update_freq": "static",
        "last_verified": "2026-06-02"
      }
    ]
  }
}
```

### Phonebook Example — HuggingFace Common Voice

```json
{
  "ptorrent_version": "1.0",
  "type": "phonebook",
  "name": "Mozilla Common Voice — multilingual speech corpus",
  "primary_tags": ["SPEECH", "AUDIO", "MULTILINGUAL", "NLP"],
  "color": "blue",
  "description": "Crowd-sourced multilingual speech dataset; 100+ languages, 20,000+ hours.",
  "phonebook": {
    "dataset_url": "https://commonvoice.mozilla.org/en/datasets",
    "license": "CC-0",
    "citation": "Ardila et al. 2020, LREC",
    "maintainer": "Mozilla Foundation",
    "last_dataset_update": "2024-06",
    "last_verified": "2026-06-02",
    "size_records": 16000000,
    "size_gb": 1800,
    "api": {
      "available": true,
      "type": "REST",
      "endpoint": "https://huggingface.co/datasets/mozilla-foundation/common_voice_17_0",
      "auth": "api_key",
      "rate_limit": "none documented",
      "docs_url": "https://huggingface.co/docs/datasets/"
    },
    "dumps": [
      {
        "url": "https://commonvoice.mozilla.org/en/datasets",
        "format": "tar.gz",
        "size_gb": 1800,
        "update_freq": "annual",
        "last_verified": "2026-06-02"
      }
    ]
  }
}
```

---

## Color Table

| Name | Hex | Used By |
|------|-----|---------|
| `gold` | `#C9A84C` | Prime Directive I — Foundations |
| `blue` | `#6EA8D4` | Prime Directive II — Meaning |
| `red` | `#B05050` | Prime Directive III — Fermat |
| `green` | `#6EAD7A` | Python Language |
| `purple` | `#9B7DC8` | C / POSIX |
| `cyan` | `#4EC9C9` | Physics, Astrophysics |
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
  "description": "QFT vocabulary for H_RB Yang-Mills projection.",
  "urls": [
    { "tag": "QFT",       "url": "https://..." },
    { "tag": "YANGMILLS", "url": "https://..." }
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

### b) Tap to open (Intent)

`.ptorrent` files are registered in `AndroidManifest.xml` via three intent
filters: `application/x-ptorrent` MIME, `*.ptorrent` via `content://`,
and `*.ptorrent` via `file://`. Tapping in any file manager opens the Seeder.

---

## Implementation Notes

- All `.ptorrent` files must be valid UTF-8 JSON.
- The `bin` field is the output filename on device at `/sdcard/Android/data/com.ptolemy.seeder/files/<bin>`.
- If both `txt` and `urls` are absent on a `corpus` job, the job fails silently.
- `requires_bin` is checked at job start; missing bins queue but do not start.
- `checkpoint_every` defaults to 10 URLs. Lower = more writes; higher = more loss risk on interrupt.
- `phonebook` entries with `api.available: false` and no `dumps` are still valid — they record that a dataset exists even if access is restricted or API-free.
- `last_verified` in phonebook entries should be updated by the verification crawler, not by hand.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-05-30 | Initial format. Corpus, dataset, transfer types. Embedded URL list. FileObserver delivery. |
| 1.0.1 | 2026-06-02 | Added `phonebook` type and `phonebook` object. Added `trackers` field. Clarified PTorrent as accessible crawler for non-coders. |
| 1.1 | 2026-06-16 | Expanded `evaluation` type. Added `j_expr` / `j_expr_cols` / `methodology` fields. J-ratio priority order documented. Researcher-defined portable evaluation methodology. Skeleton template at `spec/evaluation.ptorrent.template`. |
