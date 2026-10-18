# Access outline — per telescope, per dataset (INPUT side, Huchra's Lens)

**2026-10-17. Measured, not assumed. Nothing here is built.** Sits beside `README.md` (the ladder) in this directory.
Everything quoted as "measured" was fetched today with a Mozilla user agent; "UNVERIFIED" means recalled or read in a search
snippet and not tested.

## 0. The constraint, stated precisely (Cody, 2026-10-17)

* **Forbidden:** staging data — a whole-file copy kept on disk, a mirror, a re-download campaign.
* **Allowed:** reading a bounded chunk into memory (that is what any read is), evaluating it, discarding it. The honest accounting
  is **bytes read per source** and **nothing persisted but the result (`.peval`)**.
* So the question is not "download or not" but "which reads, how coalesced, over which protocol".

## 1. How to read in place

| mechanism | what it gives | measured / known |
|---|---|---|
| **ADQL / TAP** | the server evaluates the query; only the answer returns | works at MAST, HEASARC, ESO, ALMA, CADC. Capabilities of all five declare only `TAP`, `VOSI`, `DALI`: **no SIA, SODA (server-side cutout) or DataLink on the TAP services** (other endpoints may exist; not probed) |
| **HTTP / S3 range reads** | any byte range of a file, random access | HST on `s3://stpubdata/hst/public/<rootname[:4]>/<rootname>/<file>` and Chandra under `s3://nasa-heasarc/chandra/` (anonymous list OK, 2026-10-17); MAST download API also answers 206 |
| **A seekable file-like over ranges** | any FITS reader works unmodified on a remote object | not built; `fsspec` needs `aiohttp` (not installed); a stdlib-only `RangeFile` (block cache, `read/seek/tell`) fits the core's "stdlib only" rule and `astropy.io.fits.open` accepts file-likes |
| **FTP `REST` offsets** | resume/offset reads | anonymous FTP answered only at `ftp.eso.org` (listing showed software/docs dirs, not Q2237 data); `ftp.stsci.edu`, `cdaftp`, HEASARC and CADC FTP did not answer from here |
| **Compute next to the data** | your code runs where the bytes are | Fornax Science Console (NASA; JupyterLab on AWS us-east-1; HEASARC/IRSA/MAST cloud data) and CANFAR (CADC containers, POSIX-mounted data; ALMA, JWST, CFHT, Gemini) per search results; **ESA Datalabs and NOIRLab Astro Data Lab: not verified** |

**telnet / gopher / ssh into MAST?** No documented shell service; I did not probe ports on third-party hosts. The nearest equivalent is
the science platforms in the last row: you get a container beside the data, which is the sanctioned version of "run scripts on their
server".

### Measured read economics (one 168 MB WFC3/UVIS frame, public S3, this machine, 2026-10-17)

| quantity | value |
|---|---|
| latency per request | 0.49 s (median) |
| single-stream throughput | 4.9 MB/s; **parallel reads do not add bandwidth** (8×1 MiB in parallel: 4.6 MB/s aggregate) |
| whole frame | ≈ 34 s |
| header walk + one 1 MiB contiguous row block | ≈ 2.3 s |
| the first probe's pattern (64 tiny row reads, sequential) | 44.7 s; with 8 threads 3.9 s |

**Rule (derived): coalesce reads whose gap is below latency × bandwidth ≈ 2.4 MB.** A 64-row cutout of a 4096-pixel float32 chip is
64 rows × 16 KiB = **one 1 MiB block**: read it in a single request and slice the columns in RAM, not 64 tiny requests.
For files smaller than about 2.4 MB (SPT 104 KB, NICMOS frames, ESO frames), fetch the whole object in one request.

**Download-evaluate-delete versus ranged reads, for the 3 121 HST per-exposure frames (65 GB):** whole files ≈ **3.7 h** of pure
transfer at this link; header + one 1 MiB block per frame ≈ 3.4 GB ≈ **12 min**. Ranged wins roughly 15× for cutout work. Whole-file
streaming through memory (no disk) wins only when most of the frame is needed (for example field stars for an empirical PSF), and then
costs the same as downloading; the disk write and delete add nothing and are avoidable.

## 2. Per source

