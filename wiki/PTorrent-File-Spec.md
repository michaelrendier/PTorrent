# PTorrent File Format Specification v1.0

## Overview

```
File extension:  .ptorrent
MIME type:       application/x-ptorrent
Encoding:        UTF-8 JSON
```

A `.ptorrent` file is a UTF-8 JSON object describing a single crawl job.
The first field MUST be `ptorrent_version`.

---

## Required fields (all types)

| Field | Type | Description |
|-------|------|-------------|
| `ptorrent_version` | string | `"1.0"` |
| `type` | enum | `"corpus"` \| `"language"` \| `"dataset"` |
| `name` | string | Human-readable name shown in APK UI |

---

## Type: corpus

Trains a sedenion field on web content. Output is a `.bin` checkpoint.

```json
{
  "ptorrent_version": "1.0",
  "type": "corpus",
  "name": "Physics",
  "bin": "monad_physics.bin",
  "sources": "physics_corpus.txt",
  "primary_tags": ["WAVES", "QM", "GR", "COSMOLOGY", "DARKMATTER"],
  "primary_weight": 2.0,
  "context_weight": 1.0,
  "ua": "auto",
  "requires_bin": null,
  "checkpoint_every": 20,
  "color": "cyan",
  "description": "Wave mechanics, QM, GR, BAO, dark matter velocity curves."
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `bin` | string | — | Output bin filename |
| `sources` | string | — | Path to `[TAG] URL` corpus .txt file |
| `primary_tags` | array | `[]` | Tags receiving `primary_weight` |
| `primary_weight` | float | `2.0` | Weight for primary-tier URLs |
| `context_weight` | float | `1.0` | Weight for all other URLs |
| `ua` | enum | `"auto"` | `"ptolemy"` / `"mozilla"` / `"auto"` |
| `requires_bin` | string\|null | `null` | Pre-load this bin before training |
| `checkpoint_every` | int | `20` | Save every N URLs |
| `color` | string | `"gold"` | Card accent colour in APK UI |

### Corpus .txt format

Lines of the form `[TAG]  https://url` are parsed. Everything else is ignored.

```
# Comments and blank lines are ignored
[WAVES]       https://en.wikipedia.org/wiki/Standing_wave
[RESONANCE]   https://hyperphysics.phy-astr.gsu.edu/hbase/Waves/rescon.html
[QM]          https://en.wikipedia.org/wiki/Quantum_mechanics
```

---

## Type: language

Trains the language output geometry (second 𝕆 / Mind's Eye layer).
Uses `see_text()` path rather than `learn()`. Output is a psi2 geometry bin.

```json
{
  "ptorrent_version": "1.0",
  "type": "language",
  "name": "English Literary",
  "bin": "monad_english_literary.bin",
  "sources": "english_literary.txt",
  "window_weight": "functional",
  "requires_bin": "monad_english.bin"
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `bin` | string | — | Output language geometry bin |
| `sources` | string | — | Path to corpus .txt file |
| `window_weight` | enum | `"functional"` | `"functional"` / `"content"` / `"balanced"` |
| `requires_bin` | string\|null | `null` | Load knowledge bin alongside language training |

---

## Type: dataset

Traverses a dataset in-situ. Runs a test kernel against each record.
No corpus data is stored — only measurements are returned.

```json
{
  "ptorrent_version": "1.0",
  "type": "dataset",
  "name": "SPARC Rotation Curves — Sedenion Dark Matter Scan",
  "requires_bin": "monad_physics.bin",
  "ua": "ptolemy",
  "source": {
    "mode": "tap",
    "endpoint": "https://vizier.cds.unistra.fr/viz-bin/conesearch/J/AJ/152/157/table2",
    "fallback": {
      "mode": "file_list",
      "index_url": "http://astroweb.cwru.edu/SPARC/",
      "pattern": "*_rotmod.dat",
      "max_temp_mb": 10
    }
  },
  "test": "mindeye_sedenion_scan",
  "test_params": {
    "field_map": ["r_norm", "V_obs_norm", "V_bar_frac", "V_dm_frac",
                  "dV_dr", "SB_norm", "inclination_weight", null],
    "measure": ["callosum", "bao", "active_dims", "sigma_dev"]
  },
  "output": "sparc_sedenion_scan.json",
  "output_format": "json",
  "output_top_n": 175,
  "checkpoint_every": 20,
  "model_hook": null
}
```

### Source modes

| Mode | Protocol | Example sources |
|------|----------|----------------|
| `tap` | IVOA Table Access Protocol / ADQL | VizieR, Gaia, SIMBAD |
| `rest` | Paginated JSON/XML REST API | LMFDB, OEIS, arXiv, ADS |
| `mediawiki` | MediaWiki extracts API | Wikipedia, Wiktionary |
| `arxiv` | arXiv search + category walk | arXiv.org |
| `ads` | NASA ADS API | ui.adsabs.harvard.edu |
| `ascl` | Astrophysics Source Code Library | ascl.net |
| `github` | GitHub REST API + code search | github.com |
| `oeis` | OEIS integer sequences | oeis.org |
| `lmfdb` | L-functions / modular forms | lmfdb.org |
| `file_list` | Index page → URL pattern | SPARC .dat files |
| `zip` | Temp download, stream members, delete | Dataset archives |
| `stream` | Chunked HTTP for large ASCII tables | Common Crawl |
| `fortran` | GitHub Fortran source via ASCL index | MESA, RAMSES, CAMB |

### Test kernels

| Kernel | Input | Output |
|--------|-------|--------|
| `mindeye_sedenion_scan` | Numeric record → `mind_eye.see()` | callosum, BAO, active_dims |
| `bao_proximity` | Text | BAO distance from OMEGA_ZS |
| `sigma_deviation` | Text | \|σ − ½\| |
| `noether_scan` | Text | J_pos / J_neg balance |
| `zero_activation` | Any | Which sedenion dims activate |
| `vocabulary_coverage` | Text | New words added to field |

---

## Model hook

Optional. Fires events during traversal and posts field state to an AI model.
The model's response can optionally be learned back into the field.

```json
"model_hook": {
  "type": "anthropic",
  "model": "claude-opus-4-8",
  "api_key_env": "ANTHROPIC_API_KEY",
  "system": "You are analyzing data traversed by the Ptolemy sedenion field engine.",
  "on_event": ["checkpoint", "complete"],
  "learn_response": true,
  "response_weight": 1.5,
  "max_tokens": 512
}
```

| `type` | Description |
|--------|-------------|
| `anthropic` | Anthropic SDK (claude-opus-4-8, claude-sonnet-4-6, etc.) |
| `openai` | OpenAI-compatible endpoint (GPT-4, Ollama, LM Studio) |
| `webhook` | HTTP POST — raw JSON payload to any endpoint |
| `mcp` | Model Context Protocol — standard tool call |
| `claudecode` | Claude Code session injection via MCP |
