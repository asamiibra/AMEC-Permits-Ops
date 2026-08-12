# Runtime bindings

Decision values are effective only after a successful action has written the runtime state and passed read-back. `runtime_decision_value()` returns the existing fallback while a decision is proposed or reopened; `applied_runtime_decision_value()` returns an effective value only when `apply_state == APPLIED`. Contract authority, manual-new-contract policy, and proposal acceptance/handoff paths use this boundary. The final untouched register had zero runtime mismatches.
