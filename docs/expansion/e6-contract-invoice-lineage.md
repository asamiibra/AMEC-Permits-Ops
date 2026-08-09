# E6 contract/invoice lineage

Every invoice revision pins Contract, ContractRevision, optional ContractMilestone, requirement decision, client/reference context, and shared `LineageEdge`. A material contract revision causes the old invoice revision to become stale/revalidation-required; historical outputs remain preserved.
