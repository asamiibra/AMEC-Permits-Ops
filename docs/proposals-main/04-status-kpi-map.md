# Status and KPI map

The API computes KPI counts from the same proposal-workspace rows returned to the page. The UI does not hold editable counters.

| KPI | Included proposal/contract state | Table filter |
|---|---|---|
| Open Proposals | `RECEIVED`, `IN_REVIEW`, `READY_FOR_QUOTATION`, `QUOTATION_IN_PROGRESS`, `COMMERCIAL_REVIEW`, `CLIENT_RESPONSE_PENDING` | proposal state in the listed set |
| Open Contracts | `DRAFT`, `CONTRACT_IN_PROGRESS`, `READY_FOR_ADMIN` | linked contract state in the listed set |
| Proposal Handover | `PROPOSAL_HANDOVER` | proposal handoff state |
| Contract Handover | `CONTRACT_HANDOVER`, `HANDOVER_DRAFT_READY`, `HANDOVER_RELEASED` | linked contract handoff state |
| Proposals In Process | `QUOTATION_IN_PROGRESS`, `COMMERCIAL_REVIEW`, `PROPOSAL_HANDOVER` | proposal process state |
| Contracts In Process | `DRAFT`, `CONTRACT_IN_PROGRESS`, `CONTRACT_HANDOVER` | linked contract process state |

Handover is only counted when the configured workflow state exists. No example count is injected to match a sketch.
