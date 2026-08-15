# Target owner model

The primary BD model is one Proposal identity: source evidence → Proposal Intake → Proceed → Engineering Proposal Preparation → Engineering return → BD Commercial Review → AMEC Human Accept/release → Client Response → Contract Handoff. `Opportunity` remains a storage-compatible aggregate/context reference; it is not the primary owner-facing identity. `Quotation` remains historical/compatibility lineage.

Stage 1 is Proposal Intake. It presents Tender & Client Sources, Client & Contact, Client Request, Site / Property, Notes & Client Conversations, Missing / Conflicting Information, Intake Readiness, and Proceed to Engineering Preparation. It does not author final technical Process of Work, accept commercial terms, create Contract, activate Project, or create an AuthorityCase.
