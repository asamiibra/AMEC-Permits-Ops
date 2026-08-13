# 14 · Human submit authorization

Status: IMPLEMENTED

Submit authorization requires a current PASS precheck and matching package checksum. It creates a SubmissionAttempt in `PENDING_EXTERNAL_CONFIRMATION` and records that no machine submit operation occurred. Authorization is idempotent by key.
