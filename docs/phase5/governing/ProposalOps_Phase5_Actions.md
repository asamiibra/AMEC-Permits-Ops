# Phase 5 Actions

Default DSM/human actions: none.

`DSM_ACTIONS_REQUIRED=0`, `NAS_TASK_SCHEDULER_RUNS=0`, `SMB_CONNECTIONS=0`, `NEW_AMEC_SOURCE_READS=0`, `SECRET_REQUIRED=false`.

Do not recreate the NAS secret and do not run a Synology watcher. Phase5 uses repository fixtures, sanitized Stage1R-derived fixtures, restricted accepted evidence where policy permits, synthetic app uploads, local backend/frontend, Playwright, and disposable PostgreSQL.

Disposable PostgreSQL proves PostgreSQL behavior only; it is not Azure PostgreSQL proof. Browser uses frontend→local backend→disposable PostgreSQL; it is not Vercel/Azure deployed proof.

Real continuous Synology shadow is not part of Phase5 by default. It needs a separately independently accepted `AMEC_LIVE_SHADOW_ACTIVATION_MANIFEST_v1`.
