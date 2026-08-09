# Precheck Finding Ingestion Contract

`AuthorityPrecheckRun` + `AuthorityPrecheckItem` convert through `AuthorityEvent(source_type=AUTHORITY_PRECHECK)` into Finding, controlled code, routed WorkflowTask, and NotificationEvent. Every generated finding retains the exact precheck run ID and preparation revision ID plus raw evidence reference and source item reference.

The Week 7 service rejects missing or mismatched run/revision context. A finding from R1 cannot be rebound to R2. The current-revision open-blocking endpoint reports precheck-clear only when no current blocking precheck finding remains.
