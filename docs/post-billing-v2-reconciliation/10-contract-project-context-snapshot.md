# Contract project-context snapshot

BillingPlanRevision and InvoiceRevision persist `contract_project_context_snapshot`, sourced from finalized Contract/accepted Proposal lineage. It includes the opportunity/project reference, description, location/property context when present, source marker, and canonical-project-created flag. Issued invoice artifacts use this pinned snapshot. Later Project activation is a separate Owner action and does not rewrite historical invoice content.
