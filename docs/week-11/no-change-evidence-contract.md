# No-change evidence contract

Every trusted read creates one `MonitoringCheck` for each configured read operation. The check stores prior/current contract fingerprints, comparison result, status, repetition, comment count, normalized state hash, and evidence reference. Identical reads create checks but no new AuthorityEvent, Finding, Task, or notification.
