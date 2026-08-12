# Administration + Contract Owner Session — Architecture to Protect

Date: 2026-08-12
Protected baseline: `f07a46ccd065e9a51c9aac0b3905cc3c6fd400b9` on `main`
Scope: Administration + Contract → explicit Project activation only

## Canonical truth map

| Contract requirement | Existing canonical primitive | Protection rule | Current state |
|---|---|---|---|
| Client | `ClientAccount`, `ClientContact` | No Administration-specific Client store or copy | `PROTECTED_AND_VERIFIED` |
| Proposal | `Opportunity` plus BD Proposal APIs | Contract creation consumes Proposal context; no Proposal redesign | `PROTECTED_AND_VERIFIED` |
| Accepted Proposal revision | `ProposalAcceptedRevision` and `ProposalOutputArtifact` | Contract stores exact accepted revision ID/hash; later Proposal edits do not rewrite it | `PROTECTED_AND_VERIFIED` |
| Contract | Existing `Contract` and `ContractRevision` | Extend the existing model; do not create a second Contract repository | `PROTECTED_AND_VERIFIED` |
| Project | Existing canonical `Project` | Activation links or creates one canonical Project; Project/Opportunity Reference remains separate from Project Code | `PROTECTED_AND_VERIFIED` |
| Documents/templates | `MasterContentItem`, `DocumentVersion`, Dashboard purpose resolver | Contract Template is resolved through `ADMIN / CONTRACT_TEMPLATE`; history stores version/hash snapshots | `PROTECTED_AND_VERIFIED` |
| Tasks | `WorkflowTask` | Contract work projects into existing My Work context | `PROTECTED_AND_VERIFIED` |
| Issues | `Finding` | Contract issues use existing shared issue semantics | `PROTECTED_AND_VERIFIED` |
| Notifications | `NotificationEvent` | Contract events use existing in-app notification semantics | `PROTECTED_AND_VERIFIED` |
| Audit | `AuditEvent` | Human authority and revisions remain append-only and auditable | `PROTECTED_AND_VERIFIED` |
| Lineage | `LineageEdge` | Contract/accepted revision → Project activation lineage is relational and hash-aware | `PROTECTED_AND_VERIFIED` |
| RBAC | `require_capability`, `CAPABILITY_MATRIX`, `Role` | Owner-only Contract authority and Project activation; BD/Engineering read-only Contract context | `PROTECTED_AND_VERIFIED` |
| PostgreSQL | SQLAlchemy/Alembic runtime | New schema is additive and migrates through PostgreSQL | `PROTECTED_AND_VERIFIED` |
| SOR | Existing Synology adapter boundary | Synthetic SOR remains explicit; real Synology is the only external exception | `PROTECTED_AND_VERIFIED` |

## Authority boundaries

`Proposal Accept` ≠ `Contract authority / execution` ≠ `Project activation`.

The Contract implementation must not infer legal execution from Proposal acceptance, must not activate a Project from Contract existence, and must not grant BD or Engineering commercial/activation writes.

## Duplicate-truth prohibition

This run must not introduce a duplicate Client store, Project store, Proposal snapshot store, Contract Template repository, document repository, task system, issue system, notification system, renderer, or RBAC system. New records are limited to Contract-specific revision/template/input/evidence/activation metadata that references the canonical primitives above.

## Protected frozen modules

- `BD_PROPOSAL_OWNER_SESSION_FROZEN_READY_EXCEPT_REAL_SYNOLOGY`
- `DASHBOARD_OWNER_SESSION_V3_FROZEN_READY_EXCEPT_REAL_SYNOLOGY`

No BD Proposal redesign, Dashboard master-content redesign, Engineering execution redesign, Permit redesign, Invoice workflow, Handover workflow, e-signature, ERP, or new AI platform is in scope.

Result: `ADMIN_CONTRACT_ARCHITECTURE_PROTECTED`.
