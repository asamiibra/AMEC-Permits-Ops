# Owner Administration information architecture

The `/admin` landing page is a business-facing configuration index. It groups configuration by owner intent rather than by implementation milestone:

1. People & Access
2. Data & Connections
3. Project & Folder Setup
4. Proposal Setup
5. Contract Setup
6. Permit Workflow Setup
7. Templates & Documents
8. Notifications & Follow-up
9. Data, Security & Retention
10. Integration Health
11. Audit History
12. Advanced Diagnostics (secondary)

Inputs & Go-Live is a separate action and route. It contains AMEC decisions and readiness inputs that should not be confused with runtime Administration.

The frontend cards are backed by `/api/admin/summary`; detail screens use the corresponding owner projection endpoint. Loading, unavailable, and retry states are explicit. No empty response is translated into a fake Connected, Configured, or zero state.
