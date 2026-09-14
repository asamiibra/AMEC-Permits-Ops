# Focused tests

Executed with plugin autoload disabled:

- `backend/tests/test_ai_p07_foundation_control_plane.py`: 5 passed.
- `backend/tests/test_intelligence_contracts.py backend/tests/test_document_intelligence_platformization.py backend/tests/test_ai_p05_skill_runtime.py`: 19 passed after the SQLite reservation lease normalization fix.
- `backend/tests/test_smb_integration.py backend/tests/test_synology_adapter_contract.py backend/tests/test_document_storage_service.py` against the disposable Samba lab: 17 passed.
- Frontend: 22 test files and 126 tests passed; production build passed.

Repair classifications recorded during convergence:

- Stale pre-P07 contracts: migration inventory, startup head, rebaseline active-file inventory, and governed context dependency-count expectations updated.
- Genuine P07 defects: SQL Server `mssql_where` parity for the current-family filtered unique index; SQLite same-key reservation lock mapping; definition reference allocation and sequence seeding across `DefinitionEntry` rows.
- Direct regressions after repair: P05 same-key race passed; owner definition revision passed; Azure SQL nullable-unique audit passed; context compiler dependency/idempotency checks passed.
- PostgreSQL migration proof after portability repairs: upgrade reached `p07_intelligence_foundation_closure`; `alembic_version` and 475 public tables were verified directly.
