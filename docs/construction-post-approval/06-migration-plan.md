# Migration Plan

Migration `0050_construction_post_approval_controls` creates the additive construction tables after billing head `0049`. It is PostgreSQL-verified and SQLite-compatible. The downgrade is intentionally non-destructive because these tables are evidence boundaries.

The application imports the model module through `backend/app/models/__init__.py`; existing developer SQLite bootstrapping remains available, while deployment uses Alembic.
