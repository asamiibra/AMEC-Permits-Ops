# MFA and attended-session model v0

The synthetic municipality configuration uses `USER_PLUS_OTP` with `attended_session_required=true`. PermitOps may prepare or validate a draft in an attended session, but it does not store OTPs, reuse credentials, bypass MFA, or claim authority acceptance.

Phase 0 decisions still required: named user ownership, session timeout, approved test location, raw-data access roles, remote access policy, and evidence retention.
