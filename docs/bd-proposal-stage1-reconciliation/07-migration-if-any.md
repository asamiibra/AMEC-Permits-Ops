# Migration decision

No schema migration is required for the owner-UX reconciliation. The current schema already represents four source families, DocumentVersion/evidence lineage, Proposal companions, accepted revisions, client/property context, regulatory scoping intent, and compatibility Opportunity/Quotation foreign keys. Notes and explicit Proceed require additive implementation only if existing JSON/work projection cannot safely represent them; no frozen migration is rewritten and no legacy row is reinterpreted destructively.
