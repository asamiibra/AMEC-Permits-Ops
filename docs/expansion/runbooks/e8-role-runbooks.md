# E8 role runbooks

These are synthetic operating instructions for the shared queue.

- **BD / commercial:** inspect RFQ and quotation evidence, verify fields, draft the commercial review handoff, and keep release human-approved.
- **Contract / admin:** inspect checklist and missing-document evidence, prepare contract/form drafts, and leave communication in `HUMAN_SEND`.
- **Project bootstrap:** confirm canonical project/reference identity and Synology/Excel representations; never fuzzy-link or overwrite human-owned cells.
- **Engineering:** confirm drawing revision and regulation applicability, review advisory comments, and require Authorized Engineer disposition before closure.
- **Permit:** coordinate the handoff and read-only authority status; resolve blockers and preserve submission confirmation evidence.
- **Finance / invoice:** track milestone and invoice evidence, use generic finance handoff, and make no accounting or payment write.
- **Handover:** inspect readiness evidence and source revisions, then route to human approval; do not auto-release or close the project.
- **Communication:** review source family, recipient context, and draft hash; use human send only.
- **Incident / safety:** stop, preserve correlation and revision IDs, escalate to the owner, and re-run safety/regression checks before reopening.

All roles use the same `WorkflowTask` queue and deterministic NextAction. No role runbook grants production authority.
