# Wave 3 midpoint report — Weeks 11–12

Label: **DEMONSTRATION BASELINE — SYNTHETIC DATA — NOT CLIENT APPROVED**.

## Monitoring

The deterministic demo proves first-read material comment capture, repeated-read `NO_CHANGE`, status/comment material change, contract drift fail-closed, reviewed contract revalidation, external-mutation evidence, and human monitoring fallback. The demo result is stored in `artifacts/week11-12-demo-result.json`. Production automated monitoring remains `BLOCKED_EXTERNAL / FALLBACK_MANUAL`.

## Variant and edge maturity

`INDIVIDUAL_OWNER` and `COMPANY_OWNER` run inside the same Building Permit / Demo Municipality A envelope. Compatibility is configuration-only with no core fork. Target rendering coverage has 0 missing supported mappings. The representative attachment/grid matrix reports 32/32 synthetic cases passed across the two variants.

## Human boundary

Attended auth transitions through `WAITING_FOR_HUMAN_AUTH`, `WAITING_FOR_MFA`, and `AUTHENTICATED`; MFA challenge metadata excludes challenge content. Handoff acceptance remains distinct from submission, and no machine final-submit operation exists. Optional automation is `NOT_AUTHORIZED_NOT_BLOCKING`.

## Structural zero-tolerance counts

Machine final submissions: 0. Unauthorized production reads: 0. Unauthorized production writes: 0. Trusted parses after detected drift: 0. Duplicate blocking tasks from repeated identical comments: 0. Silent external mutation acceptance: 0. OTP/password secret persistence: 0. Final Submitter machine impersonation: 0. Stale revision handoffs: 0. Silent prior-approval reuse: 0.

## Evidence boundary

SQLite and PostgreSQL regression evidence is synthetic. Native PostgreSQL 16 clean migration and canonical seed pass; Docker Desktop is not required for acceptance. No approved real TEST evidence or live authority evidence is present. Synthetic performance metrics are not contractual thresholds.
