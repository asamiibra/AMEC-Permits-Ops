# BD / Proposal Forms-Driven v2 — entry baseline

## Repository

- Branch: `main`
- Starting HEAD: `9690e5692c0a8ed39f947e8675519c5e7c068478`
- `origin/main`: `9690e5692c0a8ed39f947e8675519c5e7c068478`
- Working tree: clean before this evidence-only entry record
- Migration script head: `0041_dashboard_v2_waves_b_c`
- Fresh PostgreSQL baseline database: `bd_v2_entry_pg_20260813`, migrated to `0041_dashboard_v2_waves_b_c`

The long-lived default developer SQLite database reported an older applied revision (`0021_e7_unified_task_context`); it was not used for PostgreSQL baseline claims. The migration head itself is `0041_dashboard_v2_waves_b_c` and the fresh PostgreSQL baseline was explicitly upgraded through that head.

## Baseline verification

- PostgreSQL backend: `153 passed, 2 warnings`
- SQLite backend: `152 passed, 1 skipped, 2 warnings`
- Frontend: `12 files, 32 tests passed`
- Production build: passed; existing Vite chunk-size advisory only
- Dashboard V1 `/dashboard`: existing route and test coverage present; no BD changes at entry
- Dashboard V2 `/dashboard-v2`: existing Wave A+B+C route and regression coverage present
- Dashboard V2 B+C evidence: code-frozen state is recorded in `docs/dashboard-v2-waves-b-c/21-final-result.md`
- Shared semantic foundation: canonical `FieldObservation` and `VerifiedAssertion` models are present
- Party foundation: canonical `Party`, ownership, representation, and authorization models are present
- Property foundation: canonical `Property` and property ownership models are present
- Regulatory Core: canonical `ExternalBody`, `Jurisdiction`, `ServiceType`, lifecycle, `RegulatoryJourney`, and `AuthorityCase` models are present
- Requirement Engine v2: canonical `RequirementDefinition`, `RequirementPolicyVersion`, applicability, evaluation, and decision models are present
- Technical Rule foundation: existing canonical models and tests are present
- Form Automation Runtime: existing canonical profile, mapping release, QA, and readiness models are present
- Contract handoff: existing accepted Proposal revision → Contract path is present and tested

## Existing BD browser baseline

The repository contains the existing Proposal/Contract and New Proposal browser suites. The real-stack configuration deliberately excludes the retired legacy specs; the final BD browser suite will add current Forms-driven v2 coverage without changing that upstream baseline. The protected current surfaces are Proposal list, New Proposal, detail, source cards, readiness, Accept, Proposal/Checklist downloads, history, and accepted-Revision Contract handoff.

## Entry decision

The baseline is stable for bounded BD implementation. No overlapping uncommitted changes were present. The only runtime discrepancy is the intentionally long-lived local developer SQLite database revision noted above; it does not alter the verified migration head or fresh PostgreSQL baseline.

Evidence: `artifacts/bd-proposal-forms-driven-v2/00-entry-baseline.json`.
