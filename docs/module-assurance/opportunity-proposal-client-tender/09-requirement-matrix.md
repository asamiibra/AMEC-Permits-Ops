# Final 37-control matrix

All controls have a final status; there are no `BLOCKED`, `FAIL`, or `UNKNOWN` outcomes in this module matrix.

| ID | Control | Status |
|---|---|---|
| OP01 | Current-main baseline and branch identity | PASS |
| OP02 | Single Proposal identity | PASS |
| OP03 | Tender/RFP source intake | PASS |
| OP04 | Client source evidence | PASS |
| OP05 | Source read-back and lineage | PASS |
| OP06 | Site/technical assessment | PASS |
| OP07 | Scope confirmation | PASS |
| OP08 | Service eligibility | PASS |
| OP09 | Governed Proposal Template resolver | PASS |
| OP10 | Governed Proposal Checklist resolver | PASS |
| OP11 | Deterministic Content Library selection | PASS |
| OP12 | Proposal preparation fields | PASS |
| OP13 | Engineering handoff | PASS |
| OP14 | Commercial readiness consolidation | PASS |
| OP15 | Human Proposal review | PASS |
| OP16 | Exact revision acceptance | PASS |
| OP17 | Immutable accepted revision | PASS |
| OP18 | Proposal and Checklist outputs | PASS |
| OP19 | Stale revision protection | PASS |
| OP20 | Protected commercial release | PASS |
| OP21 | Release idempotency | PASS |
| OP22 | Distribution evidence | PASS |
| OP23 | Distribution idempotency | PASS |
| OP24 | Client Response evidence | PASS |
| OP25 | Client acceptance verification | PASS |
| OP26 | LPO/PO reconciliation | PASS |
| OP27 | LPO mismatch blocking | PASS |
| OP28 | Contract handoff eligibility | PASS |
| OP29 | Contract boundary | PASS |
| OP30 | Project Activation boundary | PASS |
| OP31 | Human role capability enforcement | PASS |
| OP32 | Cross-client/proposal isolation | PASS |
| OP33 | Real AMEC/DSM/Entra integration | N/A — synthetic scope |
| OP34 | SQL Server migration/persistence | PASS |
| OP35 | Governed CI/cold review | FORMAL DEFER — later gate |
| OP36 | Pre-production/production deployment | LATER GATE — not in scope |
| OP37 | Final branch/PR seal | PASS |

`REQUIREMENT_COUNT=37`, `REQUIREMENT_ORPHANS=0`, `P0_UNRESOLVED=0`.
