# Owner-sketch reconciliation

| Owner annotation | Implemented component |
|---|---|
| Orange Client List | `proposal-orange-action` → `CLIENT_LIST` → `CLIENT_SOURCE` |
| Orange Proposal Form | `proposal-orange-action` → `PROPOSAL_FORM` → `PROPOSAL_SOURCE` |
| Orange Contract Form | `proposal-orange-action` → `CONTRACT_FORM` → `CONTRACT_SOURCE` |
| Orange New Proposal | orange action and toolbar button → `NEW_PROPOSAL` → `OPPORTUNITY_SOURCE` |
| Blue Open Proposal | `OPEN_PROPOSALS` KPI and table filter |
| Blue Open Contract | `OPEN_CONTRACTS` KPI and table filter |
| Blue Handover Contract | `CONTRACT_HANDOVER` KPI and table filter |
| Blue Handover Proposal | `PROPOSAL_HANDOVER` KPI and table filter |
| Blue Under Process Contract | `CONTRACTS_IN_PROCESS` KPI and table filter |
| Blue Under Process Proposal | `PROPOSALS_IN_PROCESS` KPI and table filter |
| Proposal Description | main table primary column |
| Project Reference | main table identity column and upload read-only context |
| Current Stage / Status | main table state badge |
| Amount | system-displayed governed field; hidden for Engineering |
| Last Activity | derived from meaningful record/artifact events |
| Open | shared project/proposal workspace deep link |

The owner’s orange/blue visual grammar is preserved on mobile through responsive action/KPI grids and a scrollable table.
