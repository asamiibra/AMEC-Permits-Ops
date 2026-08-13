# Domain Reuse Map

Construction references the existing canonical domains rather than copying them:

| Construction control | Canonical source |
|---|---|
| start identity | `ProjectActivation`, `Contract`, `ContractRevision` |
| authority lineage | `AuthorityCase`, `AuthorityOutcome`, `AuthoritySubmissionCycle`, `ExternalSubmissionSnapshot`, `SubmissionPackage`, `PreparationRevision` |
| approved design | `ApprovedDesignBaseline`, `ApprovedDesignBaselineMember`, `EngineeringRendition`, exact `DocumentVersion` |
| people and authority | `Party`, `PartyRoleAssignment`, `AuthorizationGrant`, `ProfessionalCredential` |
| requirements/evidence | `RequirementDefinition`, `RequirementPolicyVersion`, `RequirementInstance`, `PhysicalEvidenceItem`, `EngineeringMaterialTest` |
| traceability | `AuditEvent`, `LineageEdge` |

Construction-specific tables are execution-scoped projections and immutable command snapshots, not replacement party, document, authority, engineering, or requirement repositories.
