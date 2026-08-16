# Dashboard Reverification Plan

On the candidate integration tree, re-prove the closure invariants rather than reusing branch claims:

- `/dashboard` is the single live Dashboard root and carries the V2 root marker, governance overview, four library navigation cards, status filters, review note, and history affordances;
- `/dashboard-v2` and its Inputs deep link redirect to canonical routes without a V1 runtime branch;
- Dashboard and Administration read the same canonical MasterContentItem / DocumentVersion status, review note, and current version;
- `needs_review=true` is excluded from every normal current-master resolver, while `needs_review=false` plus active remains eligible under module/purpose bindings;
- historical exact DocumentVersion lookup remains available after later master status changes;
- Proposal Template, Proposal Checklist, and Contract Template resolver behavior remains unchanged;
- navigation-only Dashboard changes do not duplicate, migrate, or delete canonical data.

The existing deployment evidence is treated as prior evidence only; candidate and final-main runs must produce new machine-readable results.
