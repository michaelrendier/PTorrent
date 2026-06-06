# PTorrent TODO

---

## 1. Dataset Phonebook — PRIORITY #1

PTorrent as a dynamically-current, nearly exhaustive, interdisciplinary index
of publicly available datasets — not the datasets themselves, but where they
live, what format they use, whether an API exists, and whether bulk dumps are
available. One .ptorrent file per dataset. Machine-readable. Community-maintained.
Crawled and verified automatically.

Offloading dataset traversal to an LTE device frees the desktop to keep working.
A phone or tablet running PTorrent crawls and evaluates datasets in the background
at LTE speeds. The desktop never stalls. The Phonebook is the directory that makes
this possible at scale — without it, every researcher rediscovers the same datasets
from scratch.

See wiki/dataset_phonebook_seed_list.md for the manual seed catalogue (400+ entries).

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
- [ ] Meta-crawler: Papers With Code API → ML benchmarks + linked datasets
- [ ] Meta-crawler: IEEE DataPort API → engineering datasets
- [ ] Meta-crawler: OpenML API → 20K+ ML datasets with structured metadata
- [ ] Meta-crawler: UCI ML Repository API (2023+) → classical ML datasets
- [ ] Specialty crawlers (hand-curated, high-value):
      LMFDB — number theory, L-functions, modular forms (already a ptorrent)
      UniProt — protein sequences and annotations
      ENCODE — functional genomics
      NCBI/GenBank — nucleotide sequences
      NASA Earthdata — satellite, climate, atmospheric
      USGS — geophysical, hydrological, seismic
      SPARC — galaxy rotation curves (dark matter)
      SDSS SkyServer — astronomical survey
      ClinicalTrials.gov — medical trial registry
      PubChem — chemical compound database
      ChEMBL — bioactivity data for drug discovery
      OpenStreetMap Geofabrik dumps — geospatial
      Common Crawl — index entry (dump location only, not the data)
      LAION — image-text pairs (index entry + dump location only)
      The Pile sources — cross-reference with EleutherAI source list
      SEC EDGAR — financial filings
      PACER / CourtListener — legal, where accessible
      USPTO PatentsView — patent text and citations
      arXiv bulk access — scientific preprints
      Project Gutenberg — literary canon
      Internet Archive — open-access collections
      Academic Torrents — existing BitTorrent research dataset distribution
- [ ] Standards & Specifications crawler (see Corpus & Crawler section)
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

---

## 2. PTorrent Protocol — Full BitTorrent Seeding

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

---

## 3. Corpus & Crawler

