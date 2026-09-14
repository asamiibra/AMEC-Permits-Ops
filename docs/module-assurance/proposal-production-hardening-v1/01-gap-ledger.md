# P0/P1 gap ledger

Status vocabulary: `OPEN`, `IMPLEMENTED_PENDING_GATE`, `BLOCKED_EXTERNAL`, `NOT_RUN`.

| ID | Required closure | Baseline evidence | Status |
|---|---|---|---|
| P0-A | Canonical active ClientAccount; no production autocreation | `require_canonical_active_client()`; production create negative | IMPLEMENTED_PENDING_GATE |
| P0-B | Authenticated principal audit | request-local principal binding; caller actor ignored; audit metadata carries identity context | IMPLEMENTED_PENDING_GATE |
| P0-C | Governed template/checklist + real renderer + DocumentVersion/storage readback | governed source hash, production renderer, Document/DocumentVersion, verified readback; unsupported binary renderer fails closed | IMPLEMENTED_PENDING_GATE |
| P0-D | No synthetic governance evidence in production | backend production boundary plus production frontend API payload guard; TEST-only fixtures retained | IMPLEMENTED_PENDING_GATE |
| P0-E | Evidence-backed service eligibility | active canonical client, professional party, exact evidence version, capability/policy references required | IMPLEMENTED_PENDING_GATE |
| P0-F | Server-derived LPO reconciliation | exact LPO DocumentVersion metadata fields compared by `SERVER_LPO_COMPARATOR_V1`; caller variances ignored in production | IMPLEMENTED_PENDING_GATE |
| P0-G | Exact client acceptance evidence | exact accepted revision/client/contact/DocumentVersion/hash binding | IMPLEMENTED_PENDING_GATE |
| P0-H | Causal staleness revalidation | direct production clear rejected; draft revision, all active event IDs, reviewer/result persisted | IMPLEMENTED_PENDING_GATE |
| P0-I | Same-revision/current-scope release and handoff | release checks exact accepted artifacts/scope/eligibility; handoff rejects failed distribution and missing LPO evidence | IMPLEMENTED_PENDING_GATE |
| P1-A | Forward-safe migration recovery | `proposal_production_hardening_v1` adds nullable bindings; downgrade preserves history/bytes | IMPLEMENTED_PENDING_GATE |
| P1-B | Truthful distribution semantics | delivery status, receipt reference, explicit FAILED/external-evidence states persisted; failed delivery blocks handoff | IMPLEMENTED_PENDING_GATE |
| P1-C | Technical evidence semantics | PASS requires exact stored evidence DocumentVersion in production | IMPLEMENTED_PENDING_GATE |
| P1-D | Production response boundary | production projections derive `synthetic_only` from explicit TEST mode; frontend guard blocks synthetic payload markers | IMPLEMENTED_PENDING_GATE |

Unresolved P0 gaps block any final production PASS. Existing synthetic tests remain valid only under explicit TEST mode and must not be reused as production evidence.
