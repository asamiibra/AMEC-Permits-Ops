# Finding Routing Contract

Routing is controlled by `FindingRoutingRule`, matched conservatively by code, source type, severity, and discipline. The seeded synthetic examples route missing attachments to `PERMIT_PREPARER`, owner authorization to `REQUIREMENT_STEWARD`, and technical precheck/drawing findings to `RESPONSIBLE_ENGINEER`.

If no rule matches, the finding/task is explicitly `UNASSIGNED` and escalates to `PROCESS_CHAMPION`. It is never dropped or silently routed to `SYSTEM_ADMIN`.
