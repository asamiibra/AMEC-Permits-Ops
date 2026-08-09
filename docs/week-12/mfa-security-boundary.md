# MFA security boundary

`MfaChallengeEvent` stores challenge type, timestamps, completing user, result, and optional external-reference hash only. Challenge content is never persisted. Tests and APIs reject secret-shaped payload keys; audit metadata reports `secret_persisted=false`.
