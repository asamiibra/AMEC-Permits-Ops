from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import *
from ..schemas.api import *
from ..audit.service import audit
from ..services.business_case import DEFAULT_BUSINESS_CASE, calculate_business_case
from .dependencies import current_user_role
from ..services.permit_workflow import confirm_project_sources, ensure_project_sources_task, workflow_projection

router = APIRouter(prefix="/api")


def corr(request: Request) -> str: return getattr(request.state, "correlation_id", "missing-correlation-id")
def project_dict(p): return ProjectOut.model_validate(p).model_dump(mode="json")


@router.get("/projects")
def projects(db: Session = Depends(get_db)): return [project_dict(p) for p in db.scalars(select(Project).order_by(Project.project_number)).all()]


@router.post("/projects", response_model=ProjectOut)
def create_project(payload: ProjectCreate, request: Request, db: Session = Depends(get_db), role=Depends(current_user_role)):
    office = db.scalar(select(ConsultancyOffice).where(ConsultancyOffice.office_code == "QEC-DOHA"))
    if not office: raise HTTPException(500, "Seed office not found")
    p = Project(office_id=office.id, **payload.model_dump()); db.add(p); db.flush()
    audit(db, correlation_id=corr(request), event_type="PROJECT_CREATED", entity_type="Project", entity_id=p.id, actor_id=None, after=project_dict(p))
    db.commit(); db.refresh(p); return p


@router.get("/projects/{project_id}")
def project_detail(project_id: str, issue: str | None = None, db: Session = Depends(get_db)):
    p = db.get(Project, project_id)
    if not p: raise HTTPException(404, "Project not found")
    applications = [ApplicationOut.model_validate(a).model_dump(mode="json") for a in p.applications]
    application = p.applications[0] if p.applications else None
    if issue:
        finding = db.get(Finding, issue)
        if not finding:
            raise HTTPException(404, detail={"code": "ISSUE_NOT_FOUND", "issue_id": issue})
        if finding.project_id != project_id:
            raise HTTPException(409, detail={"code": "ISSUE_PROJECT_MISMATCH", "issue_id": issue, "project_id": project_id})
        target_application_id = finding.permit_id or finding.application_id
        if target_application_id:
            application = next((item for item in p.applications if item.id == target_application_id), None)
            if application is None:
                raise HTTPException(409, detail={"code": "ISSUE_APPLICATION_MISMATCH", "issue_id": issue, "project_id": project_id})
    return {**project_dict(p), "office": {"id": p.office.id, "office_code": p.office.office_code, "name_en": p.office.name_en, "name_ar": p.office.name_ar} if p.office else None, "links": [link_out(p, l) for l in p.links], "applications": applications, "workflow": workflow_projection(db, p, application) if application else None, "audit": audit_for_entity(db, "Project", p.id)}


@router.post("/projects/{project_id}/confirm-project-sources")
def confirm_project_sources_command(project_id: str, payload: dict[str, Any] | None = None, request: Request = None, db: Session = Depends(get_db), role=Depends(current_user_role)):
    payload = payload or {}
    result = confirm_project_sources(db, project_id=project_id, actor_role=role, actor_id=payload.get("actor_id") or role.value, correlation_id=corr(request), project_reference=payload.get("project_reference"))
    application = result["application"]
    return {"command": "ConfirmProjectAndSources", "result": "IDEMPOTENT" if result["idempotent"] else "COMPLETED", "project": project_dict(result["project"]), "application": ApplicationOut.model_validate(application).model_dump(mode="json"), "workflow": result["workflow"], "fixture": {"synthetic_only": True}}


def link_out(project, link):
    result = LinkOut.model_validate(link).model_dump(mode="json")
    result["mismatch"] = project.project_number not in link.external_reference and link.system_type != SystemType.MUNICIPALITY
    return result


@router.get("/projects/{project_id}/external-links")
def get_links(project_id: str, db: Session = Depends(get_db)):
    p = db.get(Project, project_id)
    if not p: raise HTTPException(404, "Project not found")
    return [link_out(p, l) for l in p.links]


