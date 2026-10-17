# POISON NOTE: monad_c

* file: `monad_c.bin`; identical copies: `holcus_monad_c.bin`
* sha256: `fe95125253737683dacffe3c94c81b224c1569ffb3f18db1f0f8a081998f8afb`; size 1,528,490 bytes; pickle vv1.218; vocabulary 8,189; word_count 0
* measured by `VAPMIP/Wernicke/sanitize/sanitize_v0.py` (deterministic ruleset), 2026-10-17
* quarantined by the sanitiser: **3,456 of 8,189 (42.2%)**; admitted tiers A 3,485 (in WordNet), B 1,095 (candidates), C 5 (proper nouns), F 148 (function words)

| tier:reason | tokens | examples |
|---|---|---|
| A:in_wordnet | 3,485 | 'previous', 'home', 'next', 'open', 'group', 'base' |
| Q:formula | 2,068 | 'pthread_create', '<<<', '>>>', '<', '>', 'pthread_create(pthread_ |
| Q:garbage | 1,032 | '1003.1-2017', '1003.1-2008', '©', '-', '#include', 'pthread.h' |
| B:candidate_evidence_pending | 861 | 'ieee', 'int', 'const', 'attr', 'arg', 'shall' |
| B:compound_of_known_parts | 234 | 'thread-local', 'floating-point', 'cpu-time', 'system-imposed', 'start-up', 'man-pages' |
| Q:number | 187 | '7', '2018', '5', '6', '1', '302' |
| F:function_word | 148 | 'of', 'and', 'a', 'with', 'by', 'within' |
| Q:no_vowel | 81 | 'std', 'tct', 'xbd', 'xsh', 'nptl', 'mb' |
| Q:chrome | 49 | 'the', 'this', 'here', 'create', 'in', 'to' |
| Q:single_letter | 23 | 's', 'c', 'x', 'm', 'y', 'n' |
| Q:ref | 12 | '2001-2018', 'https://www.kernel.org/, 'https://git.kernel.org/, 'https://mirrors.edge.ke, 'http://www.linux-pam.or, 'https://www.open-std.or |
| C:proper_noun | 5 | 'linux', 'austin', 'arp', 'forth', 'ie' |
| Q:consonant_run | 4 | 'errchkmutex', 'siocspgrp', 'stpncpy', 'strncpy' |

Top 30 words by fire count: 'pthread_create', '<<<', 'previous', 'home', 'next', '>>>', 'the', 'open', 'group', 'base', 'specifications', 'issue', '7', '2018', 'edition', 'ieee', 'std', '1003.1-2017', 'revision', 'of', '1003.1-2008', 'copyright', '©', '2001-2018', 'and', 'a', 'newer', 'this', 'document', 'exists'

Cause: not established; measured only. A code or specialist corpus can read as 'quarantined' here because its vocabulary is identifiers and symbols, which is a different thing from page-chrome poisoning.

Status: moved to `PTorrent/bin_archive/dirty/` on 2026-10-17 (Cody's instruction); kept as a historical record, not a starting point. Bins are gitignored (too large for GitHub): this note is what is committed.
