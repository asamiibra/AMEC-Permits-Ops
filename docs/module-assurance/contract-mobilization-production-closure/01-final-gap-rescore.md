# Final CM-G01..CM-G17 rescore

| Gap | Result | Executable basis |
|---|---|---|
| CM-G01 | CLOSED_AND_PROVEN | `readiness()` and acceptance tests keep review and execution states distinct. |
| CM-G02 | CLOSED_AND_PROVEN | Authority approval tests prove approval does not accept or activate. |
| CM-G03 | CLOSED_AND_PROVEN | Distinct authenticated maker/checker and same-actor denial are tested. |
| CM-G04 | CLOSED_AND_PROVEN | `commercial_reconciliation()` and exact Proposal/LPO evidence controls fail closed. |
| CM-G05 | CLOSED_AND_PROVEN | Executed evidence is exact-revision, versioned, human-recorded, and idempotent. |
| CM-G06 | CLOSED_AND_PROVEN | Client-copy distribution and Operations handoff are separate append-only evidence actions. |
| CM-G07 | CLOSED_AND_PROVEN | Read-only start-prerequisite projection exposes independent contract/payment/start facts. |
| CM-G08 | CLOSED_AND_PROVEN | Project Activation remains a protected human action after acceptance and prerequisites. |
| CM-G09 | CLOSED_AND_PROVEN | ServiceEngagement remains canonical and exact Contract/Project/revision scoped. |
| CM-G10 | CLOSED_AND_PROVEN | Four independent readiness states are exposed with policy, evidence, timestamp, and result. |
| CM-G11 | CLOSED_AND_PROVEN | Operations remains a projection over canonical rows and now includes clock/contact/readiness/billing fields. |
| CM-G12 | CLOSED_AND_PROVEN | Billing milestone eligibility is read from canonical Billing; invoice issue remains separate. |
| CM-G13 | CLOSED_AND_PROVEN | Project activation is not used as duration start; clock/extension state is explicit. |
| CM-G14 | CLOSED_AND_PROVEN | Existing Handover, Service close, and administrative close separation is preserved and tested. |
| CM-G15 | CLOSED_AND_PROVEN | Existing authorization/Form package and capability controls are preserved. |
| CM-G16 | PARTIAL | Contact absence is surfaced as `CONTACT_RESOLUTION_REQUIRED`; purpose-specific contact capture/UAT remains environment work. |
| CM-G17 | CLOSED_AND_PROVEN | Existing source-scope gates plus exact revision binding reject mismatched evidence paths. |

CM_G_IMPLEMENTATION_RESULT=PARTIAL
CM_G_PRODUCTION_GATE_RESULT=BLOCKED_BY_GOVERNED_ENVIRONMENT_EVIDENCE
