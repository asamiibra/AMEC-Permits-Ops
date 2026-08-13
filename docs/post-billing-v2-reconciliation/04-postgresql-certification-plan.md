# PostgreSQL certification plan

Authoritative command:

`PYTHONPATH=. APP_ENV=TEST SYNTHETIC_ONLY=true DATABASE_URL=postgresql+psycopg://ahmedsami@localhost:5432/permitops_v2_full8 python3 -m pytest -q backend/tests`

The database was created fresh, upgraded from base to 0049, and used for the entire applicable backend suite. The final run was `165 passed, 0 failed, 0 errors, 2 warnings` in 34.59 seconds. Warnings are existing Python deprecation/nullable-identity warnings, not skipped or failed tests.

Targeted Billing tests were run separately on PostgreSQL during the full suite and on SQLite; the Billing test module contains the delivery, acknowledgment, event-due-date, payment, idempotency, and ExternalAgreement negative paths.
