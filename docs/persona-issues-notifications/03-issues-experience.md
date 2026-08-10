# Issues experience

`/issues` presents persona-specific titles, descriptions, filters, and KPI cards. Cards and rows use the same backend projection, so the visible issue count reconciles with the open KPI count. Each row exposes domain, severity, blocking, status, owner, evidence, SLA state, and a canonical Proposal, Proposal Preparation, Contract, Permit, or project-history deep link.

Errors are rendered as a retryable “Persona data unavailable” state. An incomplete API payload is treated as an error and cannot silently become an empty list.
