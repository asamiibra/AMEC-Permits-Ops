# RBAC and security

Status: `PROTECTED_AND_REGRESSION_VERIFIED`

- Proposal read/write capabilities remain enforced on every new endpoint.
- Accept and material assumption acknowledgement use the existing consequential-operation boundary; Owner-only runtime policy remains respected.
- Regulatory confirmation is denied to Engineering; Engineering may add technical contributions through `EDIT_TECHNICAL` only.
- Engineering cannot edit commercial Proposal price through the existing patch endpoint.
- Canonical Party/Property/catalog IDs are validated before linking; exact DocumentVersion is required for source-link endpoints.
- No new visible user roles were introduced and no role is inferred from a client/contact/stakeholder name.

Negative API assertions are included in the v2 backend test; the existing backend and real-stack auth/RBAC regressions also pass.
