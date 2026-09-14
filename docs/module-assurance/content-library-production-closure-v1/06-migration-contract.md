# Migration contract

- Current-main migration head before closure: `17c6ebd99c4a`.
- Current-main historical migration bytes were preserved; the four baseline hashes are recorded in `00-preflight-identity.md`.
- No migration was required for the closure repairs because Source18 official-form authority is represented by existing canonical Document/DocumentVersion/current-pointer fields and audited transaction metadata.
- Isolated SQLite `alembic upgrade head` was attempted and stopped at the frozen baseline's existing `ALTER TABLE ... ADD CONSTRAINT` limitation. This is recorded as an infrastructure qualification limitation, not treated as implementation evidence.
- No production/preprod database was changed.
