# Conversation and discovery implementation plan

## Draft
Extend the existing assistant with discovery, reverse relationships, a session-backed transcript and dynamic suggestions. Add the missing graph queries and multilingual examples, train the expanded lightweight classifier, then replay the user journeys and regression suite.

## Critic review 1: meaning and context
Problems: a transcript alone cannot resolve pronouns; keeping several stale selected entities can mix customers and policies; model confidence cannot prove that a requested relationship/filter was executed; global listings must not be confused with a missing customer name.

Adjustments: use one visible typed focus, verified against the live graph; change focus only on an explicit entity/selection; clarify incompatible or ambiguous references; distinguish global listing from customer-specific requests with separate query contracts; use explicit relationship recognition as a transparent guard alongside the classifier, never silently return a different relationship. Maintain the old stateless engine API for regression comparison.

## Critic review 2: UI actions and validation
Problems: GET requests that mutate chat state can duplicate messages on refresh; suggested questions based only on intent can contain nonexistent names or stale IDs; client-supplied selection/context must not be trusted; result order/duplicate CRM records makes 'first customer' unstable; reusing earlier audit prompts for training would inflate evaluation claims.

Adjustments: POST/redirect/GET with CSRF for chat/reset/select, bounded per-session transcript, validated row actions and deterministic display ordering/deduplication. Suggestions use verified current results and focus, start with discovery and change after every turn; unrelated failed questions must not reset or poison focus. Keep audit prompts out of new training verbatim and report old-vs-new UX regression results separately from a fresh journey test. Test two sessions, reset, unknown names, changed focus, ambiguous references, stale/tampered buttons, and complete cross-language journeys.

## Final execution order
1. Add distinct discovery, reverse lookup, direct-claim and customer-claims contracts and SELECT templates.
2. Extend vehicle aliases to real registrations (spacing variants) and add guards against unhandled requested relations/filters.
3. Add independently phrased multilingual examples, train the expanded lightweight classifier, retain previous artifacts/reports and record evaluation limitations.
4. Implement a single typed session focus, contextual request resolution, bounded transcript, explicit selections and reset.
5. Generate initial discovery suggestions, context-appropriate follow-ups and result-based actions with real names/IDs.
6. Build the chat UI with details on demand and accessible POST actions. Retain legacy GET links as stateless previews.
7. Re-run original tests; replay the 60-question discovery audit; run fresh complete journeys in three language styles and state-isolation tests. Record exact wrong answers, refusals, and unchanged source data.
8. Deploy locally, inspect live UI/requests, save a plain-language report and local commit.

Scope: read-only insurance exploration. SQL login accounts are not insurance customers. Counts, arbitrary comparisons, writes and general conversation remain outside this iteration; ambiguity is clarified rather than guessed.

## Execution outcome
Implemented and deployed locally. Final verification: 138 passing Django tests; 60-case replay with 48 exact answers, 9 appropriate clarifications and 3 helpful replies; 27/27 fresh journey answer checks; source graph unchanged at 2,651 triples. Expanded model uses typed ID features and 1,320 seed records. Technical details, intermediate failures and remaining language-quality limits are in CONVERSATION_RESULTS.md.
