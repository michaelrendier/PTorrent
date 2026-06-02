#!/usr/bin/env bash
# android/build_apk.sh — Sync Python sources and build the APK.
# Run from the repo root or from android/.
#
# Usage:
#   bash android/build_apk.sh           # build only
#   bash android/build_apk.sh --install # build + adb install

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
PROJECT="$SCRIPT_DIR/PtolemySeeder"
PYDIR="$PROJECT/app/src/main/python"
ASSETS="$PROJECT/app/src/main/assets"
CORPORA="$REPO_ROOT/code-corpora"
PTORRENTS="$REPO_ROOT/ptorrents"

echo "[seeder] Syncing Python sources…"
cp "$REPO_ROOT/monad.py"                    "$PYDIR/monad.py"
cp "$REPO_ROOT/skills/__init__.py"          "$PYDIR/skills/__init__.py"
cp "$REPO_ROOT/skills/study.py"             "$PYDIR/skills/study.py"
cp "$REPO_ROOT/skills/corpus.py"            "$PYDIR/skills/corpus.py"
cp "$REPO_ROOT/skills/corpus_python.py"      "$PYDIR/skills/corpus_python.py"
cp "$REPO_ROOT/skills/corpus_c.py"           "$PYDIR/skills/corpus_c.py"
cp "$REPO_ROOT/skills/corpus_physics.py"     "$PYDIR/skills/corpus_physics.py"
cp "$REPO_ROOT/skills/corpus_mathematics.py" "$PYDIR/skills/corpus_mathematics.py"
cp "$REPO_ROOT/skills/foundations.py"        "$PYDIR/skills/foundations.py"
cp "$REPO_ROOT/skills/meaning.py"            "$PYDIR/skills/meaning.py"
cp "$REPO_ROOT/skills/fermat_lattice.py"     "$PYDIR/skills/fermat_lattice.py"
# seed_runner.py lives in the assets python dir — no separate copy needed

echo "[seeder] Syncing corpus assets…"
cp "$REPO_ROOT/foundations.txt"              "$ASSETS/foundations.txt"
cp "$REPO_ROOT/meaning.txt"                  "$ASSETS/meaning.txt"
cp "$REPO_ROOT/war-corpus.txt"               "$ASSETS/war_corpus.txt"
cp "$CORPORA/python_corpus.txt"              "$ASSETS/python_corpus.txt"
cp "$CORPORA/c_corpus.txt"                   "$ASSETS/c_corpus.txt"
cp "$CORPORA/physics_corpus.txt"             "$ASSETS/physics_corpus.txt"
cp "$CORPORA/mathematics_corpus.txt"         "$ASSETS/mathematics_corpus.txt"
cp "$PTORRENTS/english_corpus.txt"          "$ASSETS/english_corpus.txt"
cp "$SCRIPT_DIR/corpus_list.json"           "$ASSETS/corpus_list.json"

echo "[seeder] Building APK…"
cd "$PROJECT"
./gradlew assembleDebug

APK="$PROJECT/app/build/outputs/apk/debug/app-debug.apk"
echo "[seeder] Built: $APK ($(du -h "$APK" | cut -f1))"

if [[ "$1" == "--install" ]]; then
    echo "[seeder] Installing via adb…"
    adb install -r "$APK"
    echo "[seeder] Installed. Launch Ptolemy Seeder on your phone."
fi
