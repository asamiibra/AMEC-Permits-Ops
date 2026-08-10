# SOR contract

The test SOR is `MockSynologyAdapter`. Backend tests cover write, readback, hash verification, current promotion, historical retrieval, idempotency, missing destination/write failure, and truthful failure states. In deployed synthetic TEST, verified bytes are also persisted in PostgreSQL so a later serverless invocation can retrieve the same source; this is not a claim of real Synology parity.

The deployed health contract is `SYNTHETIC_TEST` with `SYNTHETIC_DURABLE_DB_BACKED`, PostgreSQL durable, and `real_synology: NOT_CONFIGURED`. Real AMEC Synology is the only external exception.

Results: `TEST_SOR_FULL_CONTRACT_E2E_PASS`, `UNVERIFIED_CURRENT_PROMOTION_ZERO`, `FAKE_UPLOAD_SUCCESS_ZERO`, `REAL_SYNOLOGY_VERIFICATION_BLOCKED_EXTERNAL`.
