# PTorrent Format Specification — v1.2

**Author:** Cody Michael Allison
**Status:** Stable
**Supersedes:** v1.1 (see `ptorrent-format-v1.md` version history)
**MIME type:** `application/x-ptorrent`
**File extension:** `.ptorrent`
**Reference implementation:** `core/python/ptorrent_core` (runtime) over `core/c/libptorrent` (parse/classify/expr)

---

## 0. What changed in v1.2

| Area | v1.1 | v1.2 |
|------|------|------|
| Crawl behaviour | implicit in the runtime | explicit **`crawl`** block — resolution ladder, robots policy, per-host politeness, HTTP, extraction |
| Seed visibility | seeding == listed | **`distribution`** block — `seed_listing` opt-in, default `off` (`trackers` moves here) |
| Security marking | `security.level` + `embargo_until` | **`security.labels`** — a normalised superset of TLP 2.0 / STIX markings / CSAF / MITRE CWE·CAPEC·ATLAS / CVSS·EPSS·SSVC |
| Evaluation on binary data | `fn` for known tabular cases | `fn` extended with **data reductions** (image / cube / catalog → a dimensionless J per record), still in-situ |
| Provenance | STIX 2.1 bundle | the same, plus a hash-linked **custody chain** carrying a `marking` digest on every transaction; exports to CASE/UCO, STIX 2.1, AFF4 |

A v1.0/v1.1 file is a valid v1.2 file. Unknown fields are retained through a
distribution hop, never discarded.

---

## 1. Root object

| Field | Type | Req | Description |
|-------|------|-----|-------------|
| `ptorrent_version` | string | yes | `"1.2"` |
| `type` | enum | yes | `corpus` \| `dataset` \| `transfer` \| `phonebook` \| `evaluation` |
| `name` | string | yes | Human-readable name |
| `description` | string | yes | One sentence: what this file does or describes |
| `color` | string | yes | Card accent — `gold` `blue` `red` `green` `purple` `cyan` `orange` `silver` |
| `bin` | string | yes\* | Output checkpoint filename. Required for `corpus` and `transfer`. |
| `txt` | string | no | `[TAG] URL` companion list. Optional if `crawl.seeds` / `urls` present. |
| `requires_bin` | string | no | Bin loaded before seeding (transfer-learning chains) |
| `primary_tags` | string[] | yes | Semantic domain tags |
| `primary_weight` / `context_weight` | float | no | Ingestion weight multipliers (default 1.0) |
| `urls` | object[] | no | Embedded `{tag,url}` list (alternative to `txt` / `crawl.seeds`) |
| `source` | object | no | External data source descriptor (see §5) |
| `crawl` | object | no | **v1.2** — declarative crawler spec (see §2) |
| `distribution` | object | no | **v1.2** — seed listing + trackers (see §3) |
| `security` | object | no | Classification + warning labels (see §4). Required when `security.level >= 1`. |
| `resources` | object | no | Resource requirements / hard gates. Required above 1 GB or 1 h. |
| `evaluation` | object | no | Researcher-defined σ-face methodology (see §6). Present when `type` is `evaluation`. |
| `phonebook` | object | no | Dataset phonebook entry (see §7). Present when `type` is `phonebook`. |
| `data_model` | object | no | Structured dataset geometry (see `ptorrent-format-v1.md` §data_model) |
| `output` / `output_format` / `output_top_n` | — | no | Dataset job output controls |

\* `corpus`/`transfer` need `bin` **and** at least one of `txt` / `urls` / `crawl.seeds`.
`evaluation` needs at least one J method (§6). Parse is **fail-closed**: a corpus
with no source, a corpus with no bin, an evaluation with no J method, and a
non-public `security` block missing `labels`/`tlp` are all rejected at parse.

---

## 2. `crawl` — user-defined, api-first, robots-compliant

Every field has a runtime default; a researcher overrides only what they need
and can read the whole crawl policy without opening code.

