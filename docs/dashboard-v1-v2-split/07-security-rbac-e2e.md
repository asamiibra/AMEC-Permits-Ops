# Security and RBAC E2E

V2 route access is Owner-only in the existing frontend policy (`SYSTEM_ADMIN` and `OWNER_SPONSOR`). BD and Engineering retain the existing V1 destination. Direct non-owner navigation is redirected to V1, and the V2 home card is hidden.

The shared backend role dependency and Wave A governance authorization remain unchanged. Existing backend certification covers denial of BD governance writes, restricted-reference resolver/download gating, external-official readiness/currentness behavior, immutable history, and source-section lineage. V1 does not introduce a second security service or bypass binary/body protections.

Real-stack direct-route coverage passed for `COMMERCIAL_APPROVER`; the backend suite passed all corresponding negative-control tests.
