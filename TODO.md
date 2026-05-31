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

- [ ] Torrent-style user/dataset seeding protocol
      DHT peer discovery for trained .bin distribution
      Tracker support in .ptorrent files (trackers[] field)
      Multi-peer bin download + merge (β weighted average, A-matrix union)
      Seeder reputation: word_count + BAO proximity as quality signal
      "Seed what you trained" — contribute compute, receive community bins
      Cross-device field convergence toward shared corpus ground state

## Platforms

- [ ] Desktop runner: ptorrent CLI tool (Python, uses same corpus.py)
- [ ] PTorrent daemon: long-running desktop service with socket API
- [ ] iOS: evaluate Swift/Objective-C port of monad.c (PtolC PTOL binary compatible)
