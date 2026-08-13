# Wave 3 — Expected Client Inputs — Preliminary

Status: `IMPLEMENTED_AND_VERIFIED`

`ProposalExpectedInputPreview` is a read-only consumer snapshot of the canonical Requirement Engine. It records exact policy-version IDs, scope-intent IDs, evaluator context, result items, actor/time, supersession, and content hash.

The preview resolver is fail-closed:

- only `CLIENT_COLLECTION` / `PRE_APPLICATION_CLIENT_COLLECTION` policy purposes are eligible;
- `APPLICABILITY_UNKNOWN`, `NOT_APPLICABLE`, and dependency-aware item results remain distinct;
- no policy produces `NO_POLICY` rather than an invented list;
- resolver ambiguity produces `POLICY_AMBIGUOUS`;
- a previously resolved preview whose current canonical policy or confirmed intent set changes is projected as `POLICY_STALE` until refreshed.

Proposal Checklist and Expected Client Inputs remain separate. Accept does not instantiate authority execution records or mutate Requirement Engine policy.
