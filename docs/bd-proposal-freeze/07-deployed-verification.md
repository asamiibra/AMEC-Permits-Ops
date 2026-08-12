# Deployed verification

Frontend deployment: `dpl_14eoM3BnVPEDxYkuvqDhuxN7LQou`, alias https://amec-permits-ops.vercel.app. Backend deployment: `dpl_6NTaQXGMBkX5YmPgK3o4HUM47Q81`, alias https://amec-permits-ops-backend.vercel.app. Production health reported PostgreSQL, durable database, no SQLite fallback, migration `0032_bd_proposal_owner_session`, and `real_synology: NOT_CONFIGURED`. Deployed API E2E had 12 passing checks including explicit handoff lineage fields; cleanup returned 200 and post-cleanup search count was 0.

`DEPLOYED_BD_PROPOSAL_PASS` · `LOCAL_DEPLOYED_BD_PROPOSAL_PARITY_PASS`
