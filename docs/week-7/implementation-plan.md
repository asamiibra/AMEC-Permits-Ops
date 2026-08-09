# Week 7 Implementation Plan

1. Preserve the Week 6 gate and canonical fixture.
2. Add typed source taxonomy, versioned FindingCode, durable AuthorityEvent, Finding, WorkflowTask, routing rules, provisional SLA policy, NotificationEvent, and the minimum SubmissionCycle seam.
3. Implement one transactional routing service: AuthorityEvent → Finding → WorkflowTask → NotificationEvent.
4. Add precheck conversion, manual official-comment capture, configured portal-validation conversion, conservative deduplication, open-blocking gates, retryable notification delivery, and the deterministic shadow report.
5. Extend the focused console with Findings List/Detail, My Tasks, Notification Outbox, English/Arabic labels, RTL layout, mixed-direction IDs, and raw source preservation.
6. Run SQLite, native PostgreSQL 16, frontend tests/build, clean migration/seed, and the canonical Week 7 scenarios.

Explicitly deferred: authority polling, full closure/reopen/resubmission, recurrence analytics, production Microsoft adapters, and machine submission.