@router.post("/projects/{project_id}/external-links", response_model=LinkOut)
def create_link(project_id: str, payload: LinkCreate, request: Request, db: Session = Depends(get_db), role=Depends(current_user_role)):
    p = db.get(Project, project_id)
    if not p: raise HTTPException(404, "Project not found")
    mismatch = p.project_number not in payload.external_reference and payload.system_type != SystemType.MUNICIPALITY
    if mismatch and not payload.confirm_mismatch: raise HTTPException(409, "LINK MISMATCH - USER CONFIRMATION REQUIRED")
    link = ExternalSystemLink(project_id=project_id, **payload.model_dump(exclude={"confirm_mismatch"})); db.add(link); db.flush()
    audit(db, correlation_id=corr(request), event_type="EXTERNAL_LINK_CREATED", entity_type="ExternalSystemLink", entity_id=link.id, after=LinkOut.model_validate(link).model_dump(mode="json"))
    db.commit(); db.refresh(link); out = link_out(p, link); return out


@router.get("/applications")
def applications(db: Session = Depends(get_db)): return [ApplicationOut.model_validate(a).model_dump(mode="json") for a in db.scalars(select(PermitApplication).order_by(PermitApplication.external_request_number)).all()]

@router.get("/applications/{application_id}")
def application(application_id: str, db: Session = Depends(get_db)):
    a = db.get(PermitApplication, application_id)
    if not a: raise HTTPException(404, "Application not found")
    return {**ApplicationOut.model_validate(a).model_dump(mode="json"), "comments": [{"text": "Owner name differs from supporting document.", "synthetic": True}, {"text": "Drawing revision does not match package revision.", "synthetic": True}, {"text": "Required attachment missing.", "synthetic": True}] if a.application_status == ApplicationStatus.RETURNED else [], "project": {"id": a.project.id, "project_number": a.project.project_number, "project_name": a.project.project_name}}


@router.get("/discovery/decisions", response_model=list[DecisionOut])
def decisions(db: Session = Depends(get_db)): return db.scalars(select(DiscoveryDecision).order_by(DiscoveryDecision.category, DiscoveryDecision.key)).all()

@router.patch("/discovery/decisions/{decision_id}", response_model=DecisionOut)
def update_decision(decision_id: str, payload: DecisionPatch, request: Request, db: Session = Depends(get_db), role=Depends(current_user_role)):
    item = db.get(DiscoveryDecision, decision_id)
    if not item: raise HTTPException(404, "Decision not found")
    before = DecisionOut.model_validate(item).model_dump(mode="json")
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(item, key, value)
    item.updated_at = datetime.now(timezone.utc); db.flush()
    audit(db, correlation_id=corr(request), event_type="DISCOVERY_DECISION_CHANGED", entity_type="DiscoveryDecision", entity_id=item.id, before=before, after=DecisionOut.model_validate(item).model_dump(mode="json")); db.commit(); db.refresh(item); return item


def single_values(db, model, defaults):
    item = db.scalar(select(model).limit(1))
    if not item: item = model(values_json=defaults); db.add(item); db.commit(); db.refresh(item)
    return item

@router.get("/discovery/business-case")
def business_case(db: Session = Depends(get_db)): return calculate_business_case(single_values(db, BusinessCase, DEFAULT_BUSINESS_CASE).values_json)

@router.put("/discovery/business-case")
def update_business_case(payload: ValuesPayload, request: Request, db: Session = Depends(get_db), role=Depends(current_user_role)):
    item = single_values(db, BusinessCase, DEFAULT_BUSINESS_CASE); before = item.values_json; item.values_json = {**DEFAULT_BUSINESS_CASE, **payload.values}; db.flush(); audit(db, correlation_id=corr(request), event_type="BUSINESS_CASE_CHANGED", entity_type="BusinessCase", entity_id=item.id, before=before, after=item.values_json); db.commit(); return calculate_business_case(item.values_json)

