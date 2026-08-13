# Preparation + Submission Loop — Entry Baseline

Date: 2026-08-13
Prompt: Preparation + Submission Loop v2
Execution mode: IMPLEMENT + RECONCILE + VERIFY + REPAIR CLOSURE DEFECTS + FREEZE

## Engineering gate

- Engineering token: `ENGINEERING_APPROVED_DESIGN_BASELINE_CODE_FROZEN`
- Deployment blocker: `ENGINEERING_APPROVED_DESIGN_BASELINE_DEPLOYMENT_PROVENANCE_BLOCKED_EXTERNAL`
- Downstream unlock: `PREPARATION_SUBMISSION_ENGINEERING_DEPENDENCIES_READY`
- Engineering closure SHA: `0e1b28825746f973b221670a0ed667daab4a9f95`
- `origin/main`: `0e1b28825746f973b221670a0ed667daab4a9f95`
- Working tree: clean at entry.
- Alembic head: `0043_project_engineering_approved_design_baseline`.

The prior Engineering closure explicitly proves the ApprovedDesignBaseline, exact revision/rendition linkage, Professional Approval, TechnicalRule integration, baseline immutability, project isolation, and future evidence seam. This prompt consumes those records and does not rebuild Engineering.

## Existing canonical domains verified

- `ExternalBody`, `ExternalBodyUnit`, `Jurisdiction`, `ServiceType`, lifecycle phases, `RegulatoryJourney`, `AuthorityCase`, identifiers, work periods, interaction profiles, outcomes, and relations are in `shared_domain_entities.py`.
- `RequirementDefinition`, `RequirementPolicyVersion`, policy items/groups, evidence constraints, applicability decisions, evaluations, evidence evaluations, and decisions are canonical Requirement Engine records.
- `FormAutomationProfile`, `FormMappingRelease`, `FormInstance`, `GeneratedArtifact`, validation/QA, signature requirements, and semantic assertions are canonical Form Automation records.
- `Document` / `DocumentVersion`, `FieldObservation`, and `VerifiedAssertion` are canonical evidence/version records.
- `Project`, `Contract`, `ProjectActivation`, accepted Proposal lineage, Issues, Notifications, AuditEvent, and `LineageEdge` already exist.
- Dashboard V1/V2, BD v2, Admin/Project Activation, Regulatory Core, Requirement Engine, Technical Rule, Form Automation, and Engineering regression suites are present.

## Boundary

This implementation adds only the case-specific execution runtime: policy binding, requirement instances/evidence decisions, physical readiness, immutable preparation revisions, explicit package manifests, deterministic prechecks, human submit authorization, external confirmation, submission cycles, findings/responses, resubmission lineage, and bounded case read models. Portal automation and the full Permit portfolio UX remain deferred.
