# PTorrent Output Formats

Dataset ptorrents return measurements, not raw data. The `output_format` field
in the `.ptorrent` file selects the format. Extension on `output` filename
also determines format if `output_format` is omitted.

---

## JSON (default)

RFC 8259. Always available. Most flexible.

```json
{
  "ptorrent": "SPARC Rotation Curves",
  "test": "mindeye_sedenion_scan",
  "timestamp": "2026-05-31T16:00:00Z",
  "field_state": {
    "bao": 0.56714,
    "vocab": 58003,
    "noether": 0.000012
  },
  "results": [
    {
      "id": "NGC6503",
      "label": "NGC 6503",
      "bao": 0.5621,
      "callosum": 0.8834,
      "sigma_dev": 0.0041,
      "active_dims": [2, 5, 8, 11],
      "raw": { "V_obs": 116.2, "V_bar": 58.4, "r_kpc": 4.2 }
    }
  ]
}
```

## NDJSON

One JSON result object per line. For streaming large traversals.
Use: log ingestion, real-time dashboards, `jq` pipelines.

## CSV

RFC 4180. Importable into R, Excel, pandas, SPSS.

```
id,label,bao,callosum,sigma_dev,e0,e1,...,e15,source_url,timestamp
NGC6503,NGC 6503,0.5621,0.8834,0.0041,0.12,...,0.03,...,2026-05-31T16:00:00Z
```

Columns: `id, label, bao, callosum, sigma_dev, e0..e15 (UNS activations), source_url, timestamp`

## FITS

FITS 4.0 (NASA OSSA). Standard for astronomy pipelines.
Extension: `BINTABLE`.

```
TELESCOP = 'PTOLEMY'
INSTRUME = 'HOLCUS'
SEDENION = T
BAO_REF  = 0.56714
OMEGA_ZS = 0.56714
```

Columns: `ID(A32), LABEL(A64), BAO(D), CALLOSUM(D), SIGMA_DEV(D), UNS(16D), ACTIVE_DIMS(16J)`

Compatible with: DS9, Aladin, Astropy, TOPCAT.

## VOTable

IVOA VOTable 1.4. XML-based. Direct VizieR / Aladin ingestion.

UCDs:
- `stat.correlation` → BAO
- `phys.energy` → callosum
- `stat.param` → sigma_dev
- `meta.id` → label

## HDF5

HDF5 1.12. For large numerical datasets and ML downstream use.

```
/metadata    — ptorrent name, test, timestamp, field_state
/results/bao[N]          — float64 array
/results/callosum[N]     — float64 array
/results/sigma_dev[N]    — float64 array
/results/uns[N,16]       — float64 array (UNS activations)
/results/labels[N]       — string array
```

## Parquet

Apache Parquet v2. Columnar, snappy-compressed.
Same schema as CSV. For Spark / pandas / DuckDB analytics pipelines.

## BibTeX

For literature traversal results (ADS/arXiv sources).
Standard `@article` fields preserved. Extended fields:

```bibtex
@article{lelli2016sparc,
  author  = {Lelli, Federico and McGaugh, Stacy S. and Schombert, James M.},
  title   = {SPARC: Mass Models for 175 Disk Galaxies},
  journal = {AJ},
  year    = {2016},
  note    = {ptol_bao=0.5621; ptol_callosum=0.8834; ptol_sigma_dev=0.0041}
}
```

## MRT (CDS Machine-Readable Table)

CDS/VizieR standard ASCII table format.
For results intended for re-submission to astronomical databases.
Column widths and descriptions in CDS ReadMe format.
