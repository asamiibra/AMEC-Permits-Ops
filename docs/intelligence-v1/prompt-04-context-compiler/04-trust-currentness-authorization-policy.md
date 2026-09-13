# Trust, currentness, authorization, and policy

The compiler derives the stored `User.role`, canonical persona, and sorted `CAPABILITY_MATRIX` capabilities. `authorization_context_hash` binds actor ID, stored role, derived persona, capabilities, scope, owning module, and policy version; tokens, headers, passwords, secrets, and MFA material are excluded.

CandidateAssertion requires `CURRENT`, compatible project scope, compatible target module, and `CANDIDATE` trust. `SUPERSEDED`, `STALE`, `REJECTED`, and `PROMOTED` states fail closed. Restricted candidates and restricted Phase4 envelopes require the existing restricted-evidence capability.

DocumentVersion, Phase4 evidence, VerifiedAssertion, DefinitionRevision, Master Content, and Project resolvers all require positive currentness. Missing lineage, stale pointers, superseded versions, inactive definitions, unreviewed Master Content, restricted-reference samples, unavailable sources, and ambiguity fail closed. No historical fallback is implicit.

Master Content uses the existing exact binding and purpose resolution functions; it never selects a first row. Definition and Project context use explicit whitelisted projections. All source selectors are checked against a per-resolver allowlist.

For `PROJECT` scope, `project_id == scope_id` is enforced and every project-bound source is checked against that identity. `READ_ALL` does not bypass project isolation.
