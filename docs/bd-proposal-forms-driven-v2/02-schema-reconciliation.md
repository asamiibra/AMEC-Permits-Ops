# BD / Proposal v2 schema reconciliation

| Logical concept | Current model/field | Reuse | Extend/new companion | Migration | Historical risk | Decision |
|---|---|---|---|---|---|---|
| Client / Party | `ClientAccount`; canonical `Party` | Yes | Nullable `ClientAccount.canonical_party_id` | Additive nullable FK | Low; existing IDs preserved | Link, never duplicate |
| Proposal contact | `Opportunity.proposal_fields_json` (`attn_contact`, mobile, email) and `ClientContact` | Yes | `ProposalContactContext` companion if needed | Backfill only known legacy fields | Do not infer legal role | Preserve commercial contact semantics |
| Property link | `Property` is canonical and project-scoped; `Opportunity.project_id` exists | Yes | Nullable Proposal property reference plus unresolved site snapshot | Additive | Legacy proposals have no property | Link or unresolved; no fabricated Property |
| Site snapshot | Proposal JSON location/area/photo | Yes | Typed proposal site/scoping snapshot | Preserve legacy JSON | Area meaning is ambiguous | Mark legacy area unspecified |
| Stakeholder intent | Canonical `Party`; no Proposal stakeholder intent found | Yes | `ProposalStakeholderIntent` | New rows only | Never case-role assignment | Add intent/status/source refs |
| Source link | `ProposalSourceEvidence`, `DocumentVersion`, `ProposalIntakeArtifact` | Yes | Exact `document_version_id` on evidence / source link | Deterministic only | Binary duplication and mutable current source | Pin exact versions |
| Observation/assertion | `FieldObservation`, `VerifiedAssertion`, conflict model | Yes | Proposal refs/snapshot state | No invented facts | Accept must not verify facts | Consume and snapshot state |
| Assumption | Owner settings and JSON fields; no typed Proposal assumption found | Partial | `ProposalAssumption` | New typed records; no invented legacy rows | Material acknowledgements must be revision-safe | Separate Unknown/Assumption/Conflict |
| Conflict | Canonical source conflict fields and Issues | Partial | Proposal conflict reference/materiality if needed | Preserve existing source conflicts | Do not silently select a winner | Visibility + readiness effect |
| Area | `proposal_fields_json.area` | Partial | Typed value/unit/kind in Proposal scope snapshot | Legacy `LEGACY_UNSPECIFIED` | No GFA/plot inference | Commercial scoping basis |
| Service scope item | Narrative `scope_of_work`/SOW fields only | Partial | `ProposalServiceScopeItem` | New rows; preserve narrative | Catalog IDs must remain canonical | Structured rows + narrative |
| Regulatory scope intent | Legacy `authority_approval` text only | No | `ProposalRegulatoryScopeIntent` | Preserve legacy text read-only | No ExternalBody auto-creation | Intent only; human confirmation |
| External cost | Amount/quotation fields; no clear typed pass-through model | Partial | `ProposalExternalCostAssumption` if needed | New rows | Keep separate from AMEC amount | Explicit treatment |
| Readiness | `validate_proposal` derived blockers/warnings | Yes | Extend derived result, no setter | No destructive migration | Avoid Permit-ready meaning | Commercial readiness |
| Accepted snapshot | `ProposalAcceptedRevision.snapshot` JSON, exact template/checklist fields | Yes | Expand snapshot schema and lineage | Existing revisions immutable | Never rewrite history | Snapshot all relied-on context |
| Requirement preview | No Proposal-backed preview model found | No | `ProposalExpectedInputPreview` | New immutable/open refresh records | No Requirement duplication | Pin policy/view/result |
| Handoff | `Contract.accepted_proposal_revision_id`, existing service | Yes | Expand handoff payload only | Additive | Contract must consume exact R1 | No current re-resolution |

Chosen revision pattern: retain `Opportunity` as the mutable draft aggregate and store typed companion children under it; at Accept, serialize all relied-on structured children, exact source/template/checklist/policy references, fact states, commercial terms, assumptions, conflicts, and scoping intent into the immutable `ProposalAcceptedRevision` snapshot. Post-accept edits affect a new draft/current state and never mutate the accepted row.

Status: `RECONCILED_AND_VERIFIED`.
