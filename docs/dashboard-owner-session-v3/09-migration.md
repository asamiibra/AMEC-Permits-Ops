# Migration and backfill

Migration `0033_dashboard_owner_session_v3` adds nullable indexed `master_content_items.source_type_code`. The migration is additive and introspection-safe. Existing rows remain valid without a source type, and the Owner demo reconciliation assigns explicit source types to seeded Engineering examples without rewriting their Category.

Fresh PostgreSQL verification upgraded from `0032_bd_proposal_owner_session` to `0033_dashboard_owner_session_v3` successfully.

`DASHBOARD_V3_MIGRATION_PASS`
