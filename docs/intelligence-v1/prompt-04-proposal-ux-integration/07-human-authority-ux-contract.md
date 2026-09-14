# Human authority UX contract

Protected actions use a consequence-aware `HUMAN DECISION REQUIRED` dialog before mutation. After a command, the workspace reads back the canonical Proposal projection; optimistic protected state is not used.

| Boundary | UX statement |
| --- | --- |
| Scope understood / confirmed | Separate Engineering interpretation from AMEC Scope confirmation |
| Prepared / accepted | Working revision and accepted revision are separate |
| Accepted / released | Commercial release authorizes an exact accepted revision only |
| Released / sent | Distribution records evidence separately |
| Sent / accepted | Client response and acceptance verification remain separate |
| LPO received / reconciled | Structured comparison records pass or variance; variance routes to revision |
| Handoff eligible / Contract accepted | Preflight does not create or accept a Contract |
| Contract accepted / Project active | Project Activation remains outside Proposal |

Persona controls are role-aware: Engineering receives technical editing/assessment capability, while commercial/owner roles receive commercial and protected business commands. The server remains the final authorization boundary.
