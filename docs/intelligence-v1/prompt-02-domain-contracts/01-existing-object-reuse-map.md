# Existing object reuse map

Prompt 02 extends the existing platform seams; it does not create duplicate truth engines.

| Existing authority/object | Prompt 02 use |
| --- | --- |
| `Document`, `DocumentVersion` | source identity and immutable document-version dependencies |
| `FieldObservation` | observation provenance and candidate source reference |
| `VerifiedAssertion` | existing verified business fact, generalized with scope/subject metadata |
| Phase 4 evidence/review records | preserved source/evidence/review authority; no replacement queue |
| `AIExecutionLedger` | existing execution metadata ledger, widened with scope and owning skill identity |
| `MasterContentDependency` | existing master-content dependency authority remains unchanged and is referenced by dependency identity |
| `AuditEvent` | existing audit seam remains the audit authority |

New persistence is limited to `CandidateAssertion`, `ContextSnapshot`, `ContextDependency`, `AIWorkProduct`, and `IntelligenceCitation`. None has approved, accepted, authorized, protected, or canonical business-transition semantics.
