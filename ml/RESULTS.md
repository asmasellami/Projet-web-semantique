# Multilingual NLP: implementation and measured results

Date: 2 November 2026. Branch: codex/multilingual-insurance-nlp. Starting commit: 506c290.

## What now works

The new /assistant/ page accepts French, English and experimental Tunisian Arabizi across ten insurance question families. It classifies the question, resolves names/identifiers against the live graph, extracts supported filters, constructs controlled SELECT queries and displays the graph path, SPARQL and results. The old French rules engine remains available at /question/.

Ownership and contractual coverage use separate paths. Claim filters include location, status, type and explicit dates; compensation supports amount comparisons. Unsupported count/existence/update/negation requests are refused. Ambiguous names and dates request clarification. New graph entities are read without classifier retraining.

## Models actually trained

We trained a TF-IDF word/character-feature logistic regression classifier, a logistic regression head on frozen multilingual MiniLM embeddings, and a SetFit classifier with encoder weights actually fine-tuned for 40 optimization steps (2,376 available contrastive pairs, 320 pairs processed in this budget). The selected model is the lightweight classifier. A validation-tuned blend was also tried; its best weight was 100% lightweight, so it provided no benefit.

| Candidate | Validation mean language macro-F1 | Test macro-F1 | Test accuracy |
|---|---:|---:|---:|
| TF-IDF + logistic regression | 0.911 | 0.901 | 0.904 |
| Frozen MiniLM + logistic regression | 0.831 | 0.802 | 0.803 |
| Fine-tuned SetFit MiniLM | 0.887 | 0.838 | 0.843 |
| TF-IDF + fine-tuned MiniLM blend | 0.911 | 0.901 | 0.904 |

Selection used validation, not the test score. The first aggregate test results motivated one additional blend experiment. Its weights/thresholds were chosen on validation only; the development test was reused for reporting. Stage1 results are retained in reports/classification-stage1.json. No fresh independent human-reviewed test has been completed.

## Dataset and honest interpretation

990 AI-authored seed records: 900 supported and 90 unsupported; 330 records per language style. There are 100 supported phrasing groups plus 30 negative-topic groups. Each supported phrasing has three language versions and three entity variants, so the record count is not the count of independent constructions. Train/validation/test: 594/198/198. Groups never cross splits; exact text duplicate checks also passed.

All Arabizi records remain marked native_reviewed=false. Native-speaker review is outstanding. The corpus is a reproducible internal development benchmark, not evidence of general Tunisian fluency. Generator templates and group IDs are versioned.

## Selected classifier by language

| Language | Test examples | Supported intent accuracy | Macro-F1 incl. unsupported | Unsupported rejection |
|---|---:|---:|---:|---:|
| fr | 66 | 98.3% | 0.970 | 83.3% |
| en | 66 | 80.0% | 0.751 | 66.7% |
| tn-Arabizi | 66 | 98.3% | 0.953 | 66.7% |

English macro-F1 and broad unsupported-topic rejection do not reach the proposed final targets. Short training phrases and limited vocabulary constrain generalization. A higher model name does not fix poor task/data fit: in this run SetFit improved English but was weaker on Arabizi. More independently authored examples and a fresh reviewed benchmark are the highest-value next improvements.

## Independent question-to-answer challenge

Thirty additional AI-authored supported questions (10 per language), plus six unsupported questions, with exact expected graph-ID sets. These are distinct from classifier training examples. They are still a small internal challenge, not a population estimate.

| Language | Correct exact answers | Correct unsupported refusals |
|---|---:|---:|
| fr | 9/10 | 2/2 |
| en | 8/10 | 2/2 |
| tn-Arabizi | 10/10 | 2/2 |

Cold first request: 7496 ms; warm median: 41.6 ms; warm p95: 71.1 ms on this CPU. These are local benchmark values, not guarantees.

Observed failures:
- fr: Quels objets sont couverts par les polices de Ahmed ? -> contrats_assure
- en: Retrieve the insurance agreements held by Ahmed. -> unsupported
- en: Retrieve the terms attached to policy AUTO-2026-001. -> unsupported

These failures are retained in the report rather than patched with challenge-specific rules. The graph remained at 2,651 triples before and after the benchmark.

## Verification and artifacts

- 120 Django tests pass, including multilingual query templates in three language styles, ownership/coverage distinction, duplicate and new entities, filters, rejected operations and the required claim fields.
- Main application data and supplied OWL were preserved. Development writes use the isolated test dataset.
- New interface is served locally at http://127.0.0.1:8000/assistant/.
- See data/README.md for provenance, requirements-lock.txt for training versions, reports/environment.json for hardware/base-model revision, reports/classification.json and reports/answers.json for raw results.
- Generated model files are local under ml/artifacts/ and ignored by Git; reproduce with train.py or copy this directory. The fine-tuned encoder remains available for inspection even though it was not selected for deployment.

## Next data iteration

Have Tunisian speakers review wording and write questions without seeing the templates. Collect difficult English paraphrases, more unrelated/unsupported topics, and complete slot annotations. Preserve current results and freeze a fresh test version before evaluating another development cycle. Expand advanced operators only with verified graph queries and tests.
