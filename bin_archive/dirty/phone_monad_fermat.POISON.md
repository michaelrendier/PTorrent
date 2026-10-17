# POISON NOTE: phone_monad_fermat

* file: `phone_monad_fermat.bin`; identical copies: none
* sha256: `517b3709dfc93b4aca5796f9379a3c70b4e956ea25aa5ddccc41f7465b09d0f6`; size 1,604,439 bytes; pickle vv1.218; vocabulary 10,842; word_count 0
* measured by `VAPMIP/Wernicke/sanitize/sanitize_v0.py` (deterministic ruleset), 2026-10-17
* quarantined by the sanitiser: **1,607 of 10,842 (14.8%)**; admitted tiers A 7,496 (in WordNet), B 1,211 (candidates), C 386 (proper nouns), F 142 (function words)

| tier:reason | tokens | examples |
|---|---|---|
| A:in_wordnet | 7,496 | 'alexander', 'great', 'world', 'history', 'server', 'costs' |
| B:candidate_evidence_pending | 1,080 | 'bucephalus', 'ruthven', 'diadochi', 'perdiccas', 'arienne', 'youtube' |
| Q:garbage | 704 | '-', '/', '❤', '&', '–', '336-323' |
| Q:number | 530 | '2026', '20', '20000', '21', '356', '10' |
| C:proper_noun | 386 | 'macedon', 'philip', 'egypt', 'mesopotamia', 'india', 'persepolis' |
| Q:formula | 143 | '$20,000', '$', '$5', '7th-4th', '$15', '318/311' |
| F:function_word | 142 | 'it', 'a', 'our', 'and', 'we', 'your' |
| B:compound_of_known_parts | 131 | 'by-nc-sa', 'by-sa', 'non-profit', 'non-commercially', 'by-nc-nd', 'ai-generated' |
| Q:no_vowel | 61 | 'cc', 'vs', 'bc', 'cf', 'xxx', 'lxv' |
| Q:ref | 55 | 'www.iranchamber.com', 'www.royalty.nu', 'www.forbes.com', 'www.missedinhistory.com, 'www.bbc.co.uk', 'www.youtube.com' |
| Q:chrome | 50 | 'the', 'encyclopedia', 'to', 'help', 'donate', 'in' |
| Q:time_expression | 37 | '19th', '7th', '3rd', '18th', '1st', '10th' |
| Q:single_letter | 21 | 'l', 'r', 'd', 's', 'c', 'j' |
| Q:non_latin_or_symbol | 4 | 'º', 'rolls--many', 'study--and', 'inconsistencies--the' |
| Q:greek | 2 | 'ἑλληνική', 'σαλουτίων' |

Top 30 words by fire count: 'alexander', 'the', 'great', '-', 'world', 'history', 'encyclopedia', 'server', 'costs', 'fundraiser', '2026', 'it', '$20,000', 'a', 'year', 'to', 'run', 'our', 'servers', 'and', 'we', 'need', 'your', 'help', 'pay', 'for', 'them', '$', '20', '/'

Cause: not established; measured only. A code or specialist corpus can read as 'quarantined' here because its vocabulary is identifiers and symbols, which is a different thing from page-chrome poisoning.

Status: moved to `PTorrent/bin_archive/dirty/` on 2026-10-17 (Cody's instruction); kept as a historical record, not a starting point. Bins are gitignored (too large for GitHub): this note is what is committed.
