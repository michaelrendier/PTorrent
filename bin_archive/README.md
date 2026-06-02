# PTorrent — Monad Checkpoint Archive

This directory contains monad checkpoint binary files produced by the
PtolemySeeder Android APK. Bin files are excluded from git (see .gitignore) —
they live here on disk only.

## clean/

GEOMETRIC INIT state — vocabulary loaded, prime-hash E-values assigned,
A-matrix built, but no corpus text has been fed (word_count = 0).

These are safe starting points for new training runs. Pull from a phone
immediately after the Seeder builds the initial checkpoint, before any
seeding begins.

Format: Python pickle (Chaquopy 15.0.1 / Python 3.12 compatible).
Load via `Engine.load_checkpoint(path)` in `monad.py`.

Files prefixed `phone_` were pulled directly from a device via adb.
Files prefixed `holcus_` were the working copies in PtolemyHolcus/.

## dirty/

Post-training or polluted states. Use for analysis of learned state only —
do not use as starting points without understanding what training was applied.

- `monad_wordnet.bin` / `holcus_monad_wordnet.bin` — POLLUTED from
  ~/Documents PDF OCR artifact ingest. PASS threshold but not clean.
- `monad_sedenion_after_*.bin` — post-burn training checkpoints from 2026-05-31.
- `phone_20260601_*.bin` — snapshot pulled from phone on 2026-06-01 after seeding.
- `monad_20260531_234723.bin` — full state backup before sedenion burn run.

## Note on bin file format

Monad bins from v1.218 onward are Python pickle files.
Older bins (e.g. monad_wordnet.bin before 2026-05-15) may be C binary format.
The C binary format is detected by `eval_checkpoint.py`; pickle bins will
produce "Bad magic number" errors in that tool — load with `load_checkpoint()`
instead.
