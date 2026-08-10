# Read-state contract

Read state is stored in `notification_read_states`, keyed by notification event, persona, and principal. Opening an event acknowledges it before navigation; Mark read acknowledges without navigation. The operation is idempotent and has no workflow-task, issue, stage, or external-portal side effect.
