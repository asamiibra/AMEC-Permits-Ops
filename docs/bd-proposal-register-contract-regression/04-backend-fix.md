# Backend fix

- Added `ProposalRegisterResponse` and `ProposalRegisterRow` public Pydantic models to the Proposal Register route.
- Preserved the single `_register_predicate` source for rows and lane counts.
- Preserved nullable amount, project reference, location, and last-activity values.
- Added explicit `READY_FOR_QUOTATION` support to the Proposal projection, authority states, lifecycle, next-action mapping, and register stage options.
- Kept synthetic-only provenance explicit; no fabricated zero or empty success response was added.
