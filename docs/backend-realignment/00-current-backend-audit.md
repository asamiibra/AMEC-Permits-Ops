# Backend realignment audit

## Scope and evidence

This audit is the B0 baseline for the canonical Proposal → Contract → Permit
realignment. It was performed against the FastAPI/SQLAlchemy/Alembic backend,
the existing expansion models, the ProposalOps SOR service, the canonical
synthetic seed, and the deployed Neon runtime. The audit intentionally treats
the current `Opportunity`/`Quotation` vocabulary as compatibility vocabulary;
new ProposalOps writes and projections use Proposal/ProposalRevision terms.

## Current domain inventory

| Prompt concept | Current primitive | B0 disposition | Reason |
|---|---|---|---|
| Proposal | `Opportunity` | `REUSE_AS_CANONICAL` | Existing opportunity row already owns client, status, intake identity and lifecycle; API presents it as Proposal. |
| ProposalRevision | `Quotation` + `QuotationRevision` | `REUSE_AS_INTERNAL_COMPATIBILITY` | Existing quotation revision chain is already the durable proposal snapshot used by ContractRevision. No duplicate revision table is introduced. |
| Contract | `Contract` | `REUSE_AS_CANONICAL` | Existing contract model and revision chain are preserved and extended with explicit `project_id`. |
| ContractRevision | `ContractRevision` | `REUSE_AS_CANONICAL` | Existing controlling quotation revision relationship is preserved. |
| PermitApplication | `PermitApplication` | `REUSE_AS_CANONICAL` | Existing permit engine, package, findings, municipality and human-submit controls remain authoritative. |
| Project | `Project` | `REUSE_AS_CANONICAL` | Existing canonical AMEC project identity and Synology root remain authoritative. |
| Reference lifecycle | `Opportunity.reference_state`, `ReferenceNumber`, lineage | `EXTEND` | Provisional and canonical identity are now explicit and reconciled without deleting the provisional reference. |
| Source artifact | `ProposalIntakeArtifact`, `ProjectArtifactRecord` | `REUSE_AS_CANONICAL` | One service contract governs provisional and canonical writes; the two records reflect storage lifecycle, not two SORs. |
| DocumentVersion | existing week-2 `DocumentVersion` | `REUSE_AS_CANONICAL` | Read-back-verified metadata is registered here. |
| EvidenceArtifact | existing `EvidenceArtifact` | `REUSE_AS_CANONICAL` | Evidence pointer and hash remain in the workflow DB; bytes remain in the configured SOR. |
| WorkflowTask | existing week-7 `WorkflowTask` | `REUSE_AS_CANONICAL` | Handoffs create/update the existing task primitive. |
| AssistantHandoff | existing `AssistantHandoff` | `REUSE_AS_CANONICAL` | Responsibility transitions are recorded without creating a second Proposal. |
| Notification | existing `NotificationEvent` | `REUSE_AS_CANONICAL` | Existing finding/task notification machinery remains in place. |
| Lineage | existing `LineageEdge` | `REUSE_AS_CANONICAL` | Source, promotion, revision and transition lineage use the existing graph. |
| SOR | `MockSynologyAdapter` + configured project root | `REUSE_AS_CANONICAL` | Adapter is the synthetic/runtime repository of record; database stores index, metadata and provenance only. |
| RBAC | `Role` + `current_user_role` | `EXTEND` | Existing roles map to exactly three user-facing personas and capabilities are enforced at write boundaries. |
| Duplicate Proposal/Permit entities | none required | `DEPRECATE_FROM_NEW_WRITES` | New commands must resolve existing canonical records; no parallel ProposalOps permit is allowed. |

## Existing route/service audit

The previous ProposalOps implementation already supplied provisional intake,
read-back verification, canonical SOR promotion, Proceed, Engineering Ready,
Proposal → Contract, Contract → Permit, list KPIs and detail routes under
`/api/proposals-main`. The remaining closure work was concentrated in four
areas: a single query/capability contract, canonical route aliases and
projections, strict typed project-mismatch gates, and evidence that the
negative paths cannot be converted into successful or fake-empty responses.

## Invariants adopted by the backend

* `Contract.project_id == Proposal.project_id` whenever either side is
  canonicalized.
* `PermitApplication.project_id == Contract.project_id` for a controlling
  contract link.
* A project mismatch is a typed 409 and never a best-effort relink.
* SOR registration follows target read-back verification.
* Same context, artifact class and content hash is idempotent; a different
  hash is a new revision and retains supersession/provenance.
* Proposal extraction is candidate evidence. The proposal projection exposes
  provenance and verification state rather than asserting that a raw source is
  trusted truth.

## Known non-blocking compatibility notes

The internal database names `Opportunity`, `Quotation` and legacy role names
because those tables predate the ProposalOps surface. They remain stable for
existing permit and expansion workflows. The canonical API contract and
documentation use Proposal, ProposalRevision and the three user-facing
personas; migration of historical table names is intentionally not required.
