# Corpus provenance and annotation

`questions.jsonl` is an AI-authored insurance-query seed corpus generated reproducibly by `../build_dataset.py`. It contains 900 supported examples (10 intents x 10 phrasing patterns x 3 language styles x 3 entity substitutions), plus 90 unsupported examples. The 900 records are not 900 independent question constructions. There are 100 supported source-pattern groups, with translated phrases and all substituted names kept together, plus 30 negative-topic groups.

Group split: supported patterns 0–5 train, 6–7 validation, 8–9 test; negative topics use the same rule modulo ten. This is a small development benchmark. Labels and groups are explicit, source code preserves the original templates, and no native speaker has reviewed the Arabizi. Do not present these results as validated real-world Tunisian language accuracy.

Languages: French (`fr`), English (`en`), Tunisian Latin-script/French-mixed Arabizi (`tn-Arabizi`). No automatic transliteration of numerals is performed.

Each row: ID, original text, language, intent, entity mention, source group, split, provenance, native-review status. Query semantics and fixtures are in `app/multilingual/contracts.py`, `queries.py`, and `app/tests_multilingual/`. Filters are implemented and independently tested; this first classifier corpus does not claim exhaustive slot-span annotation.

Reviewers should verify naturalness, intent, exact ownership/coverage meaning, entity mention, and any requested filter. Correct questionable phrases before adding them to a future corpus version. Avoid changing a frozen test set to improve scores: record previous results and create a fresh test version when evaluation feeds development.

The negative set is especially small and topic-grouped. Unseen unsupported-topic rejection is a genuine limitation to measure; broad refusal quality cannot be inferred from a few examples. Next data collection should prioritize independently authored questions and hard negatives rather than bulk name substitution.

`ml/evaluate_answers.py` declares a separate 30-question execution challenge (one question per intent per language), six negative questions, and exact expected graph IDs. It is also AI-authored and is not a native-reviewed test.
