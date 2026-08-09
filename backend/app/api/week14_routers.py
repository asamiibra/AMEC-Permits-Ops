"""Week 14 acceptance rehearsal and G10 evidence APIs."""

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..fixtures.canonical import fixture_metadata
from ..models import *
from ..services.week14 import create_g10_evidence, production_mode, run_acceptance_rehearsal
from ..services.week45 import row

router = APIRouter(prefix="/api")


@router.post("/acceptance-rehearsal")
def acceptance_rehearsal(payload: dict[str, Any] | None = None, request: Request = None, db: Session = Depends(get_db)):
    result = run_acceptance_rehearsal(db, actor=(payload or {}).get("actor", "synthetic-acceptance-operator"), operator_assistance_required=bool((payload or {}).get("operator_assistance_required", False)))
    return {"rehearsal": row(result["run"]), "checks": result["checks"], "safety": result["safety"], "metrics": [row(x) for x in result["metrics"]], "edge_coverage": result["edge_coverage"], "fixture": fixture_metadata()}


@router.get("/acceptance-rehearsals")
def acceptance_rehearsals(db: Session = Depends(get_db)):
    return {"rehearsals": [row(x) for x in db.scalars(select(AcceptanceRehearsalRun).order_by(AcceptanceRehearsalRun.started_at.desc())).all()], "fixture": fixture_metadata()}


@router.get("/acceptance-rehearsals/{run_id}")
def acceptance_rehearsal_detail(run_id: str, db: Session = Depends(get_db)):
    run = db.get(AcceptanceRehearsalRun, run_id)
    if not run: return {"detail": "Acceptance rehearsal not found"}
    return {"rehearsal": row(run), "metrics": [row(x) for x in db.scalars(select(AcceptanceMetric).where(AcceptanceMetric.rehearsal_run_id == run.id)).all()], "fixture": fixture_metadata()}


@router.get("/g10/evidence")
def g10_evidence(db: Session = Depends(get_db)):
    return {"items": [row(x) for x in create_g10_evidence(db)], "formal_g10": False, "fixture": fixture_metadata()}


@router.get("/production-mode")
def selected_production_mode(db: Session = Depends(get_db)):
    return {"decision": row(production_mode(db)), "formal_g10": False, "live_authorized": False, "fixture": fixture_metadata()}


@router.get("/role-readiness")
def role_readiness(db: Session = Depends(get_db)):
    return {"matrix": [row(x) for x in db.scalars(select(RoleReadinessMatrix).order_by(RoleReadinessMatrix.role)).all()], "client_approval": "BLOCKED_EXTERNAL", "fixture": fixture_metadata()}


@router.get("/pilot/workflow-approvals")
def pilot_workflow_approvals(db: Session = Depends(get_db)):
    return {"approvals": [row(x) for x in db.scalars(select(PilotWorkflowApproval).order_by(PilotWorkflowApproval.role)).all()], "client_approval": "BLOCKED_EXTERNAL", "fixture": fixture_metadata()}


@router.get("/shadow-defects")
def shadow_defects(db: Session = Depends(get_db)):
    items = db.scalars(select(ShadowDefectDisposition).order_by(ShadowDefectDisposition.severity, ShadowDefectDisposition.defect_id)).all()
    return {"defects": [row(x) for x in items], "open_p1": sum(x.severity == "P1" and x.status == "OPEN" for x in items), "open_p2": sum(x.severity == "P2" and x.status == "OPEN" for x in items), "fixture": fixture_metadata()}

