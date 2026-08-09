# Official Municipality Comment Manual Capture

Week 7 supports manual/synthetic returned-application comments only. Capture creates or reuses a typed `SubmissionCycle`, then persists an official `AuthorityEvent` and `Finding` with official source type, review-cycle reference, raw comment, timestamp, application identity, evidence, owner, task, and notification.

No scheduled status/comment polling or live authority monitoring is implemented. Official comments never receive an `AuthorityPrecheckRun` link.
