# Accepted Proposal revision v2

Status: `IMPLEMENTED_AND_VERIFIED`

`ProposalAcceptedRevision.snapshot.forms_driven_v2` captures the mutable Proposal’s commercial client/Party link, contact, site/Property state, stakeholder intents, exact source links, structured service scope, regulatory intents and canonical IDs, assumptions, external costs, engineering contributions, Expected Client Inputs preview/policy pins, and safe boundaries. Existing fields, validation, template, checklist, and source IDs remain present for historical compatibility.

Accept remains human-controlled and capability-protected. It creates output artifacts from the immutable revision, marks the Proposal accepted, and never creates a Project code, AuthorityCase, RegulatoryJourney, or construction-start state. Later draft changes do not rewrite the accepted revision.

Proof: focused SQLite/PostgreSQL tests accept a synthetic Proposal, read the persisted snapshot back, assert canonical Party and human-confirmed scope IDs/status, and assert no AuthorityCase was created.
