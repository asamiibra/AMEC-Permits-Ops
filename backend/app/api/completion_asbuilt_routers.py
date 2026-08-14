"""Completion / As-Built workflow over the canonical regulatory runtime."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..db import get_db
from ..models import *
from .dependencies import current_user_role


router = APIRouter(prefix="/api/completion", tags=["completion-asbuilt"])
OWNER_ROLES = {Role.SYSTEM_ADMIN, Role.OWNER_SPONSOR}
ENGINEERING_ROLES = OWNER_ROLES | {Role.RESPONSIBLE_ENGINEER}
REVIEW_ROLES = ENGINEERING_ROLES | {Role.REQUIREMENT_STEWARD, Role.PERMIT_PREPARER}


def _actor(role: Role) -> str:
    return role.value


def _require(role: Role, allowed: set[Role]) -> None:
    if role not in allowed:
        raise HTTPException(403, {"code": "CAPABILITY_DENIED", "capability": "COMPLETION_AS_BUILT"})


def _row(item: Any) -> dict[str, Any]:
    return jsonable_encoder({column.name: getattr(item, column.name) for column in item.__table__.columns})


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(jsonable_encoder(value), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _case_link(db: Session, case_id: str) -> CompletionCaseLink:
    link = db.scalar(select(CompletionCaseLink).where(CompletionCaseLink.authority_case_id == case_id))
    if not link:
        raise HTTPException(404, "Completion case not found")
    return link


def _case_project(db: Session, case_id: str) -> Project:
    link = _case_link(db, case_id)
    project = db.get(Project, link.project_id)
    if not project:
        raise HTTPException(404, "Completion project not found")
    return project


def _execution(db: Session, execution_id: str) -> ConstructionExecution:
    execution = db.get(ConstructionExecution, execution_id)
    if not execution:
        raise HTTPException(404, "Construction execution not found")
    return execution


def _audit(db: Session, request: Request, event: str, entity_type: str, entity_id: str, role: Role, after: Any, before: Any = None) -> None:
    audit(db, correlation_id=getattr(request.state, "correlation_id", "completion-missing"), event_type=event, entity_type=entity_type, entity_id=entity_id, actor_id=_actor(role), before=before, after=after, metadata={"synthetic_only": True, "completion_boundary": True})


class StartCompletionRequest(BaseModel):
    project_id: str
    construction_execution_id: str
    subject_type: str = "Project"
    subject_id: str | None = None
    service_type_id: str | None = None
    external_body_id: str | None = None
    jurisdiction_id: str | None = None
    idempotency_key: str


class BuildingAssetRequest(BaseModel):
    asset_ref: str
    name: str
    property_id: str | None = None
    building_type: str | None = None


class BuildingSnapshotRequest(BaseModel):
    building_asset_id: str
    snapshot_type: str = "AS_BUILT"
    snapshot_ref: str | None = None
    values_json: dict[str, Any] = Field(default_factory=dict)
    verified_assertion_ids: list[str] = Field(default_factory=list)
    source_document_version_ids: list[str] = Field(default_factory=list)
    verified_by: str | None = None


class AsBuiltRevisionRequest(BaseModel):
    deliverable_id: str | None = None
    deliverable_ref: str | None = None
    title: str = "As-Built Engineering Deliverable"
    discipline: str = "GENERAL"
    revision_code: str = "AB-1"
    document_version_id: str | None = None
    rendition_kind: str = "PUBLISHED"
    content_hash: str | None = None


class ReviewRequest(BaseModel):
    status: str
    finding_description: str | None = None
    severity: str = "MAJOR"
    credential_reference: str = "SYNTHETIC-PROFESSIONAL-CREDENTIAL"
    approver_party_id: str | None = None
    professional_credential_id: str | None = None


class BaselineMemberRequest(BaseModel):
    engineering_revision_id: str | None = None
    rendition_id: str | None = None
    document_version_id: str | None = None
    building_snapshot_id: str | None = None
    member_role: str = "AS_BUILT_ENGINEERING"
    pinned_hash: str | None = None


class BaselineRequest(BaseModel):
    baseline_ref: str = "AB-1"
    source_construction_design_snapshot_id: str | None = None
    members: list[BaselineMemberRequest] = Field(default_factory=list)
    scope_json: dict[str, Any] = Field(default_factory=dict)
    supersedes_baseline_id: str | None = None


class ComparisonRequest(BaseModel):
    baseline_id: str
    approved_snapshot_id: str
    as_built_snapshot_id: str
    rule_version: str = "ASBUILT-COMPARE-1.0"


class VarianceDispositionRequest(BaseModel):
    disposition: str
    reason: str
    requires_design_change: bool = False
    requires_authority_modification: bool = False
    design_change_request_id: str | None = None


class EvidenceRequest(BaseModel):
    evidence_kind: str = "DOCUMENT"
    document_version_id: str | None = None
    status: str = "CANDIDATE"
    reason: str = "Human-selected candidate evidence"
    details_json: dict[str, Any] = Field(default_factory=dict)
    physical_description: str | None = None
    physical_status: str | None = None
    item_type: str | None = None
    location: str | None = None
    custodian: str | None = None


class FormRequest(BaseModel):
    master_content_item_id: str
    source_document_version_id: str
    profile_id: str
    mapping_release_id: str | None = None
    resolved_values: dict[str, Any] = Field(default_factory=dict)
    mode: str = "AUTO"


class SignatureRequest(BaseModel):
    form_instance_id: str
    signer_refs: list[str] = Field(default_factory=list)


class ReportRequest(BaseModel):
    template_version_id: str | None = None
    artifact_type: str = "COMPLETION_READINESS_REPORT"
    narrative: str | None = None


class PreparationRequest(BaseModel):
    policy_version_id: str | None = None
    case_party_snapshot_id: str | None = None


class PackageItemRequest(BaseModel):
    item_type: str
    requirement_instance_id: str | None = None
    evidence_selection_id: str | None = None
    document_version_id: str | None = None
    form_instance_id: str | None = None
    physical_evidence_item_id: str | None = None
    baseline_id: str | None = None
    baseline_member_id: str | None = None
    as_built_baseline_id: str | None = None
    label: str | None = None


class SubmitRequest(BaseModel):
    preparation_revision_id: str
    submission_package_id: str
    precheck_run_id: str
    channel_code: str = "MANUAL_AUTHORITY_CHANNEL"
    idempotency_key: str


class ConfirmRequest(BaseModel):
    external_reference: str
    evidence_document_version_id: str | None = None
    notes: str | None = None


class FindingRequest(BaseModel):
    submission_cycle_id: str | None = None
    category: str = "OTHER"
    title: str
    raw_text: str
    severity: str = "UNSPECIFIED"
    engineering_impact: str = "UNKNOWN"
    affected_requirement_instance_id: str | None = None


class ResponseRequest(BaseModel):
    response_text: str
    supporting_evidence_json: dict[str, Any] = Field(default_factory=dict)


class OutcomeRequest(BaseModel):
    submission_cycle_id: str
    external_identifier: str
    source_document_version_id: str | None = None
    issued_at: datetime | None = None
    outcome_type: str = "COMPLETION_CERTIFICATE"


def _completion_context(db: Session, execution: ConstructionExecution, actor: str) -> ConstructionCompletionContext:
    existing = db.scalar(select(ConstructionCompletionContext).where(ConstructionCompletionContext.construction_execution_id == execution.id))
    if existing:
        return existing
    if execution.work_state not in {"WORK_STOPPED", "COMPLETED", "WORK_COMPLETION_RECORDED", "POSTPONED"}:
        raise HTTPException(409, {"code": "CONSTRUCTION_COMPLETION_CANDIDATE_REQUIRED", "work_state": execution.work_state})
    issues = db.scalars(select(ConstructionIssue).where(ConstructionIssue.construction_execution_id == execution.id, ConstructionIssue.status.in_({"OPEN", "BLOCKED"}))).all()
    obligations = db.scalars(select(ConstructionObligationInstance).where(ConstructionObligationInstance.construction_execution_id == execution.id, ConstructionObligationInstance.status.notin_({"COMPLETED", "SATISFIED"}))).all()
    inspections = db.scalars(select(ConstructionInspection).where(ConstructionInspection.construction_execution_id == execution.id)).all()
    materials = db.scalars(select(EngineeringMaterialTest).where(EngineeringMaterialTest.project_id == execution.project_id)).all()
    physical = db.scalars(select(PhysicalEvidenceItem).where(PhysicalEvidenceItem.authority_case_id == execution.authority_case_id)).all() if execution.authority_case_id else []
    assignments = db.scalars(select(ConstructionPartyAssignment).where(ConstructionPartyAssignment.construction_execution_id == execution.id, ConstructionPartyAssignment.status == "ACTIVE")).all()
    snapshot = {"execution_id": execution.id, "work_state": execution.work_state, "current_authority_snapshot_id": execution.current_authority_snapshot_id, "current_design_snapshot_id": execution.current_design_snapshot_id, "open_issue_ids": [x.id for x in issues], "open_obligation_ids": [x.id for x in obligations], "inspection_ids": [x.id for x in inspections], "material_test_ids": [x.id for x in materials], "physical_evidence_ids": [x.id for x in physical], "party_ids": [x.party_id for x in assignments]}
    context = ConstructionCompletionContext(project_id=execution.project_id, construction_execution_id=execution.id, authority_approved_design_snapshot_id=execution.current_authority_snapshot_id, construction_design_snapshot_id=execution.current_design_snapshot_id, work_state=execution.work_state, open_issue_ids=[x.id for x in issues], open_obligation_ids=[x.id for x in obligations], inspection_ids=[x.id for x in inspections], material_test_ids=[x.id for x in materials], physical_evidence_ids=[x.id for x in physical], party_snapshot=[_row(x) for x in assignments], source_snapshot_json=snapshot, context_hash=_hash(snapshot), created_by=actor)
    db.add(context)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(ConstructionCompletionContext).where(ConstructionCompletionContext.construction_execution_id == execution.id))
        if existing:
            return existing
        raise
    return context


def _resolve_regulatory_context(db: Session, project: Project, payload: StartCompletionRequest, actor: str) -> tuple[ServiceType, ExternalBody, Jurisdiction]:
    service = db.get(ServiceType, payload.service_type_id) if payload.service_type_id else db.scalar(select(ServiceType).where(ServiceType.code == "BUILDING_COMPLETION"))
    body = db.get(ExternalBody, payload.external_body_id) if payload.external_body_id else db.scalar(select(ExternalBody).where(ExternalBody.code == "QATAR_MUNICIPALITY"))
    jurisdiction = db.get(Jurisdiction, payload.jurisdiction_id) if payload.jurisdiction_id else db.scalar(select(Jurisdiction).where(Jurisdiction.code == "QATAR"))
    if not (service and body and jurisdiction):
        raise HTTPException(409, {"code": "COMPLETION_REGULATORY_CONTEXT_NOT_CONFIGURED", "required": ["ServiceType", "ExternalBody", "Jurisdiction"]})
    return service, body, jurisdiction


@router.get("")
def list_completion(db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, REVIEW_ROLES | OWNER_ROLES)
    links = db.scalars(select(CompletionCaseLink).order_by(CompletionCaseLink.started_at.desc())).all()
    output = []
    for link in links:
        case = db.get(AuthorityCase, link.authority_case_id)
        project = db.get(Project, link.project_id)
        readiness = _readiness(db, link, persist=False)
        output.append({"id": link.authority_case_id, "completion_link_id": link.id, "project_id": link.project_id, "project_number": project.project_number if project else None, "project_name": project.project_name if project else None, "case_reference": case.case_reference if case else None, "subject_type": link.subject_type, "subject_id": link.subject_id, "status": case.status if case else link.status, "stage": readiness["stage"], "readiness": readiness["result"]})
    return output


@router.post("/start")
def start_completion(payload: StartCompletionRequest, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES)
    existing = db.scalar(select(CompletionCaseLink).where(CompletionCaseLink.idempotency_key == payload.idempotency_key))
    if existing:
        return workspace(existing.authority_case_id, request, db, role)
    project = db.get(Project, payload.project_id)
    execution = _execution(db, payload.construction_execution_id)
    if not project or execution.project_id != payload.project_id:
        raise HTTPException(409, "PROJECT_ISOLATION_VIOLATION")
    context = _completion_context(db, execution, _actor(role))
    subject_id = payload.subject_id or project.id
    if payload.subject_type == "BuildingAsset":
        asset = db.get(BuildingAsset, subject_id)
        if not asset or asset.project_id != project.id:
            raise HTTPException(404, "BUILDING_ASSET_NOT_FOUND")
    elif payload.subject_type != "Project" or subject_id != project.id:
        raise HTTPException(422, "UNSUPPORTED_COMPLETION_SUBJECT")
    service, body, jurisdiction = _resolve_regulatory_context(db, project, payload, _actor(role))
    journey_code = f"{project.project_number}-COMPLETION-{service.code}"
    journey = db.scalar(select(RegulatoryJourney).where(RegulatoryJourney.journey_code == journey_code))
    if not journey:
        journey = RegulatoryJourney(journey_code=journey_code, project_id=project.id, service_type_id=service.id, jurisdiction_id=jurisdiction.id, external_body_id=body.id, status="OPEN", opened_at=_now(), created_by=_actor(role)); db.add(journey); db.flush()
    case = AuthorityCase(case_reference=f"COMP-{project.project_number}-{str(uuid4())[:8].upper()}", regulatory_journey_id=journey.id, external_body_id=body.id, service_type_id=service.id, jurisdiction_id=jurisdiction.id, status="PREPARING", subject_type=payload.subject_type, subject_id=subject_id, opened_at=_now(), created_by=_actor(role)); db.add(case); db.flush()
    db.add(AuthorityCaseSubject(authority_case_id=case.id, subject_type=payload.subject_type, subject_id=subject_id, subject_snapshot_json={"project_id": project.id, "project_number": project.project_number, "subject_type": payload.subject_type, "subject_id": subject_id}, created_by=_actor(role)))
    if execution.authority_case_id:
        db.add(RegulatoryRelation(source_type="AuthorityCase", source_id=case.id, relation_type="REQUIRES_APPROVAL_FROM", target_type="AuthorityCase", target_id=execution.authority_case_id))
    db.add(RegulatoryRelation(source_type="AuthorityCase", source_id=case.id, relation_type="DEPENDS_ON", target_type="ConstructionExecution", target_id=execution.id))
    link = CompletionCaseLink(project_id=project.id, construction_execution_id=execution.id, construction_completion_context_id=context.id, authority_case_id=case.id, subject_type=payload.subject_type, subject_id=subject_id, idempotency_key=payload.idempotency_key, started_by=_actor(role))
    db.add(link)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(CompletionCaseLink).where(CompletionCaseLink.idempotency_key == payload.idempotency_key))
        if existing:
            return workspace(existing.authority_case_id, request, db, role)
        raise
    _audit(db, request, "COMPLETION_CASE_STARTED", "AuthorityCase", case.id, role, {"project_id": project.id, "construction_execution_id": execution.id, "subject_type": payload.subject_type, "auto_created": False})
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(CompletionCaseLink).where(CompletionCaseLink.idempotency_key == payload.idempotency_key))
        if existing:
            return workspace(existing.authority_case_id, request, db, role)
        raise
    return workspace(case.id, request, db, role)


@router.post("/building-assets")
def create_building_asset(payload: BuildingAssetRequest, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, ENGINEERING_ROLES)
    project = db.get(Project, payload.property_id) if False else None
    raise HTTPException(422, "BUILDING_ASSET_REQUIRES_COMPLETION_CASE_SCOPE")


@router.post("/{case_id}/building-assets")
def add_building_asset(case_id: str, payload: BuildingAssetRequest, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, ENGINEERING_ROLES)
    project = _case_project(db, case_id)
    if payload.property_id:
        prop = db.get(Property, payload.property_id)
        if not prop or prop.project_id != project.id:
            raise HTTPException(409, "PROPERTY_PROJECT_MISMATCH")
    existing = db.scalar(select(BuildingAsset).where(BuildingAsset.project_id == project.id, BuildingAsset.asset_ref == payload.asset_ref))
    if existing:
        return _row(existing)
    asset = BuildingAsset(project_id=project.id, property_id=payload.property_id, asset_ref=payload.asset_ref, name=payload.name, building_type=payload.building_type, created_by=_actor(role)); db.add(asset); db.commit(); db.refresh(asset); return _row(asset)


@router.post("/{case_id}/building-snapshots")
def create_building_snapshot(case_id: str, payload: BuildingSnapshotRequest, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, ENGINEERING_ROLES)
    project = _case_project(db, case_id)
    asset = db.get(BuildingAsset, payload.building_asset_id)
    if not asset or asset.project_id != project.id:
        raise HTTPException(404, "BUILDING_ASSET_NOT_FOUND")
    if payload.snapshot_type not in {"PROPOSED", "AUTHORITY_APPROVED", "AS_BUILT"}:
        raise HTTPException(422, "INVALID_BUILDING_SNAPSHOT_TYPE")
    if payload.snapshot_type == "AS_BUILT" and not (payload.verified_by or "").strip():
        raise HTTPException(422, "AS_BUILT_VERIFICATION_REQUIRED")
    version = (db.scalar(select(func.max(BuildingSnapshot.version_number)).where(BuildingSnapshot.building_asset_id == asset.id, BuildingSnapshot.snapshot_type == payload.snapshot_type)) or 0) + 1
    values = {"values": payload.values_json, "verified_by": payload.verified_by, "snapshot_type": payload.snapshot_type, "asset_id": asset.id, "version": version}
    snapshot = BuildingSnapshot(project_id=project.id, building_asset_id=asset.id, snapshot_type=payload.snapshot_type, version_number=version, snapshot_ref=payload.snapshot_ref or f"{asset.asset_ref}-{payload.snapshot_type}-{version}", values_json=payload.values_json, verified_assertion_ids=payload.verified_assertion_ids, source_document_version_ids=payload.source_document_version_ids, snapshot_hash=_hash(values), created_by=payload.verified_by or _actor(role)); db.add(snapshot); db.flush(); _audit(db, request, "BUILDING_SNAPSHOT_CREATED", "BuildingSnapshot", snapshot.id, role, {"snapshot_type": payload.snapshot_type, "verified_by": payload.verified_by, "immutable": True}); db.commit(); return _row(snapshot)


@router.post("/{case_id}/as-built/revisions")
def create_as_built_revision(case_id: str, payload: AsBuiltRevisionRequest, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, ENGINEERING_ROLES)
    project = _case_project(db, case_id)
    deliverable = db.get(EngineeringDeliverable, payload.deliverable_id) if payload.deliverable_id else None
    if deliverable and deliverable.project_id != project.id:
        raise HTTPException(409, "PROJECT_ISOLATION_VIOLATION")
    if not deliverable:
        work = EngineeringWorkPackage(project_id=project.id, package_ref=f"ASBUILT-{str(uuid4())[:8].upper()}", title="As-Built Completion Package", discipline=payload.discipline, owner_actor=_actor(role)); db.add(work); db.flush()
        deliverable = EngineeringDeliverable(project_id=project.id, work_package_id=work.id, deliverable_ref=payload.deliverable_ref or f"ASBUILT-{str(uuid4())[:8].upper()}", title=payload.title, discipline=payload.discipline, deliverable_type="AS_BUILT", status="DRAFT", created_by=_actor(role)); db.add(deliverable); db.flush()
    sequence = (db.scalar(select(func.max(EngineeringDeliverableRevision.sequence)).where(EngineeringDeliverableRevision.deliverable_id == deliverable.id)) or 0) + 1
    revision = EngineeringDeliverableRevision(project_id=project.id, deliverable_id=deliverable.id, revision_code=payload.revision_code, sequence=sequence, title=payload.title, issue_purpose="AS_BUILT", status="DRAFT", approval_status="NOT_APPROVED", prepared_by=_actor(role)); db.add(revision); db.flush()
    rendition = None
    if payload.document_version_id:
        document = db.get(DocumentVersion, payload.document_version_id)
        if not document:
            raise HTTPException(404, "DOCUMENT_VERSION_NOT_FOUND")
        rendition = EngineeringRendition(project_id=project.id, revision_id=revision.id, document_version_id=document.id, rendition_kind=payload.rendition_kind, content_hash=payload.content_hash or document.sha256, created_by=_actor(role)); db.add(rendition)
    deliverable.current_revision_id = revision.id
    _audit(db, request, "AS_BUILT_REVISION_CREATED", "EngineeringDeliverableRevision", revision.id, role, {"issue_purpose": "AS_BUILT", "document_version_id": payload.document_version_id})
    db.commit(); db.refresh(revision)
    return {"revision": _row(revision), "rendition": _row(rendition) if rendition else None}


@router.post("/{case_id}/as-built/revisions/{revision_id}/review")
def review_as_built_revision(case_id: str, revision_id: str, payload: ReviewRequest, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, ENGINEERING_ROLES)
    project = _case_project(db, case_id)
    revision = db.get(EngineeringDeliverableRevision, revision_id)
    if not revision or revision.project_id != project.id or payload.status not in {"BLOCKED", "APPROVED"}:
        raise HTTPException(422, "INVALID_AS_BUILT_REVIEW")
    review = ProjectEngineeringReview(project_id=project.id, revision_id=revision.id, review_number=(db.scalar(select(func.count()).select_from(ProjectEngineeringReview).where(ProjectEngineeringReview.revision_id == revision.id)) or 0) + 1, status=payload.status, started_by=_actor(role), completed_by=_actor(role), completed_at=_now()); db.add(review); db.flush()
    finding = None
    if payload.status == "BLOCKED":
        finding = EngineeringReviewFinding(project_id=project.id, review_id=review.id, finding_ref=f"AB-F-{str(uuid4())[:8].upper()}", severity=payload.severity, status="OPEN", description=payload.finding_description or "As-Built review finding requires correction"); db.add(finding); revision.status = "REVIEW_BLOCKED"
    else:
        open_finding = db.scalar(select(EngineeringReviewFinding).join(ProjectEngineeringReview, ProjectEngineeringReview.id == EngineeringReviewFinding.review_id).where(ProjectEngineeringReview.revision_id == revision.id, EngineeringReviewFinding.status == "OPEN"))
        if open_finding:
            raise HTTPException(409, "OPEN_AS_BUILT_REVIEW_FINDING")
        approval = EngineeringProfessionalApproval(project_id=project.id, revision_id=revision.id, approval_type="AS_BUILT_PROFESSIONAL_APPROVAL", status="APPROVED", approver_actor=_actor(role), approver_party_id=payload.approver_party_id, professional_credential_id=payload.professional_credential_id, credential_reference=payload.credential_reference, approved_at=_now(), reason="Human professional As-Built review approval"); db.add(approval); revision.status = "APPROVED"; revision.approval_status = "APPROVED"; revision.immutable_at = _now()
    _audit(db, request, "AS_BUILT_PROFESSIONAL_REVIEW", "EngineeringDeliverableRevision", revision.id, role, {"status": payload.status, "professional_approval": payload.status == "APPROVED"})
    db.commit(); return {"review": _row(review), "finding": _row(finding) if finding else None, "revision": _row(revision)}


@router.post("/{case_id}/as-built/baselines")
def create_as_built_baseline(case_id: str, payload: BaselineRequest, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, ENGINEERING_ROLES)
    link = _case_link(db, case_id); project = _case_project(db, case_id)
    members_payload = payload.members
    if not members_payload:
        raise HTTPException(422, "AS_BUILT_BASELINE_MEMBER_REQUIRED")
    revision_ids = [x.engineering_revision_id for x in members_payload if x.engineering_revision_id]
    revisions = db.scalars(select(EngineeringDeliverableRevision).where(EngineeringDeliverableRevision.id.in_(revision_ids), EngineeringDeliverableRevision.project_id == project.id)).all() if revision_ids else []
    if len(revisions) != len(set(revision_ids)) or any(x.approval_status != "APPROVED" for x in revisions):
        raise HTTPException(409, "PROFESSIONAL_AS_BUILT_APPROVAL_REQUIRED")
    member_data = [jsonable_encoder(x.model_dump()) for x in members_payload]
    baseline = AsBuiltBaseline(project_id=project.id, construction_execution_id=link.construction_execution_id, authority_case_id=case_id, source_construction_design_snapshot_id=payload.source_construction_design_snapshot_id, baseline_ref=payload.baseline_ref, version_number=(db.scalar(select(func.max(AsBuiltBaseline.version_number)).where(AsBuiltBaseline.project_id == project.id, AsBuiltBaseline.construction_execution_id == link.construction_execution_id)) or 0) + 1, scope_json=payload.scope_json, manifest_hash=_hash(member_data), created_by=_actor(role), supersedes_baseline_id=payload.supersedes_baseline_id); db.add(baseline); db.flush()
    members = []
    for item in members_payload:
        if item.building_snapshot_id:
            snapshot = db.get(BuildingSnapshot, item.building_snapshot_id)
            if not snapshot or snapshot.project_id != project.id or snapshot.snapshot_type != "AS_BUILT":
                raise HTTPException(409, "AS_BUILT_BUILDING_SNAPSHOT_REQUIRED")
        member = AsBuiltBaselineMember(project_id=project.id, baseline_id=baseline.id, engineering_revision_id=item.engineering_revision_id, rendition_id=item.rendition_id, document_version_id=item.document_version_id, building_snapshot_id=item.building_snapshot_id, member_role=item.member_role, pinned_hash=item.pinned_hash or _hash(item.model_dump())); db.add(member); members.append(member)
    _audit(db, request, "AS_BUILT_BASELINE_CREATED", "AsBuiltBaseline", baseline.id, role, {"version": baseline.version_number, "member_count": len(members)})
    db.commit(); return {"baseline": _row(baseline), "members": [_row(x) for x in members]}


@router.post("/{case_id}/as-built/baselines/{baseline_id}/approve")
def approve_as_built_baseline(case_id: str, baseline_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES)
    project = _case_project(db, case_id); baseline = db.get(AsBuiltBaseline, baseline_id)
    if not baseline or baseline.project_id != project.id or baseline.authority_case_id != case_id:
        raise HTTPException(404, "AS_BUILT_BASELINE_NOT_FOUND")
    if baseline.status != "DRAFT":
        return _row(baseline)
    if not db.scalar(select(AsBuiltBaselineMember.id).where(AsBuiltBaselineMember.baseline_id == baseline.id)):
        raise HTTPException(409, "AS_BUILT_BASELINE_MEMBER_REQUIRED")
    baseline.status = "APPROVED"; baseline.approved_by = _actor(role); baseline.approved_at = _now(); baseline.immutable_at = _now(); _audit(db, request, "AS_BUILT_BASELINE_APPROVED", "AsBuiltBaseline", baseline.id, role, {"immutable": True}); db.commit(); return _row(baseline)


@router.post("/{case_id}/comparisons")
def run_comparison(case_id: str, payload: ComparisonRequest, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, REVIEW_ROLES)
    project = _case_project(db, case_id); baseline = db.get(AsBuiltBaseline, payload.baseline_id); approved = db.get(BuildingSnapshot, payload.approved_snapshot_id); as_built = db.get(BuildingSnapshot, payload.as_built_snapshot_id)
    if not baseline or baseline.project_id != project.id or baseline.status != "APPROVED": raise HTTPException(409, "APPROVED_AS_BUILT_BASELINE_REQUIRED")
    if not approved or approved.project_id != project.id or approved.snapshot_type != "AUTHORITY_APPROVED": raise HTTPException(409, "AUTHORITY_APPROVED_SNAPSHOT_REQUIRED")
    if not as_built or as_built.project_id != project.id or as_built.snapshot_type != "AS_BUILT": raise HTTPException(409, "AS_BUILT_SNAPSHOT_REQUIRED")
    reference_fingerprint = _hash({"approved": approved.id, "as_built": as_built.id})
    existing = db.scalar(select(AsBuiltComparisonRun).where(AsBuiltComparisonRun.baseline_id == baseline.id, AsBuiltComparisonRun.reference_fingerprint == reference_fingerprint, AsBuiltComparisonRun.rule_version == payload.rule_version))
    if existing:
        return comparison_workspace(db, existing)
    approved_values = approved.values_json or {}; as_built_values = as_built.values_json or {}; keys = sorted(set(approved_values) | set(as_built_values)); differences = [(key, approved_values.get(key), as_built_values.get(key)) for key in keys if approved_values.get(key) != as_built_values.get(key)]
    run = AsBuiltComparisonRun(project_id=project.id, baseline_id=baseline.id, construction_design_snapshot_id=baseline.source_construction_design_snapshot_id, authority_approved_building_snapshot_ids=[approved.id], as_built_building_snapshot_ids=[as_built.id], reference_fingerprint=reference_fingerprint, rule_version=payload.rule_version, result="DIFFERENCE_DETECTED" if differences else "MATCH", difference_count=len(differences), created_by=_actor(role)); db.add(run); db.flush()
    variances = []
    for key, old, new in differences:
        variance = AsBuiltVariance(project_id=project.id, comparison_run_id=run.id, building_asset_id=as_built.building_asset_id, field_key=key, approved_value_json=old, as_built_value_json=new, delta_json={"approved": old, "as_built": new}, status="OPEN", category="STRUCTURED_FIELD"); db.add(variance); variances.append(variance)
    _audit(db, request, "AS_BUILT_COMPARISON_RUN", "AsBuiltComparisonRun", run.id, role, {"result": run.result, "difference_count": run.difference_count})
    db.commit(); return comparison_workspace(db, run)


def comparison_workspace(db: Session, run: AsBuiltComparisonRun) -> dict[str, Any]:
    variances = db.scalars(select(AsBuiltVariance).where(AsBuiltVariance.comparison_run_id == run.id).order_by(AsBuiltVariance.field_key)).all()
    return {"run": _row(run), "variances": [_row(x) for x in variances]}


@router.patch("/{case_id}/variances/{variance_id}/disposition")
def dispose_variance(case_id: str, variance_id: str, payload: VarianceDispositionRequest, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, ENGINEERING_ROLES)
    project = _case_project(db, case_id); variance = db.get(AsBuiltVariance, variance_id)
    if not variance or variance.project_id != project.id: raise HTTPException(404, "AS_BUILT_VARIANCE_NOT_FOUND")
    allowed = {"ACCEPTABLE_NO_ACTION", "NEEDS_DOCUMENT_CORRECTION", "NEEDS_ENGINEERING_REVIEW", "REQUIRES_DESIGN_CHANGE", "REQUIRES_AUTHORITY_MODIFICATION", "NOT_APPLICABLE"}
    if payload.disposition not in allowed: raise HTTPException(422, "INVALID_VARIANCE_DISPOSITION")
    if payload.disposition in {"REQUIRES_DESIGN_CHANGE", "REQUIRES_AUTHORITY_MODIFICATION"} and not payload.design_change_request_id: raise HTTPException(422, "DESIGN_CHANGE_REQUEST_REQUIRED")
    variance.professional_disposition = payload.disposition; variance.requires_design_change = payload.requires_design_change or payload.disposition == "REQUIRES_DESIGN_CHANGE"; variance.requires_authority_modification = payload.requires_authority_modification or payload.disposition == "REQUIRES_AUTHORITY_MODIFICATION"; variance.design_change_request_id = payload.design_change_request_id; variance.disposition_reason = payload.reason; variance.dispositioned_by = _actor(role); variance.dispositioned_at = _now(); variance.status = "DISPOSITIONED"; _audit(db, request, "AS_BUILT_VARIANCE_DISPOSITIONED", "AsBuiltVariance", variance.id, role, {"disposition": payload.disposition, "requires_design_change": variance.requires_design_change}); db.commit(); return _row(variance)


def _readiness(db: Session, link: CompletionCaseLink, persist: bool = False) -> dict[str, Any]:
    baselines = db.scalars(select(AsBuiltBaseline).where(AsBuiltBaseline.authority_case_id == link.authority_case_id).order_by(AsBuiltBaseline.version_number.desc())).all(); baseline = baselines[0] if baselines else None
    snapshots = db.scalars(select(BuildingSnapshot).where(BuildingSnapshot.project_id == link.project_id, BuildingSnapshot.snapshot_type == "AS_BUILT")).all()
    variances = db.scalars(select(AsBuiltVariance).join(AsBuiltComparisonRun).where(AsBuiltComparisonRun.baseline_id == baseline.id)).all() if baseline else []
    requirements = db.scalars(select(RequirementInstance).where(RequirementInstance.authority_case_id == link.authority_case_id)).all()
    forms = db.scalars(select(FormInstance).where(FormInstance.context_type == "COMPLETION", FormInstance.context_id == link.authority_case_id)).all()
    blockers: list[dict[str, str]] = []
    if not baseline: blockers.append({"code": "AS_BUILT_BASELINE_REQUIRED", "message": "An immutable professionally approved AsBuiltBaseline is required"})
    elif baseline.status != "APPROVED": blockers.append({"code": "AS_BUILT_BASELINE_NOT_APPROVED", "message": "AsBuiltBaseline requires human baseline approval"})
    if not snapshots: blockers.append({"code": "AS_BUILT_BUILDING_SNAPSHOT_REQUIRED", "message": "At least one verified AS_BUILT BuildingSnapshot is required"})
    if any(x.status != "DISPOSITIONED" for x in variances): blockers.append({"code": "AS_BUILT_VARIANCE_OPEN", "message": "Every approved-vs-As-Built variance needs a professional disposition"})
    if not requirements: blockers.append({"code": "COMPLETION_REQUIREMENTS_NOT_INITIALIZED", "message": "Completion requirements are not initialized"})
    for item in requirements:
        if item.applicability == "APPLICABILITY_UNKNOWN": blockers.append({"code": "APPLICABILITY_UNKNOWN", "message": item.reason})
        elif item.applicability == "APPLICABLE" and item.status not in {"SATISFIED", "WAIVED"}: blockers.append({"code": "REQUIREMENT_UNSATISFIED", "message": item.reason})
    if any(x.status == "BLOCKED" for x in forms): blockers.append({"code": "FORM_BLOCKED", "message": "Blocked/reference-only form cannot satisfy Completion package"})
    if not baseline: stage = "AS_BUILT_IN_PROGRESS"
    elif baseline.status != "APPROVED": stage = "AS_BUILT_REVIEW"
    elif any(x.status != "DISPOSITIONED" for x in variances): stage = "VARIANCE_REVIEW"
    elif not requirements or blockers: stage = "COMPLETION_REQUIREMENTS"
    else: stage = "READY_FOR_PREPARATION"
    return {"result": "READY_FOR_PREPARATION" if not blockers else "NEEDS_REVIEW", "stage": stage, "blockers": blockers, "baseline_id": baseline.id if baseline else None, "as_built_snapshot_ids": [x.id for x in snapshots], "requirement_count": len(requirements), "form_count": len(forms)}


@router.get("/{case_id}/readiness")
def completion_readiness(case_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, REVIEW_ROLES | OWNER_ROLES); link = _case_link(db, case_id); return _readiness(db, link)


@router.post("/{case_id}/requirements/initialize")
def initialize_completion_requirements(case_id: str, request: Request, payload: dict[str, Any] | None = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, REVIEW_ROLES)
    case = db.get(AuthorityCase, case_id); _case_project(db, case_id)
    if not case: raise HTTPException(404, "AUTHORITY_CASE_NOT_FOUND")
    existing = db.scalar(select(AuthorityCasePolicyBinding).where(AuthorityCasePolicyBinding.authority_case_id == case_id))
    if existing:
        items = db.scalars(select(RequirementInstance).where(RequirementInstance.authority_case_id == case_id)).all(); return {"binding": _row(existing), "policy": _row(db.get(RequirementPolicyVersion, existing.policy_version_id)), "items": [_row(x) for x in items]}
    effective_date = str((payload or {}).get("effective_date") or datetime.now(timezone.utc).date())
    policies = db.scalars(select(RequirementPolicyVersion).where(RequirementPolicyVersion.service_type_id == case.service_type_id, RequirementPolicyVersion.jurisdiction_id == case.jurisdiction_id, RequirementPolicyVersion.external_body_id == case.external_body_id, RequirementPolicyVersion.purpose == "COMPLETION_CLOSEOUT", RequirementPolicyVersion.status == "ACTIVE")).all()
    if not policies: raise HTTPException(409, {"code": "NO_POLICY", "state": "COMPLETION_REQUIREMENTS_NOT_CONFIGURED", "production_source_blocked": True})
    if len(policies) != 1: raise HTTPException(409, {"code": "AMBIGUOUS_POLICY", "policy_ids": [x.id for x in policies]})
    policy = policies[0]; binding = AuthorityCasePolicyBinding(authority_case_id=case_id, policy_version_id=policy.id, resolution_state="RESOLVED", resolved_by=_actor(role), resolution_facts={"purpose": "COMPLETION_CLOSEOUT", "effective_date": effective_date}); db.add(binding); db.flush()
    items = db.scalars(select(RequirementPolicyItem).where(RequirementPolicyItem.policy_version_id == policy.id, RequirementPolicyItem.status == "ACTIVE").order_by(RequirementPolicyItem.order_index)).all(); instances = []
    for item in items:
        instance = RequirementInstance(authority_case_id=case_id, policy_version_id=policy.id, policy_item_id=item.id, requirement_definition_id=item.requirement_definition_id, group_id=item.group_id, lifecycle_phase_id=item.phase_id, purpose="COMPLETION_CLOSEOUT", applicability="APPLICABILITY_UNKNOWN", status="MISSING", dependency_state="NOT_DUE", reason="Applicability requires governed Completion decision", source_snapshot={"policy_version": policy.version, "policy_item_id": item.id}); db.add(instance); instances.append(instance)
    case.status = "PREPARING"; db.commit(); return {"binding": _row(binding), "policy": _row(policy), "items": [_row(x) for x in instances]}


@router.post("/{case_id}/requirements/{instance_id}/evidence")
def add_completion_evidence(case_id: str, instance_id: str, payload: EvidenceRequest, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, REVIEW_ROLES)
    _case_project(db, case_id); instance = db.get(RequirementInstance, instance_id)
    if not instance or instance.authority_case_id != case_id: raise HTTPException(404, "REQUIREMENT_INSTANCE_NOT_FOUND")
    physical = None
    if payload.evidence_kind in {"PHYSICAL_SAMPLE", "SITE_ACTION"}:
        physical = PhysicalEvidenceItem(authority_case_id=case_id, requirement_instance_id=instance.id, item_type=payload.item_type or payload.evidence_kind, description=payload.physical_description or payload.reason, status=payload.physical_status or "EXPECTED", location=payload.location, custodian=payload.custodian); db.add(physical); db.flush()
        selection = CaseEvidenceSelection(authority_case_id=case_id, requirement_instance_id=instance.id, evidence_kind=payload.evidence_kind, status="SELECTED", reason=payload.reason, details_json={"physical_evidence_item_id": physical.id}, selected_by=_actor(role))
    else:
        if payload.document_version_id and not db.get(DocumentVersion, payload.document_version_id): raise HTTPException(404, "DOCUMENT_VERSION_NOT_FOUND")
        selection = CaseEvidenceSelection(authority_case_id=case_id, requirement_instance_id=instance.id, document_version_id=payload.document_version_id, evidence_kind=payload.evidence_kind, status=payload.status, reason=payload.reason, details_json=payload.details_json, selected_by=_actor(role))
    db.add(selection)
    definition = db.get(RequirementDefinition, instance.requirement_definition_id)
    requirement_code = (definition.code if definition else "").upper()
    exact_kinds = {
        "SITE_CLEANLINESS_CERTIFICATE": "AUTHORITY_CERTIFICATE",
        "SURVEY_MARK_RESTORATION": "SITE_ACTION",
        "PHYSICAL_PAINT_SAMPLE": "PHYSICAL_SAMPLE",
        "MATERIALS_CONFORMITY_CERTIFICATE": "CONFORMITY_CERTIFICATE",
    }
    exact_kind = next((kind for code, kind in exact_kinds.items() if requirement_code == code or requirement_code.startswith(f"{code}_")), None)
    evidence_is_valid = exact_kind is None or payload.evidence_kind == exact_kind
    if evidence_is_valid and (payload.status == "VERIFIED" or (physical and physical.status == "VERIFIED")):
        instance.status = "SATISFIED"; instance.applicability = "APPLICABLE"; instance.reason = "Verified evidence recorded"; instance.evaluated_by = _actor(role); instance.evaluated_at = _now()
    elif not evidence_is_valid:
        instance.reason = f"Evidence kind {payload.evidence_kind} does not satisfy {requirement_code}; governed {exact_kind} evidence is required"
    db.commit(); return {"selection": _row(selection), "physical": _row(physical) if physical else None, "requirement": _row(instance)}


@router.post("/{case_id}/forms")
def create_completion_form(case_id: str, payload: FormRequest, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, REVIEW_ROLES)
    project = _case_project(db, case_id); profile = db.get(FormAutomationProfile, payload.profile_id); source = db.get(DocumentVersion, payload.source_document_version_id)
    if not profile or not source or profile.source_document_version_id != source.id: raise HTTPException(409, "FORM_SOURCE_PROFILE_MISMATCH")
    policy = profile.writer_policy_json or {}; authority_fields = {k for k, v in policy.items() if isinstance(v, dict) and str(v.get("writer", "")).upper() in {"AUTHORITY", "AUTHORITY_ONLY"}}
    if authority_fields.intersection(payload.resolved_values): raise HTTPException(403, {"code": "AUTHORITY_ONLY_FIELD_WRITE_DENIED", "fields": sorted(authority_fields.intersection(payload.resolved_values))})
    if payload.mode == "AUTO" and profile.automation_status == "AUTOMATED_USE_READY": status = "AUTOMATED_USE_READY"
    elif payload.mode in {"MANUAL", "AUTO"} and profile.source_version_state in {"CURRENT", "SOURCE_VERIFIED"}: status = "MANUAL_USE_READY" if payload.mode == "MANUAL" else "BLOCKED"
    else: status = "BLOCKED"
    form = FormInstance(master_content_item_id=payload.master_content_item_id, source_document_version_id=source.id, profile_id=profile.id, mapping_release_id=payload.mapping_release_id, context_type="COMPLETION", context_id=case_id, resolved_values=payload.resolved_values, status=status, created_by=_actor(role)); db.add(form); db.flush(); _audit(db, request, "COMPLETION_FORM_PREPARED", "FormInstance", form.id, role, {"status": status, "source_version_id": source.id}); db.commit(); return _row(form)


@router.post("/{case_id}/approval-packets")
def create_signature_packet(case_id: str, payload: SignatureRequest, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, REVIEW_ROLES); _case_project(db, case_id); form = db.get(FormInstance, payload.form_instance_id)
    if not form or form.context_type != "COMPLETION" or form.context_id != case_id: raise HTTPException(404, "COMPLETION_FORM_NOT_FOUND")
    packet = SignaturePacket(form_instance_id=form.id, status="DRAFT", signer_refs=payload.signer_refs, created_by=_actor(role)); db.add(packet); db.commit(); db.refresh(packet); return _row(packet)


@router.post("/{case_id}/reports")
def generate_completion_report(case_id: str, payload: ReportRequest, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, REVIEW_ROLES); _case_project(db, case_id); template = db.get(TemplateVersion, payload.template_version_id) if payload.template_version_id else db.scalar(select(TemplateVersion).order_by(TemplateVersion.version))
    if not template: raise HTTPException(409, "COMPLETION_REPORT_TEMPLATE_REQUIRED")
    link = _case_link(db, case_id); baseline = db.scalar(select(AsBuiltBaseline).where(AsBuiltBaseline.authority_case_id == case_id).order_by(AsBuiltBaseline.version_number.desc())); readiness = _readiness(db, link); source = {"case_id": case_id, "baseline_id": baseline.id if baseline else None, "readiness": readiness, "narrative": payload.narrative, "template_version_id": template.id}; artifact = RenderedArtifact(template_version_id=template.id, context_type="COMPLETION_REPORT", context_id=case_id, artifact_type=payload.artifact_type, content_hash=_hash(source), storage_reference=f"synthetic://completion-reports/{case_id}/{payload.artifact_type}", status="GENERATED", render_input_hash=_hash(source), source_revision_ids=[baseline.id] if baseline else [], rendered_values=source, language="EN", synthetic_only=True); db.add(artifact); db.commit(); db.refresh(artifact); return _row(artifact)


@router.post("/{case_id}/preparations")
def create_completion_preparation(case_id: str, payload: PreparationRequest, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, REVIEW_ROLES); link = _case_link(db, case_id); project = _case_project(db, case_id); baseline = db.scalar(select(AsBuiltBaseline).where(AsBuiltBaseline.authority_case_id == case_id, AsBuiltBaseline.status == "APPROVED").order_by(AsBuiltBaseline.version_number.desc()))
    if not baseline: raise HTTPException(409, "APPROVED_AS_BUILT_BASELINE_REQUIRED")
    policy_id = payload.policy_version_id or (db.scalar(select(AuthorityCasePolicyBinding.policy_version_id).where(AuthorityCasePolicyBinding.authority_case_id == case_id)))
    sequence = (db.scalar(select(func.max(PreparationRevision.authority_revision_number)).where(PreparationRevision.authority_case_id == case_id)) or 0) + 1
    snapshot = {"completion_case_id": case_id, "construction_completion_context_id": link.construction_completion_context_id, "as_built_baseline_id": baseline.id, "as_built_snapshot_ids": [x.id for x in db.scalars(select(BuildingSnapshot).where(BuildingSnapshot.project_id == project.id, BuildingSnapshot.snapshot_type == "AS_BUILT")).all()], "comparison_ids": [x.id for x in db.scalars(select(AsBuiltComparisonRun).where(AsBuiltComparisonRun.baseline_id == baseline.id)).all()], "policy_version_id": policy_id}
    prep = PreparationRevision(project_id=project.id, application_id=None, sequence=sequence, status="WORKING", scenario_version="COMPLETION_AS_BUILT_V1", field_authority_version="COMPLETION-CANONICAL", requirement_config_version=str(policy_id or "NO_POLICY"), rendering_config_version="DASHBOARD-FORMS-CANONICAL", authority_case_id=case_id, authority_revision_number=sequence, authority_policy_version_id=policy_id, authority_approved_design_baseline_id=None, authority_state="WORKING", authority_snapshot_hash=_hash(snapshot), authority_snapshot_json=snapshot, case_party_snapshot_id=payload.case_party_snapshot_id, created_by=_actor(role)); db.add(prep); db.flush(); db.commit(); return _row(prep)


@router.post("/{case_id}/preparations/{preparation_id}/lock")
def lock_completion_preparation(case_id: str, preparation_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES); _case_project(db, case_id); prep = db.get(PreparationRevision, preparation_id)
    if not prep or prep.authority_case_id != case_id: raise HTTPException(404, "PREPARATION_NOT_FOUND")
    if prep.authority_state == "LOCKED": return _row(prep)
    prep.authority_state = "LOCKED"; prep.status = "READY_FOR_SUBMISSION"; prep.authority_locked_at = _now(); prep.authority_snapshot_hash = _hash(prep.authority_snapshot_json); _audit(db, request, "COMPLETION_PREPARATION_LOCKED", "PreparationRevision", prep.id, role, {"snapshot_hash": prep.authority_snapshot_hash}); db.commit(); return _row(prep)


@router.post("/{case_id}/packages")
def create_completion_package(case_id: str, preparation_revision_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, REVIEW_ROLES); _case_project(db, case_id); prep = db.get(PreparationRevision, preparation_revision_id)
    if not prep or prep.authority_case_id != case_id: raise HTTPException(404, "PREPARATION_NOT_FOUND")
    existing = db.scalar(select(SubmissionPackage).where(SubmissionPackage.preparation_revision_id == prep.id));
    if existing: return _row(existing)
    package = SubmissionPackage(authority_case_id=case_id, preparation_revision_id=prep.id, state="DRAFT", created_by=_actor(role)); db.add(package); db.commit(); db.refresh(package); return _row(package)


@router.post("/{case_id}/packages/{package_id}/items")
def add_completion_package_item(case_id: str, package_id: str, payload: PackageItemRequest, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, REVIEW_ROLES); project = _case_project(db, case_id); package = db.get(SubmissionPackage, package_id)
    if not package or package.authority_case_id != case_id: raise HTTPException(404, "SUBMISSION_PACKAGE_NOT_FOUND")
    if package.state != "DRAFT": raise HTTPException(409, "LOCKED_PACKAGE_IMMUTABLE")
    order = (db.scalar(select(func.max(SubmissionPackageItem.display_order)).where(SubmissionPackageItem.package_id == package.id)) or 0) + 1
    as_built_baseline = db.get(AsBuiltBaseline, payload.as_built_baseline_id) if payload.as_built_baseline_id else None
    if as_built_baseline and (as_built_baseline.project_id != project.id or as_built_baseline.authority_case_id != case_id):
        raise HTTPException(409, "AS_BUILT_BASELINE_PROJECT_MISMATCH")
    item = SubmissionPackageItem(package_id=package.id, item_type=payload.item_type, requirement_instance_id=payload.requirement_instance_id, evidence_selection_id=payload.evidence_selection_id, document_version_id=payload.document_version_id, form_instance_id=payload.form_instance_id, physical_evidence_item_id=payload.physical_evidence_item_id, baseline_id=payload.baseline_id, baseline_member_id=payload.baseline_member_id, as_built_baseline_id=payload.as_built_baseline_id, display_order=order, label=payload.label); db.add(item); db.commit(); db.refresh(item); return _row(item)


@router.post("/{case_id}/packages/{package_id}/lock")
def lock_completion_package(case_id: str, package_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES); _case_project(db, case_id); package = db.get(SubmissionPackage, package_id)
    if not package or package.authority_case_id != case_id: raise HTTPException(404, "SUBMISSION_PACKAGE_NOT_FOUND")
    items = db.scalars(select(SubmissionPackageItem).where(SubmissionPackageItem.package_id == package.id).order_by(SubmissionPackageItem.display_order)).all()
    if package.state == "LOCKED": return _row(package)
    package.manifest_json = {"case_id": case_id, "items": [_row(x) for x in items], "recipe": "COMPLETION_CANONICAL_PACKAGE_V1"}; package.manifest_hash = _hash(package.manifest_json); package.state = "LOCKED"; package.locked_at = _now(); db.commit(); return _row(package)


@router.post("/{case_id}/precheck")
def completion_precheck(case_id: str, preparation_revision_id: str, submission_package_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, REVIEW_ROLES); link = _case_link(db, case_id); prep = db.get(PreparationRevision, preparation_revision_id); package = db.get(SubmissionPackage, submission_package_id)
    if not prep or not package or prep.authority_case_id != case_id or package.authority_case_id != case_id: raise HTTPException(404, "PRECHECK_CONTEXT_NOT_FOUND")
    readiness = _readiness(db, link); checks = []
    checks.append(("AS_BUILT_BASELINE", "PASS" if readiness["baseline_id"] and not any("AS_BUILT_BASELINE" in x["code"] for x in readiness["blockers"]) else "BLOCKED", "Approved AsBuiltBaseline is required"))
    checks.append(("REQUIREMENTS", "PASS" if not any(x["code"] in {"REQUIREMENT_UNSATISFIED", "APPLICABILITY_UNKNOWN", "COMPLETION_REQUIREMENTS_NOT_INITIALIZED"} for x in readiness["blockers"]) else "BLOCKED", "Completion requirements must be satisfied or controlled N/A"))
    checks.append(("VARIANCES", "PASS" if not any(x["code"] == "AS_BUILT_VARIANCE_OPEN" for x in readiness["blockers"]) else "BLOCKED", "All variances require professional disposition"))
    checks.append(("PREPARATION", "PASS" if prep.authority_state == "LOCKED" else "BLOCKED", "PreparationRevision must be locked"))
    checks.append(("PACKAGE", "PASS" if package.state == "LOCKED" and package.manifest_hash else "BLOCKED", "SubmissionPackage manifest must be locked"))
    result = "PASS" if all(x[1] == "PASS" for x in checks) else "BLOCKED"; run = SubmissionPrecheckRun(authority_case_id=case_id, preparation_revision_id=prep.id, submission_package_id=package.id, policy_version_id=prep.authority_policy_version_id, package_hash=package.manifest_hash or "", result=result, digital_readiness="READY" if result == "PASS" else "BLOCKED", physical_readiness="READY" if result == "PASS" else "BLOCKED", evaluated_by=_actor(role)); db.add(run); db.flush()
    for code, status, message in checks: db.add(SubmissionPrecheckCheck(precheck_run_id=run.id, code=code, category="COMPLETION", result=status, message=message, blocking=status != "PASS", source_type="CompletionReadiness", source_id=case_id))
    db.commit(); return {"run": _row(run), "checks": [_row(x) for x in db.scalars(select(SubmissionPrecheckCheck).where(SubmissionPrecheckCheck.precheck_run_id == run.id)).all()]}


@router.post("/{case_id}/submit-authorization")
def authorize_completion_submission(case_id: str, payload: SubmitRequest, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES); _case_project(db, case_id); existing = db.scalar(select(SubmissionAttempt).where(SubmissionAttempt.idempotency_key == payload.idempotency_key))
    if existing: return _row(existing)
    prep = db.get(PreparationRevision, payload.preparation_revision_id); package = db.get(SubmissionPackage, payload.submission_package_id); precheck = db.get(SubmissionPrecheckRun, payload.precheck_run_id)
    if not prep or not package or not precheck or prep.authority_case_id != case_id or package.authority_case_id != case_id or precheck.authority_case_id != case_id: raise HTTPException(404, "SUBMISSION_CONTEXT_NOT_FOUND")
    if precheck.result != "PASS": raise HTTPException(409, "COMPLETION_PRECHECK_NOT_PASS")
    attempt_number = (db.scalar(select(func.max(SubmissionAttempt.attempt_number)).where(SubmissionAttempt.authority_case_id == case_id)) or 0) + 1
    attempt = SubmissionAttempt(authority_case_id=case_id, preparation_revision_id=prep.id, submission_package_id=package.id, precheck_run_id=precheck.id, channel_code=payload.channel_code, attempt_number=attempt_number, idempotency_key=payload.idempotency_key, state="PENDING_EXTERNAL_CONFIRMATION", authorized_by=_actor(role), authorized_at=_now()); db.add(attempt); case = db.get(AuthorityCase, case_id); case.status = "PENDING_EXTERNAL_CONFIRMATION"; db.commit(); db.refresh(attempt); return _row(attempt)


@router.post("/{case_id}/submission-attempts/{attempt_id}/external-confirmation")
def confirm_completion_submission(case_id: str, attempt_id: str, payload: ConfirmRequest, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES); _case_project(db, case_id); attempt = db.get(SubmissionAttempt, attempt_id)
    if not attempt or attempt.authority_case_id != case_id: raise HTTPException(404, "SUBMISSION_ATTEMPT_NOT_FOUND")
    existing = db.scalar(select(ExternalSubmissionSnapshot).where(ExternalSubmissionSnapshot.submission_attempt_id == attempt.id))
    if existing: return {"snapshot": _row(existing), "cycle": _row(db.scalar(select(AuthoritySubmissionCycle).where(AuthoritySubmissionCycle.external_submission_snapshot_id == existing.id)))}
    package = db.get(SubmissionPackage, attempt.submission_package_id); snapshot = ExternalSubmissionSnapshot(submission_attempt_id=attempt.id, authority_case_id=case_id, channel_code=attempt.channel_code, package_hash=package.manifest_hash or "", external_reference=payload.external_reference, external_status="RECEIVED", external_submitted_at=_now(), confirmation_source="MANUAL_CONFIRMED", evidence_document_version_id=payload.evidence_document_version_id, confirmed_by=_actor(role), notes=payload.notes); db.add(snapshot); db.flush()
    cycle_number = (db.scalar(select(func.max(AuthoritySubmissionCycle.cycle_number)).where(AuthoritySubmissionCycle.authority_case_id == case_id)) or 0) + 1; cycle = AuthoritySubmissionCycle(authority_case_id=case_id, cycle_number=cycle_number, preparation_revision_id=attempt.preparation_revision_id, submission_package_id=attempt.submission_package_id, external_submission_snapshot_id=snapshot.id, status="SUBMITTED_CONFIRMED"); db.add(cycle); attempt.state = "EXTERNALLY_SUBMITTED_CONFIRMED"; db.get(AuthorityCase, case_id).status = "SUBMITTED_CONFIRMED"; db.commit(); return {"snapshot": _row(snapshot), "cycle": _row(cycle)}


@router.post("/{case_id}/findings")
def capture_completion_finding(case_id: str, payload: FindingRequest, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, REVIEW_ROLES); _case_project(db, case_id); finding = AuthorityCaseFinding(authority_case_id=case_id, submission_cycle_id=payload.submission_cycle_id, category=payload.category, title=payload.title, raw_text=payload.raw_text, status="OPEN", severity=payload.severity, captured_by=_actor(role), engineering_impact=payload.engineering_impact, affected_requirement_instance_id=payload.affected_requirement_instance_id); db.add(finding); db.commit(); db.refresh(finding); return _row(finding)


@router.post("/{case_id}/findings/{finding_id}/responses")
def respond_completion_finding(case_id: str, finding_id: str, payload: ResponseRequest, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, REVIEW_ROLES); _case_project(db, case_id); finding = db.get(AuthorityCaseFinding, finding_id)
    if not finding or finding.authority_case_id != case_id: raise HTTPException(404, "AUTHORITY_FINDING_NOT_FOUND")
    response = AuthorityFindingResponse(finding_id=finding.id, response_text=payload.response_text, supporting_evidence_json=payload.supporting_evidence_json, status="PREPARED", prepared_by=_actor(role)); db.add(response); db.commit(); db.refresh(response); return _row(response)


@router.post("/{case_id}/outcomes")
def record_completion_outcome(case_id: str, payload: OutcomeRequest, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES); _case_project(db, case_id); cycle = db.get(AuthoritySubmissionCycle, payload.submission_cycle_id)
    if not cycle or cycle.authority_case_id != case_id or cycle.status != "SUBMITTED_CONFIRMED": raise HTTPException(409, "VERIFIED_SUBMISSION_CYCLE_REQUIRED")
    existing = db.scalar(select(AuthorityCaseOutcome).where(AuthorityCaseOutcome.authority_case_id == case_id, AuthorityCaseOutcome.outcome_type == payload.outcome_type))
    if existing: return _row(existing)
    outcome = AuthorityCaseOutcome(authority_case_id=case_id, submission_cycle_id=cycle.id, outcome_type=payload.outcome_type, status="VERIFIED", external_identifier=payload.external_identifier, source_document_version_id=payload.source_document_version_id, evidence_snapshot_json={"cycle_id": cycle.id, "external_reference": payload.external_identifier, "verified": True}, issued_at=payload.issued_at or _now(), verified_by=_actor(role), verified_at=_now()); db.add(outcome); db.get(AuthorityCase, case_id).status = "AUTHORITY_OUTCOME_RECORDED"; db.commit(); db.refresh(outcome); return {"authority_decision": _row(outcome), "handover_created": False}


@router.get("/{case_id}/outcome-context")
def completion_outcome_context(case_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, REVIEW_ROLES | OWNER_ROLES); link = _case_link(db, case_id); baseline = db.scalar(select(AsBuiltBaseline).where(AsBuiltBaseline.authority_case_id == case_id, AsBuiltBaseline.status == "APPROVED").order_by(AsBuiltBaseline.version_number.desc())); cycles = db.scalars(select(AuthoritySubmissionCycle).where(AuthoritySubmissionCycle.authority_case_id == case_id).order_by(AuthoritySubmissionCycle.cycle_number)).all(); outcomes = db.scalars(select(AuthorityCaseOutcome).where(AuthorityCaseOutcome.authority_case_id == case_id)).all(); reports = db.scalars(select(RenderedArtifact).where(RenderedArtifact.context_type == "COMPLETION_REPORT", RenderedArtifact.context_id == case_id)).all(); forms = db.scalars(select(FormInstance).where(FormInstance.context_type == "COMPLETION", FormInstance.context_id == case_id)).all(); return {"completion_case_id": case_id, "construction_completion_context_id": link.construction_completion_context_id, "as_built_baseline": _row(baseline) if baseline else None, "cycles": [_row(x) for x in cycles], "outcomes": [_row(x) for x in outcomes], "reports": [_row(x) for x in reports], "forms": [_row(x) for x in forms], "handover_ready": bool(baseline and outcomes), "handover_created": False}


def workspace(case_id: str, request: Request, db: Session, role: Role) -> dict[str, Any]:
    link = _case_link(db, case_id)
    case = db.get(AuthorityCase, case_id)
    context = db.get(ConstructionCompletionContext, link.construction_completion_context_id)
    readiness = _readiness(db, link)
    baseline = db.scalars(select(AsBuiltBaseline).where(AsBuiltBaseline.authority_case_id == case_id).order_by(AsBuiltBaseline.version_number.desc())).all()
    revisions = db.scalars(select(EngineeringDeliverableRevision).where(EngineeringDeliverableRevision.project_id == link.project_id, EngineeringDeliverableRevision.issue_purpose == "AS_BUILT").order_by(EngineeringDeliverableRevision.created_at)).all()
    assets = db.scalars(select(BuildingAsset).where(BuildingAsset.project_id == link.project_id)).all()
    snapshots = db.scalars(select(BuildingSnapshot).where(BuildingSnapshot.project_id == link.project_id).order_by(BuildingSnapshot.created_at)).all()
    variances = db.scalars(select(AsBuiltVariance).join(AsBuiltComparisonRun).where(AsBuiltComparisonRun.baseline_id.in_([x.id for x in baseline]))).all() if baseline else []
    requirements = db.scalars(select(RequirementInstance).where(RequirementInstance.authority_case_id == case_id)).all()
    forms = db.scalars(select(FormInstance).where(FormInstance.context_type == "COMPLETION", FormInstance.context_id == case_id)).all()
    packages = db.scalars(select(SubmissionPackage).where(SubmissionPackage.authority_case_id == case_id)).all()
    cycles = db.scalars(select(AuthoritySubmissionCycle).where(AuthoritySubmissionCycle.authority_case_id == case_id).order_by(AuthoritySubmissionCycle.cycle_number)).all()
    findings = db.scalars(select(AuthorityCaseFinding).where(AuthorityCaseFinding.authority_case_id == case_id)).all()
    outcomes = db.scalars(select(AuthorityCaseOutcome).where(AuthorityCaseOutcome.authority_case_id == case_id)).all()
    return {
        "case": _row(case), "link": _row(link), "construction_context": _row(context), "readiness": readiness,
        "baselines": [_row(x) for x in baseline], "as_built_revisions": [_row(x) for x in revisions],
        "building_assets": [_row(x) for x in assets], "building_snapshots": [_row(x) for x in snapshots],
        "variances": [_row(x) for x in variances], "requirements": [_row(x) for x in requirements],
        "forms": [_row(x) for x in forms], "packages": [_row(x) for x in packages],
        "cycles": [_row(x) for x in cycles], "findings": [_row(x) for x in findings],
        "outcomes": [_row(x) for x in outcomes],
    }


@router.get("/{case_id}")
def workspace_route(case_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, REVIEW_ROLES | OWNER_ROLES); return workspace(case_id, request, db, role)
