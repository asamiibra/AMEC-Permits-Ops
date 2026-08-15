# Dashboard and resolvers

Deployed API probes returned `RESOLVED` for `BD/PROPOSAL_TEMPLATE`, `BD/PROPOSAL_CHECKLIST`, and `ADMIN/CONTRACT_TEMPLATE`. The deployed browser showed current forms, current templates, version history, Administration, and the Proposal workspace with pinned Proposal Template and Checklist.

The deployed synthetic fixture contains 10 Current items and 0 Needs Review / 0 Inactive items. The filter controls are present, but the absence of those fixture rows is recorded as a bounded data limitation rather than a fabricated deployed result. Local regression covers Needs Review exclusion and historical-version behavior.
