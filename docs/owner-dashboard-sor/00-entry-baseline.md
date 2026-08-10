# ProposalOps owner dashboard / SOR change — entry baseline

Date: 2026-08-10

## Repository

- Branch: `main`
- Commit: `e7597d81228b009af7188a7a7980357b5dd9ce8b`
- Working tree: clean at entry (the evidence directory was created for this change)
- Backend: FastAPI, SQLAlchemy, Alembic, SQLite fallback / PostgreSQL target
- Frontend: React + Vite + TypeScript
- Migration script head: `0026_notification_read_states`
- Checked local database stamp: `0021_e7_unified_task_context` (local fixture is behind the script head)

## Existing primitives found

- `Document` / `DocumentVersion` already provide immutable document version records, hashes, source references, and a current-version pointer.
- `EvidenceArtifact`, `LineageEdge`, `MaterialChangeEvent`, `DocumentValidity`, and `AuditEvent` already exist.
- `ProjectArtifactRecord` and `proposals_sor.py` already implement a verified synthetic project SOR write path.
- `MockSynologyAdapter` is a filesystem-backed synthetic adapter; no real Synology transport or credentials are present in this repository.
- Roles are represented by the existing `Role` enum and the development `X-Dev-Role` header. Existing owner-facing personas are Owner, Business Development, and Engineering.
- The current navigation keeps AMEC Work, Proposals & Contracts, Issues, Notifications, and Administration separate.

## Protected baseline evidence

- Backend suite: `119 passed, 2 warnings` (`python3 -m pytest -q backend/tests --disable-warnings --maxfail=1`)
- Frontend build: PASS (`npm run build`)
- Alembic current against the local default database: `0021_e7_unified_task_context`
- Alembic repository head: `0026_notification_read_states`

## Baseline interpretation

The repository is a synthetic/test implementation. It does not contain a production Synology connection, production credentials, or an approved production master-library folder hierarchy. The implementation therefore must use an explicit, configuration-driven synthetic master SOR mapping and must not claim deployed or real-Synology verification.
