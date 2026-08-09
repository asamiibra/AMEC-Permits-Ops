# Governance Status Reconciliation

The governance axes are intentionally separate:

| Axis | Status | Meaning |
|---|---|---|
| Synthetic Development Track | `PASS / ACTIVE_SYNTHETIC` | Synthetic implementation and local simulator evidence may continue |
| Formal Client Build Track | `NOT_AUTHORIZED / BLOCKED_EXTERNAL` | Client authorization, approved data path and accepted responsibilities are not evidenced |
| Live Production Track | `NOT_AUTHORIZED / BLOCKED_G10` | Production credentials, real Ministry write permission and G10 evidence are absent |

Stage 2: `DRAFT`, checksum present, reviewer acknowledgement if recorded means `REVIEWED`, not `APPROVED`.

Sign-off C: `DRAFT`, unsigned.

Real-data approval: absent. Approved data path: absent. Client responsibilities: not accepted in signed evidence. G10/live authorization: absent.

External blockers prevent approved-real/formal/live progression but do not block synthetic development or the synthetic Golden Path.

