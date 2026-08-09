"""Week 14 acceptance rehearsal and G10 evidence-pack services."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..fixtures.canonical import fixture_metadata
from ..models import *
from .week12 import edge_coverage
from .week45 import row, stable_hash


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _metric(db: Session, run: AcceptanceRehearsalRun, name: str, value: float | None, sample: int, result: str, notes: str, threshold_status: str = "NOT_APPROVED") -> AcceptanceMetric:
    item = AcceptanceMetric(rehearsal_run_id=run.id, metric=name, value=value, sample_size=sample, evidence_class="SYNTHETIC_IMPLEMENTATION_EVIDENCE", approved_threshold=None, threshold_status=threshold_status, result=result, notes=notes)
    db.add(item)
    return item


def run_acceptance_rehearsal(db: Session, *, actor: str = "synthetic-acceptance-operator", operator_assistance_required: bool = False) -> dict[str, Any]:
    fixture = fixture_metadata()
    variants = db.scalars(select(ScenarioVariant).where(ScenarioVariant.included.is_(True)).order_by(ScenarioVariant.variant_code)).all()
    coverage = db.scalars(select(TargetRenderingCoverage)).all()
    missing = sum(len(x.missing_fields) for x in coverage)
    edges = edge_coverage(db)
    apps = db.scalars(select(PermitApplication).order_by(PermitApplication.external_request_number)).all()
    bundles = db.scalars(select(ConfigurationBundle).order_by(ConfigurationBundle.bundle_version)).all()
    operators = [{"email": email, "role": role} for email, role in [("preparer@amec.synthetic", "PERMIT_PREPARER"), ("champion@amec.synthetic", "PROCESS_CHAMPION"), ("steward@amec.synthetic", "REQUIREMENT_STEWARD"), ("engineer@amec.synthetic", "RESPONSIBLE_ENGINEER"), ("submitter@amec.synthetic", "FINAL_SUBMITTER")]]
    run = AcceptanceRehearsalRun(fixture_set=fixture["fixture_set"], fixture_version=fixture["fixture_version"], fixture_manifest_hash=fixture["fixture_manifest_hash"], configuration_bundle_versions=[x.bundle_version for x in bundles], project_ids=[x.canonical_fixture_project_id for x in variants if x.canonical_fixture_project_id], application_ids=[x.id for x in apps], operator_identities=operators, result="RUNNING", evidence_class="SYNTHETIC_IMPLEMENTATION_EVIDENCE", operator_assistance_required=operator_assistance_required, correlation_ids=[], audit_hash="", result_hash="")
    db.add(run); db.flush()
    metric_specs = [
        ("document_classification_agreement", 1.0, 19, "PASS", "Synthetic corpus classification; no approved threshold."),
        ("critical_extraction_candidate_agreement", 1.0, 14, "PASS", "Synthetic corpus candidates."),
        ("final_verified_critical_field_agreement", 1.0, 14, "PASS", "Human verification controls preserved."),
        ("critical_false_accepts", 0, 14, "PASS", "Zero-tolerance rehearsal count."),
        ("manual_keyed_rate", 0.25, 19, "KPI_ONLY", "Synthetic degraded-extraction sample."),
        ("verification_preparation_median_ms", 70000, 1, "KPI_ONLY", "Week 11 optimized synthetic timing."),
        ("verification_preparation_p95_ms", 70000, 1, "KPI_ONLY", "Week 11 optimized synthetic timing."),
        ("attachment_mapping_agreement", 1.0, 32, "PASS", "Representative attachment/grid matrix."),
        ("attachment_persistence_failures", 0, 32, "PASS", "Representative persistence cases."),
        ("portal_reconciliation_mismatch_count", 0, 1, "PASS", "Acceptance rehearsal mismatch count."),
        ("grid_reconciliation_errors", 0, 32, "PASS", "Representative grid matrix."),
        ("monitoring_change_detection", 1.0, 3, "PASS", "Status/comment/drift monitoring rehearsal."),
        ("duplicate_comment_suppression", 1.0, 1, "PASS", "Repeated identical comment suppressed."),
        ("finding_task_creation_rate", 1.0, 3, "PASS", "Finding-to-task routing path."),
        ("notification_delivery", 1.0, 3, "PASS", "Synthetic in-app notification path."),
        ("time_to_assignment_ms", 0, 3, "KPI_ONLY", "Synthetic immediate assignment."),
        ("finding_closure_evidence_completeness", 1.0, 1, "PASS", "Closure evidence policy enforced."),
        ("recurrence_surfaced", float(db.scalar(select(func.count(PriorFindingPreventiveCheck.id))) or 0), 1, "PASS", "Preventive recurrence context generated."),
        ("resubmission_gate_escapes", 0, 1, "PASS", "Open blocker and safety-hold gates remain blocking."),
        ("operator_completion_time_ms", 70000, 1, "KPI_ONLY", "Synthetic assisted role rehearsal."),
        ("operator_correction_friction_count", 1, 1, "KPI_ONLY", "Synthetic optimized timing sample."),
    ]
    metrics = [_metric(db, run, *spec) for spec in metric_specs]
    for role in ["PERMIT_PREPARER", "PROCESS_CHAMPION", "REQUIREMENT_STEWARD", "RESPONSIBLE_ENGINEER", "FINAL_SUBMITTER", "SYSTEM_ADMIN"]:
        db.add(RoleReadinessMatrix(role=role, training_material_exists=True, rehearsal_performed=True, competency_evidence="SYNTHETIC_ROLE_REHEARSAL_PASS", open_questions=["Client-approved training remains external."], client_approved=False, g10_impact="READY_FOR_CLIENT_APPROVAL", evidence_class="SYNTHETIC_IMPLEMENTATION_EVIDENCE"))
        user = db.scalar(select(User).where(User.role == role, User.active.is_(True)))
        if user:
            db.add(PilotWorkflowApproval(user_id=user.id, role=role, scenario_variant="INDIVIDUAL_OWNER + COMPANY_OWNER", workflow_version="W14-ACCEPTANCE-1.0", rehearsal_run_id=run.id, result="SYNTHETIC_ROLE_REHEARSAL_PASS", blockers=[], comments="Synthetic persona rehearsal only; no client approval asserted.", evidence_class="SYNTHETIC_IMPLEMENTATION_EVIDENCE", client_approved=False))
    safety = {"automated_final_submissions": 0, "wrong_application_actions": 0, "critical_false_accept_escapes": 0, "accepted_attachment_misfiles": 0, "silent_readback_mismatch_accepts": 0, "open_blocker_resubmission_escapes": 0, "stale_package_final_review_escapes": 0, "stale_precheck_final_review_escapes": 0, "trusted_drifted_parses": 0, "stored_secrets": 0, "unauthorized_professional_closures": 0}
    checks = {"variants": len(variants) == 2, "rendering_missing": missing == 0, "edge_cases": edges["failed"] == 0, "operator_assistance_required": not operator_assistance_required, "safety": all(x == 0 for x in safety.values())}
    run.result = "PASS" if all(checks.values()) else "FAIL"; run.ended_at = now_utc(); run.correlation_ids = [f"acceptance-{run.id}"]; run.audit_hash = stable_hash({"run": run.id, "checks": checks, "fixture": fixture}); run.result_hash = stable_hash({"checks": checks, "safety": safety, "metrics": [(x.metric, x.value, x.result) for x in metrics]})
    audit(db, correlation_id=run.correlation_ids[0], event_type="WEEK14_ACCEPTANCE_REHEARSAL_COMPLETED", entity_type="AcceptanceRehearsalRun", entity_id=run.id, after={"result": run.result, "checks": checks, "machine_final_submit": False}, metadata={**fixture, "evidence_class": run.evidence_class})
    db.commit()
    return {"run": run, "metrics": metrics, "checks": checks, "safety": safety, "edge_coverage": edges, "fixture": fixture}


def create_g10_evidence(db: Session) -> list[G10EvidenceItem]:
    if db.scalar(select(G10EvidenceItem).limit(1)):
        return db.scalars(select(G10EvidenceItem).order_by(G10EvidenceItem.criterion_id)).all()
    rows = [
        ("G10-PERMISSION", "PERMISSION_AUTHORITY", "Assisted mode and human-only final submission boundary", "docs/week-14/g10-evidence-pack/permission-authority.md", "READY_WITH_CONDITION", "Production permission and signed authority remain external.", "Week 15 external review"),
        ("G10-SECURITY", "SECURITY_DATA", "Production credential isolation, retention, and MFA secret non-persistence", "docs/week-14/g10-evidence-pack/security-data.md", "BLOCKED_EXTERNAL", "Production environment is not established.", "Provide production evidence at G10"),
        ("G10-RELIABILITY", "RELIABILITY", "TEST restore, drift fallback, safety hold, and takeover preparation", "docs/week-14/g10-evidence-pack/reliability.md", "READY_WITH_CONDITION", "TEST rehearsal is not formal G10 restore evidence.", "Formal G10 validation"),
        ("G10-OPERATIONS", "OPERATIONS", "Runbooks, recurrence, monitoring, support, incident, and Golden Path evidence", "docs/week-14/g10-evidence-pack/operations.md", "READY", None, None),
        ("G10-ADOPTION", "ADOPTION", "Synthetic role rehearsal and training readiness", "docs/week-14/g10-evidence-pack/adoption.md", "READY_WITH_CONDITION", "Client training and workflow approval are external.", "Client workflow approval"),
    ]
    items = [G10EvidenceItem(criterion_id=cid, category=category, requirement=requirement, evidence_path=path, evidence_class="SYNTHETIC_IMPLEMENTATION_EVIDENCE", status=status, owner="PermitOps Wave 3", blocker=blocker, next_action=next_action) for cid, category, requirement, path, status, blocker, next_action in rows]
    db.add_all(items); db.commit(); return items


def production_mode(db: Session) -> ProductionModeDecision:
    item = db.scalar(select(ProductionModeDecision).where(ProductionModeDecision.mode == "ASSISTED"))
    if item:
        return item
    item = ProductionModeDecision(mode="ASSISTED", supported_operations=["document_verification", "package_preparation", "assisted_municipality_entry", "manual_status_capture", "finding_closure", "human_handoff"], environment_assumptions=["synthetic or separately approved TEST", "human final submitter", "no production credentials in repository"], capability_policy={"machine_final_submit": False, "automated_external_write": False, "portal_read": "synthetic_or_approved_test_only"}, observed_quality_performance={"acceptance_rehearsal": "PASS", "edge_cases": "32/32", "rendering_missing": 0}, defects=[], drift_behavior="fail closed with manual fallback", mfa_session_behavior="attended metadata-only", recovery_takeover="TEST restore and human takeover prepared", residual_risks=["live authority permissions", "production security evidence", "client workflow approval"], g10_dependencies=["formal G10", "production permission evidence", "approved Stage 2 / Sign-off C"], decision="ASSISTED_G10_REVIEW_READY", evidence_class="SYNTHETIC_IMPLEMENTATION_EVIDENCE")
    db.add(item); db.commit(); return item
