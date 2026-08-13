# Domain reconciliation

## Canonical domains retained

| Concern | Existing canonical source | Engineering use |
|---|---|---|
| Project | `projects` / `backend.app.models.entities.Project` | Foreign-key anchor; no second project table |
| Activation | `project_activations` / Admin Contract activation service | Hard gate before new engineering work |
| Binary/version truth | `documents`, `document_versions` | Exact native and published rendition pins |
| Parties and credentials | Shared Party / PartyCredential models | Approver and laboratory identity seam |
| Property | Shared Property models | Project context only; no duplicate property identity |
| Technical rules | `TechnicalRuleSetVersion`, `TechnicalRule`, evaluator service | Exact deterministic rule-set references and outcomes |
| Requirements | Requirement Engine foundations | Future internal-QA seam; no copied policy truth |
| Audit and lineage | `AuditEvent`, `LineageEdge` | Append-only history and evidence graph |
| Dashboard Engineering Works | `MasterContentItem` | Reusable master/reference content only; never project deliverable truth |

## New project-specific layer

The implementation may add Project Engineering records for work packages, stable deliverables, business revisions, renditions, review cycles/findings, professional approvals, technical evidence, material/lab evidence, immutable baseline manifests, and design changes. These records must reference the canonical domains above and must not reinterpret “latest file.”

## Boundary decisions

- Existing E5/E6 engineering advisory records remain bounded advisory/closeout workflows; they are not silently redefined as the new approved-design baseline.
- Professional approval is a human capability-controlled transaction over an exact revision and exact rendition set.
- AMEC approved baseline is distinct from external authority approval and construction release.
- Engineering does not create AuthorityCase, ExternalApproval, SubmissionPackage, or Construction Start records.
