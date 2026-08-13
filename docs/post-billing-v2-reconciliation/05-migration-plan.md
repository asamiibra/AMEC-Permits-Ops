# Migration plan

Migration `0049_billing_v2_communication_due_events.py` is forward-only relative to committed 0048 history. It adds typed Contract agreement classification, immutable project-context snapshots, due-date rule/event fields, delivery events, and acknowledgment events. Existing 0048 was not edited in place.

Validated:

- fresh PostgreSQL base → 0049;
- PostgreSQL 0049 → 0048 → 0049 round-trip;
- fresh SQLite base → 0049;
- SQLite 0049 → 0048 → 0049 round-trip;
- final Alembic head: `0049_billing_v2_communication_due_events`.

The 0049 downgrade is intentionally additive-policy safe: the migration version can be downgraded and re-upgraded without destructive data rewriting, consistent with the repository’s finance migration policy.
