# E7 unified work queue

`GET /api/my-work` returns summary cards, workflow tasks, communication drafts, issues, and handoffs. Existing `WorkflowTask` is the canonical queue; no assistant-specific task store is introduced.
# E7 unified work queue

`WorkflowTask` is the single queue. Each card exposes assistant owner, owner role, shared context, blocking state, evidence revision IDs, deterministic next action, and a deep link. Summary cards cover Action Required, Reviews Waiting, Blocked Work, Authority Changes, Communication Drafts, and Delivery Failures.

The queue is read-only at the system boundary; proposals remain drafts and communication remains `HUMAN_SEND`.
