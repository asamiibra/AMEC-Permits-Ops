# Regression Result

- Backend: `206 passed, 8 skipped, 2 warnings`.
- Frontend unit: `36 passed` across 13 files.
- Frontend build: passed (`tsc -b` and Vite build).
- Contract-focused backend coverage: passed, including the new version/field/source/acceptance test.
- Browser real-stack: 2 new Contract delta tests passed; 5 existing Administration owner tests passed.
- Alembic: fresh disposable database reaches `0055_bd_proposal_final_hardening` head.
- Docker/PostgreSQL: blocked by unavailable Docker daemon; no PostgreSQL pass token is claimed.
