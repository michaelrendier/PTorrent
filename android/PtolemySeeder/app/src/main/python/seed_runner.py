"""
seed_runner.py — Dynamic torrent-style corpus seeder for Android.

Reads corpus_list.json from the app files directory.
Creates one GenericCorpus + Engine per entry, runs all in parallel threads.
New corpora can be added by pushing an updated corpus_list.json via adb
without rebuilding the APK, or by dropping a .ptorrent file into inbox/.

Called from SeedService.kt via Chaquopy.
"""

import json
import os
import threading
from typing import Any, Callable, Dict, List, Optional

from monad import Engine
from skills.corpus import GenericCorpus, parse_corpus_txt


def _build_corpus(entry: Dict[str, Any], files_dir: str) -> GenericCorpus:
    """Construct a GenericCorpus from a corpus_list.json entry.

    :param entry: Dict with name, bin, txt, primary_tags keys.
    :param files_dir: App external files directory.
    :returns: Configured GenericCorpus instance.
    :rtype: GenericCorpus
    """
    txt_path = os.path.join(files_dir, entry['txt']) if entry.get('txt') else None
    bin_path = os.path.join(files_dir, entry['bin'])
    primary_tags = set(entry.get('primary_tags', []))

    if txt_path is None or not os.path.exists(txt_path):
        war_fallback = os.path.join(files_dir, 'war_corpus.txt')
        if os.path.exists(war_fallback):
            txt_path = war_fallback

    return GenericCorpus(
        engine=Engine(),
        txt_path=txt_path or '',
        bin_path=bin_path,
        name=entry.get('name', entry['bin']),
        interval=entry.get('interval', 60),
        primary_tags=primary_tags,
        primary_weight=float(entry.get('primary_weight', 2.0)),
        context_weight=float(entry.get('context_weight', 1.0)),
    )


def run_all(
    files_dir: str,
    on_progress: Callable,
    check_interval: int = 15,
) -> Dict[str, Any]:
    """Run all corpus seed passes defined in corpus_list.json (blocking).

    Each corpus runs in its own thread. Returns when all are exhausted.

    :param files_dir: App external files directory.
    :param on_progress: Callable(name, tag, url, idx, total, studied, skipped).
    :param check_interval: Seconds between network retry attempts.
    :returns: Dict of results keyed by corpus name.
    :rtype: dict
    """
    list_path = os.path.join(files_dir, 'corpus_list.json')
    if not os.path.exists(list_path):
        raise FileNotFoundError(f'corpus_list.json not found in {files_dir}')

    with open(list_path, encoding='utf-8') as f:
        corpus_list: List[Dict[str, Any]] = json.load(f)

    results: Dict[str, Any] = {}
    threads = []

    for entry in corpus_list:
        try:
            corpus = _build_corpus(entry, files_dir)
        except Exception as e:
            name = entry.get('name', entry.get('bin', '?'))
            results[name] = {'complete': False, 'error': f'build failed: {e}'}
            continue
        name = entry.get('name', entry['bin'])
        t = threading.Thread(
            target=_seed_one,
            args=(corpus, name, on_progress, check_interval, results),
            daemon=True,
            name=f'seed-{name[:16]}',
        )
        threads.append(t)

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    return results


def run_one(
    entry: Dict[str, Any],
    files_dir: str,
    on_progress: Callable,
    check_interval: int = 15,
) -> Dict[str, Any]:
    """Seed a single corpus entry (blocking). Used for PTorrent inbox additions.

    :param entry: corpus_list.json-style dict.
    :param files_dir: App external files directory.
    :param on_progress: Progress callback.
    :param check_interval: Network retry interval seconds.
    :returns: Seed result dict.
    :rtype: dict
    """
    try:
        corpus = _build_corpus(entry, files_dir)
    except Exception as e:
        return {'complete': False, 'error': f'build failed: {e}'}
    results: Dict[str, Any] = {}
    name = entry.get('name', entry.get('bin', 'ptorrent'))
    _seed_one(corpus, name, on_progress, check_interval, results)
    return results.get(name, {})


def _seed_one(
    corpus: GenericCorpus,
    name: str,
    on_progress: Callable,
    check_interval: int,
    results: Dict[str, Any],
) -> None:
    """Seed one corpus; called from a thread. Writes result into *results* dict.

    :param corpus: GenericCorpus instance.
    :param name: Corpus name.
    :param on_progress: Progress callback.
    :param check_interval: Network retry interval seconds.
    :param results: Shared results dict.
    """
    def _cb(tag: str, url: str, idx: int, total: int,
            studied: int, skipped: int) -> None:
        try:
            on_progress(name, tag, url, idx, total, studied, skipped)
        except Exception:
            pass
    try:
        results[name] = corpus.seed(
            on_progress=_cb,
            check_interval=check_interval,
        )
    except Exception as e:
        results[name] = {'complete': False, 'error': str(e)}
