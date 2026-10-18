# in_situ / huchras_lens — INPUT side design

**Status 2026-10-17: DESIGN + one measured probe. No evaluator is built.** Output goes to `BulletCluster/huchras_lens/`.

**The constraint:** the dataset is evaluated *where it sits*. Never download-then-evaluate. The `.ptorrent` spec already says it
(`evaluation`: "the computation travels to the data; the data never moves here"); this directory is the first target that has to
make that literally true for pixels.

## The dataset to travel
`PTorrent/ptorrents/einstein_cross_q2237_alltelescopes.ptorrent` (regular `dataset` file, parses, preflight passes). Its `sources[]`
are the telescopes; `pending[]` is the queue of telescopes not yet confirmed.

## How to travel it: the ladder (cheapest rung that answers the question wins)
| rung | what is touched | measured/known cost | status |
|---|---|---|---|
| 0 | ADQL / TAP on the archive (the only archive-side compute found) | one query, KB | works (MAST, HEASARC, ESO, ALMA) |
| 1 | ready-made catalogs on the server: HST `POINT-CAT`, `SEGMENT-CAT` (`.ecsv`), `FLT_HLET` | KB | listed in the product census, not yet read |
| 2 | headers + auxiliary files: FITS headers (WCS), `SPT`, `JIT`/`JIF` (pointing jitter), `ASN` | tens to hundreds of KB per exposure | header walk measured: 242 KB (21 requests) |
| 3 | pixel cutouts by HTTP range reads of `FLC`/`FLT` (`RAW` where needed) | 64×64 cutout: 64 requests, 16 KB of pixels | measured (see below) |
| 4 | whole files | 168 MB per WFC3/UVIS frame | **not allowed by the constraint** |

**Measured 2026-10-17** (`BulletCluster/huchras_lens/probe_log/insitu_probe_2026-10-17.txt`): MAST's download API answers `Range`
with HTTP 206, and the public bucket `stpubdata/hst/public/<first 4 chars>/<rootname>/<file>` answers anonymously with
`Accept-Ranges: bytes`. A 64×64 cutout of one 168 382 080-byte frame cost **85 requests, 258 304 bytes (0.15 %)**; 94 % of that was
the sequential header walk, which can be cut. "On the server" means: bytes stay at the archive, only requested ranges reach RAM,
nothing is written. No compute runs at MAST/AWS.

## What file types exist (one WFC3/UVIS observation, `hst_11791_02_wfc3_uvis_f218w_ib0r02`: 92 products)
`FLC` (CTE-corrected, per exposure, 168 MB), `FLT` (168 MB), `RAW` (35 MB), `DRC`/`DRZ` (drizzled), `SPT` (support: pointing/jitter
summary, 104 KB), `JIT`/`JIF` (jitter), `ASN` (association = which exposures belong together = the dither set), `TRL`/`LOG`,
`FLT_HLET`, `POINT-CAT`/`SEGMENT-CAT`, `CRC`/`CRJ` (cosmic-ray-rejected combos), JPEG previews. Full list:
`BulletCluster/huchras_lens/catalog/hst_products_wfc3uvis_ib0r02_2026-10-17.json`.

## Items and the queue (for the In Situ console tab)
One item = (source, exposure, product, rung). Statuses: `pending` → `queued` → `running` → `done` | `error`, plus `blocked` for
anything that would need rung 4. A "move to queue" key promotes the selected `pending` item to `queued`; the In Situ layer shows the
live queue on the right and the selected item's detail (rung, bytes read, requests, errors) in the bottom box. The BitTorrent layer
uses the same pending/queue pattern.

## Open design questions (nothing decided)
1. Where the evaluation terms live (`in_situ.ptorrent` `evaluation` block) and what the first J is for a cutout.
2. How the dither/scan positions (WCS + `SPT`/`JIT`) become ptychography "probe positions", and how the PSF (probe) is supplied
   without a download (TinyTim/WebbPSF are generated, not fetched).
3. Whether non-FITS products (ALMA measurement sets, Chandra event lists) get a range-read adapter or stay at rung 0-2.
4. The full per-exposure manifest must be paged (the cone query returned 2 239 of 4 720 target-named rows).

## Files
`probe/insitu_probe.py` (range-read cutout probe), `probe/tap.sh`, `probe/vot.py`, `probe/votb.py` (TAP helpers; `votb.py` decodes
HEASARC's BINARY VOTable). Scratch-quality, kept as evidence.

## The dataset navigation explorer = the walk-the-hallway skill
The exploration of a dataset (what is there, how it is laid out, which protocol each level speaks, what file types hold) is the job
of Cody's **walk-the-hallway** surface mapper (`~/.claude/skills/walk-the-hallway/`, `references/surface-map.md`): a breadth-first,
level-at-a-time walker that records its own sitemap, in resumable chunk cycles, to power the actual crawl. The `mount` door is one
of its protocol families. Closed doors (`robots.txt`, login, rate limit) are recorded, never opened; see `ACCESS_OUTLINE.md` §3.
