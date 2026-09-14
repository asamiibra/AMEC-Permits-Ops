# Prompt 04 existing context contract reuse map

The exact P03 entry gate passed before P04 changes. P04 reuses the existing P02 persistence and ProposalOps authority seams; it adds no parallel truth or persistence model.

| Existing seam | P04 treatment | Preservation rule |
| --- | --- | --- |
| `ContextSnapshot` | `REUSE_AS_IS` | Persist snapshot metadata, hashes, actor identity, and dependency count only. |
| `ContextDependency` | `REUSE_AS_IS` | Persist typed identity/version/hash and capture trust/currentness; no compiled payload. |
| `intelligence_contracts.py` dependency registry | `ADAPT_IN_PLACE` | Add only the string vocabulary `CANDIDATE_ASSERTION`; no migration. |
| `SkillManifest` / `build_skill_manifest` | `REUSE_AS_IS` | Enforce allowed scope/context types, trust floor, manifest hash, and authority=`NONE`. |
| `User`, `Role`, `persona_for_role`, `CAPABILITY_MATRIX`, `require_capability` | `REUSE_AS_IS` | Derive actor authorization server-side; caller persona/capabilities are not accepted. |
| `CandidateAssertion` | `REUSE_AS_IS` | Consume only `CURRENT` candidates at `CANDIDATE` trust and preserve target-module/scope lineage. |
| `DocumentVersion` / Phase4 evidence envelope | `REUSE_AS_IS` | Resolve exact governed identity and current lineage; never load bytes. |
| `VerifiedAssertion` | `REUSE_AS_IS` | Consume an existing current, lineage-bound assertion only; never create or promote. |
| Master Content resolvers | `REUSE_AS_IS` | Use `canonical_master_content_candidates`, `resolve_master_content_purpose`, and exact binding checks; ambiguity fails closed. |
| `DefinitionEntry` / `DefinitionRevision` | `REUSE_AS_IS` | Consume only active entry/current revision. |
| `Project` | `ADAPTER` | Static whitelisted Project projection is the representative domain revision resolver. |
| Phase4 review/promotion/projection and legacy tasks/notifications | `LEGACY_COMPATIBILITY_ONLY` | P04 neither calls nor expands these paths; P07 debt remains unchanged. |

The new boundary is:

```text
SkillManifest + authenticated actor + typed source specs
  → static resolver registry
  → scope/trust/currentness/policy checks
  → minimized in-memory projections
  → ContextSnapshot + ContextDependency
  → CompiledContext
```
