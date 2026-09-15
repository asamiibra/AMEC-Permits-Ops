# Regression

Evidence: compile and `git diff --check` pass; backend focused Proposal/auth/storage/migration suite passes; frontend build passes; frontend unit suite passes 114/114; available backend regression passes 909 with 33 existing skips and one explicitly excluded heavyweight source-preflight CLI case. SQL portability suite passes 31/31, but native runtime SQL/Entra/DSM/browser-real-stack acceptance is not claimed. Static scan confirms the Proposal workspace has no synthetic governance payload constants and `frontend/src/api.ts` blocks synthetic production payloads.
