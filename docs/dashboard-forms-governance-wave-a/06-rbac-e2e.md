# RBAC and audit E2E

Owner/System Admin governance capabilities were added for governance writes, ingest-version actions, currentness verification, quality management, source-section management, readiness evaluation, accepted-risk handling, and restricted-sample access. BD and Engineering remain read/use roles for this surface.

The Wave A contract suite verifies BD governance-write denial. Governance mutations emit audit records, and currentness changes use the existing material-change propagation seam with idempotent retry behavior.
