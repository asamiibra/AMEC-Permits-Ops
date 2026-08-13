# Dependency reconciliation

| Concept | Canonical current model/service | Proposal consumes? | Proposal owns? | Reuse? | Extension needed? | Duplicate risk | Migration impact |
|---|---|---:|---:|---:|---:|---|---|
| Commercial Client | `ClientAccount` plus canonical `Party` | Yes | Commercial compatibility link only | Yes | Link/compatibility fields | Do not create Proposal legal-party master | Add nullable canonical Party link; preserve historical ClientAccount IDs |
| Proposal Contact | `ClientContact`, canonical contact/Party capability where available | Yes | Proposal-purpose contact snapshot/reference | Yes | Explicit purpose/status semantics | Do not equate contact with Owner/Applicant/signatory | Preserve Attn/Contact/Mobile/Email |
| Property | `Property`, `PropertyOwnership`, source refs | Yes | Site scoping snapshot when unresolved | Yes | Proposal link and unresolved state | Do not create `ProposalProperty` master | Add nullable link; preserve legacy location/area |
| External facts | `FieldObservation`, `VerifiedAssertion`, conflicts | Yes | No | Yes | Proposal source/reference projections | No Proposal observation/fact tables | Pin refs/status at Accept |
| Sources | `Document` / `DocumentVersion`, existing transactional intake evidence | Yes | Proposal source links | Yes | Exact version link and source role | Do not promote tender evidence to Dashboard master content | Backfill only deterministic links |
| Stakeholder intent | Canonical `Party` and role/resolution path | Yes | Proposal context intent | Yes | Companion intent records | Never create case-role assignment | New records snapshot at Accept |
| Service scope | Existing commercial Proposal fields/catalogues | Yes | AMEC commercial scope rows | Yes | Structured companion rows | Do not use ServiceType as AMEC offering | New rows; narrative SOW preserved |
| Regulatory scope | `ExternalBody`, `Jurisdiction`, `ServiceType`, versions | Yes | Proposal scoping intent only | Yes | Companion intent records | Never create AuthorityCase/RegulatoryJourney | New rows; preserve legacy Authority text |
| Requirement preview | `RequirementPolicyVersion`, resolver/evaluator | Read-only | Preview snapshot only | Yes | Preview snapshot seam | No second Requirement Engine | Pin policy/view/result at Accept |
| Proposal Template/Checklist | `MasterContentItem` / `DocumentVersion` resolver | Yes | No master content | Yes | Exact pins already exist | No Dashboard V1/V2 proposal masters | Preserve current resolver and renderer |
| Technical contribution | Canonical technical rule foundation | Read-only | Proposal contribution context | Yes | Optional pinned reference | No Proposal rule engine | Snapshot supporting refs only |
| Form Automation | Canonical runtime | Read-only governance metadata only | No | Yes | None unless existing renderer intentionally uses it | No Proposal renderer/runtime duplicate | No mapping-release writes from Proposal |
| Readiness | Existing Proposal validation and owner decisions | Yes | Proposal commercial readiness | Yes | Derived v2 dimensions | No arbitrary `ready=true` | Preserve old validation semantics |
| Accepted revision | `ProposalAcceptedRevision` | Yes | Immutable Proposal snapshot | Yes | Expanded snapshot payload | No current-state reconstruction | Add structured snapshot refs where needed |
| Contract handoff | `create_contract_from_proposal`, Admin Contract | Yes | Handoff payload only | Yes | Exact accepted revision payload | No live current Proposal re-resolution | Preserve existing contract seam |
| My Work / Issues / Notifications / Audit | Existing shared services/models | Yes | No duplicate operations hub | Yes | High-value aggregated hooks | Avoid task-per-field noise | Add bounded events/tasks only |

Decision: implement the smallest companion records and typed columns needed to make Proposal commercial/scoping state reconstructable, while keeping Party, Property, Regulatory Core, Requirement Engine, Technical Rule, Form Automation, and master content canonical upstream domains.

Status: `RECONCILED_AND_VERIFIED`.
