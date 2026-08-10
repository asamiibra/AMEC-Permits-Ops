# Canonical work projection

`backend/app/services/work_projection.py` is the single server-side projection used by `GET /api/work` and `GET /api/work/summary`. It reads existing `WorkflowTask`, proposal, contract, permit, Finding, CommunicationDraft, AssistantHandoff, and NotificationEvent records. It does not create a second task table or mutate domain state.

Work sources are normalized into `ACTION`, `REVIEW`, `HANDOFF`, `BLOCKER_ACTION`, and `COMMUNICATION` items. Passive notification events become `recent_changes`; they do not become work items unless an existing actionable primitive exists.

Ranking is deterministic: blocking first, overdue next, earliest due time, configured priority, oldest created time, then stable item ID. The response carries exact business deep links and the visible list is filtered by role, team, domain, and KPI on the server.
