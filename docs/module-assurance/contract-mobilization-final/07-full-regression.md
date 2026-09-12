# Full regression

Candidate validation on the uncommitted repair tree completed as follows:

- Backend regression: `877 passed, 17 skipped, 4 warnings` with the repository's clean isolated SQLite test database; the native SQL Server test module was intentionally excluded by the repository's local command.
- Focused Contract/Business/Handover suites: `20 passed, 1 warning`.
- Frontend unit: `113 passed` across 21 files.
- Frontend production build: passed.
- Migration source head: `source18_committee_implementation_v1`; no migration or schema files changed. A fresh SQLite Alembic upgrade remains unsupported by the pre-existing baseline constraint operation, and a fresh PostgreSQL upgrade from zero remains blocked by the pre-existing untyped parameter in the baseline migration; neither path is introduced by this repair.
- Portability and policy checks are included in the clean backend result; storage-contract and native SQL Server lanes require their separately provisioned services.

Required GitHub checks are `backend-regression`, `frontend-regression`, `migration-head`, `policy-and-security`, and `samba-contract`. These are still required on the committed candidate through the governed PR.

This package does not treat a green test as a production deployment or protected-human acceptance. Azure G8 remains a separate infrastructure lane and is not executed by this repair.
