# State separation

The implementation preserves these independent transitions:

`Proposal approval` → `client acceptance` → `PO/LPO reconciliation` →
`Contract review` → `maker/checker` → `internal acceptance` → human execution
evidence → client-copy distribution → Operations handoff → commercial readiness
→ human Project Activation.

`HANDOVER_READY`, delivery, receipt, ServiceEngagement close, Contract
administrative close, and financial settlement remain separate canonical states.
The new `readiness-states` and `start-prerequisites` endpoints are read-only.
