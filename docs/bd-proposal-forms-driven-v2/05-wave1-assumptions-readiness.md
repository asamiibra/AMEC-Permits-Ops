# Wave 1 — assumptions, unknowns, conflicts, and readiness

Status: `PROTECTED_AND_REGRESSION_VERIFIED`

- `ProposalAssumption` distinguishes open/acknowledged state and materiality. Material open assumptions block Accept; acknowledgement is recorded by actor and time.
- Source conflicts are retained as `ProposalSourceEvidence.status=CONFLICT` and are exposed through `forms_v2`; readiness emits `MATERIAL_CONFLICT_REQUIRES_DECISION`.
- Unknown Property and unknown regulatory scope are warnings under the safe commercial policy. They do not become Permit-ready or submission-ready claims.
- Existing Proposal validation remains authoritative for legacy required fields, template, checklist, and source requirements. v2 readiness is additive and derived; there is no arbitrary ready setter.
- Commercial readiness is explicitly separate from regulatory readiness through `commercial_ready_not_regulatory_ready` and safe-default messaging.

The unresolved-site test proves a commercial-only draft can retain location/plot/area without a canonical Property and cannot cross the Contract handoff boundary before an accepted revision. The accepted-snapshot test proves material assumption acknowledgement is reconstructable.
