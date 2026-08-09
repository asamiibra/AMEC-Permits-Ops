# Minimum requirement and dependency matrix v0

| Requirement | Applicability | Evidence | Blocking | Synthetic test case |
|---|---|---|---|---|
| `TITLE_DEED_PRESENT` | All building permits | Current TITLE_DEED | Yes | Clean and poor-OCR title deeds |
| `OWNER_ID_PRESENT` | All owner cases | Current OWNER_QID | Yes | Conflicting QID |
| `DRAWING_PACKAGE` | All building permits | DRAWING_SET + metadata controls | Yes | R01/R02 mismatch |
| `CIVIL_DEFENCE_NOC` | Based on permit scope | Approved, current NOC or dependency | Yes | Expired dependency for PRJ-2026-002 |

Dependency status and validity dates are evaluated at readiness time. An `APPROVED` document with an expired `valid_until` remains historical evidence but does not satisfy a current requirement.
