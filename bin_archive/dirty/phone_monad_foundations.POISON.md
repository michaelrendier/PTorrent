# POISON NOTE: phone_monad_foundations

* file: `phone_monad_foundations.bin`; identical copies: none
* sha256: `ce4f5646ec8a2f4942f3fc9fc51f180cd210b3a4270816a2c2616ad239ae5b23`; size 1,554,233 bytes; pickle vv1.218; vocabulary 10,736; word_count 0
* measured by `VAPMIP/Wernicke/sanitize/sanitize_v0.py` (deterministic ruleset), 2026-10-17
* quarantined by the sanitiser: **2,013 of 10,736 (18.8%)**; admitted tiers A 6,309 (in WordNet), B 1,844 (candidates), C 428 (proper nouns), F 142 (function words)

| tier:reason | tokens | examples |
|---|---|---|
| A:in_wordnet | 6,309 | 'ptolemy', 'world', 'history', 'public', 'domain', 'bce' |
| B:candidate_evidence_pending | 1,716 | 'soter', 'marie-lan', 'nguyen', 'phillip', 'would', 'phillips' |
| Q:number | 713 | '3000', '332', '323', '30', '2000', '301' |
| Q:garbage | 710 | '-', '366-282', '&', 'c.301', '–', '282-246' |
| C:proper_noun | 428 | 'egypt', 'cleopatra', 'lagos', 'persia', 'halicarnassus', 'issus' |
| Q:ref | 242 | 'https://www.worldhistor, '1226-1286', 'https://www.worldhistor, 'https://www.worldhistor, 'www.theoi.com', 'www.attalus.org' |
| Q:formula | 162 | '$5', '$15', '318/311', '270/268', '340/330-269', '5th-century' |
| F:function_word | 142 | 'i', 'was', 'of', 'he', 'not', 'only' |
| B:compound_of_known_parts | 128 | 'by-nc-nd', 'by-nc-sa', 'non-profit', 'non-commercially', 'high-quality', 'by-sa' |
| Q:no_vowel | 56 | 'bc', 'cc', 'fr', 'xxxv', 'xxv', 'qr' |
| Q:chrome | 50 | 'encyclopedia', 'the', 'to', 'personal', 'in', 'this' |
| Q:time_expression | 29 | '7th', '3rd', '18th', '270s', '10th', '19th' |
| Q:single_letter | 24 | 's', 'r', 'd', 'l', 'v', 'c' |
| Q:non_latin_or_symbol | 17 | 'º', 'à', "mathematics--fermat's", 'theorem--at', 'transform--cosine', 'transform--delta' |
| Q:greek | 10 | 'βιβλιοθήκη', 'ἀποθήκη', 'βιβλίων', 'πρὸς', 'ἀπαίδευτον', 'καὶ' |

Top 30 words by fire count: 'ptolemy', 'i', '-', 'world', 'history', 'encyclopedia', 'soter', 'marie-lan', 'nguyen', 'public', 'domain', '366-282', 'bce', 'was', 'one', 'of', 'the', 'successor', 'kings', 'to', 'empire', 'alexander', 'great', 'he', 'served', 'not', 'only', 'as', 'king', 'egypt'

Cause: not established; measured only. A code or specialist corpus can read as 'quarantined' here because its vocabulary is identifiers and symbols, which is a different thing from page-chrome poisoning.

Status: moved to `PTorrent/bin_archive/dirty/` on 2026-10-17 (Cody's instruction); kept as a historical record, not a starting point. Bins are gitignored (too large for GitHub): this note is what is committed.
