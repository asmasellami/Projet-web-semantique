# Conversational discovery release — results

2 November 2026. Plan and both critic reviews: `CONVERSATION_PLAN.md`.

## What changed for a user

The assistant now keeps a conversation transcript and one visible selection in the Django session. Start by exploring customers, companies, contracts or insured assets. Select a returned record or type `select Ahmed`, then ask follow-ups such as `Show his policies`, `Et ses propriétés ?`, or `w les biens mte3ou`.

Suggestions change with the actual results and selection. A customer list suggests selecting returned customers. A selected customer offers policies/assets/claims. Returned policies offer selection; a selected policy offers guarantees, clauses, covered assets, holder, insurer and claims. A vehicle offers owner and covering policies. A claim offers damage, assessments, payments and compensation scales. An insurer offers customers and issued policies.

New conversation clears history, pending choices and focus. Separate browser sessions do not share focus. Tabs in the same browser session share the conversation; versioned POST actions reject stale buttons. Refresh does not resubmit messages because POST redirects to GET.

## Query coverage

Expanded from ten to 23 query contracts: the original ten plus global customer/insurer/policy/asset discovery, owner and policies by vehicle, holder and issuer by policy, specific claim lookup, customer-specific claims, policy assets, policy claims and insurer policies.

All queries remain controlled SELECTs. Registrations accept spacing variants such as `205 TU 8890`, `205TU8890` and `205 TU8890`. Historical CRM duplicates with the same name and CIN appear as one customer, retaining their graph identifiers internally.

## Context and correctness rules

- One typed focus avoids retaining a policy belonging to a different customer after the customer changes.
- Explicit names/IDs override context. Unknown names do not inherit the previous customer, even when the sentence includes a pronoun.
- Referenced entities and selection actions are verified against the live graph. Deleted/stale selections request clarification.
- Ambiguous names or several possible policies require selection. Ordinal references use the deterministic displayed result order.
- Successful discovery clears the prior focus. Failed/unrelated questions preserve it. A typed selection clears the previous filter request.
- Arbitrary writes/counts/comparisons/negation remain unsupported. Dates/status not supported by a query contract request clarification rather than disappearing.
- `assurances` alone asks whether the user means companies or contracts, with relevant suggestion choices.
- Transcript is bounded to the latest twelve exchanges, with at most fifty rows per stored response. Selection state persists until changed/reset/invalidated.

## NLP implementation and training

The trained word/character TF-IDF logistic regression classifier was expanded to 24 labels (23 supported contracts + unsupported). Added 330 AI-authored multilingual records, giving 1,320 total: 792 training, 264 validation, 264 test. Translations and entity substitutions remain in one source group. The earlier 60 UX prompts were excluded from the new examples verbatim.

Identifier normalization now preserves entity type (`policy_reference`, `claim_reference`, `vehicle_reference`) while masking the individual number. This improved validation macro-F1 from approximately 0.618 to 0.668 and the internal development-test macro-F1 from 0.669 to 0.768. Both runs are retained in `reports/conversation-classification*.json`; test reuse during development means these are comparative internal results, not a fresh external benchmark.

Runtime is deliberately hybrid: the trained classifier proposes intent; explicit relationship contracts, verified entity types and session context constrain it to the graph operation actually requested. This prevents the earlier holder→guarantees and customer-filter omissions. These deterministic relation rules and context memory are application code, not a newly trained generative chatbot or an LLM API.

Arabizi/Darija data remain AI-authored and not native-reviewed. The expanded classifier alone still makes mistakes; especially its English model-only performance is limited. Passing the scripted journeys does not establish unlimited language understanding.

## Validation

- **138 Django tests pass**, including existing CRUD/NLP regressions, new query contracts, dynamic suggestions, session isolation/reset, CSRF, stale/tampered actions, unknown names, deleted focus, homonyms, context switching and natural multilingual follow-ups.
- **60-question UX replay:** 48 exact expected record sets, 9 appropriate clarifications, 3 helpful onboarding replies; zero wrong-record answers in this replay. These are regression checks targeting previously missing capabilities, not a general language-accuracy percentage.
- **27/27 answer checks** across three additional multilingual journeys, each covering customer discovery/selection, policies, assets, reverse owner lookup, vehicle policies, policy issuer/holder, policy claims and an unpaid claim's empty compensation result.
- Main graph remains **2,651 triples** before and after both evaluations. Destructive automated tests use the isolated test dataset.
- Duplicate-person gold normalization treats equivalent CRM identifiers as the same customer. The old ordinal case now expects selection of the first displayed customer, rather than a clarification; this is an intentional UX expectation change documented in the audit script.
- Desktop/browser automation helper initialization failed in this environment. Visual checks use headless Chrome rendering, while session/form interactions are verified through Django clients and real HTTP requests.

## What exploratory testing caught

1. A bare SPARQL BIND in direct lookup initially returned all claims: corrected by binding through the matched claim pattern; S001 is checked to return only S001.
2. A generic conjunction guard mistook `And its claims?` plus an injected policy ID for two requests. It now distinguishes follow-up conjunctions.
3. Natural variants `propriétés`, `chkoun souscrit fih`, and `for this claim` exposed gaps in relation/reference resolution. Covered by dedicated regressions.
4. A customer name not in the graph could be mistaken for a global listing. Scoping words and unknown explicit selections now trigger clarification.
5. A typed change of customer could retain the prior filter query. Typed selection now clears it, matching button selection.

These checks were used to improve the release and are retained as development regressions. A future independently authored/native-reviewed evaluation is still needed.

## Reproduce

After basic setup in `README.md`:

```powershell
python ml/train_conversation.py
python manage.py test app
python ml/exploration_audit.py
python ml/evaluate_journeys.py
```

Use the reference `assurance` graph for the two evaluation scripts. They issue SELECTs and create only local Django sessions. The selected classifier artifact is `ml/artifacts/conversation-tfidf.joblib` and its manifest is `ml/artifacts/selected.json`; generated weights are not tracked by Git. Restart Django after training.

## Try this journey

1. Click **Explorer les clients**.
2. Select **Ahmed Ben Salah**.
3. Ask **Show his policies**.
4. Ask **Et ses propriétés ?**.
5. Ask **karhba hedhi mta chkoun 205 TU 8890**.
6. Ask **Which policies cover that vehicle?**.
7. Select the returned policy, then try **Who issued it?**, **And its holder?**, and **Et ses sinistres ?**.

The suggestions below each response provide equivalent next steps using real identifiers.
