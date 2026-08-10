# G6 — Proposal → Contract

Contract is a human-controlled action from an eligible Proposal. It creates or reuses the internal Quotation/Proposal revision and creates a linked Contract with explicit related Proposal and project context. Contract source intake uses the bounded SOR service. Existing seeded legacy ReferenceNumber project context is promoted into `Contract.project_id` when the transition is exercised.

The API blocks ineligible proposals, missing client context, and cross-project contract links.
