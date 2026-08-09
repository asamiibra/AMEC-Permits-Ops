# WorkflowTask Contract

Every blocking finding creates one durable `WorkflowTask` with project/application/finding identity, task type, owner role/user, priority, timestamps, due date, escalation date, and correlation ID. Task states are `OPEN`, `ACKNOWLEDGED`, `IN_PROGRESS`, `BLOCKED`, `DISPUTED`, `COMPLETED`, and `CANCELLED`.

Completing a task does not close its finding. The Week 7 API exposes acknowledgement, start, block, completion, assignment, dispute, note, and evidence-inspection seams without professional closure.
