# Production rollback / forward-fix plan

Status: `NOT_AUTHORIZED / NOT_TESTED_IN_PRODUCTION`.

The safe response to a live defect is pause/safety hold, preserve request/correlation/workflow/revision evidence, disable the affected capability, and use a controlled versioned forward fix. Database rollback is not promised. Any rollback or forward fix requires a change ID, impact/risk, test evidence, approval, deployment evidence, and recovery verification. Unknown portal drift fails closed to assisted/manual handling; it is never resolved by an unbounded browser agent.
