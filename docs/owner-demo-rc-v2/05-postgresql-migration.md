# PostgreSQL Migration and Seed

Disposable database `permitops_owner_demo_rc_v2` was created locally, upgraded from an empty schema with Alembic, and seeded successfully. Current Alembic output is `0025_permit_workflow_stage_confirmation (head)`.

The local TEST PostgreSQL seed reset uses guarded `TRUNCATE ... RESTART IDENTITY CASCADE` behavior only when `APP_ENV=TEST`, `SYNTHETIC_ONLY=true`, PostgreSQL is local, and Vercel is not present. This prevents fixture reset foreign-key failures while avoiding deploy-time truncation.
