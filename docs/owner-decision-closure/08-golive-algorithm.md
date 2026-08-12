# Go-live algorithm

Go-live is `BLOCKED` when any required decision is unanswered/proposed/reopened, an apply failure exists, a contradiction is unresolved, content/software is not ready, or the technical Synology gate is not verified. `READY_EXCEPT_REAL_SYNOLOGY` is reserved for completed business/content/software gates with synthetic-only storage. `FULL_PRODUCTION_READY` requires real Synology verification. The final state is `BLOCKED`, not production-ready.
