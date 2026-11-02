# Discovery and conversation UX audit

Historical audit before implementation. The resulting features and verification are now documented in [CONVERSATION_RESULTS.md](CONVERSATION_RESULTS.md). Original machine-readable evidence is retained in `reports/exploration-audit-before-conversation.json`.

2 November 2026. This audit responds to the user’s four screenshot examples. These prompts are retained as evaluation evidence and were not added to training.

## UI changes completed

Removed the two introductory implementation/provenance paragraphs from the assistant page. The language label now says Tunisian Darija. Dataset provenance and experimental limitations remain in technical documentation.

## Method and scope

Twenty realistic scenarios, each asked in English, French and Tunisian Darija: 60 prompts through the Django assistant route. Follow-up cases issue a preceding request using the same client. Independent SELECT queries define expected graph IDs. The audit deliberately targets discovery and relationship gaps; its counts are not overall language accuracy.

The classifier/model and NLP behavior were not changed as part of this audit. Main graph triplets before and after: 2651 / 2651.

## Outcomes

- not_answered: 38
- wrong_records: 7
- appropriate_clarification: 9
- correct_records: 6

## Confirmed gaps

- Discovery: customer directory, insurer directory, all contracts and all insured assets. Only the existing all-claims listing works.
- Reverse navigation: owner by vehicle registration, policies covering a vehicle, issuer of a policy, and holder of a policy.
- Specific claim and customer filters: a claim reference/customer name can be ignored or sent to the wrong existing family.
- Conversation: the endpoint has no selected-entity/session context. Pronouns such as his/its and cross-language follow-ups cannot resolve the previous entity.
- Help/onboarding: no useful response to what can I ask. The interface currently teaches a few known examples rather than helping a newcomer explore records.
- Minor spelling variants of names are not recovered by the multilingual matcher; asking for clarification is safer than guessing but less helpful.
- Insurance/assurance alone is ambiguous between insurer and policy; it needs a choice, not an arbitrary missing-customer prompt.

## Wrong-answer cases (higher priority than refusals)

| Language | Question | Selected family | Returned IDs | Expected IDs |
|---|---|---|---|---|
| en | Who holds policy AUTO-2026-001? | garanties_contrat | Garantie_BrisGlace_Auto, Garantie_RC_Auto | Assure_Ahmed, Client_CRM_4471 |
| tn-Darija | chkoun souscrit contrat AUTO-2026-001 | garanties_contrat | Garantie_BrisGlace_Auto, Garantie_RC_Auto | Assure_Ahmed, Client_CRM_4471 |
| en | Show claim S001 | indemnisation_sinistre | Indemnisation_I001 | Sinistre_S001 |
| fr | Montre le sinistre S001 | expertises_sinistre | Expertise_E001 | Sinistre_S001 |
| tn-Darija | warini sinistre S001 | indemnisation_sinistre | Indemnisation_I001 | Sinistre_S001 |
| fr | Liste les sinistres de Ahmed | sinistres_filtres | Sinistre_S001, Sinistre_S002, Sinistre_S003, Sinistre_S004, Sinistre_S005 | Sinistre_S001 |
| tn-Darija | warini les sinistres mta3 Ahmed | sinistres_filtres | Sinistre_S001, Sinistre_S002, Sinistre_S003, Sinistre_S004, Sinistre_S005 | Sinistre_S001 |

## Recommended next implementation order

1. Prevent unsupported relationships or unhandled requested filters from being answered as if they were understood. Request clarification instead.
2. Add genuine discovery queries: list customers, list insurers, list policies and list assets, with useful names/identifiers and next-step links. Define users here as insurance customers; Django login accounts are a separate concept.
3. Add reverse relations: vehicle registration -> owners -> policies, policy -> holder/issuer, and direct claim lookup/customer-specific claims. Preserve registration spacing variants with identifier-specific normalization.
4. Add visible, browser-session selected-customer/policy/vehicle context. Resolve follow-ups against a verified entity; ask when several entities are possible and provide a clear way to change/reset context.
5. Train for these newly defined capabilities with multilingual, varied examples. Run full journey tests on fresh wording in all three styles. Keep these user-reported cases as regressions, and use new independently phrased tests for final performance claims.

Example desired journey: list customers -> select Ahmed -> list his policies -> select a policy -> view guarantees/clauses; alternatively search 123 TU 4567 -> owner -> owner’s other assets/policies. This is graph exploration plus conversation state, not solely classifier retraining.

No new NLP families or conversation memory have been implemented in this audit. UI cleanup is complete; the results define the next functional iteration. Full machine-readable evidence is in exploration-audit.json.
