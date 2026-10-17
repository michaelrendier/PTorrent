# POISON NOTE: monad_mathematics

* file: `monad_mathematics.bin`; identical copies: `holcus_monad_mathematics.bin`
* sha256: `7f1f05510caac70117e36f72519a6effb022912d20398ed1da8326cea5618148`; size 9,063,372 bytes; pickle vv1.218; vocabulary 56,451; word_count 0
* measured by `VAPMIP/Wernicke/sanitize/sanitize_v0.py` (deterministic ruleset), 2026-10-17
* quarantined by the sanitiser: **38,659 of 56,451 (68.5%)**; admitted tiers A 8,974 (in WordNet), B 7,961 (candidates), C 711 (proper nouns), F 146 (function words)

| tier:reason | tokens | examples |
|---|---|---|
| Q:garbage | 18,544 | '-', 'aragonés', 'ænglisc', 'العربية', 'الدارجة', 'مصرى' |
| Q:formula | 13,106 | '×', '\\displaystyle', '\\sqrt', '=', '2,3,\\dots', 'a000040' |
| A:in_wordnet | 8,974 | 'prime', 'number', 'na', 'interlingua', 'bahasa', 'ido' |
| B:candidate_evidence_pending | 7,042 | 'nordfriisk', 'gaeilge', 'gwiyannen', 'galego', 'hrvatski', 'hornjoserbsce' |
| Q:number | 3,605 | '142', '1', '5', '4', '2', '300' |
| Q:ref | 2,812 | '978-0-19-850105-3', '978-1-136-63662-2', '978-0-7641-0768-9', '978-0-7167-0076-0', '978-0-08-096019-7', '978-0-387-98289-2' |
| B:compound_of_known_parts | 919 | 'public-key', 'equal-size', 'zeta-function', 'non-constant', 'prime-generating', 'higher-degree' |
| C:proper_noun | 711 | 'indonesia', 'aks', 'euclid', 'eratosthenes', 'al-haytham', 'alhazen' |
| Q:no_vowel | 304 | 'bc', 'th', 'mr', 'st', 'pdf', 'pp' |
| F:function_word | 146 | 'only', 'by', 'and', 'itself', 'for', 'other' |
| Q:chrome | 87 | 'wikipedia', 'jump', 'to', 'content', 'search', 'donate' |
| Q:greek | 83 | 'ελληνικά', 'πρῶτος', 'ἀριθμὸς', 'μ', 'ζ', 'π' |
| Q:time_expression | 62 | '19th', '1970s', '17th', 'mid-18th', '20th', '2nd' |
| Q:non_latin_or_symbol | 28 | 'à', 'problem--project', 'ø', 'ĝ', 'ŷ', 'â' |
| Q:single_letter | 24 | 'e', 'n', 'p', 's', 'c', 'x' |
| Q:consonant_run | 4 | 'grrlscientist', 'goldschmidt', 'habilitationsschrift', 'mdcclxxvi' |

Top 30 words by fire count: 'prime', 'number', '-', 'wikipedia', 'jump', 'to', 'content', 'search', 'donate', 'create', 'account', 'log', 'in', 'personal', 'tools', '142', 'languages', 'afrikaans', 'alemannisch', 'aragonés', 'ænglisc', 'العربية', 'الدارجة', 'مصرى', 'অসমীয়া', 'asturianu', 'azərbaycanca', 'تۆرکجه', 'башҡортса', 'žemaitėška'

Cause: Built from Wikipedia/MathWorld/DLMF pages by an HTML-strip path (corpus list code-corpora/mathematics_corpus.txt). Evidence: Wikipedia page chrome and the interlanguage list sit at the top of the fire counts; LaTeX source fragments and ISBN/DOI/bibcode strings are in the vocabulary. The old cleaner only deleted what looked non-English.

Status: moved to `PTorrent/bin_archive/dirty/` on 2026-10-17 (Cody's instruction); kept as a historical record, not a starting point. Bins are gitignored (too large for GitHub): this note is what is committed.
