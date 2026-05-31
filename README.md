# PTorrent

A robots.txt-compliant, API-first corpus, language, and dataset traversal system with a Model Context Protocol (MCP) server. Currently available as an Android APK. More platforms coming.

## What it does

PTorrent uses `.ptorrent` descriptor files to define crawl jobs. The APK runs those jobs on your phone while it charges — fetching text via APIs (Wikipedia MediaWiki, NASA ADS, arXiv, VizieR TAP, GitHub, OEIS, LMFDB), training sedenion field engines, and saving trained `.bin` files.

Three ptorrent types:

| Type | Purpose | Output |
|------|---------|--------|
| `corpus` | Train a sedenion field on web content | `.bin` checkpoint |
| `language` | Train the language output geometry | `.bin` checkpoint |
| `dataset` | Traverse a dataset in-situ, return measurements | JSON / CSV / FITS / HDF5 / VOTable |

## APK — PTorrent 3.0

- Ptolemy Holcus Engine v1.218
- robots.txt compliant crawler with Mozilla/Ptolemy UA negotiation
- Wikipedia MediaWiki extracts API (clean plaintext — no HTML stripping)
- SSL fallback for misconfigured institutional servers (HyperPhysics etc.)
- MCP server toggle (JSON-RPC 2.0 — connect Claude Code via ADB forward)
- PGui color scheme: red → cyan → blue (J_pos / critical line / J_neg)
- Settings: storage, cloud sync stubs, API credentials, seeder behaviour

[Download APK 3.0](releases/)

## ADB quick start

```bash
# Push a ptorrent to the phone inbox
adb push my.ptorrent /sdcard/Ptolemy/ptorrents/

# Pull a trained bin when done
adb pull /sdcard/Android/data/com.ptolemy.seeder.debug/files/monad_physics.bin ~/.ptolemy/

# MCP server (if enabled in Settings)
adb forward tcp:3001 tcp:3000
# then point Claude Code MCP config to localhost:3001/mcp
```

## Ptorrent file format

See [wiki/PTorrent-File-Spec.md](wiki/PTorrent-File-Spec.md)

## Output formats

See [wiki/Output-Formats.md](wiki/Output-Formats.md)

## Model insertion API

See [wiki/Model-Insertion-API.md](wiki/Model-Insertion-API.md)

## License

MIT
