# Migration round-trip

Fresh PostgreSQL and SQLite databases upgraded to 0049. PostgreSQL and SQLite both executed `downgrade 0048` followed by `upgrade head`; both reported `0049_billing_v2_communication_due_events (head)`. Existing 0048 was not rewritten.
