# Governance endpoint reconciliation

The old homepage shell called `/api/reconciliation/governance` and could show an internal 500. AMEC Work no longer calls that endpoint. The shell also skips the unrelated `/api/applications` fetch while the homepage is mounted; AMEC Work obtains its list from `/api/work`.

The governance endpoint remains available for its existing downstream regression tests. It is not a dependency of the homepage. The real-stack browser test records the request paths and asserts that `/api/reconciliation/governance` is absent.

Result: `HOMEPAGE_GOVERNANCE_500_CLOSED` for the homepage path. Deployment verification remains outstanding.
