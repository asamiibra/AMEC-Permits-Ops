# Regression evidence

Backend: `161 passed, 1 skipped, 2 warnings` via `pytest -q backend/tests`. Focused cross-workstream and prior critical suites pass. Fresh SQLite migration from base reaches `0047_prebilling_regulatory_context`. Frontend: `npm run build` passes (`tsc -b` and Vite). Browser: local real stack verified New Permit, Permit Portfolio, Engineering Drawing Review, Administration Contract Setup, and Contract Inputs/Go-Live; no browser failure was observed. PostgreSQL and real Synology provenance are not available in this environment and remain external deployment/go-live checks.
