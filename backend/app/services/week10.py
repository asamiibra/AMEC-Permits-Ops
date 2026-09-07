"""Week 10 deterministic closure, review-cycle, and resubmission services.

This module deliberately contains policy checks rather than automation.  It
records evidence and asks an explicitly configured human role to verify it;
it never submits to an authority or makes a professional decision.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, true
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..fixtures.canonical import fixture_metadata
from ..models import *
from .week7 import ACTIVE_FINDING_STATUSES, _notification_delivery, create_routed_finding
from .week8 import ensure_project_lineage, record_material_change
from .week45 import row, snapshot_for_revision, stable_hash


ROOT_CAUSES = {
    "SOURCE_DOCUMENT_WRONG", "SOURCE_DOCUMENT_STALE", "EXTRACTION_ERROR",
    "VERIFICATION_ERROR", "FIELD_AUTHORITY_ERROR", "RENDERING_ERROR",
    "FORM_GENERATION_ERROR", "EXCEL_PROJECTION_ERROR", "ATTACHMENT_MISSING",
    "ATTACHMENT_WRONG_CATEGORY", "ATTACHMENT_PERSISTENCE", "GRID_ENTRY_ERROR",
    "GRID_IDENTITY_ERROR", "PORTAL_DERIVED_DIFFERENCE", "DRAWING_REVISION_ERROR",
    "REQUIREMENT_CONFIG_ERROR", "DEPENDENCY_EXPIRED", "HUMAN_ENTRY_ERROR",
    "AUTHORITY_CHANGE", "OTHER", "UNKNOWN_REVIEW_REQUIRED",
}

ACTIVE_RESOLUTION_STATUSES = {"PROPOSED", "EVIDENCE_REQUIRED", "READY_FOR_VERIFICATION"}
ACTIVE_OFFICIAL_STATUSES = ACTIVE_FINDING_STATUSES | {FindingStatus.CORRECTION_MADE, FindingStatus.EVIDENCE_ATTACHED}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _actor_role(db: Session, actor: str | None, supplied_role: str | None = None) -> str:
    if actor:
        user = db.get(User, actor) or db.scalar(select(User).where(User.email == actor))
        if user:
            return user.role.value if hasattr(user.role, "value") else str(user.role)
    if supplied_role:
        return supplied_role.value if hasattr(supplied_role, "value") else supplied_role
    return "UNKNOWN"


def _code_for(db: Session, finding: Finding) -> FindingCode | None:
    return db.get(FindingCode, finding.finding_code_id) if finding.finding_code_id else None


def required_evidence(db: Session, finding: Finding) -> list[str]:
    code = _code_for(db, finding)
    if not code:
        return ["OTHER"]
    policy = code.closure_evidence_policy
    if code.allowed_dispositions and finding.source_type == FindingSourceType.AUTHORITY_PRECHECK:
        return ["AUTHORITY_RECHECK"]
    mapping = {
        "DRAWING_REVISION": ["DRAWING_REVISION", "AUTHORITY_RESPONSE"],
        "DOCUMENT_EVIDENCE": ["DOCUMENT_EVIDENCE"],
        "AUTHORITY_RESPONSE": ["AUTHORITY_RESPONSE"],
        "AUTHORITY_RECHECK": ["AUTHORITY_RECHECK"],
        "TEXT_JUSTIFICATION": ["ENGINEER_VERIFICATION"],
        "PORTAL_FIELD": ["PORTAL_SNAPSHOT"],
        "PROPERTY_IDENTITY": ["FIELD_VERIFICATION"],
    }
    return mapping.get(policy, [policy or "OTHER"])


def resolution_requirements(db: Session, finding: Finding) -> dict[str, Any]:
    code = _code_for(db, finding)
    return {
        "finding_id": finding.id,
        "finding_code": code.code if code else None,
        "finding_code_version": code.version if code else finding.finding_code_version,
        "finding_class": code.finding_class if code else "UNKNOWN_REVIEW_REQUIRED",
        "required_evidence": required_evidence(db, finding),
        "required_verifier_role": code.closure_verifier_role if code else "REQUIREMENT_STEWARD",
        "allowed_dispositions": code.allowed_dispositions if code else ["CORRECTED"],
        "resubmission_gate_effect": code.resubmission_gate_effect if code else "STILL_BLOCKS",
        "fixture": fixture_metadata(),
    }


def create_resolution(db: Session, finding: Finding, payload: dict[str, Any], *, actor: str, correlation_id: str) -> FindingResolution:
    code = _code_for(db, finding)
    disposition = payload.get("disposition", "CORRECTED")
    allowed = code.allowed_dispositions if code and code.allowed_dispositions else ["CORRECTED"]
    if disposition not in allowed:
        raise ValueError("DISPOSITION_NOT_ALLOWED")
    root = payload.get("root_cause_category", code.typical_root_cause_category if code else "UNKNOWN_REVIEW_REQUIRED")
    if root not in ROOT_CAUSES:
        raise ValueError("UNKNOWN_ROOT_CAUSE_CATEGORY")
    latest = db.scalar(select(FindingResolution).where(FindingResolution.finding_id == finding.id).order_by(FindingResolution.resolution_version.desc()))
    resolution = FindingResolution(
        finding_id=finding.id, resolution_version=(latest.resolution_version + 1 if latest else 1),
        disposition=disposition, status="PROPOSED", correction_type=payload.get("correction_type", "OPERATOR_CORRECTION"),
        correction_summary=payload.get("correction_summary", "Correction recorded by operator."), root_cause_category=root,
        corrected_entity_type=payload.get("corrected_entity_type"), corrected_entity_id=payload.get("corrected_entity_id"),
        corrected_version_or_hash=payload.get("corrected_version_or_hash"),
        required_evidence_policy=code.closure_evidence_policy if code else "OTHER",
        closure_criteria_version=payload.get("closure_criteria_version", "W10-CLOSURE-1.0"), proposed_by=actor,
        prior_resolution_id=latest.id if latest else None, correlation_id=correlation_id,
    )
    db.add(resolution)
    finding.status = FindingStatus.CORRECTION_MADE
    db.flush()
    audit(db, correlation_id=correlation_id, event_type="FINDING_CORRECTION_RECORDED", entity_type="Finding", entity_id=finding.id, after={"resolution_id": resolution.id, "root_cause_category": root}, metadata=fixture_metadata())
    audit(db, correlation_id=correlation_id, event_type="FINDING_RESOLUTION_CREATED", entity_type="FindingResolution", entity_id=resolution.id, after={"finding_id": finding.id, "version": resolution.resolution_version}, metadata=fixture_metadata())
    return resolution


def add_evidence(db: Session, resolution: FindingResolution, payload: dict[str, Any], *, actor: str, correlation_id: str) -> FindingResolutionEvidence:
    item = FindingResolutionEvidence(
        finding_resolution_id=resolution.id, evidence_artifact_id=payload.get("evidence_artifact_id", ""),
        evidence_type=payload.get("evidence_type", "OTHER"), source_entity_type=payload.get("source_entity_type"),
        source_entity_id=payload.get("source_entity_id"), source_version_or_hash=payload.get("source_version_or_hash"),
        added_by=actor,
    )
    if not item.evidence_artifact_id:
        raise ValueError("EVIDENCE_ARTIFACT_REQUIRED")
    db.add(item)
    resolution.status = "EVIDENCE_REQUIRED"
    finding = db.get(Finding, resolution.finding_id)
    if finding:
        finding.status = FindingStatus.EVIDENCE_ATTACHED
    db.flush()
    audit(db, correlation_id=correlation_id, event_type="FINDING_RESOLUTION_EVIDENCE_ADDED", entity_type="FindingResolutionEvidence", entity_id=item.id, after={"resolution_id": resolution.id, "evidence_type": item.evidence_type}, metadata=fixture_metadata())
    return item


def evaluate_closure(db: Session, resolution: FindingResolution, *, verifier: str | None = None, verifier_role: str | None = None) -> FindingClosureEvaluation:
    finding = db.get(Finding, resolution.finding_id)
    if not finding:
        raise ValueError("FINDING_NOT_FOUND")
    req = resolution_requirements(db, finding)
    evidence = db.scalars(select(FindingResolutionEvidence).where(FindingResolutionEvidence.finding_resolution_id == resolution.id)).all()
    provided = sorted({x.evidence_type for x in evidence})
    blockers: list[str] = []
    for required in req["required_evidence"]:
        if required not in provided:
            blockers.append(f"MISSING_EVIDENCE:{required}")
    if resolution.corrected_version_or_hash:
        for item in evidence:
            if item.source_version_or_hash and item.source_version_or_hash != resolution.corrected_version_or_hash:
                blockers.append("STALE_EVIDENCE_VERSION")
    for item in evidence:
        if item.evidence_type == "AUTHORITY_RECHECK" and item.source_entity_type == "AuthorityPrecheckRun" and item.source_entity_id:
            recheck = db.get(AuthorityPrecheckRun, item.source_entity_id)
            recheck_revision = db.get(PreparationRevision, recheck.preparation_revision_id) if recheck else None
            if not recheck or recheck.status in {"STALE", "SUPERSEDED"} or not recheck_revision or recheck_revision.status in {"STALE", "SUPERSEDED"}:
                blockers.append("BLOCKED_STALE_EVIDENCE")
    actual_role = _actor_role(db, verifier, verifier_role)
    expected_role = req["required_verifier_role"]
    if verifier and actual_role != expected_role:
        blockers.append("WRONG_VERIFIER_ROLE")
    result = "VERIFIED_CLOSABLE" if not blockers and verifier else ("BLOCKED_WRONG_VERIFIER" if "WRONG_VERIFIER_ROLE" in blockers else "BLOCKED_STALE_EVIDENCE" if any("STALE" in x for x in blockers) else "BLOCKED_MISSING_EVIDENCE" if blockers else "READY_TO_VERIFY")
    evaluation = FindingClosureEvaluation(
        finding_id=finding.id, resolution_id=resolution.id, finding_code_version=req["finding_code_version"] or "UNKNOWN",
        required_evidence=req["required_evidence"], provided_evidence=provided, required_verifier_role=expected_role,
        verifier=verifier, result=result, blockers=blockers,
    )
    db.add(evaluation)
    db.flush()
    return evaluation


def verify_resolution(db: Session, resolution: FindingResolution, *, verifier: str, verifier_role: str | None, correlation_id: str) -> FindingClosureEvaluation:
    evaluation = evaluate_closure(db, resolution, verifier=verifier, verifier_role=verifier_role)
    finding = db.get(Finding, resolution.finding_id)
    if evaluation.result != "VERIFIED_CLOSABLE":
        resolution.status = "READY_FOR_VERIFICATION" if not evaluation.blockers else resolution.status
        audit(db, correlation_id=correlation_id, event_type="FINDING_CLOSURE_REJECTED", entity_type="FindingResolution", entity_id=resolution.id, after={"result": evaluation.result, "blockers": evaluation.blockers}, metadata=fixture_metadata())
        return evaluation
    resolution.status = "VERIFIED"
    resolution.verified_by = verifier
    resolution.verifier_role = evaluation.required_verifier_role
    resolution.verified_at = _now()
    resolution.verification_result = "VERIFIED_CLOSABLE"
    finding.status = FindingStatus.CLOSED_VERIFIED
    audit(db, correlation_id=correlation_id, event_type="FINDING_CLOSURE_VERIFIED", entity_type="Finding", entity_id=finding.id, after={"resolution_id": resolution.id, "verifier": verifier, "verifier_role": evaluation.required_verifier_role}, metadata=fixture_metadata())
    audit(db, correlation_id=correlation_id, event_type="FINDING_CLOSED", entity_type="Finding", entity_id=finding.id, after={"resolution_id": resolution.id}, metadata=fixture_metadata())
    return evaluation


def reject_resolution(db: Session, resolution: FindingResolution, reason: str, *, actor: str, correlation_id: str) -> FindingResolution:
    resolution.status = "REJECTED"
    resolution.rejection_reason = reason
    finding = db.get(Finding, resolution.finding_id)
    if finding:
        finding.status = FindingStatus.OPEN
    audit(db, correlation_id=correlation_id, event_type="FINDING_CLOSURE_REJECTED", entity_type="FindingResolution", entity_id=resolution.id, after={"reason": reason, "actor": actor}, metadata=fixture_metadata())
    return resolution


def raise_dispute(db: Session, finding: Finding, payload: dict[str, Any], *, actor: str, correlation_id: str) -> FindingDispute:
    if not payload.get("reason"):
        raise ValueError("DISPUTE_REASON_REQUIRED")
    code = _code_for(db, finding)
    effect = code.resubmission_gate_effect if code and code.resubmission_gate_effect == "ALLOWED_FORMAL_DISPUTE" else "STILL_BLOCKS"
    dispute = FindingDispute(finding_id=finding.id, raised_by=actor, reason=payload["reason"], evidence_artifact_ids=payload.get("evidence_artifact_ids", []), status="OPEN", resubmission_effect=effect)
    db.add(dispute); finding.status = FindingStatus.DISPUTED; db.flush()
    audit(db, correlation_id=correlation_id, event_type="FINDING_DISPUTE_RAISED", entity_type="FindingDispute", entity_id=dispute.id, after={"finding_id": finding.id, "resubmission_effect": effect}, metadata=fixture_metadata())
    return dispute


def review_dispute(db: Session, dispute: FindingDispute, payload: dict[str, Any], *, actor: str, correlation_id: str) -> FindingDispute:
    decision = payload.get("decision", "REJECTED")
    dispute.status = "ACCEPTED" if decision == "ACCEPT" else "REJECTED"
    dispute.decision = decision
    dispute.reviewed_by = actor; dispute.reviewed_at = _now()
    finding = db.get(Finding, dispute.finding_id)
    if finding:
        finding.status = FindingStatus.DISPUTED if dispute.status == "ACCEPTED" else FindingStatus.OPEN
    audit(db, correlation_id=correlation_id, event_type="FINDING_DISPUTE_ACCEPTED" if dispute.status == "ACCEPTED" else "FINDING_DISPUTE_REJECTED", entity_type="FindingDispute", entity_id=dispute.id, after={"decision": decision, "resubmission_effect": dispute.resubmission_effect}, metadata=fixture_metadata())
    return dispute


def reopen_finding(db: Session, finding: Finding, *, actor: str, reason: str, correlation_id: str, authority_event_id: str | None = None) -> FindingReopenEvent:
    prior = db.scalar(select(FindingResolution).where(FindingResolution.finding_id == finding.id, FindingResolution.status == "VERIFIED").order_by(FindingResolution.resolution_version.desc()))
    event = FindingReopenEvent(finding_id=finding.id, prior_resolution_id=prior.id if prior else None, reason=reason, source_authority_event_id=authority_event_id, reopened_by=actor)
    db.add(event); finding.status = FindingStatus.REOPENED
    task = db.scalar(select(WorkflowTask).where(WorkflowTask.finding_id == finding.id).order_by(WorkflowTask.created_at.desc()))
    if task:
        task.status = WorkflowTaskStatus.OPEN
    else:
        task = WorkflowTask(project_id=finding.project_id, application_id=finding.application_id, finding_id=finding.id, task_type="FINDING_REMEDIATION", title=finding.title, description=finding.normalized_summary, owner_user_id=finding.assignee_user_id, owner_role=finding.assignee_role or "UNASSIGNED", status=WorkflowTaskStatus.OPEN, priority=finding.severity, correlation_id=correlation_id)
        db.add(task); db.flush()
    notification = NotificationEvent(finding_id=finding.id, workflow_task_id=task.id, recipient_user_id=finding.assignee_user_id, recipient_role=finding.assignee_role or "UNASSIGNED", channel="IN_APP", event_type="FINDING_REOPENED", status=NotificationStatus.PENDING, subject=finding.title, body_preview=reason[:500], correlation_id=correlation_id)
    db.add(notification); db.flush(); _notification_delivery(notification)
    db.flush()
    audit(db, correlation_id=correlation_id, event_type="FINDING_REOPENED", entity_type="Finding", entity_id=finding.id, after={"reason": reason, "prior_resolution_id": event.prior_resolution_id}, metadata=fixture_metadata())
    return event


def link_prior_finding(db: Session, current: Finding, *, actor: str, correlation_id: str) -> FindingHistoryLink | None:
    if not current.finding_code_id:
        return None
    code = _code_for(db, current)
    query = select(Finding).where(Finding.application_id == current.application_id, Finding.id != current.id, Finding.finding_code_id == current.finding_code_id)
    if current.affected_object_id:
        query = query.where(Finding.affected_object_id == current.affected_object_id)
    prior = db.scalar(query.order_by(Finding.captured_at.desc()))
    if not prior:
        return None
    existing = db.scalar(select(FindingHistoryLink).where(FindingHistoryLink.current_finding_id == current.id, FindingHistoryLink.prior_finding_id == prior.id))
    if existing:
        return existing
    link = FindingHistoryLink(current_finding_id=current.id, prior_finding_id=prior.id, relationship_type="SAME_ISSUE_RECURRED", finding_code=code.code if code else "UNKNOWN", affected_object_key=current.affected_object_id, submission_cycle_id=current.submission_cycle_id, preparation_revision_id=current.preparation_revision_id, linked_by=actor, confidence_mode="DETERMINISTIC_CODE_OBJECT")
    db.add(link); db.flush()
    audit(db, correlation_id=correlation_id, event_type="FINDING_RECURRENCE_LINKED", entity_type="FindingHistoryLink", entity_id=link.id, after={"current_finding_id": current.id, "prior_finding_id": prior.id}, metadata=fixture_metadata())
    return link


def evaluate_precheck_clearance(db: Session, run: AuthorityPrecheckRun) -> PrecheckClearanceEvaluation:
    revision = db.get(PreparationRevision, run.preparation_revision_id)
    findings = db.scalars(select(Finding).where(Finding.authority_precheck_run_id == run.id, Finding.blocking == true())).all()
    unresolved = [x for x in findings if x.status not in {FindingStatus.CLOSED_VERIFIED}]
    stale = run.status in {"STALE", "SUPERSEDED"} or bool(run.invalidated_at) or revision is None or revision.status in {"STALE", "SUPERSEDED"}
    result = "STALE" if stale else "BLOCKED_FINDINGS" if unresolved else "CLEAR" if run.status == "CLEAR" or not findings else "BLOCKED_FINDINGS"
    evaluation = PrecheckClearanceEvaluation(preparation_revision_id=run.preparation_revision_id, precheck_run_id=run.id, blocking_finding_count=len(findings), unresolved_blocking_count=len(unresolved), stale_input=stale, result=result, evaluation_hash=stable_hash({"run": run.id, "revision": run.preparation_revision_id, "finding_statuses": [(x.id, x.status) for x in findings], "stale": stale}))
    db.add(evaluation); run.clearance_result = result
    db.flush()
    audit(db, correlation_id=f"precheck-clearance-{evaluation.id}", event_type="PRECHECK_CLEARANCE_EVALUATED", entity_type="PrecheckClearanceEvaluation", entity_id=evaluation.id, after={"result": result, "unresolved_blocking_count": len(unresolved)}, metadata=fixture_metadata())
    return evaluation


def create_correction_revision(db: Session, old_revision: PreparationRevision, *, actor: str, correlation_id: str, package_override: Package | None = None) -> PreparationRevision:
    package = package_override or (db.get(Package, old_revision.package_id) if old_revision.package_id else None)
    if package and package_override and package.id != old_revision.package_id and package.status == "DRAFT":
        # The caller supplied a rebuilt package; the historical package remains
        # immutable evidence and is explicitly stale, never silently reused.
        prior_package = db.get(Package, old_revision.package_id) if old_revision.package_id else None
        if prior_package and prior_package.status not in {"STALE", "SUPERSEDED"}:
            prior_package.status = "STALE"
    sequence = (db.scalar(select(func.max(PreparationRevision.sequence)).where(PreparationRevision.project_id == old_revision.project_id)) or 0) + 1
    old_revision.status = "SUPERSEDED"
    revision = PreparationRevision(project_id=old_revision.project_id, application_id=old_revision.application_id, sequence=sequence, status="READY_FOR_ASSISTED_PREPARATION", scenario_version=old_revision.scenario_version, field_authority_version=old_revision.field_authority_version, requirement_config_version=old_revision.requirement_config_version, rendering_config_version=old_revision.rendering_config_version, package_id=package.id if package else None, package_manifest_hash=package.manifest_hash if package else None, created_by=actor, configuration_bundle_id=package.configuration_bundle_id if package else old_revision.configuration_bundle_id)
    db.add(revision); db.flush(); snapshot_for_revision(db, revision)
    ensure_project_lineage(db, revision.project_id, correlation_id)
    audit(db, correlation_id=correlation_id, event_type="PRECHECK_CORRECTION_STARTED", entity_type="PreparationRevision", entity_id=revision.id, after={"prior_revision_id": old_revision.id, "package_id": revision.package_id}, metadata=fixture_metadata())
    return revision


def history_context(db: Session, revision: PreparationRevision) -> dict[str, Any]:
    revisions = db.scalars(select(PreparationRevision).where(PreparationRevision.project_id == revision.project_id, PreparationRevision.sequence <= revision.sequence).order_by(PreparationRevision.sequence)).all()
    packages = db.scalars(select(Package).where(Package.project_id == revision.project_id).order_by(Package.created_at)).all()
    runs = db.scalars(select(AuthorityPrecheckRun).where(AuthorityPrecheckRun.application_id == revision.application_id).order_by(AuthorityPrecheckRun.run_at)).all()
    findings = db.scalars(select(Finding).where(Finding.application_id == revision.application_id).order_by(Finding.captured_at)).all()
    approvals = db.scalars(select(Approval).where(Approval.entity_id.in_([x.id for x in packages] or ["-"])).order_by(Approval.decided_at)).all()
    return {"current_preparation_revision": row(revision), "prior_preparation_revisions": [row(x) for x in revisions if x.id != revision.id], "prior_packages": [row(x) for x in packages if x.id != revision.package_id], "prior_precheck_runs": [row(x) for x in runs if x.preparation_revision_id != revision.id], "prior_findings": [row(x) for x in findings if x.preparation_revision_id != revision.id], "prior_approvals": [row(x) for x in approvals], "recurrence_links": [row(x) for x in db.scalars(select(FindingHistoryLink).where(FindingHistoryLink.preparation_revision_id == revision.id)).all()], "fixture": fixture_metadata()}


def evaluate_resubmission(db: Session, application: PermitApplication, *, cycle: SubmissionCycle | None = None) -> ResubmissionReadinessEvaluation:
    revision = db.scalar(select(PreparationRevision).where(PreparationRevision.application_id == application.id).order_by(PreparationRevision.sequence.desc()))
    package = db.get(Package, revision.package_id) if revision and revision.package_id else None
    reasons: list[dict[str, Any]] = []
    def check(code: str, status: str, reason: str, evidence: list[str] | None = None):
        reasons.append({"condition": code, "status": status, "reason": reason, "evidence": evidence or []})
    if not revision or revision.status in {"STALE", "SUPERSEDED"}:
        check("CURRENT_REVISION", "BLOCK", "No current PreparationRevision is available.")
    elif revision.status not in {"VERIFIED_DRAFT", "READY_FOR_HUMAN_FINAL_REVIEW", "SUBMITTED"}:
        check("CURRENT_REVISION_VERIFIED", "BLOCK", "Current PreparationRevision has not passed assisted preparation verification.", [revision.id])
    if not package or package.status in {"STALE", "SUPERSEDED"}:
        check("CURRENT_PACKAGE", "BLOCK", "Current package is missing or stale.")
    if package and package.status != "APPROVED":
        check("PACKAGE_APPROVAL", "BLOCK", "Current package is not approved.", [package.id])
    precheck = db.scalar(select(AuthorityPrecheckRun).where(AuthorityPrecheckRun.preparation_revision_id == revision.id).order_by(AuthorityPrecheckRun.run_at.desc())) if revision else None
    if not precheck:
        check("PRECHECK_CURRENT", "BLOCK", "Current revision has no precheck clearance.")
    elif precheck.clearance_result != "CLEAR" or precheck.status in {"STALE", "SUPERSEDED"}:
        check("PRECHECK_CURRENT", "BLOCK", "Current precheck is not clear and current.", [precheck.id])
    dependencies = db.scalars(select(ApprovalDependency).where(ApprovalDependency.project_id == application.project_id)).all()
    invalid_dependencies = [x.id for x in dependencies if x.status != "CURRENT" or (x.valid_until and x.valid_until < _now().date())]
    if invalid_dependencies:
        check("DEPENDENCIES_VALID", "BLOCK", "Required dependency validity is not current.", invalid_dependencies)
    credentials = db.scalars(select(ProfessionalCredential).where(ProfessionalCredential.project_id == application.project_id)).all()
    if any(x.status != "CURRENT" or (x.valid_until and x.valid_until.date() < _now().date()) for x in credentials):
        check("PROFESSIONAL_VALIDITY", "BLOCK", "Professional credential validity is not current.")
    portal_mismatches = db.scalars(select(PortalReconciliationResult).where(PortalReconciliationResult.preparation_revision_id == revision.id, PortalReconciliationResult.status.in_(["MISMATCH", "BLOCKED"]))) .all() if revision else []
    if portal_mismatches:
        check("PORTAL_RECONCILIATION", "BLOCK", "Current portal reconciliation has blocking mismatches.", [x.id for x in portal_mismatches])
    holds = db.scalars(select(WorkflowSafetyHold).where(WorkflowSafetyHold.scope_type == "APPLICATION", WorkflowSafetyHold.scope_id == application.id, WorkflowSafetyHold.released_at.is_(None))).all()
    if holds:
        check("WORKFLOW_SAFETY_HOLD", "BLOCK", "An unreleased integrity safety hold blocks resubmission readiness.", [x.id for x in holds])
    official = db.scalars(select(Finding).where(Finding.application_id == application.id, Finding.source_type == FindingSourceType.OFFICIAL_MUNICIPALITY_COMMENT, Finding.blocking == true())).all()
    blockers = []; allowed_disputes = 0
    for finding in official:
        accepted = db.scalar(select(FindingDispute).where(FindingDispute.finding_id == finding.id, FindingDispute.status == "ACCEPTED", FindingDispute.resubmission_effect == "ALLOWED_FORMAL_DISPUTE"))
        if accepted:
            allowed_disputes += 1
        elif finding.status != FindingStatus.CLOSED_VERIFIED:
            blockers.append(finding.id)
    if blockers:
        check("PRIOR_OFFICIAL_FINDINGS", "BLOCK", "Applicable blocking official findings remain unresolved.", blockers)
    if not reasons:
        check("ALL_G9_CONDITIONS", "PASS", "All configured resubmission conditions pass.")
    overall = "RESUBMISSION_READY" if not any(x["status"] == "BLOCK" for x in reasons) else "RESUBMISSION_BLOCKED"
    evaluation = ResubmissionReadinessEvaluation(application_id=application.id, submission_cycle_id=cycle.id if cycle else None, preparation_revision_id=revision.id if revision else None, package_id=package.id if package else None, overall_status=overall, blocking_finding_count=len(blockers), allowed_dispute_count=allowed_disputes, package_status=package.status if package else None, precheck_status=precheck.clearance_result if precheck else "NOT_RUN", dependency_validity_status="VALID" if not invalid_dependencies else "INVALID", approval_status=package.status if package else "MISSING", portal_reconciliation_status="PASS" if not portal_mismatches else "BLOCKED", reasons=reasons, evaluation_hash=stable_hash(reasons))
    db.add(evaluation); db.flush()
    audit(db, correlation_id=f"resubmission-{evaluation.id}", event_type="RESUBMISSION_READY" if overall == "RESUBMISSION_READY" else "RESUBMISSION_BLOCKED", entity_type="ResubmissionReadinessEvaluation", entity_id=evaluation.id, after={"overall_status": overall, "blocking_finding_count": len(blockers)}, metadata=fixture_metadata())
    return evaluation


def requirement_coverage(db: Session) -> RequirementMatrixCoverage:
    scenario = db.scalar(select(ScenarioConfig).where(ScenarioConfig.scenario_code == "DEMO_BUILDING_PERMIT_V1"))
    reqs = db.scalars(select(RequirementConfig).where(RequirementConfig.scenario_id == scenario.id, RequirementConfig.status != ConfigStatus.NEEDS_DECISION)).all()
    required_attrs = ("requirement_code", "description", "requirement_type", "status")
    missing = [{"requirement_code": x.requirement_code, "missing": [a for a in required_attrs if not getattr(x, a, None)]} for x in reqs]
    missing = [x for x in missing if x["missing"]]
    complete = len(reqs) - len(missing)
    item = RequirementMatrixCoverage(scenario_id=scenario.scenario_code, scenario_version=scenario.version, total_requirements=len(reqs), complete=complete, incomplete=len(missing), blocked_external=0, not_applicable=0, unknown=0, coverage_percent=round(complete / len(reqs) * 100) if reqs else 0, missing_attributes=missing)
    db.add(item); db.flush(); audit(db, correlation_id=f"coverage-{item.id}", event_type="REQUIREMENT_MATRIX_COVERAGE_EVALUATED", entity_type="RequirementMatrixCoverage", entity_id=item.id, after={"coverage_percent": item.coverage_percent, "unknown": item.unknown}, metadata=fixture_metadata()); return item


def field_coverage(db: Session) -> FieldMatrixCoverage:
    scenario = db.scalar(select(ScenarioConfig).where(ScenarioConfig.scenario_code == "DEMO_BUILDING_PERMIT_V1"))
    fields = db.scalars(select(FieldDefinition).where(FieldDefinition.active == true())).all()
    critical = [x for x in fields if str(x.criticality.value if hasattr(x.criticality, "value") else x.criticality) == "CRITICAL"]
    complete = 0
    missing = []
    cfg = db.scalar(select(MunicipalityConfig).where(MunicipalityConfig.scenario_id == scenario.id))
    for field in fields:
        authority = db.scalar(select(FieldAuthorityRule).where(FieldAuthorityRule.field_definition_id == field.id, FieldAuthorityRule.scenario_id == scenario.id))
        targets = db.scalars(select(TargetRenderingRule).where(TargetRenderingRule.field_definition_id == field.id, TargetRenderingRule.scenario_id == scenario.id, TargetRenderingRule.status == RenderingStatus.ACTIVE)).all()
        used_portal = any((x.get("field_key") or "").upper() in field.field_code.upper() or x.get("source_mode") for x in (cfg.fields_json if cfg else []))
        okay = bool(authority and authority.human_verifier_role and (targets or not field in critical) and (not used_portal or cfg))
        if okay: complete += 1
        else: missing.append({"field_code": field.field_code, "missing": [k for k, present in {"authority": bool(authority), "verifier": bool(authority and authority.human_verifier_role), "target_rendering": bool(targets) if field in critical else True}.items() if not present]})
    configured_grids = (cfg.grids_json if cfg else []) or []
    item = FieldMatrixCoverage(scenario_id=scenario.scenario_code, field_set_version="FIELD-MATRIX-W10-1.0", total_fields=len(fields), critical_fields=len(critical), complete_fields=complete, incomplete_fields=len(fields)-complete, blocked_external=0, unknown=0, target_coverage={"form": len(fields), "excel": len(fields), "municipality": len(fields), "grid": len(configured_grids)}, result="COMPLETE" if not missing else "INCOMPLETE")
    db.add(item); db.flush(); audit(db, correlation_id=f"coverage-{item.id}", event_type="FIELD_MATRIX_COVERAGE_EVALUATED", entity_type="FieldMatrixCoverage", entity_id=item.id, after={"result": item.result, "unknown": item.unknown}, metadata=fixture_metadata()); return item


def control_result(db: Session, definition: ControlDefinition, project_id: str, package_id: str | None, revision_id: str | None) -> tuple[str, list[str]]:
    evidence: list[str] = []
    if definition.control_code == "CTRL_DRAWING_METADATA_MATCH":
        from .configuration import evaluate_drawing_controls
        results = evaluate_drawing_controls(db, project_id); evidence = [x["control_code"] for x in results]; return ("PASS" if all(x["result"] == "PASS" for x in results) else "FAIL" if any(x["result"] == "FAIL" and x["blocking"] for x in results) else "NEEDS_REVIEW", evidence)
    if definition.control_code == "CTRL_REQUIRED_DOCUMENTS_CURRENT":
        from .week45 import evaluate_readiness
        evaluation, _ = evaluate_readiness(db, project_id, preparation_revision_id=revision_id); return ("PASS" if evaluation.overall_status in {"READY", "READY_WITH_NONBLOCKING_WARNINGS"} else "FAIL", [evaluation.id])
    if definition.control_code == "CTRL_ATTACHMENT_MANIFEST_COMPLETE":
        manifest = db.scalar(select(AttachmentManifest).where(AttachmentManifest.package_id == package_id)) if package_id else None; return ("PASS" if manifest and manifest.status in {"CURRENT", "LOCKED", "APPROVED"} else "NEEDS_REVIEW", [manifest.id] if manifest else [])
    if definition.control_code == "CTRL_PRECHECK_CURRENT":
        run = db.scalar(select(AuthorityPrecheckRun).where(AuthorityPrecheckRun.preparation_revision_id == revision_id).order_by(AuthorityPrecheckRun.run_at.desc())) if revision_id else None; return ("PASS" if run and run.clearance_result == "CLEAR" else "FAIL", [run.id] if run else [])
    if definition.control_code == "CTRL_PRIOR_BLOCKING_FINDINGS_CLOSED":
        app = db.scalar(select(PermitApplication).join(PreparationRevision, PreparationRevision.application_id == PermitApplication.id).where(PreparationRevision.id == revision_id)) if revision_id else None; findings = db.scalars(select(Finding).where(Finding.application_id == app.id, Finding.source_type == FindingSourceType.OFFICIAL_MUNICIPALITY_COMMENT, Finding.blocking == true(), Finding.status != FindingStatus.CLOSED_VERIFIED)) .all() if app else []; return ("PASS" if not findings else "FAIL", [x.id for x in findings])
    return "PASS", evidence


def run_controls(db: Session, project_id: str, *, package_id: str | None, revision_id: str | None, correlation_id: str) -> list[ControlRun]:
    runs = []
    for definition in db.scalars(select(ControlDefinition).where(ControlDefinition.status == "ACTIVE").order_by(ControlDefinition.control_code)).all():
        result, evidence = control_result(db, definition, project_id, package_id, revision_id)
        item = ControlRun(control_definition_id=definition.id, project_id=project_id, package_id=package_id, preparation_revision_id=revision_id, input_hash=stable_hash({"project_id": project_id, "package_id": package_id, "revision_id": revision_id, "control": definition.control_code}), result=result, evidence_refs=evidence, correlation_id=correlation_id)
        db.add(item); db.flush(); runs.append(item)
        audit(db, correlation_id=correlation_id, event_type="CONTROL_RUN_COMPLETED", entity_type="ControlRun", entity_id=item.id, after={"control_code": definition.control_code, "result": result}, metadata=fixture_metadata())
        if result == "FAIL" and definition.blocking and definition.finding_code_on_fail:
            application = db.scalar(select(PermitApplication).where(PermitApplication.project_id == project_id).order_by(PermitApplication.external_request_number))
            project = db.get(Project, project_id)
            if application and project:
                finding = create_routed_finding(db, project=project, application=application, source_type=FindingSourceType.INTERNAL_PREFLIGHT, source_channel="CONTROL_RUN", source_reference=item.id, raw_text=f"Control {definition.control_code} failed.", title=f"Control failed: {definition.control_code}", normalized_summary=f"Deterministic control failed; human correction and verification required.", discipline="TECHNICAL", severity=definition.severity, blocking=definition.blocking, finding_code=definition.finding_code_on_fail, preparation_revision_id=revision_id, evidence_artifact_id=item.id, correlation_id=correlation_id, captured_by="permitops-control-run", normalized_key=f"CONTROL:{project_id}:{definition.control_code}:{revision_id}")
                audit(db, correlation_id=correlation_id, event_type="CONTROL_FINDING_CREATED", entity_type="Finding", entity_id=finding["finding"].id, after={"control_run_id": item.id, "control_code": definition.control_code}, metadata=fixture_metadata())
    return runs
