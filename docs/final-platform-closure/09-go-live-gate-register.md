# Go-Live Gate Register

| Gate | Status | Waivable? | Owner acceptance required? |
|---|---|---:|---:|
| G1 Software | PASS synthetic | no | yes for handover |
| G2 Owner Decisions | FAIL | no for P0/P1 | yes |
| G3 Content Currentness | FAIL | no for launch-critical sources | yes |
| G4 Golden Service Pack | FAIL | no for selected launch service | yes |
| G5 Golden Slice | FAIL | no for broad GO | yes |
| G6 Storage | FAIL external | no when Synology is SOR | yes |
| G7 Database | PARTIAL / FAIL recovery | no for GO | yes |
| G8 Deployment | FAIL | no | yes |
| G9 Security | PARTIAL / FAIL production auth | no | yes |
| G10 Backup/Restore | FAIL | no | yes |
| G11 Reliability/Observability | PARTIAL | no for critical failures | yes |
| G12 Operations/Support | PARTIAL | conditionally | yes |
| G13 Training/Handover | FAIL | no | yes |
| G14 UAT/Defects | FAIL | no without Owner acceptance | yes |

Final decision: `NO_GO`. Conditions cannot waive storage, recovery, deployment provenance, critical currentness, security, or unresolved P0 decision gates.
