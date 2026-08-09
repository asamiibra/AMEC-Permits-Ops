# Production release plan

Status: `NOT_AUTHORIZED / NOT_RELEASED`.

No approved build artifact, production configuration release, template freeze, or G10 decision exists. The candidate build hash is recorded in the scope manifest as an unapproved candidate only. A future controlled release must record approval, migration head, configuration and feature flags, assistant capability flags, ASSISTED mode, deployment order, smoke tests, and deployment evidence before enabling any live capability.

Rollback must be a documented forward-fix or an explicitly tested reversible change. Do not promise destructive database rollback when forward-fix is the safe mechanism. Named owner and war-room contacts remain external dependencies.