```json
"crawl": {
  "seeds": [ { "tag": "WAVES", "url": "https://en.wikipedia.org/wiki/Wave_equation" } ],
  "resolution": ["declared_api", "known_api", "sitemap", "feed", "html"],

  "scope": {
    "allow_hosts": [], "allow_paths": [], "deny_paths": [],
    "max_depth": 0, "max_pages": 500, "same_host_only": true,
    "follow": "none"
  },

  "politeness": {
    "ua": "Mozilla/5.0 (compatible; PtorrentBot/1.0; +https://github.com/michaelrendier/PTorrent)",
    "robots_ua": null,
    "respect_robots": true,
    "on_robots_unreachable": "allow",
    "default_delay_s": 1.0, "max_delay_s": 30.0,
    "max_concurrent_per_host": 1, "global_concurrency": 8,
    "jitter": true, "obey_retry_after": true,
    "accept_language": "en", "send_from_header": true,
    "host_ua": {},
    "backoff": { "on": [429, 503], "base_s": 2, "max_s": 300, "give_up_after": 5 }
  },

  "http": {
    "timeout_s": 15, "max_bytes_per_page": 2000000,
    "accept": ["text/html", "application/json", "text/plain"],
    "range_resume": true, "conditional": true, "cache": "etag"
  },

  "extract": {
    "html": { "strip": ["script","style","nav","header","footer","aside","noscript","form","button"],
              "main_selector": null, "min_chars": 40 },
    "json": { "pointer": "/results", "fields": [] }
  }
}
```

### 2.1 Resolution ladder — "api first"

Per seed URL, tried in `resolution` order; the first rung that yields content
wins, and the item records `resolved_via`.

| Rung | Meaning |
|------|---------|
| `declared_api` | the file's own `source` / phonebook `api` block — structured pull, no HTML |
| `known_api` | host → structured API from `core/python/ptorrent_core/known_apis.json` (MediaWiki extracts, arXiv Atom, GitHub/Zenodo/Figshare REST, DOI content negotiation…) — community-PR'd like the phonebook |
| `sitemap` | `robots.txt` `Sitemap:` entries and `/sitemap.xml`, filtered by `scope` |
| `feed` | `<link rel=alternate>` Atom/RSS/JSON-Feed discovery |
| `html` | robots-gated GET → content-type dispatch → strip to prose (the fallback, last) |

An `api → html` fallback emits a `RESOLVE` event so a silently-degraded corpus is visible.

### 2.2 robots.txt — a hard gate

* One parser per `scheme://host`, 24 h TTL, fetched with the wire `ua`. Consulted
  before **every** request — sitemap, feed, and same-host API included.
* **Matching UA ≠ wire UA.** `robots_ua` resolution: explicit value → the
  `compatible; <token>;` group parsed out of `ua` → `"*"`. Full `Mozilla/5.0…`
  strings therefore keep a site's targeted `User-agent: PtorrentBot` rules
  enforceable; when no token is detectable the item carries a `UA_OPAQUE` flag.
* `respect_robots: false` is **honoured only for a locally-authored job**. A job
  that arrived via `inbox/` (from a peer) that sets it gets a `ROBOTS_OVERRIDE`
  event and the flag is ignored.
* `on_robots_unreachable` (`allow` | `deny`) is explicit. Either way the item
  records `robots_state ∈ {allowed, denied, unreachable_allowed, unreachable_denied}`.
* `Crawl-delay` / `Request-rate` feed the per-host scheduler; `Sitemap:` feeds rung 3.

### 2.3 Per-host scheduler + network gate

`next_ok_at[host] = last_finish + max(crawl_delay, default_delay_s) + jitter`;
`max_concurrent_per_host` (default 1) and `global_concurrency` (default 8)
semaphores; `429`/`503`/`Retry-After` → item `DEFERRED` + backoff, `give_up_after`
→ `ERROR`. Total connectivity loss → checkpoint, block every queue on a probe
until it answers — **never abort**.

### 2.4 Item statuses — nothing is dropped

