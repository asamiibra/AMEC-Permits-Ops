# G10 observability review

Status: `BLOCKED_EXTERNAL`.

Synthetic request logging and workflow evidence carry request/correlation IDs and workflow/entity context. Production dashboards and retention are not supplied for task state, API errors, jobs, document processing, rendering, communication drafts, Synology/Excel, portal reads/writes, monitoring, Finding/task creation, assistant invocation, engineering, finance, or handover.

Production validation must preserve request_id, correlation_id, project/opportunity ID, user/role, workflow/task ID, revision/version IDs, and external interaction ID where applicable, without secret values.
