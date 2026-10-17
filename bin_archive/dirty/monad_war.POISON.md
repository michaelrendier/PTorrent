# POISON NOTE: monad_war

* file: `monad_war.bin`; identical copies: `holcus_monad_war.bin`
* sha256: `14a4a59654b710a4170117d7e845d4b7149e4a45004dc62c096e531535812566`; size 86,525 bytes; pickle vv1.218; vocabulary 829; word_count 0
* measured by `VAPMIP/Wernicke/sanitize/sanitize_v0.py` (deterministic ruleset), 2026-10-17
* quarantined by the sanitiser: **623 of 829 (75.2%)**; admitted tiers A 129 (in WordNet), B 42 (candidates), C 7 (proper nouns), F 28 (function words)

| tier:reason | tokens | examples |
|---|---|---|
| Q:garbage | 450 | '-', '@context":"https://sche, 'encyclopedia","legalnam, 'ltd","name":"world', 'kingdom","addresslocali, 'great","description":"k |
| Q:formula | 130 | '1he","streetaddress":"b, 'street"},"logo":{"@type, '@context":"https://sche, 'name=search_term_string, '@context":"https://sche, '356\\u2013323' |
| A:in_wordnet | 129 | 'alexander', 'great', 'world', 'history', 'publishing', 'house' |
| B:candidate_evidence_pending | 36 | 'achaemenid', 'marist', "putnam's", 'hephaestion', 'baird', 'donald' |
| F:function_word | 28 | 'of', 'and', 'where', 'was', 'which', 'he' |
| Q:number | 17 | '1', '2', '3', '4', '5', '6' |
| Q:single_letter | 11 | 'j', 's', 'g', 'p', 'c', 'l' |
| Q:chrome | 10 | 'the', 'encyclopedia', 'from', 'content', 'in', 'about' |
| C:proper_noun | 7 | 'macedonia', 'persia', 'ny', 'rogers', 'david', 'nagasaki' |
| B:compound_of_known_parts | 6 | 'co-founder', 'by-nc-sa', 'general-audience', 'min-width', 'font-size', 'line-height' |
| Q:ref | 3 | 'encyclopedia","url":"ht, 'https://cdn.fundraiseup, "https://www.googletagma |
| Q:no_vowel | 2 | 'cc', 'gtm' |

Top 30 words by fire count: 'alexander', 'the', 'great', '-', 'world', 'history', 'encyclopedia', '@context":"https:, 'encyclopedia","le, 'publishing', 'ltd","name":"worl, 'encyclopedia","ur, 'kingdom","address, '1he","streetaddre, 'house', 'mint', 'street"},"logo":{, '@context":"https:, 'name=search_term_, '@context":"https:, 'great","descripti, 'of', 'macedonia', 'and', 'conqueror', 'achaemenid', 'persia', '356\\u2013323', 'bc)","sameas":"ht, 'ancient'

Cause: Fermat/Caesar war corpus (monad_war). Evidence: the top fire-count words are 'alexander', 'great', 'world', 'history', 'encyclopedia' followed by JSON-LD page metadata fragments (@context, streetaddress, publisher) from a World History Encyclopedia page, so a page's embedded structured data was ingested as prose. Small vocabulary, so the percentage is dominated by those fragments.

Status: moved to `PTorrent/bin_archive/dirty/` on 2026-10-17 (Cody's instruction); kept as a historical record, not a starting point. Bins are gitignored (too large for GitHub): this note is what is committed.
