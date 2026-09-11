# Contract & Mobilization gap-closure implementation

## CM15 — ServiceEngagement authorization gate

`POST /api/handover/service-engagements` now requires all of the following before any ServiceEngagement row can be created:

- the supplied Project, Contract, and ContractRevision exist;
- the Contract is explicitly related to the supplied Project;
- the supplied revision is the Contract's exact current revision;
- the current revision has explicit accepted Contract evidence; and
- an active ProjectActivation exists for the same Project, Contract, and revision.

Wrong project, stale/wrong revision, pre-activation, unauthorized-role, and duplicate/idempotency paths remain denied or non-duplicating. This gate does not treat Proposal acceptance, Contract acceptance, Project Activation, or ServiceEngagement authorization as interchangeable.

## Executed Contract evidence

Executed-copy upload is a retained `DocumentVersion` operation. It becomes executed evidence only through the dedicated `POST /api/admin/contracts/{id}/executed-evidence` action, which pins the exact current accepted Contract revision and document version, records the evidence reference/hash/actor/time, writes an append-only audit event, and is idempotent. The persisted metadata explicitly states `HUMAN_CONTROLLED` signature policy and `NOT_INFERRED` forms completion.

No status, PDF, review, or Proposal acceptance is used as a substitute for executed evidence.

## CM16 — Operations projection

`GET /api/admin/contracts/{id}/operations` and the Contract workspace Operations surface are read-only projections over canonical Contract, ContractRevision, ProjectActivation/Project, ServiceEngagement, tasks, findings, required inputs, and retained evidence. The projection exposes status, dates, mobilization, blockers, overdue work, schedule/delay/risk, responsible/next action, invoice signals, and exact executed-evidence references. No second Operations database or authoritative UI state was introduced.

No AI or automated actor is granted a protected action path; external send remains `HUMAN_CONTROLLED`.
