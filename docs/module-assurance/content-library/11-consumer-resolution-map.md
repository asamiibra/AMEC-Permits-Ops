# Consumer Resolution Map

| Consumer | Resolver/seam | Allowed Content Library projection | Status |
|---|---|---|---|
| BD Proposal | `proposal_workspace.master_content_purpose` | exact current FORM template/checklist | PASS |
| Engineering proposal | `engineering_references_for_proposal` / canonical candidates | `ENGINEERING_WORK` only | PASS |
| Permit/regulatory preparation | Source18/currentness + preparation seams | current Form source and exact OfficialFormVersion | PASS |
| Contract/Admin | purpose resolver | `ADMIN` `CONTRACT_TEMPLATE` Form | PASS |
| Reports | dependency and report-definition seams | reusable REPORT source; actual report remains Project artifact | PASS |
| Requirements | policy/source lineage | Form/Definition source only; requirement state remains engine-owned | PASS |
| Evidence | governed prefill/citation seam | source/version citation only | PASS |
| Correspondence | construction/correspondence domain | reusable template only | OUT_OF_SCOPE |
| Handover | Handover domain | reusable template only | OUT_OF_SCOPE |
| Finance | Finance domain | no operational finance state | OUT_OF_SCOPE |

Resolution is deterministic and ambiguity is preserved rather than selecting the first row.
