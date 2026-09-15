# ProposalOps — Final Proposal Production-Hardening Closure

Date: 2026-09-15

Status: **NOT READY FOR PRODUCTION RELEASE**

This closure record covers the Proposal / Opportunity / Client Tender production-hardening continuation on the canonical `module/opportunity-proposal-client-tender` branch. The source and focused validation work are complete, but production release is intentionally held because the newest API image fails the governed database-head check and the live owner-test path has unresolved provider-output failures on the currently serving fallback image.

## Branch and provenance

- Canonical working branch: `module/opportunity-proposal-client-tender`.
- `origin/main`: `d92cef6d6fdbb7e4248061ebbcfef30cf2f0011d`; tree `04af916251fb2cf92b8575a9e780d35c3322baf8`.
- Canonical Proposal branch after push: `ca590b0faf3fb78bfdfa3dc5f65b7320e9fcb37f`; tree `877d28b47bf9407cbf917162ada044d568bbfa1b`.
- Merge-base with protected main: `d92cef6d6fdbb7e4248061ebbcfef30cf2f0011d`.
- Ahead/behind relative to main: `0/50` for `origin/main...HEAD` (the Proposal branch is 50 commits ahead and has no commits behind main).
- Ahead/behind relative to the remote Proposal branch after push: `0/0`.
- PR41 accepted SHA `dbd54c8e208e7347c959364b0bffd0f513eb81c7` remains an ancestor.
- PR41 merge SHA `e3af5e8d5c8abc996f1039aaae394bb734cc0193` remains an ancestor.
- Those historical SHAs were preserved as immutable provenance and were not promoted as the current branch head.
- Remote branch inventory confirmed PR #48 remains open on this canonical branch. PR #55 (`branch/proposalops-convergence-v1`) is a newer, separate cross-module convergence effort; repository evidence does not designate it as a replacement for PR #48, so no new hardening branch was created.
- `git merge --no-edit origin/main` was already up to date; no ungoverned branch fork or destructive reset was used.

## Source changes closed on this branch

- Hardened recursive provider schema compilation for Azure Responses structured output: required object properties, `additionalProperties=false`, supported nullable optional semantics, unsupported-constraint removal, and `const` to single-value `enum` conversion.
- Preserved Pydantic validation as the authoritative application-level contract.
- Hardened Responses output extraction to accept reasoning preambles, direct `output_text` items, and the top-level `output_text` envelope while rejecting refusals, incomplete output, malformed messages, and invalid structured output.
- Added safe recursive UI/API error and text normalization so provider error objects cannot become invalid React children or textarea values.
- Preserved all six Proposal Intelligence operations and generated a fresh idempotency key for every interactive run.
- Enforced exact synthetic Owner-test source selection: active `BD-PROP-001`, its current document version, and synthetic-only metadata/source markers. Real or ambiguous canonical content fails closed.
- Added a narrow legacy pre-production metadata repair path for durable synthetic fixtures; official production content is not relabeled or rewritten.
- Added governed synthetic master-content fixtures to the Proposal Intelligence contract tests.

## Validation evidence

- Focused backend closure set: **73 passed, 1 warning**.
- Proposal Intelligence suite: **47 passed, 1 warning**.
- AI D2/D3 platform suite: **10 passed, 1 warning**.
- Frontend: **25 test files passed; 124 tests passed; production build passed**.
- `python3 -m compileall -q backend/app`: passed.
- `git diff --check`: passed.

## Live deployment state

Canonical public web:

- URL: `https://www.amecidsystem.com`.
- Current web release marker: `48559f8db3346c4a1bbcab85010737a59fbb47e4`.
- Current web build ID: `owner-test-48559f8-real-auth`.
- Serving web revision: `proposalops-web-preprod--owner-test-48559f8a`, healthy, 100% traffic.
- Serving web image: `sha256:c10fba6e0cd3116f4a1899c9794e2cb95a6b68c582c33892c145560547d66f1c`.
- The serving web build uses the actual Entra tenant/client configuration; the earlier placeholder-identity build was not retained as the final serving revision.

API:

- Serving revision: `proposalops-api-preprod--owner-test-1e10257`, healthy, running at max scale, 100% traffic.
- Serving image: `sha256:a604808cac7a5522ff1ce860e72eb7640c3ac46a41c70d5c62cbc82315d33731`.
- Latest hardening image: `proposalops-api-preprod--owner-test-e4fe092`, image `sha256:9338778b68cdff3ec5e2c33830b5eae0bf7a1cebe022415a67d3d846e501cd60`.
- The hardening image is held at 0% traffic and `ActivationFailed`. Its startup log reports expected migration head `proposal_hardening_schema_repair_v2` but database head `proposal_billing_contract_convergence_v1`; the application correctly fails closed instead of serving against an unverified schema state.
- The database migration job used for the earlier Proposal hardening state succeeded with migration head `proposal_hardening_schema_repair_v2`. A later separate convergence job advanced the shared environment to `proposal_billing_contract_convergence_v1`; that state must be reconciled through the governed integration/migration process before promoting the new API image.

## Owner-test evidence

- Canonical synthetic proposal: `79c0a371-7299-4dc5-9cea-280c96f6ae78`.
- Owner Sponsor / Entra-authenticated session reached the target synthetic Proposal with seven views and six Proposal Intelligence options.
- Tender-intake analysis completed through the live Azure provider and persisted source-grounded citations.
- LPO variance and handoff-preflight probes completed in the prior healthy owner-test revision.
- Requirement/evidence, section draft, and commercial consistency probes returned provider-invalid output on the serving `1e10257` revision and are not accepted as passing release evidence.
- The `e4fe092` parser fix is covered by the local provider tests but was not runtime-verified because its image cannot start against the current database migration head.
- No Accept, Correct, Reject, Defer, Escalate, apply-draft, Proposal acceptance, release, or handoff action was executed during this closure.

## Required next gate

Before marking production-ready, reconcile the shared database migration state with the canonical API source through the repository’s governed integration approach, activate the e4 hardening image, rerun the six Owner-test operations, and obtain a green required-check rollup for the updated PR #48 head. Until those gates pass, the safe fallback revision remains at 100% traffic and this record remains **NOT READY**.

## Browser test link

[Open the Owner-test Proposal](https://www.amecidsystem.com/opportunities/79c0a371-7299-4dc5-9cea-280c96f6ae78?view=outputs&ownerTestBuild=48559f8-real-auth)
