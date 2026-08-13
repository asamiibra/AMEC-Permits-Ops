# Wave 1 — commercial, semantic, and Property foundation

Status: `IMPLEMENTED_AND_VERIFIED`

- `ClientAccount.canonical_party_id` is an additive nullable FK to canonical `Party`; existing client IDs and names remain intact.
- `ProposalContactContext` preserves Proposal-purpose contact semantics and does not imply Owner, Applicant, legal signatory, or case role.
- `ProposalSiteContext` supports `LINKED` canonical `Property` or explicit `UNRESOLVED` free-text context. No Property is fabricated from location/plot/area text.
- Area is typed as value/unit/kind; legacy or unspecified meaning is represented as `LEGACY_UNSPECIFIED`. Duration remains a commercial estimate.
- `ProposalStakeholderIntent` stores known/candidate/unknown stakeholder intent with optional canonical Party reference; it does not create AuthorityCase roles.
- Uploaded Proposal sources create exact `Document`/`DocumentVersion` lineage plus `ProposalSourceLink`; source hash conflicts remain visible and block readiness.

Executable proof: `backend/tests/test_bd_proposal_forms_driven_v2.py` covers canonical Party linking, unresolved Property context, exact source-version linkage, no fabricated Property, and readiness behavior. The real-stack browser proof covers the owner workspace sections for Client/Contacts and Site/Property.

Safe boundary: Proposal reads shared semantic and Property domains; it does not create a second fact, Party, or Property authority.
