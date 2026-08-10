# API error and refetch audit

The shared client in `frontend/src/api.ts` now fails closed for non-JSON success responses, invalid JSON, and non-JSON errors. The Stage 1 command clears prior messages, disables the command while in flight, reports typed API errors, and refetches both project detail and findings after the command.

Verified cases:

- Stage 1 command success returns a structured command result.
- Wrong project reference returns `409 PROJECT_REFERENCE_MISMATCH`.
- Missing capability returns `403 CAPABILITY_DENIED`.
- Repeated command returns `IDEMPOTENT` and does not create a second verify task.
- SQLite migration through `0025_permit_workflow_stage_confirmation` succeeds.
- Real-stack browser requests include the POST command and subsequent detail reads.

Open audit items:

- Legacy screens still contain catch-to-empty handlers.
- The deployed frontend/backend pair has not yet been redeployed with this change, so deployed verification is intentionally not marked complete.
- A full API status/error matrix across every material route is still required.
