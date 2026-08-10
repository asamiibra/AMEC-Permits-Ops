"""Canonical AMEC Work list and KPI endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..api.dependencies import current_user_role
from ..db import get_db
from ..models import Role
from ..services.work_projection import project_work

router = APIRouter(prefix="/api/work", tags=["amec-work"])


def _projection(team: str | None, domain: str | None, kpi: str | None, db: Session, role: Role):
    return project_work(db, role=role.value, team=team, domain=domain, kpi=kpi)


@router.get("")
def work(team: str | None = None, domain: str | None = None, kpi: str | None = None,
         db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    return _projection(team, domain, kpi, db, role)


@router.get("/summary")
def work_summary(team: str | None = None, domain: str | None = None,
                 db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    result = _projection(team, domain, None, db, role)
    return {"persona": result["persona"], "filters": result["filters"], "summary": result["summary"], "total_visible": result["total_visible"], "projection": result["projection"]}
