# Opportunity / Quotation rehome

No destructive migration is justified. `Opportunity` is referenced by Proposal companions, legacy RFQ/tender rows, Contract lineage, fixtures, and foreign keys. New Proposal intake continues using that aggregate behind a Proposal projection. `Quotation` and its revisions/terms/approvals/releases remain readable for legacy records and Contract compatibility. Their owner-facing primary labels are removed from the current Proposal Intake workspace. Exact historical references such as `SYN-OPP-*` and `SYN-QTN-*` remain available in history/advanced lineage.