Every seed and every discovered URL becomes an item with a terminal status:

```
PENDING → ACTIVE → { OK | OK_UNCHANGED(304) | SKIPPED(reason) | MALFORMED
                     | ROBOTS_DENIED | DEFERRED(retry_at) | ERROR(msg) }
resolved_via ∈ { declared_api | known_api | sitemap | feed | html | none }
```

### 2.5 Caching / resume

`http.cache: "etag"` stores `{url → (etag, last_modified, sha256)}`. A re-run
sends `If-None-Match` / `If-Modified-Since`; `304` → `OK_UNCHANGED`, no re-fetch,
no re-study. `range_resume` continues an interrupted large GET.

---

## 3. `distribution` — seed listing (opt-in, default off)

```json
"distribution": { "seed_listing": "off", "trackers": [] }
```

| Field | Type | Description |
|-------|------|-------------|
| `seed_listing` | `"off"` \| `"opt-in"` | The **content author's ceiling** on whether any peer may advertise itself as a live seed source for this content in the phonebook. Default `off`. |
| `trackers` | string[] | BitTorrent tracker URLs (moved here from the root in v1.2) |

A peer appears in `phonebook_get(key).live_seeds` **iff**
`distribution.seed_listing == "opt-in"` **and** the peer's own
`phonebook.list_my_seeds` is `anon` or `identified` (default `off`) **and**
`security.level == 0` (`tlp: CLEAR`). Custody is never gated by this: `ACQUIRE` /
`ANNOUNCE` / `EVALUATE` still record possession and provenance; `seed_listing`
suppresses only the ephemeral `SEED` presence beacon and the inbound listener.

---

## 4. `security` + `security.labels`

```json
"security": {
  "classification": "dual-use",
  "level": 3,
  "warning": "…full text displayed before any access…",
  "embargo_until": "2027-06-03",
  "contact_orcid": "0000-0001-2345-6789",
  "acknowledge_required": true,
  "chain_of_custody": true,
  "disclosure_ref": "NIST-PRE-DISCLOSURE-2026-…",
  "cve_id": "CVE-2027-NNNNN",

  "labels": {
    "tlp":   "AMBER+STRICT",
    "iep":   { "policy_id": "…", "handling": [], "sharing": [] },
    "cwe":   ["CWE-327"],
    "capec": ["CAPEC-97"],
    "cvss":  { "version": "4.0", "vector": "CVSS:4.0/AV:N/…", "score": 8.1 },
    "epss":  0.42,
    "ssvc":  { "role": "supplier", "decision": "attend", "vector": "SSVCv2/…" },
    "atlas": { "techniques": ["AML.T0019", "AML.T0020"],
               "mitigations_applied": ["AML.M0007", "AML.M0014"], "note": "…" },
    "hazard_class": ["crypto-attack-vector", "poisoned-dataset"],
    "advisory": { "csaf_url": "https://…/csaf.json", "csaf_tlp": "AMBER" },
    "scan":  { "service": "virustotal", "verdict": "malicious", "ratio": "42/70",
               "scanned_at": "…", "report_url": "…" }
  }
}
```

### 4.1 Field origins

| Field | Standard | Notes |
|-------|----------|-------|
| `tlp` | FIRST **TLP 2.0** | `CLEAR` \| `GREEN` \| `AMBER` \| `AMBER+STRICT` \| `RED` |
| `iep` | FIRST **IEP 2.0 / PAP** | optional machine-readable handling policy |
| `cwe` / `capec` | MITRE | weakness / attack-pattern class |
| `cvss` | FIRST **CVSS 4.0** (3.x accepted) | `vector` must start `CVSS:3.x/` or `CVSS:4.0/` |
| `epss` | FIRST **EPSS** | advisory, time-varying — **excluded from `labels_hash`** |
| `ssvc` | **CISA SSVC** | decision label |
| `atlas` | MITRE **ATLAS** | for poisoned / adversarial data (`AML.Txxxx` / `AML.Mxxxx`) |
| `hazard_class` | PTorrent controlled vocab | `crypto-attack-vector` `exploit-code` `malware-sample` `credential-dump` `poisoned-dataset` `adversarial-benchmark` `side-channel-measurement` `pre-publication-vuln` `pii` `phi` `financial-records` |
| `advisory` | OASIS **CSAF 2.x** | pointer to the machine-readable advisory form |
| `scan` | PTorrent | report-don't-block byte scan; **never a gate** — a positive hit is a label, not a block |

