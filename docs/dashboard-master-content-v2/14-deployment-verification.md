# Deployment Verification

The current release was deployed through Vercel to `amec-permits-ops.vercel.app` and `amec-permits-ops-backend.vercel.app`. Frontend HTTP returned 200. Backend health returned PostgreSQL durable connectivity and Alembic `0029_dashboard_master_content_v2`. The deployed synthetic SOR is explicitly ephemeral; real AMEC Synology remains external. See `deployed-result.json`.
