# Work, Issue, and Notification Correlation

Finding-backed WorkflowTasks use `FINDING:{finding_id}` as the canonical action key and link to `/issues/{finding_id}`. Projection dedupe keeps one human action. Notifications remain separate domain events; acknowledgement preserves task and Issue state.
