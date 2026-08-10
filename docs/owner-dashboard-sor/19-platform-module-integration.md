# Existing platform module integration

The implementation reuses the existing platform seams rather than creating replacement stores:

| Seam | Existing canonical record | Master-content projection |
|---|---|---|
| Issues | `Finding` | project-scoped revalidation Issue |
| AMEC Work | `WorkflowTask` | open revalidation task |
| Notifications | `NotificationEvent` | persona-targeted in-app event |
| Audit | `AuditEvent` | promotion, SOR verification, archive, revalidation |
| Lineage | `LineageEdge` | exact source-version edge |
| Material changes | `MaterialChangeEvent` family | `MasterContentChangeEvent` with materiality |
| Definitions | `DefinitionEntry` / `DefinitionRevision` | current structured lookup and revision event |

The registry and delivery ledger are the only new coordination tables. They prevent duplicate issue, task, notification, and lineage projections while keeping the current Dashboard and AMEC Work surfaces intact.
