# SLA Policy Contract

`FindingSlaPolicy` stores acknowledgement, assignment, target-action, and escalation hours plus calendar mode, version, and active state. Week 7 seeded values are explicitly labeled `PROVISIONAL_SYNTHETIC` and are not contractual client SLAs.

The console/report derives `ON_TIME`, `DUE_SOON`, and `OVERDUE`; escalation timing is persisted on the task as `escalation_at` and exposed for later operational hardening.
