# Final regression

Focused backend coverage is in `backend/tests/test_proposals_main.py`. It verifies derived KPI invariants, successful manual SOR registration, read-back verification, idempotent retry, mismatch blocking, SOR-unavailable failure, and persona action boundaries.

Frontend production build, focused browser coverage, the full backend suite, and the existing frontend unit suite are run as part of the final handoff. The focused owner page browser suite passes 3/3. Some older permit-centric browser specs still assert labels retired by the active AMEC/ProposalOps rebrand; this is recorded explicitly in `artifacts/proposals-main/final-result.json` rather than treated as owner-page evidence.
