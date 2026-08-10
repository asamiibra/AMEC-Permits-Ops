# Domain model

```text
Finding (canonical issue) ──optional──> WorkflowTask (AMEC Work action)
        │
        └──optional──> NotificationEvent (awareness / delivery event)

Finding or NotificationEvent ──> Proposal | Contract | Permit | Project
                                  └── backend persona projection
```

Issues own severity, blocking, status, ownership, evidence, SLA state, actionability, and deep link. Notifications own event type, audience, actor, message projection, read/acknowledge state, and delivery status. A notification acknowledgement never changes task status or closes an issue.