| source | discovery | read in place | formats / catch | `robots.txt` for a generic agent (`*`), 2026-10-17 |
|---|---|---|---|---|
| **HST** (MAST) | MAST TAP `…/vo-tap/api/v0.1/caom`; MAST API `/api/v0/invoke` (`Mast.Caom.Cone`, `Mast.Caom.Products`) | S3 `stpubdata/hst/public/…` anonymous, hourly refresh (search snippet) | uncompressed FITS (`FLC`/`FLT` float32 chips); `SPT`/`JIT`/`JIF` small aux FITS; `POINT-CAT`/`SEGMENT-CAT` ecsv | **`mast.stsci.edu`: `Disallow: /`**; only named bots (Applebot, Bingbot, baiduspider…) get `Allow: /api/v0/`. `archive.stsci.edu`: `Disallow: /*?*` and several paths. S3 is not a website: no robots |
| **Chandra** (HEASARC / CDA) | HEASARC TAP `chanmaster` (40 ObsIDs found) | `s3://nasa-heasarc/chandra/` anonymous (layout under it not yet inspected) | event lists/images FITS, often gzip (not seekable: whole object) | **`heasarc.gsfc.nasa.gov`: `Disallow: /xamin`, `/vo/`, `/FTP/`, `/cgi-bin/`** (TAP lives under `/xamin/vo/tap`). `cxc.cfa.harvard.edu`: `Disallow: /cdaftp /cgi-bin`, **Crawl-delay 3**. `cda.harvard.edu`: `Disallow: /chaser/*` |
| **ALMA** | TAP `almascience.eso.org/tap` (TAP, VOSI, DALI; SSO methods present) | HTTP from the archive; range support **not tested**; products are measurement sets/cubes | ObsCore lists image and cube products (FITS); MS directories would need tar-offset reads: undecided | **`Disallow:` empty for `*` (everything allowed)**; Googlebot has extra rules; sitemap listed |
| **ESO** (VLT, NTT, 2.2 m) | TAP `archive.eso.org/tap_obs` (`dbo.raw`) | HTTP/DataLink retrieval (UNVERIFIED); raw frames commonly compressed (not seekable) | small frames (≈6 MB average here): fetch whole objects | `*` disallows `/search/`, `/cgi-bin/`, `/archive/rh/`… but **`Crawl-delay: 333.333` s** (5.6 min per request) |
| **CADC** (CFHT, Gemini; pending) | TAP `…/argus` (SSO token/cookie/cert present) | DataLink/SODA cutouts and CANFAR (UNVERIFIED for these holdings) | — | **no robots.txt (404)** |
| **NRAO VLA** (pending) | `data-query.nrao.edu` TAP: **connection timed out from here** (DNS resolves) | unknown | measurement sets | `archive.nrao.edu/robots.txt` returns an HTML page, not a robots file (ambiguous); `data-query` unreachable |
| **XMM, COS, GALEX…** | coverage only, not fetched | — | — | — |

## 3. The robots.txt problem — a decision, not a detail

The core's gate is real and hard (`net.py`: `RobotsCache.can_fetch` before every request; `respect_robots:false` only honoured for
a locally authored job). Under it, with a generic agent today:

* **MAST (HST): refused.** `Disallow: /` for `*`. TAP, the Caom API and the download API are all on `mast.stsci.edu`.
* **HEASARC (Chandra catalogue): refused** for `/xamin` and `/vo/`.
* **ESO: allowed, but the 333 s `Crawl-delay` makes it about 8 hours for 85 requests** if honoured literally.
* **ALMA, CADC: allowed.** CXC: allowed except `/cdaftp`, `/cgi-bin`; 3 s delay.

robots.txt is written for spiders; MAST names bots it permits on `/api/v0/`, which suggests the API is meant for programmatic use but
only for those agents. Whether a documented API client is "a crawler" is a judgement the spec already made (the spec says the gate
covers "same-host API included"). Options, none chosen:

1. **Honour it, route around it:** HST bytes from S3 (not a website), Chandra bytes from `nasa-heasarc`; discovery of exposures from a
   one-off catalogue (the census already taken) instead of live TAP; CADC/ALMA/ESO live. Slower to discover, fully compliant.
2. **Ask:** write to the MAST and HEASARC helpdesks to allow the `PtorrentBot` token on the API paths.
3. **Run inside the platform:** Fornax Science Console, where access is sanctioned by the archive itself.
4. **Documented-API exception for a locally authored job**, recorded as an event: possible under the spec, but it is the opposite of
   "robots.txt compliant", so only on Cody's explicit word.

**Disclosure.** Before reading these files I had already made several dozen requests to `mast.stsci.edu` (TAP, Caom API, download
API ranges) and to HEASARC's TAP, at low rate with a Mozilla user agent, treating them as documented programmatic endpoints. The
crawler as specified would have refused them. I will read `robots.txt` before touching a host again and will not use a disallowed
path again without his say.

## 4. What the crawler needs, per source, mapped onto the existing v1.2 `crawl` block

Existing and reused: `RobotsCache`, per-host scheduler (`Crawl-delay` honoured), `HttpClient`, the resolution ladder
(`declared_api → known_api → sitemap → feed → html`), item statuses. Missing (spec lists them as not built): the FITS/TAP/HDF5
evaluation adapters. `known_apis.json` is named by the spec and **is not present in the package** (a small built-in registry exists).

| need | for |
|---|---|
| `declared_api` entries: TAP endpoint + ADQL + read-method (`tap` / `s3_range`), per source | all (the `.ptorrent` already carries endpoint + query) |
| a **range-read adapter**: `RangeFile` (block cache, coalescing at the 2.4 MB gap rule, bytes-read counter, requests counter) | HST, Chandra, any S3/HTTP-range host |
| per-host policy in the file: `respect_robots`, `robots_ua`, `host_ua`, `default_delay_s`, and an explicit **`on_disallowed`** outcome so a refusal is recorded as an item status, not a failure | MAST, HEASARC, ESO |
| **whole-object fetch** path for small or compressed objects, under the same bytes accounting | ESO, Chandra event files |
| auth: none for the public sources above; CADC/ALMA SSO only if proprietary data is wanted (not needed) | — |
| accounting fields on every item: rung, bytes read, requests, seconds | the In Situ tab (queue + detail box) |

## 5. Open for Cody

1. Which robots option in §3 (or a different one).
2. Is a platform run (Fornax / CANFAR) acceptable as "in place", given it is the archive's own compute?
3. First evaluation scope: cutout around the lens only (≈1 MiB per frame), or also field-star regions for an empirical PSF?
