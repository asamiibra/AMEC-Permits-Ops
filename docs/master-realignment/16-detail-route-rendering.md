# G11 — Dedicated detail-route rendering

Local and deployed focused browser evidence passes for `/proposals/new`, `/proposals/:proposalId`, `/proposals/:proposalId/preparation`, and `/contracts/:contractId`. Direct load, refresh, and controlled not-found behavior are covered by `frontend/browser-e2e/proposals-main.spec.ts`.

The Proposal detail view renders identity, client context, source evidence, Proposal fields, status, handoff, related Contract, issues/history summary, promotion action, Proceed, and Contract transition. Proposal Preparation renders the Engineering-owned Inputs & Sources, SOW, Process of Work, technical fields, readiness, and BD handoff context. Contract detail renders Contract identity, related Proposal, Project, amount, dates, revisions, commercial state, linked Permit count, history, and Permit action.

The true downstream Permit route remains owned by the existing `PermitWorkspacePage` and preserves legitimate Permit terminology. The route inventory records that component boundary explicitly rather than redirecting Permit detail to a Proposal screen.

Result: `material_detail_routes_without_dedicated_rendering=0` in the local route inventory. Deployed ProposalOps detail rendering passes the 7-test focused live browser run; full persona and downstream Permit refresh/back-forward coverage remains part of the open historical/deployed Golden Path gate.
