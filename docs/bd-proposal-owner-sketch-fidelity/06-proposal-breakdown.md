# Proposal Breakdown

`proposal_breakdown` is a read projection over existing `ProposalServiceScopeItem`, `ProposalEngineeringContribution`, `ProposalExternalCostAssumption`, and current technical-deliverable fields. It includes lineage for each item and a commercial summary for price, currency, duration, payment terms, inclusions, and exclusions.

Accepted snapshots now carry this projection alongside the existing fields, AMEC Input, Additional Information, source IDs, forms-driven data, and exact Dashboard configuration. No `ProposalBreakdownMaster` or duplicate scope store was added.
