# API route inventory

Existing route families were preserved for Proposal list/detail, source intake, contact/site context, structured scope, regulatory intent, assumptions, expected inputs, engineering contributions, validation, Accept, outputs, and Contract handoff.

Final hardening adds typed routes for `unknowns`, `conflicts`, `acknowledgments`, `staleness/review`, `revisions`, `client-responses`, and `commercial-outcome`. PATCH accepts `expected_updated_at`; Accept locks the Opportunity row and rejects an unchanged duplicate.

All write routes require explicit capabilities. Read projections expose provenance, history, boundaries, and synthetic-only status.
