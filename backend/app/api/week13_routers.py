"""Week 13 recurrence, support, incident, and recovery APIs."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..db import get_db
from ..fixtures.canonical import fixture_metadata
from ..models import *
from ..services.week13 import analyze_recurrence, create_integrity_incident, now_utc, operations_report, preventive_check, release_hold, run_restore_rehearsal
from ..services.week45 import row

router = APIRouter(prefix="/api")


def cid(request: Request) -> str:
    return getattr(request.state, "correlation_id", "week13-api")


@router.post("/recurrence/analyze")
def recurrence_analyze(payload: dict[str, Any] | None = None, request: Request = None, db: Session = Depends(get_db)):
    return {"analysis": analyze_recurrence(db, payload or {}, actor=(payload or {}).get("created_by", "synthetic-analytics")), "fixture": fixture_metadata()}


@router.get("/recurrence/analysis")
def recurrence_analysis(run_id: str | None = None, db: Session = Depends(get_db)):
    run = db.get(FindingRecurrenceAnalysisRun, run_id) if run_id else db.scalar(select(FindingRecurrenceAnalysisRun).order_by(FindingRecurrenceAnalysisRun.created_at.desc()))
    if not run:
        return {"run": None, "items": [], "fixture": fixture_metadata()}
    return {"run": row(run), "items": [row(x) for x in db.scalars(select(FindingRecurrenceAnalysisItem).where(FindingRecurrenceAnalysisItem.run_id == run.id)).all()], "fixture": fixture_metadata()}


@router.post("/preparation-revisions/{revision_id}/preventive-check")
def run_preventive_check(revision_id: str, payload: dict[str, Any] | None = None, db: Session = Depends(get_db)):
    revision = db.get(PreparationRevision, revision_id)
    if not revision: raise HTTPException(404, "Preparation revision not found")
    return {"checks": [row(x) for x in preventive_check(db, revision, finding_code=(payload or {}).get("finding_code"))], "fixture": fixture_metadata()}


@router.get("/preparation-revisions/{revision_id}/preventive-context")
def preventive_context(revision_id: str, db: Session = Depends(get_db)):
    return run_preventive_check(revision_id, {}, db)


@router.get("/support/cases")
def support_cases(db: Session = Depends(get_db)):
    return {"cases": [row(x) for x in db.scalars(select(SupportCase).order_by(SupportCase.opened_at.desc())).all()], "fixture": fixture_metadata()}


@router.post("/support/cases")
def create_support_case(payload: dict[str, Any], request: Request, db: Session = Depends(get_db)):
    item = SupportCase(severity=payload.get("severity", "P3"), category=payload.get("category", "GENERAL"), project_id=payload.get("project_id"), application_id=payload.get("application_id"), finding_id=payload.get("finding_id"), monitoring_run_id=payload.get("monitoring_run_id"), opened_by=payload.get("opened_by", "synthetic-operator"), current_level=payload.get("current_level", "L1"), assigned_to=payload.get("assigned_to"), status=payload.get("status", "OPEN"), external_dependency=payload.get("external_dependency"), correlation_id=cid(request))
    db.add(item); db.flush(); audit(db, correlation_id=cid(request), event_type="SUPPORT_CASE_OPENED", entity_type="SupportCase", entity_id=item.id, after={"level": item.current_level, "severity": item.severity}, metadata=fixture_metadata()); db.commit()
    return {"case": row(item), "fixture": fixture_metadata()}


@router.patch("/support/cases/{case_id}")
def update_support_case(case_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db)):
    item = db.get(SupportCase, case_id)
    if not item: raise HTTPException(404, "Support case not found")
    for field in ["current_level", "assigned_to", "status", "external_dependency", "resolution_summary"]:
        if field in payload: setattr(item, field, payload[field])
    if item.status == "CLOSED": item.closed_at = now_utc()
    audit(db, correlation_id=cid(request), event_type="SUPPORT_CASE_UPDATED", entity_type="SupportCase", entity_id=item.id, after={"status": item.status, "level": item.current_level}, metadata=fixture_metadata()); db.commit()
    return {"case": row(item), "fixture": fixture_metadata()}


@router.get("/incidents/integrity")
def integrity_incidents(db: Session = Depends(get_db)):
    return {"incidents": [row(x) for x in db.scalars(select(IntegrityIncident).order_by(IntegrityIncident.created_at.desc())).all()], "holds": [row(x) for x in db.scalars(select(WorkflowSafetyHold).order_by(WorkflowSafetyHold.created_at.desc())).all()], "fixture": fixture_metadata()}


@router.post("/incidents/integrity")
def create_incident(payload: dict[str, Any], request: Request, db: Session = Depends(get_db)):
    try: incident, hold, assessment = create_integrity_incident(db, payload, cid(request))
    except ValueError as exc: db.rollback(); raise HTTPException(422, str(exc))
    return {"incident": row(incident), "hold": row(hold), "impact": row(assessment), "professional_decision_human_only": True, "fixture": fixture_metadata()}


@router.post("/incidents/{incident_id}/impact-assess")
def incident_impact(incident_id: str, db: Session = Depends(get_db)):
    incident = db.get(IntegrityIncident, incident_id)
    if not incident: raise HTTPException(404, "Incident not found")
    assessment = db.scalar(select(IncidentImpactAssessment).where(IncidentImpactAssessment.incident_id == incident.id).order_by(IncidentImpactAssessment.assessed_at.desc()))
    return {"incident": row(incident), "impact": row(assessment), "fixture": fixture_metadata()}


@router.post("/workflow-safety-holds/{hold_id}/release")
def release_safety_hold(hold_id: str, payload: dict[str, Any], db: Session = Depends(get_db)):
    hold = db.get(WorkflowSafetyHold, hold_id)
    if not hold: raise HTTPException(404, "Safety hold not found")
    try: release_hold(db, hold, released_by=payload.get("released_by", "synthetic-reviewer"), evidence=payload.get("evidence", []))
    except ValueError as exc: db.rollback(); raise HTTPException(422, str(exc))
    return {"hold": row(hold), "fixture": fixture_metadata()}


@router.get("/recovery/manifests")
def recovery_manifests(db: Session = Depends(get_db)):
    return {"manifests": [row(x) for x in db.scalars(select(RecoveryManifest).order_by(RecoveryManifest.created_at.desc())).all()], "rehearsals": [row(x) for x in db.scalars(select(RestoreRehearsal).order_by(RestoreRehearsal.started_at.desc())).all()], "fixture": fixture_metadata()}


@router.post("/recovery/test-restore")
def test_restore(db: Session = Depends(get_db)):
    try: item = run_restore_rehearsal(db)
    except ValueError as exc: raise HTTPException(422, str(exc))
    return {"rehearsal": row(item), "formal_g10": False, "fixture": fixture_metadata()}


@router.get("/operations/report")
def week13_operations_report(db: Session = Depends(get_db)):
    return {"report": operations_report(db), "optional_automation_branch": "NOT_AUTHORIZED_NOT_BLOCKING", "fixture": fixture_metadata()}


@router.get("/training/checklists")
def training_checklists(db: Session = Depends(get_db)):
    return {"checklists": [row(x) for x in db.scalars(select(RoleTrainingChecklist).order_by(RoleTrainingChecklist.role)).all()], "fixture": fixture_metadata()}


@router.get("/kill-switch/readiness")
def kill_switch_readiness(db: Session = Depends(get_db)):
    return {"items": [row(x) for x in db.scalars(select(KillSwitchReadiness)).all()], "fixture": fixture_metadata()}
