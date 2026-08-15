# Regression matrix

Local SQLite backend: 205 passed, 8 skipped, 2 warnings. Focused Proposal regression tests passed after expansion. PostgreSQL synthetic backend: 213 passed, 2 warnings. Frontend unit tests: 36 passed. Production TypeScript/Vite build: passed with the existing chunk-size warning.

The targeted real-stack browser suite passed 3 tests. It covers register reconciliation, all four source-card panels, existing detail render/reload, controlled not-found, and Forms-v2. No database migration was added; the database head remains `0055_bd_proposal_final_hardening`.
