# Negative matrix

Covered by focused API/unit tests and the browser journey:

| Denial/control | Result |
|---|---|
| Release before accepted revision/scope/eligibility | Denied, fail closed |
| Engineering/AI-only release or acceptance | Denied by capability/human gate |
| Distribution before protected release | Denied |
| Acceptance verification without `ACCEPTED` client evidence | Denied |
| LPO without client evidence | Denied |
| LPO variance | Persisted as `MISMATCH`; handoff blocked |
| Unauthorized LPO/release/handoff capability | Denied |
| Stale revision release | Denied with `STALE_REVISION_RELEASE_FORBIDDEN` |
| Cross-proposal source/idempotency key | Denied |
| Duplicate protected transition | Idempotent or rejected; no duplicate row |
| Contract acceptance / Project activation from Proposal | Not performed by Proposal; boundary endpoint returns eligibility only |
| Ambiguous/inactive/wrong-purpose Content Library resolution | No auto-selection |
