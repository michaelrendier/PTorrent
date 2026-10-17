# POISON NOTE: monad_sedenion

* file: `monad_sedenion.bin`; identical copies: `holcus_monad_sedenion.bin`
* sha256: `c97c272b0657dc929a8ac4814132944919025149363fb195cce5cb4bd8cf4907`; size 117,895,324 bytes; pickle vv1.218; vocabulary 35,930; word_count 0
* measured by `VAPMIP/Wernicke/sanitize/sanitize_v0.py` (deterministic ruleset), 2026-10-17
* quarantined by the sanitiser: **9,640 of 35,930 (26.8%)**; admitted tiers A 8,228 (in WordNet), B 17,428 (candidates), C 466 (proper nouns), F 168 (function words)

| tier:reason | tokens | examples |
|---|---|---|
| B:candidate_evidence_pending | 17,216 | 'azv', 'hosh', 'diem', 'cricy', 'ekluo', 'zora' |
| A:in_wordnet | 8,228 | 'fluid', 'papaw', 'farm', 'alters', 'peaty', 'kinks' |
| Q:garbage | 4,576 | "wood'", '', '', '', '', '' |
| Q:formula | 2,398 | 'e0', 'e1', 'e2', 'e3', 'e4', 'e5' |
| Q:no_vowel | 1,872 | "t'l", 'clnb', 'flk', 'cjgs', 'vqr', 'xcv' |
| Q:ref | 529 | 'ftp://', 'https://www.ancient.eu/, 'https://www.britannica., 'https://www.jstor.org/s, 'https://www.worldhistor, 'https://www.worldhistor |
| C:proper_noun | 466 | 'aiai', 'frey', 'donar', 'ashton', 'stalin', 'speke' |
| B:compound_of_known_parts | 212 | 'self-reference', 'self-application', 'then-after', 'f-then-g', 'three-face', 'self-applying' |
| F:function_word | 168 | "i's", "she's", "you'd", "on's", 'same', 'then' |
| Q:number | 138 | '0.56714', '0.000707', '0.5', '1.618034', '0.0', '0' |
| Q:chrome | 55 | 'version', 'donate', 'jstor', 'the', 'this', 'log' |
| Q:greek | 34 | 'θ', 'β-field', 'β', 'jμ', 'δ', 'φ-walk' |
| Q:single_letter | 30 | "m's", "p's", "t's", "w's", "b's", "f's" |
| Q:time_expression | 7 | '25s', '20th', '21st', '8th', '60s', '6th' |
| Q:non_latin_or_symbol | 1 | "d''la" |

Top 30 words by fire count: "t'l", 'clnb', 'fluid', 'azv', 'hosh', 'diem', 'papaw', 'flk', 'cricy', "wood'", 'farm', 'ekluo', 'alters', 'cjgs', 'zora', 'zje', 'vqr', 'kilyo', 'ofkind', '', 'ethno', 'peaty', 'koor', 'benuz', 'tsuk', 'ghyc', '', 'xcv', 'kinks', 'sary'

Cause: Sedenion/Ainulindale corpus bin. Evidence: thousands of random-looking strings (azv, hosh, cricy, ekluo, zje), URL fragments (ftp://, https://www.jstor.org/...) and empty tokens. The e0..e15 basis names classify as FORMULA here and are legitimate vocabulary, not poison. Cause of the random strings not established.

Status: moved to `PTorrent/bin_archive/dirty/` on 2026-10-17 (Cody's instruction); kept as a historical record, not a starting point. Bins are gitignored (too large for GitHub): this note is what is committed.
