# Canonical intelligence contracts

The persistence contract is additive and shared. Every scope has an explicit `scope_type` and `scope_id`; project identity is nullable where a shared/global scope is valid.

`CandidateAssertion` is candidate-only. It records producer identity, value hash, provenance references, classification, confidence, and lifecycle state. It never auto-verifies. `PROMOTED` requires a later explicit workflow reference to a `VerifiedAssertion`.

`ContextSnapshot` records only context metadata and stable hashes. `ContextDependency` records typed dependency identity/version/hash, trust/currentness at capture, and metadata. Heterogeneous dependencies intentionally have no polymorphic foreign key and never copy raw bytes or source text.

`AIWorkProduct` stores structured output plus output hash, owning skill identity, scope, output class, citation count, and currentness state. Allowed output classes are `CANDIDATE`, `ANALYSIS`, `DRAFT`, and `RECOMMENDATION`; states are `CURRENT`, `STALE`, and `INVALID`.

`IntelligenceCitation` stores ordinal source identity/version/hash and a locator. Ordinal uniqueness is scoped to a work product.

The `SkillManifest` is code-level schema. Its deterministic hash excludes `manifest_hash` itself. Any value other than `NONE` for canonical/protected authority is rejected.
