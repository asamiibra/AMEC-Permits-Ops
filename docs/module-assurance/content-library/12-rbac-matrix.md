# RBAC Matrix

| Capability | Owner/System Admin | BD | Engineering | Other consumer roles |
|---|---:|---:|---:|---:|
| Discover applicable content | yes | scoped read | scoped read | scoped read |
| Create/update content | yes | no | no | no |
| Change categories/reference policy | yes | no | no | no |
| Change module bindings | yes | no | no | no |
| Write dependencies | yes via `MASTER_CONTENT_DEPENDENCY_WRITE` | no | no | no |
| Revalidate dependencies | yes via `MASTER_CONTENT_DEPENDENCY_REVALIDATE` | no | no | no |
| Official form release/packet actions | Source18-authorized role only | no | no | no |
| Professional engineering approval | responsible professional role only | no | yes where authorized | no |

Direct API capability tests verify that consumer personas cannot mutate owner-controlled Content Library configuration.
