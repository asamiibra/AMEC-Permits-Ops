# Phase4 compatibility and P07 review debt

P03 preserves legacy Phase4 review behavior and does not expand its central-review shape. P07 must later reconcile these seams into module-owned review without breaking existing compatibility.

| Current behavior | Current owner | Future intended owner | P03 treatment | Classification |
| --- | --- | --- | --- | --- |
| Phase4 source/evidence/classification envelope persistence | Phase4 service | Shared immutable evidence primitives plus consuming module | Keep unchanged; P03 wraps with candidate projection | `KEEP_AS_SHARED_PRIMITIVE` |
| `review_queue` over pending classification envelopes | Phase4 service | Consuming module-owned review queue | Retain for backward compatibility; P03 never calls it | `LEGACY_COMPATIBILITY_TO_RETAIN` |
| `Phase4ReviewDecision` and six review decisions | Phase4 service/authorized capability | Consuming module review command | Do not refactor in P03 | `MODULE_OWNERSHIP_TO_BE_ADDED_P07` |
| Phase4 promotion bridge to `VerifiedAssertion` | Phase4 service and authorized human capability | Module-owned promotion command | P03 never invokes it | `MODULE_OWNERSHIP_TO_BE_ADDED_P07` |
| Phase4 typed projection plan/receipt | Phase4 service and domain command | Module-owned canonical transition | P03 never invokes it | `MODULE_OWNERSHIP_TO_BE_ADDED_P07` |
| Phase4 `WorkflowTask` / `NotificationEvent` coupling in existing review flows | Phase4/legacy workflow surfaces | Module-owned queue and notification policy | No new task or notification for a P03 candidate | `CENTRAL_REVIEW_BEHAVIOR_TO_RETIRE_OR_CONTAIN_P07` |
| `AuditEvent`, immutable hashes, record versions, and idempotency keys | Shared audit/Phase4 primitives | Shared immutable decision/evidence primitives | Reuse unchanged | `KEEP_AS_SHARED_PRIMITIVE` |

Required principle: P03 does not break legacy review; P03 does not expand central review; P07 reconciles review ownership.

