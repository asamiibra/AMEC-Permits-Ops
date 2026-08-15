# Client / Activity / Location search

Search is backend-derived through `GET /api/bd/proposals`; it is not a current-page filter. `q` searches Proposal title/reference, Project Ref, Client, activity/project description, Client Requested Scope, AMEC Scope, location/site context, and stage. The explicit filters are `client`, `activity`, and `location`; `stage` and `lane` remain separate controls.

Location uses the current `ProposalSiteContext.location_text` / site description and legacy Proposal location context where present. Activity means Proposal/project description and scope context, not raw AuditEvent text. Search rows remain role/project isolated by the canonical list route.