DEFAULT_VOLUME = {"applications_per_month": 25, "active_permit_preparers": 3, "average_open_applications": 18, "peak_concurrent_applications": 8, "portal_accounts": 3, "sessions_per_day": 10, "relogin_frequency": "UNKNOWN", "excel_simultaneous_users": 4}
@router.get("/discovery/volume")
def volume(db: Session = Depends(get_db)): return single_values(db, VolumeBaseline, DEFAULT_VOLUME).values_json
@router.put("/discovery/volume")
def update_volume(payload: ValuesPayload, request: Request, db: Session = Depends(get_db), role=Depends(current_user_role)):
    item = single_values(db, VolumeBaseline, DEFAULT_VOLUME); before = item.values_json; item.values_json = {**DEFAULT_VOLUME, **payload.values}; db.flush(); audit(db, correlation_id=corr(request), event_type="VOLUME_BASELINE_CHANGED", entity_type="VolumeBaseline", entity_id=item.id, before=before, after=item.values_json); db.commit(); return item.values_json

@router.get("/ministry-inquiries", response_model=list[InquiryOut])
def inquiries(db: Session = Depends(get_db)): return db.scalars(select(MinistryInquiry).order_by(MinistryInquiry.question_code)).all()
@router.patch("/ministry-inquiries/{inquiry_id}", response_model=InquiryOut)
def update_inquiry(inquiry_id: str, payload: InquiryPatch, request: Request, db: Session = Depends(get_db), role=Depends(current_user_role)):
    item = db.get(MinistryInquiry, inquiry_id)
    if not item: raise HTTPException(404, "Inquiry not found")
    before = InquiryOut.model_validate(item).model_dump(mode="json"); data = payload.model_dump(exclude_unset=True)
    for key, value in data.items(): setattr(item, key, value)
    if item.status == InquiryStatus.ASKED and not item.sent_at: item.sent_at = datetime.now(timezone.utc)
    if item.status == InquiryStatus.ANSWERED and not item.response_at: item.response_at = datetime.now(timezone.utc)
    db.flush(); audit(db, correlation_id=corr(request), event_type="MINISTRY_INQUIRY_CHANGED", entity_type="MinistryInquiry", entity_id=item.id, before=before, after=InquiryOut.model_validate(item).model_dump(mode="json")); db.commit(); return item

@router.get("/raid", response_model=list[RaidOut])
def raid(db: Session = Depends(get_db)): return db.scalars(select(RaidItem).order_by(RaidItem.type, RaidItem.title)).all()
@router.post("/raid", response_model=RaidOut)
def create_raid(payload: RaidCreate, request: Request, db: Session = Depends(get_db), role=Depends(current_user_role)):
    item = RaidItem(**payload.model_dump()); db.add(item); db.flush(); audit(db, correlation_id=corr(request), event_type="RAID_ITEM_CREATED", entity_type="RaidItem", entity_id=item.id, after=RaidOut.model_validate(item).model_dump(mode="json")); db.commit(); db.refresh(item); return item
@router.patch("/raid/{item_id}", response_model=RaidOut)
def update_raid(item_id: str, payload: RaidCreate, request: Request, db: Session = Depends(get_db), role=Depends(current_user_role)):
    item = db.get(RaidItem, item_id)
    if not item: raise HTTPException(404, "RAID item not found")
    before = RaidOut.model_validate(item).model_dump(mode="json")
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(item, key, value)
    db.flush(); audit(db, correlation_id=corr(request), event_type="RAID_ITEM_CHANGED", entity_type="RaidItem", entity_id=item.id, before=before, after=RaidOut.model_validate(item).model_dump(mode="json")); db.commit(); return item

@router.get("/audit", response_model=list[AuditOut])
def audit_events(db: Session = Depends(get_db)): return db.scalars(select(AuditEvent).order_by(AuditEvent.occurred_at.desc()).limit(200)).all()

def audit_for_entity(db, entity_type, entity_id): return [AuditOut.model_validate(a).model_dump(mode="json") for a in db.scalars(select(AuditEvent).where(AuditEvent.entity_type == entity_type, AuditEvent.entity_id == entity_id).order_by(AuditEvent.occurred_at.desc())).all()]
