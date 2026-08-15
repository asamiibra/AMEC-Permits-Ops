# Scope and invariants

Protected invariants:

- Existing API-backed content, status, version, history, dependency, and propagation behavior remains in `CurrentDashboard`.
- Existing business deep links remain reachable, including `/dashboard`, `/dashboard-v2`, `/work`, `/notifications`, `/issues`, permit routes, authority cases, proposals, contracts, admin, and readiness routes.
- The exact seven-stage business flow is navigation and workspace composition; it is not a new lifecycle state machine.
- Role headers and backend RBAC remain authoritative.
- No production-ready, hosted-runtime, or external portal-write claim is introduced.
