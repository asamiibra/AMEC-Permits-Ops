# Authority / Review

Proposal Review / Authority is human commercial Proposal authority, not government authority and not `AuthorityCase`. The detail projection exposes status, required human authority, current reviewer, readiness blockers, last review decision, and Next Action without raw capability IDs.

The source is the existing `PROPOSAL_ACCEPT_AUTHORITY` Owner decision. The existing `/accept` command remains the only human Accept command; no duplicate approval or free-form status patch was added. Engineering direct Accept remains denied by `BD_PROPOSAL_ACCEPT`.
