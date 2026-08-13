# Canonical domain reuse map

The Permit / Authority Case UX adds no Permit-local source-of-truth model. Every displayed value is read from, or derived from, the following canonical records.

| UX concept | Canonical source | Read rule |
|---|---|---|
| Permit / case | `AuthorityCase`, `RegulatoryJourney` | Join the case to its journey and activated project. |
| Permit number | `AuthorityCaseIdentifier` | Use approved authority identifiers in configured priority order; never use a database ID or project code. |
| Project | `Project`, `ProjectActivation` | Only activated projects can start a case. |
| Proposal scope | accepted Proposal / Contract regulatory-scope records | Show as a suggestion and require explicit Owner confirmation. |
| External body / jurisdiction / service | `ExternalBody`, `Jurisdiction`, `ServiceType` | Use active catalog records only. |
| Requirement | `RequirementInstance`, `RequirementPolicyVersion`, requirement catalog | Project status and blocker reason are derived from canonical requirement state. |
| Evidence | evidence evaluation and selection records, `DocumentVersion`, `VerifiedAssertion` | A selected version is immutable and traceable to its source. |
| Property / ownership / parties | `Property`, `PropertyOwnership`, `Party`, assertions and source versions | Display provenance and mask sensitive identifiers by default. |
| Drawing | `ApprovedDesignBaseline`, baseline member, `EngineeringDeliverableRevision`, `EngineeringRendition`, `DocumentVersion` | Require an explicit baseline/member/revision/rendition chain. |
| Form | `FormInstance`, `FormAutomationProfile`, mapping release, rendered artifact | Preserve automated/manual origin and signature/stamp state. |
| Preparation | `PreparationRevision`, preparation requirements, evidence selections, readiness | Show revision and readiness; do not copy into Permit tables. |
| Precheck / submission | precheck records, `SubmissionPackage`, attempts, snapshots, cycles | Use immutable snapshots for history. |
| Comments / findings | `AuthorityCaseFinding` and response records | Count only open findings in portfolio. |
| Outcome / license | `AuthorityCaseOutcome`, identifiers, authority document version | Render outcome provenance and document actions only when evidence-backed. |
| History / lineage | audit events and lineage edges | Link each material decision to actor, timestamp, source, and revision. |

## Explicit non-models

The UX must not create `PermitProject`, `PermitParty`, `PermitProperty`, `PermitRequirement`, `PermitDocument`, `PermitDrawing`, `PermitForm`, `PermitComment`, `PermitApproval`, `permit_status`, `permit_project_details`, `permit_comments`, `permit_documents`, `permit_drawings`, or `permit_forms` tables. Backend access is through projections and existing canonical APIs/models.
