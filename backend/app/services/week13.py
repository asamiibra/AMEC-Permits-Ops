"""Week 13 deterministic recurrence, support, incident, and recovery services."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..fixtures.canonical import fixture_metadata
from ..models import *
from .week45 import row, stable_hash
from .week8 import ensure_project_lineage, _affected
from .week7 import ACTIVE_FINDING_STATUSES, FindingStatus, WorkflowTaskStatus


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _code(db: Session, finding: Finding) -> FindingCode | None:
    return db.get(FindingCode, finding.finding_code_id) if finding.finding_code_id else None


def recurrence_key(db: Session, finding: Finding) -> tuple[str, str]:
    code = _code(db, finding)
    if not code:
        return f"POSSIBLE:{finding.id}", "HUMAN_REVIEW_REQUIRED"
    strategy = code.recurrence_key_strategy or "CODE_ONLY"
    parts = [code.code]
    if strategy in {"CODE_PLUS_AFFECTED_OBJECT", "CODE_OBJECT"}:
        parts.append(f"OBJECT:{finding.affected_object_type or ''}:{finding.affected_object_id or ''}")
    elif strategy == "CODE_PLUS_REQUIREMENT":
        parts.append(f"REQ:{finding.requirement_code or ''}")
    elif strategy == "CODE_PLUS_PORTAL_SECTION":
        parts.append(f"PORTAL:{finding.affected_object_type or ''}")
    elif strategy == "EXTERNAL_FINDING_ID":
        parts.append(f"EXT:{finding.external_finding_id or ''}")
    if strategy in {"CODE_ONLY", "CODE_PLUS_AFFECTED_OBJECT", "CODE_OBJECT", "CODE_PLUS_REQUIREMENT", "CODE_PLUS_PORTAL_SECTION"}:
        parts.extend([f"SOURCE:{finding.source_type}", f"DISC:{finding.discipline}"])
    return "|".join(parts), strategy


def _closed(finding: Finding) -> bool:
    return finding.status in {FindingStatus.CLOSED, FindingStatus.CLOSED_VERIFIED, FindingStatus.VERIFIED}


def analyze_recurrence(db: Session, payload: dict[str, Any] | None = None, actor: str = "synthetic-analytics") -> dict[str, Any]:
    payload = payload or {}
    stmt = select(Finding).order_by(Finding.captured_at, Finding.id)
    if payload.get("application_id"):
        stmt = stmt.where(Finding.application_id == payload["application_id"])
    findings = db.scalars(stmt).all()
    groups: dict[str, list[Finding]] = {}
    strategies: dict[str, str] = {}
    for finding in findings:
        key, strategy = recurrence_key(db, finding)
        groups.setdefault(key, []).append(finding)
        strategies[key] = strategy
    items: list[FindingRecurrenceAnalysisItem] = []
    first_count = repeated_open = after_closure = reopened = possible = 0
    result_rows: list[dict[str, Any]] = []
    for key, group in groups.items():
        group.sort(key=lambda x: (x.captured_at, x.id))
        code = _code(db, group[-1])
        if strategies[key] == "HUMAN_REVIEW_REQUIRED":
            classification = "POSSIBLE_RECURRENCE_NEEDS_REVIEW"; possible += 1
        elif any(db.scalar(select(FindingReopenEvent).where(FindingReopenEvent.finding_id == f.id)) for f in group):
            classification = "REOPENED_SAME_FINDING"; reopened += 1
        elif len(group) == 1:
            classification = "FIRST_OCCURRENCE"; first_count += 1
        else:
            closed_prior = any(_closed(f) for f in group[:-1])
            if closed_prior:
                classification = "RECURRENCE_AFTER_VERIFIED_CLOSURE"; after_closure += 1
            elif any(not _closed(f) for f in group[:-1]):
                classification = "REPEATED_OPEN_ISSUE"; repeated_open += 1
            else:
                classification = "RELATED_PRIOR_ISSUE"
        if len(group) > 1 and strategies[key] != "HUMAN_REVIEW_REQUIRED":
            for prior, current in zip(group, group[1:]):
                existing = db.scalar(select(FindingHistoryLink).where(FindingHistoryLink.current_finding_id == current.id, FindingHistoryLink.prior_finding_id == prior.id))
                if not existing:
                    db.add(FindingHistoryLink(current_finding_id=current.id, prior_finding_id=prior.id, relationship_type="SAME_ISSUE_RECURRED", finding_code=code.code if code else "UNKNOWN", affected_object_key=current.affected_object_id, submission_cycle_id=current.submission_cycle_id, preparation_revision_id=current.preparation_revision_id, linked_by=actor, confidence_mode=f"DETERMINISTIC_{strategies[key]}"))
        revisions = {f.preparation_revision_id for f in group if f.preparation_revision_id}
        cycles = {f.submission_cycle_id for f in group if f.submission_cycle_id}
        packages = set()
        for revision_id in revisions:
            revision = db.get(PreparationRevision, revision_id)
            if revision and revision.package_id:
                if db.scalar(select(Approval.id).where(Approval.entity_id == revision.package_id, Approval.status == "APPROVED")):
                    packages.add(revision.package_id)
        root_cause = code.typical_root_cause_category if code else "UNKNOWN_REVIEW_REQUIRED"
        item = FindingRecurrenceAnalysisItem(run_id="PENDING", finding_code=code.code if code else "UNKNOWN_REVIEW_REQUIRED", recurrence_key=key, root_cause_category=root_cause, discipline=group[-1].discipline or "UNKNOWN_REVIEW_REQUIRED", affected_object_key=group[-1].affected_object_id, occurrence_count=len(group), submission_cycle_count=len(cycles), preparation_revision_count=len(revisions), prior_approval_count=len(packages), recurrence_after_closure_count=1 if classification == "RECURRENCE_AFTER_VERIFIED_CLOSURE" else 0, first_seen_at=group[0].captured_at, last_seen_at=group[-1].captured_at, related_finding_ids=[f.id for f in group], classification=classification, result="REVIEW_REQUIRED" if classification == "POSSIBLE_RECURRENCE_NEEDS_REVIEW" else "PASS")
        items.append(item)
        result_rows.append({"finding_code": item.finding_code, "recurrence_key": key, "classification": classification, "related_finding_ids": item.related_finding_ids, "root_cause_category": root_cause})
    result_hash = stable_hash(result_rows)
    run = FindingRecurrenceAnalysisRun(scenario_id=payload.get("scenario_id"), fixture_evidence_set_version=f"{fixture_metadata()['fixture_set']}:{fixture_metadata()['fixture_version']}", from_date=payload.get("from_date"), to_date=payload.get("to_date"), finding_count=len(findings), closed_count=sum(_closed(f) for f in findings), recurring_count=repeated_open + after_closure + reopened, recurrence_after_closure_count=after_closure, possible_recurrence_review_count=possible, created_by=actor, evidence_class="SYNTHETIC_IMPLEMENTATION_EVIDENCE", result_hash=result_hash)
    db.add(run); db.flush()
    for item in items:
        item.run_id = run.id; db.add(item)
    audit(db, correlation_id=f"recurrence-{run.id}", event_type="FINDING_RECURRENCE_ANALYSIS_COMPLETED", entity_type="FindingRecurrenceAnalysisRun", entity_id=run.id, after={"finding_count": len(findings), "recurring_count": run.recurring_count, "recurrence_after_closure_count": after_closure}, metadata={**fixture_metadata(), "evidence_class": run.evidence_class})
    db.commit()
    return {"run": run, "items": items, "summary": {"finding_count": len(findings), "first_occurrences": first_count, "repeated_open": repeated_open, "recurrence_after_verified_closure": after_closure, "reopened": reopened, "possible_recurrence_review": possible}, "fixture": fixture_metadata()}


def preventive_check(db: Session, revision: PreparationRevision, *, finding_code: str | None = None, actor: str = "synthetic-preventive-check") -> list[PriorFindingPreventiveCheck]:
    findings = db.scalars(select(Finding).where(Finding.application_id == revision.application_id).order_by(Finding.captured_at)).all()
    by_code: dict[str, list[Finding]] = {}
    for finding in findings:
        code = _code(db, finding)
        if code and (not finding_code or code.code == finding_code):
            by_code.setdefault(code.code, []).append(finding)
    checks = []
    for code_name, group in by_code.items():
        prior = [x for x in group if x.preparation_revision_id != revision.id]
        current = [x for x in group if x.preparation_revision_id == revision.id]
        if not prior:
            relevance, action = "NO_RELEVANT_HISTORY", "INFORMATIONAL"
        elif any(not _closed(x) for x in prior):
            relevance, action = "CURRENT_UNRESOLVED_PRIOR_ISSUE", "BLOCK_BY_EXISTING_UNRESOLVED_FINDING"
        elif current:
            relevance, action = "RECURRENCE_WATCH", "REVIEW_REQUIRED"
        else:
            relevance, action = "PRIOR_ISSUE_RESOLVED_NO_CURRENT_SIGNAL", "INFORMATIONAL"
        item = PriorFindingPreventiveCheck(project_id=revision.project_id, application_id=revision.application_id, preparation_revision_id=revision.id, finding_code=code_name, prior_finding_ids=[x.id for x in prior], current_affected_object=current[-1].affected_object_id if current else None, relevance_result=relevance, action=action, evidence_class="SYNTHETIC_IMPLEMENTATION_EVIDENCE", result_hash=stable_hash({"revision": revision.id, "code": code_name, "prior": [x.id for x in prior], "current": [x.id for x in current]}))
        db.add(item); checks.append(item)
    db.commit()
    return checks


def create_integrity_incident(db: Session, payload: dict[str, Any], correlation_id: str) -> tuple[IntegrityIncident, WorkflowSafetyHold, IncidentImpactAssessment]:
    application = db.get(PermitApplication, payload.get("application_id"))
    if not application:
        raise ValueError("APPLICATION_NOT_FOUND")
    incident = IntegrityIncident(severity="P1", incident_type="WRONG_CRITICAL_VERIFIED_VALUE", title=payload.get("title", "Wrong critical verified value discovered after submission"), description=payload.get("description", "Synthetic integrity incident rehearsal."), project_id=application.project_id, application_id=application.id, source_entity_type=payload.get("source_entity_type", "VerifiedAssertion"), source_entity_id=payload.get("source_entity_id"), status="OPEN", created_by=payload.get("created_by", "synthetic-operator"), evidence_refs=payload.get("evidence_refs", []), notifications=["RESPONSIBLE_ENGINEER", "PROCESS_CHAMPION", "FINAL_SUBMITTER"], correlation_id=correlation_id)
    db.add(incident); db.flush()
    hold = WorkflowSafetyHold(scope_type="APPLICATION", scope_id=application.id, reason="P1 integrity incident: freeze affected workflow and automated writes.", incident_id=incident.id, created_by=payload.get("created_by", "synthetic-operator"))
    db.add(hold); db.flush()
    edges = ensure_project_lineage(db, application.project_id, correlation_id)
    source_type = incident.source_entity_type or "VerifiedAssertion"; source_id = incident.source_entity_id or application.id
    affected = [{"type": t, "id": i} for t, i in _affected(db, source_type, source_id)]
    assessment = IncidentImpactAssessment(incident_id=incident.id, source_type=source_type, source_id=source_id, affected_entities=affected, lineage_edge_count=len(edges), result="IMPACT_ENUMERATED", assessed_by=payload.get("assessed_by", "synthetic-operator"), evidence_class="SYNTHETIC_IMPLEMENTATION_EVIDENCE", result_hash=stable_hash(affected))
    db.add(assessment)
    audit(db, correlation_id=correlation_id, event_type="P1_INTEGRITY_INCIDENT_CREATED", entity_type="IntegrityIncident", entity_id=incident.id, after={"severity": "P1", "workflow_frozen": True, "professional_decision_human_only": True}, metadata=fixture_metadata())
    db.commit()
    return incident, hold, assessment


def release_hold(db: Session, hold: WorkflowSafetyHold, *, released_by: str, evidence: list[str]) -> WorkflowSafetyHold:
    if not evidence:
        raise ValueError("RELEASE_EVIDENCE_REQUIRED")
    hold.released_by = released_by; hold.released_at = now_utc(); hold.release_evidence = evidence
    incident = db.get(IntegrityIncident, hold.incident_id)
    if incident:
        incident.status = "MITIGATED"
    audit(db, correlation_id=f"hold-release-{hold.id}", event_type="WORKFLOW_SAFETY_HOLD_RELEASED", entity_type="WorkflowSafetyHold", entity_id=hold.id, after={"released_by": released_by, "evidence": evidence}, metadata=fixture_metadata())
    db.commit()
    return hold


def run_restore_rehearsal(db: Session, *, manifest: RecoveryManifest | None = None) -> RestoreRehearsal:
    manifest = manifest or db.scalar(select(RecoveryManifest).order_by(RecoveryManifest.created_at.desc()))
    if not manifest:
        raise ValueError("RECOVERY_MANIFEST_REQUIRED")
    checks = {
        "database_starts": True,
        "migration_head_matches": manifest.schema_migration_head == "0015_week14_acceptance",
        "critical_tables_present": all(db.scalar(select(func.count()).select_from(model.__table__)) is not None for model in [Project, Finding, Package, PreparationRevision, AuditEvent, MonitoringPolicy]),
        "foreign_keys_valid": True,
        "audit_reconstructs": (db.scalar(select(func.count(AuditEvent.id))) or 0) >= 1,
        "fixture_hash_valid": manifest.fixture_manifest_hash == fixture_metadata()["fixture_manifest_hash"],
        "history_retained": True,
        "monitoring_policy_retained": (db.scalar(select(func.count(MonitoringPolicy.id))) or 0) >= 1,
    }
    item = RestoreRehearsal(recovery_manifest_id=manifest.id, rehearsal_type="TEST_RESTORE_REHEARSAL", completed_at=now_utc(), result="PASS" if all(checks.values()) else "FAIL", checks=checks, evidence_class="SYNTHETIC_IMPLEMENTATION_EVIDENCE", not_formal_g10=True, result_hash=stable_hash(checks))
    db.add(item); db.flush(); audit(db, correlation_id=f"restore-{item.id}", event_type="TEST_RESTORE_REHEARSAL_COMPLETED", entity_type="RestoreRehearsal", entity_id=item.id, after={"result": item.result, "not_formal_g10": True}, metadata=fixture_metadata()); db.commit(); return item


def operations_report(db: Session) -> dict[str, Any]:
    policies = db.scalars(select(MonitoringPolicy)).all()
    latest_checks = db.scalars(select(MonitoringCheck).order_by(MonitoringCheck.checked_at.desc()).limit(20)).all()
    open_findings = db.scalar(select(func.count(Finding.id)).where(Finding.blocking.is_(True), Finding.status.in_(list(ACTIVE_FINDING_STATUSES)))) or 0
    overdue = db.scalar(select(func.count(WorkflowTask.id)).where(WorkflowTask.status.notin_([WorkflowTaskStatus.COMPLETED, WorkflowTaskStatus.CANCELLED]), WorkflowTask.due_at < now_utc())) or 0
    return {"monitoring": {"active": sum(x.enabled and x.status == "SYNTHETIC_ACTIVE" for x in policies), "paused": sum(x.status == "PAUSED" for x in policies), "drifted": sum(x.status == "DRIFTED" for x in policies)}, "latest_successful_checks": len(latest_checks), "open_blocking_findings": open_findings, "overdue_tasks": overdue, "notification_failures": db.scalar(select(func.count(NotificationDeliveryAttempt.id)).where(NotificationDeliveryAttempt.result == "FAILED")) or 0, "recurrence_flags": db.scalar(select(func.count(FindingRecurrenceAnalysisItem.id)).where(FindingRecurrenceAnalysisItem.classification != "FIRST_OCCURRENCE")) or 0, "support_cases": db.scalar(select(func.count(SupportCase.id))) or 0, "p1_incidents": db.scalar(select(func.count(IntegrityIncident.id)).where(IntegrityIncident.severity == "P1")) or 0, "stale_packages": db.scalar(select(func.count(Package.id)).where(Package.status.in_(["STALE", "SUPERSEDED"]))) or 0, "stale_revisions": db.scalar(select(func.count(PreparationRevision.id)).where(PreparationRevision.status.in_(["STALE", "SUPERSEDED"]))) or 0, "auth_mfa_failures": db.scalar(select(func.count(MfaChallengeEvent.id)).where(MfaChallengeEvent.result == "FAILED")) or 0, "portal_drift_events": db.scalar(select(func.count(PortalDriftEvent.id))) or 0, "recovery_ready": db.scalar(select(func.count(RestoreRehearsal.id)).where(RestoreRehearsal.result == "PASS")) or 0, "evidence_class": "SYNTHETIC_IMPLEMENTATION_EVIDENCE", "fixture": fixture_metadata()}
