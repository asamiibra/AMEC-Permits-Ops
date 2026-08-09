# Open control disposition

No bare `NEEDS_REVIEW` state is carried into the pre-G10 decision.

| control_code | control_type | scenario/project | why NEEDS_REVIEW occurred | expected behavior | blocking? | owner | required verifier | evidence | current disposition | future proof point |
|---|---|---|---|---|---|---|---|---|---|---|
| `CTRL_DRAWING_METADATA_MATCH` | Synthetic drawing metadata control | `DEMO_BUILDING_PERMIT_V1` / `GHCE-2026-0187` | The synthetic returned-application variant deliberately omits one non-authoritative drawing metadata observation while preserving the canonical source value. The engine must not infer a match from absence. | Preserve the original `NEEDS_REVIEW`, expose the missing observation, require Responsible Engineer review, and prevent a consequential package/review escape until resolved. | Blocking for the affected package; nonblocking to the synthetic corpus-wide gate because the case is isolated and explicitly adjudicated. | Responsible Engineer | `RESPONSIBLE_ENGINEER` | `backend/app/services/week10.py`, `backend/app/services/configuration.py`, Week 10 control run evidence, synthetic returned-application case | `HUMAN_REVIEW_REQUIRED_BY_DESIGN` | Independent Week 10 control run and any approved real-data drawing evidence. |

The original engine result is not converted to `PASS`. The disposition records actor, evidence, and the reason the synthetic Wave 3 decision can proceed without claiming client-approved completeness.
