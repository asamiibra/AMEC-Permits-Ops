# G1 — Domain, terminology, and route contract

Quotation remains the stable internal Proposal implementation identifier; it is not a second business truth. Opportunity carries the owner-facing Proposal context. Contract retains its internal relation to Quotation and now also carries explicit `project_id`. PermitApplication carries `controlling_contract_id`.

Canonical commercial routes are `/`, `/proposals-contracts`, `/proposals/new`, `/proposals/:proposalId/preparation`, and `/contracts/:contractId`. The legacy collection `/permits` redirects to `/proposals-contracts`; true downstream Permit detail routes are not globally redirected.

Classification is recorded in `artifacts/master-realignment/terminology-audit.json`.
