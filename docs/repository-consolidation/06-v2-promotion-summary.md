# Dashboard V2 Promotion Summary

The owner decision is implemented in `cc604f8` and validated by the existing promotion evidence. `/dashboard` renders the governance-capable current Dashboard; `/dashboard-v2` and its Inputs & Go-Live deep link rewrite to the canonical routes while preserving query strings and hashes. There is no public `/dashboard-v1` route and no separate V1 data model.

The retained canonical universe is `MasterContentItem`, `Document`, `DocumentVersion`, definitions, purpose/module bindings, audit, RBAC, storage, and Source Intake. Current, Needs Review, and Inactive remain status projections over those records; reviewed/inactive records are excluded from normal consumer resolvers. Forms, Reports, Engineering Works, Definitions, Inputs & Go-Live, Administration parity, and Source Intake visibility are covered by the existing focused and full regression artifacts.

Truthful deployment caveat: the current Vercel certification is synthetic-document mode; real document storage and Synology verification remain uncertified/external.
