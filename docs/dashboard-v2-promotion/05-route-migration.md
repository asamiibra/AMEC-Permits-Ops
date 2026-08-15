# Route Migration

- `/dashboard` is the only active Owner Dashboard route.
- `/dashboard-v2` is rewritten to `/dashboard`, preserving query string and hash.
- `/dashboard/inputs-go-live` is the only active Inputs & Go-Live route.
- `/dashboard-v2/inputs-go-live` is rewritten to `/dashboard/inputs-go-live`.
- AMEC Work contains exactly one Dashboard destination.
- No `/dashboard-v1` or archive route was created.

Local browser proof is in `dashboard-v1-v2-split.spec.ts`.
