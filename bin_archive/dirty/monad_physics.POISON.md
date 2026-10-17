# POISON NOTE: monad_physics

* file: `monad_physics.bin`; identical copies: `holcus_monad_physics.bin`
* sha256: `39ab6f2eaad7f627f965b9a341e2ab7ed9a1fb997d5580d75ada1f1c6eb69f03`; size 10,363,731 bytes; pickle vv1.218; vocabulary 58,003; word_count 0
* measured by `VAPMIP/Wernicke/sanitize/sanitize_v0.py` (deterministic ruleset), 2026-10-17
* quarantined by the sanitiser: **29,764 of 58,003 (51.3%)**; admitted tiers A 14,200 (in WordNet), B 12,669 (candidates), C 1,202 (proper nouns), F 168 (function words)

| tier:reason | tokens | examples |
|---|---|---|
| A:in_wordnet | 14,200 | 'resonances', 'global', 'electromagnetic', 'generated', 'excited', 'lightning' |
| Q:formula | 11,878 | '\\displaystyle', 'f_{n', '=', '+', 'f_{n}={\\frac', 'c}{2\\pi' |
| B:candidate_evidence_pending | 11,078 | 'winfried', 'otto', 'dissipative', 'could', 'unsourced', 'francis' |
| Q:garbage | 7,287 | '-', 'العربية', 'български', 'català', 'čeština', 'español' |
| Q:ref | 5,576 | '978-0-19-507337-9', '978-0-8493-8647-3', '10.1016/b978-008044648-, '978-0-08-044648-6', '1992sci...256.1184w', '10.1126/science.256.506 |
| Q:number | 4,235 | '28', '1', '1952', '2', '3', '60' |
| B:compound_of_known_parts | 1,591 | 'variable-sized', 'lowest-frequency', 'solar-induced', 'fair-weather', 'high-impedance', 'asia-america' |
| C:proper_noun | 1,202 | 'schumann', 'williams', 'george', 'fitzgerald', "fitzgerald's", 'heaviside' |
| Q:no_vowel | 487 | 'sr', 'hz', 'km', 'khz', 'fl', 'crc' |
| F:function_word | 168 | 'and', 'by', 'a', 'of', 'are', 'they' |
| Q:greek | 94 | 'ελληνικά', 'π', 'μ', 'σ', 'ω', 'τ' |
| Q:chrome | 89 | 'wikipedia', 'jump', 'to', 'content', 'search', 'donate' |
| Q:time_expression | 69 | '1990s', '63rd', '3rd', '2nd', '7th', '1860s' |
| Q:single_letter | 26 | 's', 'g', 'n', 'h', 'l', 'f' |
| Q:non_latin_or_symbol | 19 | 'ż', 'equation--cartesian', 'mathworld--a', 'ħ', 'æ', 'à' |
| Q:consonant_run | 4 | 'durchschnitten', 'durchschnittsfigur', 'fortschritte', 'goldschmidt' |

Top 30 words by fire count: 'schumann', 'resonances', '-', 'wikipedia', 'jump', 'to', 'content', 'search', 'donate', 'create', 'account', 'log', 'in', 'personal', 'tools', '28', 'languages', 'العربية', 'български', 'català', 'čeština', 'dansk', 'deutsch', 'ελληνικά', 'español', 'euskara', 'français', 'עברית', 'magyar', 'italiano'

Cause: Built from Wikipedia/HyperPhysics/Feynman Lectures pages by an HTML-strip path (corpus list code-corpora/physics_corpus.txt). Evidence: Wikipedia page chrome and the interlanguage list sit at the top of the fire counts; LaTeX fragments and ISBN/DOI/bibcode strings are in the vocabulary.

Status: moved to `PTorrent/bin_archive/dirty/` on 2026-10-17 (Cody's instruction); kept as a historical record, not a starting point. Bins are gitignored (too large for GitHub): this note is what is committed.
