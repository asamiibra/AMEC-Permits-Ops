# PostgreSQL full suite

Authoritative database: PostgreSQL, `permitops_v2_full8`, migration `0049_billing_v2_communication_due_events (head)`.

Command: `PYTHONPATH=. APP_ENV=TEST SYNTHETIC_ONLY=true DATABASE_URL=postgresql+psycopg://ahmedsami@localhost:5432/permitops_v2_full8 python3 -m pytest -q backend/tests`

Result: **165 passed, 0 skipped, 0 failed, 0 errors**, 2 warnings, 34.59 seconds. The warnings are existing deprecation/nullable-identity warnings and are not unadjudicated skips. The full run includes upstream modules and the Billing-v2 tests.
