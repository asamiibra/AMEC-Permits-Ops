# Status / comment monitoring runbook

Policy and read mode are visible at `/api/monitoring/policies`; runs are recorded with three `MonitoringCheck` rows for `READ_CURRENT_STATE`, `READ_STATUS`, and `READ_COMMENTS`. A trusted snapshot is compared with the prior snapshot.

`NO_CHANGE` records remain auditable. Status, repetition, or new comment creates an `AuthorityEvent`; new comments route through Finding → Task → Notification. Repeated unchanged comments are deduplicated. Auth/MFA failures use bounded retry rules; outage falls back to `/api/monitoring/manual-capture`.

Drift sequence: **DRIFT → STOP TRUSTING AUTOMATED PARSE → preserve raw evidence → manual/assisted capture → maintainer escalation → contract validation → re-enable**. External human mutation creates lineage material-change invalidation. Notification failure remains observable and support-routable.
