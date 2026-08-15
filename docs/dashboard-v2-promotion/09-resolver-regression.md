# Resolver Regression

- `needs_review=true`: visible and openable, exact versions remain downloadable, normal current-master resolvers exclude it.
- `status=ARCHIVED`: historical access remains, normal current-master resolvers exclude it.
- `status=ACTIVE` plus `needs_review=false`: remains subject to the existing binding, current-version, and readiness rules.
- Proposal Template, Proposal Checklist, and Contract Template each resolve exactly one canonical record in the regression suite.

The fresh PostgreSQL promotion-focused suite passed 39 tests; the full backend suite passed 236 tests with 6 expected skips.
