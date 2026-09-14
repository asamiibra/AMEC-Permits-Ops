# P03 preservation and P07 non-interference

P04 consumes the P03 candidate-only boundary. It does not create, promote, update, or review a CandidateAssertion; it only records a typed `CANDIDATE_ASSERTION` dependency when a current candidate is explicitly allowed by a manifest.

The existing Phase4 review queue, `Phase4ReviewDecision`, promotion bridge, projection plan/receipt, and legacy WorkflowTask/Notification coupling remain untouched. P04 does not call or expand them. `P07_REVIEW_REFACTOR=false`.

Prompt 05 remains deferred: no Skill Registry persistence, Model Gateway, provider, prompt template, tool execution, RAG, embedding, vector, token accounting, or model fallback was added. Prompt 06 remains deferred: no invalidation watcher, stale propagation, or re-analysis queue was added.
