# POISON NOTE: monad_python

* file: `monad_python.bin`; identical copies: `holcus_monad_python.bin`
* sha256: `339f177c23b06ce7b237a3d1836f805c160d5d207e9ce0936ef31b85a3526194`; size 5,690,749 bytes; pickle vv1.218; vocabulary 25,541; word_count 0
* measured by `VAPMIP/Wernicke/sanitize/sanitize_v0.py` (deterministic ruleset), 2026-10-17
* quarantined by the sanitiser: **13,457 of 25,541 (52.7%)**; admitted tiers A 7,181 (in WordNet), B 4,592 (candidates), C 129 (proper nouns), F 182 (function words)

| tier:reason | tokens | examples |
|---|---|---|
| A:in_wordnet | 7,181 | 'data', 'model', 'python', 'documentation', 'report', 'bug' |
| Q:garbage | 6,074 | '3.14.5', '/', '»', '¶', 'id(x', 'e.g' |
| Q:formula | 5,913 | '=', '__repr__', '__str__', '<=', '<', '+' |
| B:candidate_evidence_pending | 3,808 | 'cpython', 'cannot', 'tuples', 'cyclically', 'would', 'tuple' |
| Q:number | 879 | '3', '3.1', '1', '3.2', '3.9', '3.14' |
| B:compound_of_known_parts | 784 | 'garbage-collected', 'reference-counting', 'floating-point', 'machine-level', 'single-precision', 'read-only' |
| Q:no_vowel | 249 | 'gc', 'str', 'chr', 'cls', 'tb', 'bsd' |
| Q:ref | 234 | 'https://ocert.org/advis, '2147483647', 'https://github.com/pyth, 'http://barry.warsaw.us/, 'http://www.wikipedia.co, 'https://github.com/pyth |
| F:function_word | 182 | 'a', 'and', 'are', 'for', 'all', 'is' |
| C:proper_noun | 129 | 'bruce', 'forth', 'augustus', 'galahad', 'warsaw', 'oh' |
| Q:chrome | 55 | 'this', 'page', 'navigation', 'the', 'in', 'changes' |
| Q:single_letter | 26 | 'x', 'b', 'c', 'd', 'e', 'f' |
| Q:consonant_run | 11 | 'richcmpfunc', 'goldschmidt', 'httpsconnection', 'threadinghttpserver', 'abstracthttphandler', 'ncmdshow' |
| Q:time_expression | 8 | '3rd', '26th', '10th', '10s', '0s', '2nd' |
| Q:non_latin_or_symbol | 6 | 'ü', 'ı', 'ſ', 'pro----gram-files', 'pro--gram', 'à' |
| Q:greek | 2 | 'τ', 'π' |

Top 30 words by fire count: '3', 'data', 'model', 'python', '3.14.5', 'documentation', 'this', 'page', 'report', 'a', 'bug', 'improve', 'show', 'source', 'navigation', 'index', 'modules', '|', 'next', 'previous', '»', 'the', 'language', 'reference', 'theme', 'auto', 'light', 'dark', '¶', '3.1'

Cause: not established; measured only. A code or specialist corpus can read as 'quarantined' here because its vocabulary is identifiers and symbols, which is a different thing from page-chrome poisoning.

Status: moved to `PTorrent/bin_archive/dirty/` on 2026-10-17 (Cody's instruction); kept as a historical record, not a starting point. Bins are gitignored (too large for GitHub): this note is what is committed.