### 4.2 The marking rides the custody chain

Every custody transaction touching a labelled artifact carries
`marking = { tlp, level, labels_hash }`, `labels_hash = sha256` of the durable
label subset (`tlp iep cwe capec cvss ssvc atlas hazard_class advisory` — `epss`
and `scan` excluded so the digest is stable).

* **Inheritance:** a derived artifact (evaluation → `.peval`, merge → `.bin`,
  retained crawl blob) inherits its parent's labels; the derived `ACQUIRE`
  carries the inherited marking. A child may **raise** restrictiveness.
* **No silent downgrade:** the core rejects a lowering of `tlp` or `level`
  except via a signed `DISCLOSE` (`E_MARKING_DOWNGRADE`).
* **TLP → capability:**

| TLP | seeding / listing |
|-----|-------------------|
| `CLEAR` | free; phonebook-listable |
| `GREEN` | VERIFIED peers; never phonebook-listed |
| `AMBER` | VERIFIED **+ prior `GRANT`** from `contact_orcid`; `SEED` beacon suppressed |
| `AMBER+STRICT` | as AMBER; grant is per-request, **non-transitive** |
| `RED` | no `SEED` ever; only ORCIDs named in an explicit `GRANT`; encrypted at rest |

### 4.2b `auth_provenance` — data source ⇄ authentication

