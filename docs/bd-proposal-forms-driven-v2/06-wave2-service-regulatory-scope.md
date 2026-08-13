# Wave 2 — structured AMEC service scope and regulatory intent

Status: `IMPLEMENTED_AND_VERIFIED`

- `ProposalServiceScopeItem` separates AMEC service offering, discipline, inclusion/exclusion, commercial treatment, narrative description, and optional canonical regulatory references.
- `ProposalRegulatoryScopeIntent` references canonical `ExternalBody`, `ServiceType`, optional `ServiceTypeVersion`, and optional `Jurisdiction`; it stores Proposal intent and human confirmation only.
- Human confirmation is capability-protected and records actor/time. It never creates or mutates `AuthorityCase`, `RegulatoryJourney`, `RequirementInstance`, or canonical catalog definitions.
- External/pass-through costs use `ProposalExternalCostAssumption` and remain separate from the AMEC amount unless an explicit commercial treatment says otherwise.
- Engineering contributions use the existing `EDIT_TECHNICAL` capability and a typed Proposal companion; the endpoint does not edit price or accept the Proposal.
- Legacy authority text remains in the existing Proposal fields and is not auto-converted into a fake ExternalBody.

Executable proof covers canonical catalog references, human confirmation, no AuthorityCase creation, Engineering RBAC boundaries, and accepted snapshot pinning of the intent.
