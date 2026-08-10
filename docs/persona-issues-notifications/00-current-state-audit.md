# Current-state audit

ProposalOps now has one shared Week 7 substrate: `Finding` is the canonical issue record, `WorkflowTask` is the AMEC Work queue record, and `NotificationEvent` is the event/delivery record. The former Issues page rendered permit findings directly and the former Notifications page rendered delivery observability as its primary KPI surface.

The realignment adds nullable proposal, contract, permit, domain, persona, deep-link, audience, and acknowledgement metadata to those existing tables. It does not create persona-specific issue or notification tables. The new `/api/issues`, `/api/issues/summary`, `/api/notifications`, and `/api/notifications/summary` projections are backend-derived and keep the legacy ingestion and AMEC Work routes compatible.

Operational UI copy is English/LTR. The Operating Guide remains the bilingual surface. The three user-facing personas are Owner, Business Development, and Engineering; internal roles remain compatibility identifiers only.
