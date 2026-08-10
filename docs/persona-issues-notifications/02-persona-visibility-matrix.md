# Persona visibility matrix

| Domain | Owner | Business Development | Engineering |
|---|---|---|---|
| PROPOSAL_COMMERCIAL | ACTIONABLE | ACTIONABLE | HIDDEN |
| PROPOSAL_TECHNICAL | ACTIONABLE | CONTEXT_ONLY when blocking | ACTIONABLE |
| CONTRACT | ACTIONABLE | ACTIONABLE | HIDDEN |
| PERMIT_ADMINISTRATIVE | ACTIONABLE | HIDDEN | CONTEXT_ONLY when blocking |
| PERMIT_TECHNICAL | ACTIONABLE | CONTEXT_ONLY when blocking | ACTIONABLE |
| AUTHORITY | ACTIONABLE | CONTEXT_ONLY when blocking | ACTIONABLE |
| SYSTEM_INTEGRITY | ACTIONABLE | HIDDEN | CONTEXT_ONLY when blocking |
| COMMUNICATION_DELIVERY | ACTIONABLE | ACTIONABLE | HIDDEN |

Owner is the union view. Engineering and Business Development receive only backend-derived rows whose actionability is actionable or contextual. Hidden rows are excluded from list and KPI counts.