A root-level array (written by the wizard's Cybersecurity tab) that ties each
sensitive data source to how it is authenticated, so the access gate and any
downstream audit know the origin of trust for every source the job touches.

```json
"auth_provenance": [
  { "match": "s3://stpubdata/jwst/",        "kind": "institutional", "detail": "MAST" },
  { "match": "https://data.lsst.cloud",     "kind": "oauth",         "detail": "RSP" },
  { "match": "/media/researcher/Datasets/", "kind": "orcid-session", "detail": "" }
]
```

| Field | Description |
|-------|------------|
| `match` | a path or host/URL prefix the entry governs |
| `kind` | `orcid-session` \| `oauth` \| `institutional` \| `api-key` \| `none` |
| `detail` | provider name, key slot, or a free-text note |

### 4.3 Classification levels (unchanged from v1.1)

`0 public` · `1 sensitive` (ORCID verified) · `2 restricted` (ORCID + `contact_orcid`,
`embargo_until` a hard block) · `3 dual-use` (ORCID acknowledgment, no override).
`preflight` blocks a job before `embargo_until`; the block surfaces as `E_EMBARGO`.

### 4.4 Chain-of-custody export

`chain_export(fmt)` projects the native hash-linked chain to:
`native` (authoritative) · `case` (CASE/UCO JSON-LD — `ChainOfCustody` /
`ProvenanceRecord`; the canonical evidentiary form) · `stix` (STIX 2.1 bundle
with `marking-definition` + `object_marking_refs`; the disclosure subset,
reuses `skills/disclosure/stix_builder.py`) · `aff4` (container; not yet
implemented).

---

## 5. `source` — external data source

For `dataset` / `evaluation` jobs pulling structured data.

```json
"source": {
  "mode": "rest",
  "endpoint": "https://www.lmfdb.org/api/zeros/zeta/",
  "format": "json",
  "pagination": true,
  "total_known": 100000
}
```

`mode`: `rest` · `tap_adql` · `file_list` · `zip` · `stream` · `s3_fits` ·
`fits` · `fits_table` · `hdf5` · `votable` · `mrt` · `github_repo`.
(`rest` is fully served by the current runtime; the rest are adapter hooks.)

---

## 6. `evaluation` — researcher-defined σ-face methodology, in situ

The computation travels to the data; the data never materialises. Output is a
`.peval` file and an `EVALUATE` custody transaction.

### 6.1 J-ratio extraction — priority order

The evaluator extracts a dimensionless **J-ratio** per record, first method that succeeds:

| # | Field | Meaning |
|---|-------|---------|
| 1 | `j_col` | a column that is already the J-ratio |
| 2 | `j_num_col` / `j_den_col` | J = numerator / denominator |
| 3 | `j_expr` | safe arithmetic over column names — **recursive-descent, never `eval()`** |
| 4 | `fn` | a named built-in reduction (tabular *or* binary — see §6.3) |
| 5 | *(fallback)* | the adapter's primary `value` |

### 6.2 `j_expr` grammar

`+ - * / **` (Python precedence: `-2**2 == -4`, `2**-1 == 0.5`),
functions `sqrt abs log log10 exp` (1 arg) / `max min` (2 args), constants `pi e`.
Anything else is a parse error — no escape hatch. **NaN discipline:** division by
zero, `sqrt` of a negative, `log` of a non-positive, and overflow yield NaN and
propagate; a NaN J classifies as **`undefined`**, never `∞`. A column bound to
null is a data condition (NaN); a column never bound is a config error
(`E_NOTFOUND` on the first row).

### 6.3 `fn` — named reductions (v1.2: tabular **and** binary)

A reduction turns one record — a catalog row, a FITS cube slice, or a fetched
image — into one dimensionless J. The bytes are fetched, reduced, and discarded
(an `ACQUIRE` with `retained: false` records lineage without keeping the bytes);
only the σ-tally and the final `.peval` are retained. This is what lets a job
walk 5 000 images at an API's rate limit without ever storing the 196 GB.

**Tabular (from v1.1):** `σ_face_bao_residual` `σ_face_rotation_curve`
`σ_face_spectral` `σ_face_cmb_residual` `σ_face_photometric` `σ_face_multiband`
`σ_face_cmb_peaks`.

**Binary / image (v1.2, `core/python/ptorrent_core/reductions.py`):**

| `fn` | J-ratio | notes |
|------|---------|-------|
| `img_brightness_ratio` | mean(foreground) / mean(background), Otsu split | bright subject on dark field ⇒ large J |
| `img_foreground_area_ratio` | foreground px / background px (Otsu) | how much of the frame the subject fills |
| `img_entropy_ratio` | Shannon entropy(histogram) / log2(bins) | texture / information density, in [0,1] |
| `img_edge_density_ratio` | edge px / interior px (Sobel magnitude ≥ `edge_threshold`) | structural busyness |
| `img_gradient_energy_ratio` | Σ\|∇I\| / Σ I | total local contrast normalised by brightness |

`fn_params`: `bins` (entropy, default 256), `edge_threshold` (edge density,
default 48). Each reduction returns a positive float or `None` (→ the row is
`undefined`, counted, not dropped). Decode uses **Pillow if installed** (JPEG /
PNG / everything); otherwise a pure-stdlib decoder for the uncompressed formats
(PNM `P2·P3·P5·P6`, 24-bit BMP) and PNG/JPEG are skipped with a recorded reason.
Cube (FITS/HDF5) and catalog reductions arrive with their adapters.

### 6.4 σ-face assignment (fixed constants — do not tune)

`d* = 0.246`, `Ω_ZS = 0.5671432904097838`.

| J range | σ-face | semantic |
|---------|--------|----------|
| J < d* | ∞ | BH interior — compressible limit |
| d* ≤ J < 1 | ½ | causality — critical line |
| 1 ≤ J < 1/d* | 1 | Yang-Mills — mass assembly |
| 1/d* ≤ J < 1/d* + Ω_ZS | 2 | gravity — force regime |
| J ≥ 1/d* + Ω_ZS | ∞ | BH interior — force extreme |
| non-finite J | undefined | row counted, contributes to no face |

### 6.5 Fields

| Field | Req | Description |
|-------|-----|-------------|
| `methodology` | recommended | plain-language statement of what is measured and why |
| `j_expr` / `j_expr_cols` | recommended | the expression and its columns (TAP minimum-column selection) |
| `j_col` / `j_num_col` / `j_den_col` / `fn` | no | alternative J methods |
| `prediction` | recommended | the σ-face distribution expected, and why |
| `fn_params` | no | reduction parameters (`bins`, `fft_split`, `plane_axis`, `threshold`…) |
| `max_rows` | no | cap on records evaluated (default 50 000) |
| `σ_table` | no | canonical: `{"½":"causality","1":"Yang-Mills","2":"gravity","∞":"BH interior"}` |
| `bin_hash` | no | SHA-256 of `requires_bin` — the terms hash in the `EVALUATE` tx |

Two evaluations with the same `bin_hash` and `data_model` are β-mergeable.

---

## 7. `phonebook` — dataset entry (unchanged shape; intake is new)

Fields as in `ptorrent-format-v1.md` §phonebook (`dataset_url`, `license`,
`citation`, `maintainer`, `api{}`, `dumps[]`, `size_records`, `size_gb`,
`last_verified`).

**v1.2 intake ("Alexandrian"):** every `add()` of *any* `.ptorrent` computes a
canonical key (normalised `dataset_url`, or `sha256` of the `source`/`api`
descriptor) and checks it into the library. New key → a synthesised `phonebook`
entry + a `PHONEBOOK_ADD` custody transaction. Existing key → `seen_count++`,
`last_seen_by` appended, new `dumps`/`api` merged. The phonebook materialised
view is rebuilt from the chain, so a peer that syncs the chain has the whole
library. `phonebook_verify` re-checks endpoints/dumps and writes
`verify_status ∈ {LIVE, STALE, DEAD, UNKNOWN}` + a `PHONEBOOK_VERIFY` tx.

---

## 8. Custody chain transaction classes (v1.2)

`GENESIS` · `ACQUIRE` · `ANNOUNCE` · `UPDATE` / `RETIRE` · `SEED` / `UNSEED` ·
`SEED_LISTED` / `SEED_UNLISTED` · `MERGE` · `EVALUATE` · `PHONEBOOK_ADD` /
`PHONEBOOK_VERIFY` · `CLASSIFY` · `ACKNOWLEDGE` · `DISCLOSE` · `REVOKE` · `FLAG` ·
`NOTIFY` · `REQUEST` / `GRANT` / `DENY` · `VOTE` / `VOTE_ADDRESSED` /
`VOTE_DISPUTED`.

Each transaction carries `actor` (ORCID-attributed `peer_id`), `object_hash`,
`parent_hash` (lineage), `prev_hash` (supersede), `marking`, UTC `timestamp`
(monotonic-checked), `tx_hash` (integrity), optional `sig`. The chain is
append-only, `prev_hash`-linked, Merkle-rooted, light-PoW-mined.

---

## 9. Version history

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-05-30 | Corpus / dataset / transfer types; embedded URL list; FileObserver delivery |
| 1.0.1 | 2026-06-02 | `phonebook` type + object; `trackers` field |
| 1.1 | 2026-06-16 | Expanded `evaluation`; `j_expr` / `j_expr_cols` / `methodology`; J-ratio priority order |
| **1.2** | **2026-08-29** | `crawl` block (resolution ladder, robots policy, per-host politeness, HTTP, extraction); `distribution` block (opt-in `seed_listing`, `trackers` relocated); `security.labels` (TLP 2.0 / STIX markings / CSAF / MITRE CWE·CAPEC·ATLAS / CVSS·EPSS·SSVC); binary/image `fn` reductions for in-situ evaluation; custody-chain `marking` digest on every transaction + CASE/UCO / STIX / AFF4 exporters; Alexandrian phonebook intake |
