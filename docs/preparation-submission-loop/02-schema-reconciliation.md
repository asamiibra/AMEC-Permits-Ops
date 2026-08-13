# Schema Reconciliation

The post-Engineering Alembic head is `0043_project_engineering_approved_design_baseline`. The runtime companions are additive and use hard foreign keys to existing canonical identities wherever they exist.

## Runtime tables

- `authority_case_policy_bindings`, `requirement_instances`, `case_evidence_selections`, `physical_evidence_items`
- `preparation_revisions`, `submission_packages`, `submission_package_items`
- `submission_precheck_runs`, `submission_precheck_checks`, `submission_attempts`
- `external_submission_snapshots`, `authority_submission_cycles`
- `authority_case_findings`, `authority_finding_responses`, `authority_case_outcomes`

## Integrity rules

- Case creation is explicit, idempotent, project-activated, and canonical body/jurisdiction/service-bound.
- Policy binding is exact and fail-closed on no policy or ambiguity.
- Requirement instances preserve policy version/item/definition lineage and three-valued applicability.
- Locked preparation, package, precheck, external snapshot, and cycle records cannot be mutated through runtime APIs.
- Revision and cycle numbers are unique per case.
- Package item references are exact evidence/form/baseline/physical references.
- Precheck stores structured checks and pins the package checksum.
- External confirmation is required before a confirmed cycle exists.
