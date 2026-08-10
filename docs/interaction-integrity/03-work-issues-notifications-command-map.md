# Work, Issues and Notifications command map

`AMEC Work` is the task/action projection, `Issues` is the finding projection, and `Notifications` is the delivery/event projection. They are intentionally separate queues.

| Surface | Classification | Evidence | Open gap |
|---|---|---|---|
| AMEC Work cards | `NAVIGATION` | Work items deep-link to permit stages | Full persona click-through is not rerun in this task. |
| Workflow task transitions | `DOMAIN_COMMAND` | `/api/tasks/{id}/acknowledge`, `/start`, `/complete` | Whole-app browser mapping still needs a complete matrix. |
| Issue status/note/dispute/closure | `DOMAIN_COMMAND` | Finding command endpoints | Existing tests cover bounded commands; no new no-op scan proof yet. |
| Notification list and observability | `BACKEND_READ` | `/api/notifications`, `/api/notifications/observability` | Swallowed fetch errors in the legacy surface need typed error/empty-state review. |
| Persona selector | `LOCAL_UI` + `QUERY_FILTER` | Session state and persona query | Existing persona browser tests pass. |

No notification is a substitute for a task, and no task completion is inferred from notification display.
