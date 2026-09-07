# Consumer integration matrix

| Consumer/domain | Current lookup and identity | Binding/governance | Classification | Step 3 disposition |
|---|---|---|---|---|
| Owner Dashboard discovery | `canonical_master_content_read` | role-aware canonical projection | CANONICAL_DISCOVERY_ONLY | preserve |
| Governed retrieval | `governed_retrieve` | permission-aware evidence/citation | CANONICAL_DISCOVERY_ONLY | preserve; never select workflow sources |
| BD Proposal template | `resolve_master_content_purpose(BD, PROPOSAL_TEMPLATE)` | active binding, exact current `DocumentVersion`, governed readiness | CANONICAL_BUT_NOT_PINNED before acceptance | pin through `ProposalAcceptedRevision` |
| BD Proposal checklist | `resolve_master_content_purpose(BD, PROPOSAL_CHECKLIST)` | same as template; checklist remains a FORM | CANONICAL_BUT_NOT_PINNED before acceptance | pin through `ProposalAcceptedRevision` |
| BD definitions | `DefinitionEntry.current_revision_id` | exact `DefinitionRevision` projection | CANONICAL_AND_PINNED | preserve |
| BD engineering references | direct master query in Proposal adapter | current/reviewed/source-available/readiness gates | UNSAFE_DYNAMIC_LOOKUP | route through shared candidate seam |
| Contract template | `resolve_master_content_purpose(ADMIN, CONTRACT_TEMPLATE)` | `ContractTemplateSnapshot` exact item/version/hash | CANONICAL_AND_PINNED | preserve and regression-test |
| Form automation | profile source and `FormInstance` | exact item/version before create and render | MISSING_ELIGIBILITY_ENFORCEMENT | enforce |
| Completion form | profile source and case-bound `FormInstance` | case, exact item/version, readiness | MISSING_ELIGIBILITY_ENFORCEMENT | enforce |
| Permit/rule lineage | typed policy/rule source pointers | exact source identity | CANONICAL_AND_PINNED | preserve |
| Preparation/submission | project/case evidence and package pointers | transactional context | NOT_APPLICABLE | preserve; no master promotion |
| Project Engineering | project-bound evidence | transactional context | NOT_APPLICABLE | preserve |
| Reports/renderers | renderer metadata and transactional inputs | no reusable Master Content dependency | NOT_APPLICABLE | preserve |
| Handover/billing | project evidence and domain records | transactional context | NOT_APPLICABLE | preserve |
| Source Intake | explicit promotion producer | only explicit master promotion | NOT_APPLICABLE | preserve producer boundary |

The machine-readable companion is `02-consumer-classification-matrix.json`.
