# PostgreSQL targeted Billing

The Billing module ran as part of the full PostgreSQL suite and passed. Explicit Billing coverage includes plan/revision creation, milestone eligibility, partial payment, invoice revision immutability, issue/accept idempotency, delivery, acknowledgment, event due date, receivable states, payment verification/allocation, financial-account version resolution, and typed external-agreement rejection. SQLite targeted Billing independently passed 3 tests; PostgreSQL full suite passed all 165 tests.
