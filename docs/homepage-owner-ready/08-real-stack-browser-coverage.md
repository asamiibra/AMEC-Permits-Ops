# Real-stack browser coverage

Command: `npm run browser-real-stack -- homepage-owner-ready.spec.ts`

Result: 7 passed.

Coverage includes Owner copy and legacy absence, KPI/domain/team filter composition, Business Development and Engineering role switching, mobile horizontal overflow, controlled API failure and recovery without fake zeros, duplicate dashboard absence, and critical/serious Axe accessibility checks. The tests use real Vite and real FastAPI against the local synthetic SQLite database; the API failure test is explicitly isolated to validate error UX. This is local browser-stack evidence, not the required PostgreSQL/Neon or deployed evidence.

The backend projection tests are in `backend/tests/test_work_projection.py` and passed 8 tests. The full backend suite passed 99 tests.
