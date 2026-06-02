# PTorrent TODO

## APK — immediate

- [ ] MCP server: integrate Ktor embedded HTTP server on configurable port
      JSON-RPC 2.0 at /mcp — tools: ptorrent_run, ptorrent_status,
      ptorrent_inject, ptorrent_abort, pull_bin, field_query, field_health
- [ ] MCP server: ADB forward documentation + auto-discovery on local WiFi (mDNS)
- [ ] Cloud sync: Google Drive upload on corpus completion (Play Services OAuth2)
- [ ] Cloud sync: Dropbox (dropbox-core-sdk OAuth2)
- [ ] Cloud sync: OneDrive (MSAL + Microsoft Graph)
- [ ] Cloud sync: iCloud WebDAV (experimental, Apple ID app-specific password)
- [ ] Cloud sync: Samsung Cloud (conditional on Build.MANUFACTURER == "samsung")
- [ ] Settings: folder picker intent for custom output/tmp/inbox directories
- [ ] SD card auto-detection: grey out SD options when no SD card present
- [ ] API credentials: EncryptedSharedPreferences for GitHub/ADS tokens
- [ ] Inbox watcher: FileObserver on /sdcard/Ptolemy/ptorrents/ for MTP-dropped files
- [ ] Progress bar: gradient fill (red→cyan→blue) via ClipDrawable + LinearGradient

## Corpus & crawler

- [ ] ADS client: NASA ADS literature graph traversal
- [ ] ASCL client: Astrophysics Source Code Library → Fortran code discovery
- [ ] GitHub client: zero-scope PAT (PTOL_SEED_TOKEN) → Fortran source traversal
- [ ] FortranParser: extract subroutine names, PARAMETER constants, comments
- [ ] TAP client: IVOA Table Access Protocol for VizieR, Gaia, SIMBAD
- [ ] Language ptorrent type: see_text() training path → psi2 language geometry bin
- [ ] psi2 persistence: add psi2 + label_map to save_session / load_checkpoint
- [ ] WordNet → Mind's Eye: map WordNet synset geometry into psi2 label_map

## Dataset traversal

- [ ] Dataset ptorrent runner: source adapter dispatch (tap/rest/file_list/zip/stream)
- [ ] SPARC rotation curve test kernel: mind_eye.see() encoding for (r, V_obs, V_bar)
- [ ] Output formats: CSV, FITS, VOTable, HDF5, Parquet, BibTeX, MRT
- [ ] Model hook: Anthropic API integration (fire on page_studied / checkpoint / complete)
- [ ] Model hook: OpenAI-compatible endpoint
- [ ] Model hook: MCP tool call (claudecode type — inject results into Claude Code session)

## PTorrent protocol

- [ ] Full BitTorrent seeding of corpus bins and datasets
      Once a device builds a monad checkpoint, it becomes a seed.
      Trained .bin files propagate peer-to-peer — no adb pull required.
      DHT peer discovery for trained .bin distribution.
      Tracker support in .ptorrent files (trackers[] field).
      Multi-peer bin download + merge (β weighted average, A-matrix union).
      Seeder reputation: word_count + BAO proximity as quality signal.
      "Seed what you trained" — contribute compute, receive community bins.
      Cross-device field convergence toward shared corpus ground state.
      Full BitTorrent protocol compliance: piece hashing, choking, rarest-first.
      libtorrent Python bindings via Chaquopy — evaluate feasibility on ARM64.

## Dataset Phonebook

PTorrent as a dynamically-current, nearly exhaustive, interdisciplinary index
of publicly available datasets — not the datasets themselves, but where they
live, what format they use, whether an API exists, and whether bulk dumps are
available. One .ptorrent file per dataset. Machine-readable. Community-maintained.
Crawled and verified automatically. The dataset index that doesn't exist yet.

- [ ] `phonebook` type in .ptorrent format spec — see spec/ptorrent-format-v1.md
- [ ] Meta-crawler: Kaggle API → auto-generate .ptorrent phonebook entries
      (~250,000+ datasets; batch via kaggle.com/api/v1/datasets/list)
- [ ] Meta-crawler: HuggingFace Hub API → auto-generate phonebook entries
      (huggingface.co/api/datasets — NLP, vision, multimodal, audio)
- [ ] Meta-crawler: Zenodo REST API → academic cross-disciplinary deposits
      (zenodo.org/api/records?type=dataset — biology, physics, social science)
- [ ] Meta-crawler: Figshare API → research data repository
- [ ] Meta-crawler: data.gov API → US federal open data (~300,000 datasets)
- [ ] Meta-crawler: data.europa.eu → EU open data portal
- [ ] Meta-crawler: World Bank Open Data API → economic/development indicators
- [ ] Meta-crawler: OpenAlex API → bibliometric + dataset provenance graph
- [ ] Specialty crawlers (hand-curated, high-value):
      LMFDB — number theory, L-functions, modular forms (already a ptorrent)
      UniProt — protein sequences and annotations
      ENCODE — functional genomics
      NCBI/GenBank — nucleotide sequences
      NASA Earthdata — satellite, climate, atmospheric
      USGS — geophysical, hydrological, seismic
      SPARC — galaxy rotation curves (dark matter)
      SDSS SkyServer — astronomical survey
      ClinicalTrials.gov — medical trial registry (already partially crawled)
      PubChem — chemical compound database
      ChEMBL — bioactivity data for drug discovery
      OpenStreetMap Geofabrik dumps — geospatial
      Common Crawl — web corpus index entry (URL to dumps only, not the data)
      LAION — image-text pairs (index entry + dump location only)
      The Pile sources — cross-reference with EleutherAI source list
      BooksCorpus successors — open book datasets
      SEC EDGAR — financial filings
      PACER (court records) — legal, where accessible
      USPTO — patent text and citations
      arXiv bulk access — scientific preprints
      Project Gutenberg — literary canon
      Internet Archive — open-access collections
- [ ] Phonebook .ptorrent schema fields (add to spec):
      dataset_url, api{type,endpoint,auth,rate_limit,docs_url},
      dumps[{url,size_gb,format,update_freq,last_verified}],
      license (SPDX), citation (DOI), domain_tags, size_records,
      maintainer, last_dataset_update, last_verified_by_ptorrent
- [ ] Verification crawler: re-crawl all phonebook entries on a schedule
      Check: API alive? Dump URL returns 200? Schema changed?
      Update last_verified field. Flag stale entries.
- [ ] Phonebook browser: read-only APK mode showing the full index
      Filter by domain_tag, format, API availability, dump availability
      One-tap: "seed this dataset" — converts phonebook entry to active job
- [ ] Phonebook distribution: the phonebook itself seeds via PTorrent
      All .ptorrent phonebook files bundled as a meta-ptorrent
      Peers share the phonebook the same way they share bins
- [ ] Community submission: PR-based workflow for adding new phonebook entries
      Lint check: required fields present, URL reachable, license valid SPDX

## Platforms

- [ ] Desktop runner: ptorrent CLI tool (Python, uses same corpus.py)
- [ ] PTorrent daemon: long-running desktop service with socket API
- [ ] iOS: evaluate Swift/Objective-C port of monad.c (PtolC PTOL binary compatible)