- [ ] ADS client: NASA ADS literature graph traversal
- [ ] ASCL client: Astrophysics Source Code Library → Fortran code discovery
- [ ] GitHub client: zero-scope PAT (PTOL_SEED_TOKEN) → Fortran source traversal
- [ ] FortranParser: extract subroutine names, PARAMETER constants, comments
- [ ] TAP client: IVOA Table Access Protocol for VizieR, Gaia, SIMBAD
- [ ] Language ptorrent type: see_text() training path → psi2 language geometry bin
- [ ] psi2 persistence: add psi2 + label_map to save_session / load_checkpoint
- [ ] WordNet → Mind's Eye: map WordNet synset geometry into psi2 label_map
- [ ] Standards & Specifications corpus:
      IETF RFCs (datatracker.ietf.org/doc/html — all public, 9000+ documents)
      W3C Recommendations (w3.org/TR — HTML, CSS, XML, SVG, WebAssembly, etc.)
      ECMA Standards (ecma-international.org — ECMAScript/JS, JSON, C#, Dart)
      Python PEPs (peps.python.org — all public, definitive Python spec)
      IEEE Xplore open-access standards (partial — many paywalled; target open subset)
      NIST publications (nvlpubs.nist.gov — FIPS, SP 800-series cybersecurity, etc.)
      NIST DLMF (dlmf.nist.gov — Digital Library of Mathematical Functions)
      OpenGroup / POSIX (pubs.opengroup.org — Single UNIX Specification)
      ISO/IEC freely available standards (standards.iso.org/ittf/PubliclyAvailableStandards)
      Unicode Standard (unicode.org/versions/latest — 1900+ page specification)
      ANSI/INCITS open publications (where publicly released)
      WHATWG Living Standards (html.spec.whatwg.org, fetch, streams, encoding)
      OpenAPI Specification (spec.openapis.org — REST API description standard)
      JSON Schema (json-schema.org/specification)
      Protocol Buffers / gRPC spec (protobuf.dev)
      OGC Standards (ogc.org/standards — geospatial: WMS, WFS, GeoJSON, KML)
      OASIS Standards (docs.oasis-open.org — MQTT, AMQP, SAML, XLIFF, LegalXML)
      OMG Standards (omg.org/spec — UML, BPMN, CWM)
      ASHRAE Standards summaries (ashrae.org — HVAC, building energy, ventilation)
      ASTM freely available standards (subset — astm.org/sitemap)
      ASME open publications (asme.org — mechanical engineering codes)
      ASCE open publications (assce.org — civil engineering standards)
      Actuarial Standards of Practice / ASOP (actuarialstandardsboard.org — all public)
      SAE open standards (sae.org — automotive: J1979 OBD-II, J1772 EV charging)
      USB-IF public specifications (usb.org/documents — USB 3.2, USB4, USB-C)
      Bluetooth SIG core spec (bluetooth.com/specifications/specs — partial public)
      WiFi Alliance specifications (wi-fi.org — summary docs public)
      MPEG/ISO IEC JTC1 working documents (some public via MPEG site)
      PDF Reference / ISO 32000 (pdfa.org and adobe.com/devnet — PDF spec)
      DICOM Standard (dicomstandard.org/current — medical imaging interchange)
      HL7 FHIR (hl7.org/fhir — healthcare data exchange, fully public)
      OpenEHR specifications (openehr.org/programs/specification)
      FIX Protocol (fixtrading.org/standards — financial messaging)
      SWIFT MT/MX message standards (swift.com — financial; partial public)
      AUTOSAR Classic/Adaptive (autosar.org — automotive embedded, partial)
      CAN bus / ISO 11898 (partial public via Bosch original spec PDF)
      NMEA 0183/2000 (nmea.org — GPS/marine data sentences; partial)
      IEC 61850 summary (substation automation; partial public)
      OpenDocument Format / ODF (oasis-open.org/standards — office document format)

---

## 4. Dataset Traversal

- [ ] Dataset ptorrent runner: source adapter dispatch (tap/rest/file_list/zip/stream)
- [ ] SPARC rotation curve test kernel: mind_eye.see() encoding for (r, V_obs, V_bar)
- [ ] Output formats: CSV, FITS, VOTable, HDF5, Parquet, BibTeX, MRT
- [ ] Model hook: Anthropic API integration (fire on page_studied / checkpoint / complete)
- [ ] Model hook: OpenAI-compatible endpoint
- [ ] Model hook: MCP tool call (claudecode type — inject results into Claude Code session)

---

## 5. APK — Features

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
- [ ] Torrent list: add vertical ScrollView/RecyclerView so job list scrolls independently
      of the rest of the UI — currently truncates when job count exceeds screen height
- [ ] Status section: separate panel below the torrent list, with its own scrollbar,
      showing per-job live status (bytes fetched, URL count, errors, ETA)
      — decoupled from the job list so both scroll independently
- [ ] Status section: completions list is foldable (ExpandableListView or animated
      visibility toggle), collapsed by default — tap header to expand full list of
      finished jobs with their output paths and byte counts
- [ ] File location: tap any completed job to open its output .bin in Android Files
      (ACTION_VIEW with FileProvider URI); show the /sdcard/PTorrent/bins/ path
      inline in the status panel so the user always knows where the data landed

---

## 6. Platforms

- [ ] Desktop runner: ptorrent CLI tool (Python, uses same corpus.py)
- [ ] PTorrent daemon: long-running desktop service with socket API
- [ ] iOS: evaluate Swift/Objective-C port of monad.c (PtolC PTOL binary compatible)

---

## 7. Responsible Disclosure Open Protocol (RDOP)

PTorrent implements the RDOP — a formally-specified open protocol for
responsible disclosure of security vulnerabilities discovered during research.
Full specification: wiki/Responsible-Disclosure-Protocol.md

### 7.1 Protocol Formalization

- [x] CLASSIFY chain transaction — security classification with embargo enforcement
- [x] NOTIFY chain transaction — agency notification record (committed before send)
- [x] ACKNOWLEDGE chain transaction — researcher consent with warning_hash
- [x] DISCLOSE chain transaction — embargo lift with classification downgrade
- [x] REVOKE chain transaction — access withdrawal
- [x] FLAG chain transaction — malicious file block
- [x] EVALUATE chain transaction — data transversal result with parallel semantics
- [x] security block in .ptorrent format — classification, level, embargo_until
- [x] disclosure section in .peval format — chain references in evaluation output
- [ ] Automatic DISCLOSE on embargo_until date (scheduled chain job)
- [ ] CNA (CVE Numbering Authority) application — PTorrent as a CNA

### 7.2 Agency Interface

- [x] NIST NVD adapter — CVE database query (check_cve_exists)
- [x] CISA KEV adapter — Known Exploited Vulnerabilities catalog
- [x] STIX 2.1 builder — vulnerability/CoA/report/bundle (pure Python)
- [x] Notifier — NIST, CISA, MITRE, CERT/CC, NCSC, ENISA dispatch
- [x] TAXII 2.1 client — CISA AIS machine-readable submission
- [ ] CISA AIS endpoint configuration — contact CISA for researcher TAXII access
- [ ] NIST NVD structured intake — contact NIST for RDOP-format intake channel
- [ ] MITRE CNA registration — apply to become CVE Numbering Authority
- [ ] CERT/CC formal partnership — integrate CERT/CC Vince platform
- [ ] Bidirectional: receive CISA advisories as ptorrent phonebook entries
      (CISA publishes advisories as JSON — auto-generate phonebook entries)

### 7.3 APK Disclosure UI

- [ ] Level 3 acknowledgment screen — full-screen interstitial, ORCID entry required
- [ ] Disclosure status card — shows NOTIFY tx history for classified files
- [ ] Embargo countdown — days remaining displayed on classified corpus cards
- [ ] Auto-DISCLOSE notification — APK notifies researcher when embargo date reached
- [ ] Agency response tracking — record CVE numbers, advisory IDs in chain notes

### 7.4 F-Droid and GNU Compliance

- [ ] Replace Chaquopy with process-separated Python runtime (MCP socket bridge)
      Chaquopy is proprietary — required for F-Droid inclusion
      Architecture: SeedService.kt → Unix socket → seed_runner.py (separate process)
      Python component: embed CPython 3.12 ARM64 as asset, load via JNI
      Benefit: removes commercial dependency, enables F-Droid distribution
- [ ] F-Droid metadata file (fastlane/metadata/android/)
      title, short_description, full_description, changelogs
      screenshots, feature graphic
- [ ] F-Droid reproducible build — deterministic APK from source
- [ ] GNU makefile for desktop components
- [ ] CERN OHL consideration for any hardware designs distributed via PTorrent
- [ ] GNU AGPL evaluation — should PTorrent server components be AGPL?
      (network use provision — AGPL ensures server-side modifications share back)

### 7.5 User Profiles and ORCID

- [ ] UserProfileActivity.kt — ORCID entry, verification, profile storage
- [ ] UserProfileManager.kt — ORCID API verification, EncryptedSharedPreferences
- [ ] Seeding gate in SeedService — isProfileComplete() check before any corpus starts
- [ ] peer_id reform: ORCID:xxxx-xxxx-xxxx-xxxx@device_hash format throughout
- [ ] GitHub username linking via ORCID public profile
- [ ] Profile display in ChainActivity — researcher identity per seeder

### 7.6 Blockchain Live Seeds Face

- [ ] ChainActivity.kt — dedicated blockchain state screen
      Live seeders list with ORCID identity and seeding status
      Recent transactions timeline (ANNOUNCE/SEED/EVALUATE/NOTIFY/DISCLOSE)
      Chain health: tip_hash, block count, last commit
      Per-file seeder count with contact links
      Anonymous seeder warnings (no-profile peers flagged)
- [ ] Chain sync — share chain state between devices over LAN/WiFi
- [ ] Conflict resolution — longest-valid-chain rule for divergent chain states

### 7.7 Security Data Corpus

- [ ] monad_security.bin — train on security vocabulary:
      NIST NVD CVE descriptions (public, free via NVD API)
      CISA KEV entries (public, free download)
      MITRE ATT&CK matrix (public, JSON download)
      MITRE CWE list (public, XML download)
      NIST SP 800-series publications (public PDF)
      CERT/CC vulnerability notes (public)
      NIST FIPS publications (public)
- [ ] security.ptorrent — corpus descriptor for monad_security.bin
- [ ] Sedenion mapping of CVE vocabulary documented in wiki

### 7.8 RDOP Open Standard Outreach

- [ ] Submit RDOP to OASIS Open for consideration as a TC contribution
      (STIX TC or a new Vulnerability Disclosure TC)
- [ ] Present RDOP at FIRST (Forum of Incident Response and Security Teams)
      FIRST annual conference — primary international CSIRT/CERT venue
- [ ] IEEE S&P / CCS / USENIX Security — workshop paper on RDOP
- [ ] Contact ENISA about EU-wide RDOP adoption (NIS2 directive context)
- [ ] Contact NCSC (UK) — their vulnerability reporting team
- [ ] ISO/IEC 29147 alignment — map RDOP to international standard
- [ ] security.txt (RFC 9116) — add .well-known/security.txt to PTorrent GitHub

---

## 8. IP — Patents, Trademarks, Copyright

Goal: defensive protection. Prevent enclosure of the RedBlue Geometries and
SMMIP/Ainulindale framework by third parties after publication. The goal is
NOT exclusivity — it is ensuring the knowledge remains permanently open.

### 8.1 Patent (Defensive — Software Implementations)

- [ ] Engage IP attorney — patent prosecution counsel with CS/mathematics depth
      Priority candidates: Fish & Richardson (fr.com), Quinn Emanuel (quinnemanuel.com)
      Ask specifically for partner with algebra/cryptography background
      Explore contingency / equity arrangement for initial prosecution costs
- [ ] Patent applications — specific software implementations (not the mathematics itself):
      [ ] LSHS engine architecture (Lagrangian Self-Adjoint Hyperindexing Speaking Model)
          σ-face evaluation method (J_ratio buoyancy table, stratum assignment)
      [ ] PTorrent chain protocol — RDOP transaction types as a disclosure protocol
      [ ] RedBlue Geometry evaluation engine — H_hat_RB computational method
      [ ] UDEO locus computation — secp256k1 GF(2) nilpotency scan (secp256k1_locus.py)
- [ ] Issue patent pledge post-grant:
      "These patents will never be enforced against non-commercial, academic,
       open-source, or security research uses." (Tesla/IBM open patent model)
- [ ] Prior art protection (automatic, free — no attorney required):
      IACR ePrint submission post-2026-12-02 = global prior art on the mathematics
      No one can patent RedBlue Geometries or the T_n/GF(2) Frobenius result
      after that date. Publication IS the protection for the mathematical content.

### 8.2 Trademark

- [ ] "RedBlue Geometries" — trademark application (USPTO, class 42: scientific research)
      Prevents any third party from calling their product "RedBlue Geometries"
      Does NOT restrict the science — restricts the brand name only
- [ ] "PTorrent" — trademark application (USPTO, class 42 + class 9: software)
- [ ] "LSHS" / "Lagrangian Self-Adjoint Hyperindexing Speaking Model" — evaluate
- [ ] "Ainulindale" — evaluate (note: Tolkien Estate may have prior claim on the word)
      Consider: "Ainulindale Conjecture" as the scientific term (fair use for science)
      Do NOT trademark the word itself — risk of conflict with Tolkien Estate

### 8.3 Copyright

- [ ] Copyright registration (US Copyright Office) for:
      The UDEO paper (post-embargo, post-IACR publication)
      The Ainulindale Conjecture papers (D-CS, D-M, D-P, D-CHEM) as published
      The PTorrent chain protocol specification document
      monad.py source code (automatic copyright, but registration strengthens enforcement)
- [ ] License audit — ensure consistent licensing across repos:
      TuringStack: MIT + responsible disclosure notice (done)
      PtolemyHolcus: MIT (current) — evaluate GPL/AGPL for F-Droid compliance
      Ainulindale: MIT (current) — papers are CC-BY on publication

### 8.4 Domain IP Alignment

- [ ] thewanderinggod.tech — PTorrent / LSHS product site
- [ ] michaelrendier.com — researcher personal/academic site
- [ ] michaelrendier.info — real-world impact work (Erika Schafer collab, D-CHEM)
- [ ] michaelrendier.online — personal tracker / Manfred Macx mode
- [ ] Ensure all domain WhoIs records are consistent with trademark registrations
