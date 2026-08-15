"""Construction / post-approval execution API.

All write commands are explicit human commands. External authority systems are
represented by prepared, sent, and acknowledged evidence; this module never
pretends that an external notification or inspection happened automatically.
"""

from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..config.settings import get_settings
from ..db import get_db
from ..models import *
from .dependencies import current_user_role


router = APIRouter(prefix="/api/construction", tags=["construction-post-approval"])
OWNER_ROLES = {Role.SYSTEM_ADMIN, Role.OWNER_SPONSOR}
ENGINEERING_ROLES = {Role.SYSTEM_ADMIN, Role.OWNER_SPONSOR, Role.RESPONSIBLE_ENGINEER}


def _corr(request: Request) -> str:
    return getattr(request.state, "correlation_id", "construction-correlation-missing")


def _require(role: Role, allowed: set[Role]) -> None:
    if role not in allowed:
        raise HTTPException(403, "Role is not authorized for this construction command")


def _columns(item: Any) -> dict[str, Any]:
    values = {column.name: getattr(item, column.name) for column in item.__table__.columns}
    return jsonable_encoder(values)


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(jsonable_encoder(value), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _execution(db: Session, execution_id: str) -> ConstructionExecution:
    item = db.get(ConstructionExecution, execution_id)
    if not item:
        raise HTTPException(404, "Construction execution not found")
    return item


def _project(db: Session, project_id: str) -> Project:
    item = db.get(Project, project_id)
    if not item:
        raise HTTPException(404, "Project not found")
    return item


def _assert_execution_project(execution: ConstructionExecution, project_id: str | None) -> None:
    if project_id and execution.project_id != project_id:
        raise HTTPException(409, {"code": "PROJECT_ISOLATION_VIOLATION", "project_id": project_id})


def _audit(db: Session, request: Request, event_type: str, entity_type: str, entity_id: str, after: Any, role: Role, before: Any = None, metadata: dict[str, Any] | None = None) -> None:
    audit(db, correlation_id=_corr(request), event_type=event_type, entity_type=entity_type, entity_id=entity_id,
          actor_id=role.value, before=before, after=after, metadata=metadata)


class ExecutionCreate(BaseModel):
    project_id: str
    execution_ref: str
    title: str
    scope_description: str | None = None
    contract_id: str | None = None
    contract_revision_id: str | None = None
    authority_case_id: str | None = None


class AuthoritySnapshotCreate(BaseModel):
    approved_design_baseline_id: str
    authority_case_id: str | None = None
    authority_outcome_id: str | None = None
    submission_cycle_id: str | None = None
    external_submission_snapshot_id: str | None = None
    submission_package_id: str | None = None
    preparation_revision_id: str | None = None
    authority_decision_reference: str | None = None
    external_approval_reference: str | None = None
    authority_state: str = "APPROVED"
    effective_from: date | None = None
    effective_until: date | None = None
    source_document_version_ids: list[str] = Field(default_factory=list)
    member_ids: list[str] = Field(default_factory=list)
    source_lineage_json: dict[str, Any] = Field(default_factory=dict)


class DesignSnapshotCreate(BaseModel):
    authority_approved_design_snapshot_id: str
    snapshot_ref: str
    member_ids: list[str] = Field(default_factory=list)


class ReadinessRequest(BaseModel):
    project_activation_id: str | None = None
    intended_start_date: date | None = None


class StartAuthorizationCreate(BaseModel):
    project_activation_id: str
    contract_revision_id: str
    authority_approved_design_snapshot_id: str
    construction_design_snapshot_id: str
    intended_start_date: date | None = None
    reason: str
    idempotency_key: str


class PartyAssignmentCreate(BaseModel):
    party_id: str
    role_code: str
    authority_case_id: str | None = None
    party_role_assignment_id: str | None = None
    professional_credential_id: str | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    source_document_version_id: str | None = None
    credential_snapshot: dict[str, Any] = Field(default_factory=dict)


class ObligationDefinitionCreate(BaseModel):
    authority_case_id: str | None = None
    requirement_definition_id: str | None = None
    policy_version_id: str | None = None
    code: str
    version: str = "1"
    title: str
    description: str
    trigger_type: str = "MANUAL"
    source_document_version_id: str | None = None
    required_role_codes: list[str] = Field(default_factory=list)
    due_rule_json: dict[str, Any] = Field(default_factory=dict)


class ObligationInstanceCreate(BaseModel):
    definition_id: str
    due_at: datetime | None = None
    participant_party_ids: list[str] = Field(default_factory=list)


class NotificationCreate(BaseModel):
    notification_type: str
    obligation_instance_id: str | None = None
    work_control_event_id: str | None = None
    channel_code: str = "MANUAL_PORTAL"
    recipient_snapshot: dict[str, Any] = Field(default_factory=dict)
    payload_snapshot: dict[str, Any] = Field(default_factory=dict)
    evidence_document_version_id: str | None = None
    idempotency_key: str


class NotificationSend(BaseModel):
    external_reference: str
    evidence_document_version_id: str | None = None


class CorrespondenceCreate(BaseModel):
    direction: str
    authority_case_id: str | None = None
    sender_party_id: str | None = None
    recipient_party_id: str | None = None
    subject: str
    reference: str | None = None
    document_version_id: str | None = None
    external_reference: str | None = None
    status: str = "PREPARED"
    occurred_at: datetime | None = None
    notes: str | None = None


class InspectionCreate(BaseModel):
    inspection_kind: str
    idempotency_key: str | None = None
    authority_case_id: str | None = None
    scheduled_at: datetime | None = None
    inspector_party_id: str | None = None


class InspectionRecord(BaseModel):
    status: str = "COMPLETED"
    occurred_at: datetime | None = None
    outcome: str
    authority_reference: str | None = None
    findings_json: list[dict[str, Any]] = Field(default_factory=list)
    evidence_document_version_ids: list[str] = Field(default_factory=list)


class IssueCreate(BaseModel):
    issue_ref: str
    category: str
    severity: str = "MAJOR"
    description: str
    affected_scope: str | None = None
    authority_case_finding_id: str | None = None
    design_change_request_id: str | None = None
    requirement_instance_id: str | None = None
    evidence_document_version_ids: list[str] = Field(default_factory=list)


class IssueResolve(BaseModel):
    resolution_notes: str
    evidence_document_version_ids: list[str] = Field(default_factory=list)


class WorkEventCreate(BaseModel):
    event_type: str
    start_authorization_id: str | None = None
    source_type: str = "HUMAN_COMMAND"
    source_id: str | None = None
    evidence_document_version_id: str | None = None
    notes: str | None = None
    idempotency_key: str
    event_at: datetime | None = None


def _baseline_members(db: Session, baseline_id: str, explicit_ids: list[str]) -> list[dict[str, Any]]:
    members = []
    rows = [db.get(ApprovedDesignBaselineMember, item_id) for item_id in explicit_ids] if explicit_ids else db.scalars(
        select(ApprovedDesignBaselineMember).where(ApprovedDesignBaselineMember.baseline_id == baseline_id).order_by(ApprovedDesignBaselineMember.id)
    ).all()
    if not rows:
        raise HTTPException(409, "Approved design baseline has no pinned members")
    for row in rows:
        if not row or row.baseline_id != baseline_id:
            raise HTTPException(409, "Every design member must belong to the selected approved baseline")
        rendition = db.get(EngineeringRendition, row.rendition_id)
        members.append({"member_id": row.id, "revision_id": row.revision_id, "rendition_id": row.rendition_id, "member_role": row.member_role, "pinned_hash": row.pinned_hash, "document_version_id": rendition.document_version_id if rendition else None})
    return members


def _lineage(db: Session, project_id: str, upstream_type: str, upstream_id: str, downstream_type: str, downstream_id: str, correlation: str, version: str | None = None) -> None:
    db.add(LineageEdge(project_id=project_id, upstream_type=upstream_type, upstream_id=upstream_id,
                       upstream_version_or_hash=version, downstream_type=downstream_type, downstream_id=downstream_id,
                       dependency_kind="CONSTRUCTION_EXECUTION", correlation_id=correlation))


@router.get("")
def list_executions(project_id: str | None = None, db: Session = Depends(get_db)):
    query = select(ConstructionExecution).order_by(ConstructionExecution.updated_at.desc())
    if project_id:
        query = query.where(ConstructionExecution.project_id == project_id)
    return [_columns(item) for item in db.scalars(query).all()]


@router.post("/executions")
def create_execution(payload: ExecutionCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES)
    _project(db, payload.project_id)
    if payload.contract_id and not db.get(Contract, payload.contract_id):
        raise HTTPException(409, "Contract reference does not exist")
    if payload.contract_revision_id and not db.get(ContractRevision, payload.contract_revision_id):
        raise HTTPException(409, "Contract revision reference does not exist")
    if payload.authority_case_id and not db.get(AuthorityCase, payload.authority_case_id):
        raise HTTPException(409, "Authority case reference does not exist")
    item = ConstructionExecution(**payload.model_dump(), created_by=role.value)
    db.add(item); db.flush()
    _audit(db, request, "CONSTRUCTION_EXECUTION_CREATED", "ConstructionExecution", item.id, _columns(item), role)
    db.commit(); db.refresh(item)
    return _columns(item)


@router.post("/test-support/completed-execution")
def create_completed_test_execution(project_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    """Create a completed synthetic handoff for real-stack Completion UI tests.

    This seam is deliberately unavailable outside TEST. It creates only the
    upstream construction state needed to exercise the explicit Completion
    start boundary; it never represents a production construction record.
    """
    if get_settings().app_env.upper() != "TEST":
        raise HTTPException(404, {"code": "TEST_SUPPORT_NOT_AVAILABLE"})
    _require(role, OWNER_ROLES)
    _project(db, project_id)
    if not db.scalar(select(ServiceType).where(ServiceType.code == "BUILDING_COMPLETION")):
        db.add(ServiceType(code="BUILDING_COMPLETION", name_en="Synthetic Building Completion", status="ACTIVE", provenance_json={"synthetic": True, "test_support": True}))
    if not db.scalar(select(ExternalBody).where(ExternalBody.code == "QATAR_MUNICIPALITY")):
        db.add(ExternalBody(code="QATAR_MUNICIPALITY", name_en="Synthetic Municipality", body_type="AUTHORITY", status="ACTIVE", verification_state="SYNTHETIC_VERIFIED"))
    if not db.scalar(select(Jurisdiction).where(Jurisdiction.code == "QATAR")):
        db.add(Jurisdiction(code="QATAR", country_code="QA", name_en="Synthetic Qatar", status="ACTIVE"))
    db.flush()
    suffix = uuid4().hex[:12].upper()
    item = ConstructionExecution(project_id=project_id, execution_ref=f"TEST-COMPLETION-{suffix}", title="Synthetic completed construction scope", scope_description="Real-stack synthetic Completion fixture", status="COMPLETED", work_state="COMPLETED", created_by=role.value)
    db.add(item); db.flush()
    _audit(db, request, "CONSTRUCTION_TEST_FIXTURE_CREATED", "ConstructionExecution", item.id, _columns(item), role, metadata={"synthetic_only": True, "test_support": True})
    db.commit(); db.refresh(item)
    return _columns(item)


@router.get("/executions/{execution_id}")
def execution_detail(execution_id: str, db: Session = Depends(get_db)):
    item = _execution(db, execution_id)
    return {
        **_columns(item),
        "authority_design_snapshots": [_columns(x) for x in db.scalars(select(AuthorityApprovedDesignSnapshot).where(AuthorityApprovedDesignSnapshot.construction_execution_id == item.id).order_by(AuthorityApprovedDesignSnapshot.captured_at.desc())).all()],
        "design_snapshots": [_columns(x) for x in db.scalars(select(ConstructionDesignSnapshot).where(ConstructionDesignSnapshot.construction_execution_id == item.id).order_by(ConstructionDesignSnapshot.version_number.desc())).all()],
        "parties": [_columns(x) for x in db.scalars(select(ConstructionPartyAssignment).where(ConstructionPartyAssignment.construction_execution_id == item.id).order_by(ConstructionPartyAssignment.role_code)).all()],
        "obligations": [_columns(x) for x in db.scalars(select(ConstructionObligationInstance).where(ConstructionObligationInstance.construction_execution_id == item.id).order_by(ConstructionObligationInstance.created_at.desc())).all()],
        "notifications": [_columns(x) for x in db.scalars(select(AuthorityNotification).where(AuthorityNotification.construction_execution_id == item.id).order_by(AuthorityNotification.prepared_at.desc())).all()],
        "correspondence": [_columns(x) for x in db.scalars(select(ProjectCorrespondence).where(ProjectCorrespondence.construction_execution_id == item.id).order_by(ProjectCorrespondence.occurred_at.desc())).all()],
        "inspections": [_columns(x) for x in db.scalars(select(ConstructionInspection).where(ConstructionInspection.construction_execution_id == item.id).order_by(ConstructionInspection.requested_at.desc())).all()],
        "issues": [_columns(x) for x in db.scalars(select(ConstructionIssue).where(ConstructionIssue.construction_execution_id == item.id).order_by(ConstructionIssue.observed_at.desc())).all()],
        "work_events": [_columns(x) for x in db.scalars(select(ConstructionWorkControlEvent).where(ConstructionWorkControlEvent.construction_execution_id == item.id).order_by(ConstructionWorkControlEvent.event_at.desc())).all()],
    }


@router.post("/executions/{execution_id}/authority-design-snapshots")
def capture_authority_snapshot(execution_id: str, payload: AuthoritySnapshotCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, ENGINEERING_ROLES)
    item = _execution(db, execution_id)
    baseline = db.get(ApprovedDesignBaseline, payload.approved_design_baseline_id)
    if not baseline or baseline.project_id != item.project_id:
        raise HTTPException(409, "Approved design baseline is not in the construction project")
    if baseline.status != "APPROVED" or not baseline.approved_at:
        raise HTTPException(409, "Only an AMEC-approved design baseline can be captured")
    members = _baseline_members(db, baseline.id, payload.member_ids)
    document_ids = sorted(set(payload.source_document_version_ids + [x["document_version_id"] for x in members if x.get("document_version_id")]))
    if payload.authority_case_id and not db.get(AuthorityCase, payload.authority_case_id):
        raise HTTPException(409, "Authority case reference does not exist")
    if payload.external_submission_snapshot_id:
        external = db.get(ExternalSubmissionSnapshot, payload.external_submission_snapshot_id)
        if not external or (payload.authority_case_id and external.authority_case_id != payload.authority_case_id):
            raise HTTPException(409, "External submission snapshot does not match the authority case")
    source = {**payload.source_lineage_json, "approved_design_baseline_id": baseline.id, "baseline_ref": baseline.baseline_ref, "member_ids": [x["member_id"] for x in members]}
    snapshot_hash = _hash({"baseline": baseline.manifest_hash, "members": members, "documents": document_ids, "authority": payload.model_dump(exclude={"member_ids", "source_lineage_json"})})
    previous = db.scalars(select(AuthorityApprovedDesignSnapshot).where(AuthorityApprovedDesignSnapshot.construction_execution_id == item.id, AuthorityApprovedDesignSnapshot.status == "CURRENT")).all()
    for old in previous:
        old.status = "SUPERSEDED"
    snapshot = AuthorityApprovedDesignSnapshot(project_id=item.project_id, construction_execution_id=item.id, approved_design_baseline_id=baseline.id,
        **payload.model_dump(exclude={"approved_design_baseline_id", "member_ids", "source_document_version_ids", "source_lineage_json"}),
        source_document_version_ids=document_ids, baseline_member_snapshot=members, source_lineage_json=source, snapshot_hash=snapshot_hash, captured_by=role.value)
    db.add(snapshot); db.flush(); item.current_authority_snapshot_id = snapshot.id
    _lineage(db, item.project_id, "ApprovedDesignBaseline", baseline.id, "AuthorityApprovedDesignSnapshot", snapshot.id, _corr(request), baseline.manifest_hash)
    for source_type, source_id in (("AuthorityCase", payload.authority_case_id), ("AuthoritySubmissionCycle", payload.submission_cycle_id), ("ExternalSubmissionSnapshot", payload.external_submission_snapshot_id), ("SubmissionPackage", payload.submission_package_id), ("PreparationRevision", payload.preparation_revision_id)):
        if source_id:
            _lineage(db, item.project_id, source_type, source_id, "AuthorityApprovedDesignSnapshot", snapshot.id, _corr(request))
    _audit(db, request, "AUTHORITY_APPROVED_DESIGN_SNAPSHOT_CAPTURED", "AuthorityApprovedDesignSnapshot", snapshot.id, _columns(snapshot), role)
    db.commit(); db.refresh(snapshot)
    return _columns(snapshot)


@router.post("/executions/{execution_id}/design-snapshots")
def promote_design_snapshot(execution_id: str, payload: DesignSnapshotCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, ENGINEERING_ROLES)
    item = _execution(db, execution_id)
    authority = db.get(AuthorityApprovedDesignSnapshot, payload.authority_approved_design_snapshot_id)
    if not authority or authority.construction_execution_id != item.id or authority.status != "CURRENT":
        raise HTTPException(409, "Current authority-approved design snapshot is required")
    baseline = db.get(ApprovedDesignBaseline, authority.approved_design_baseline_id)
    if not baseline or baseline.status != "APPROVED":
        raise HTTPException(409, "Design snapshot must reference an approved AMEC baseline")
    members = _baseline_members(db, baseline.id, payload.member_ids or [x["member_id"] for x in authority.baseline_member_snapshot])
    current = db.scalar(select(ConstructionDesignSnapshot).where(ConstructionDesignSnapshot.construction_execution_id == item.id, ConstructionDesignSnapshot.status == "CURRENT"))
    version = (current.version_number + 1) if current else 1
    if current:
        current.status = "SUPERSEDED"
    snapshot = ConstructionDesignSnapshot(project_id=item.project_id, construction_execution_id=item.id, authority_approved_design_snapshot_id=authority.id,
        approved_design_baseline_id=baseline.id, version_number=version, snapshot_ref=payload.snapshot_ref,
        member_revision_ids=[x["revision_id"] for x in members], member_rendition_ids=[x["rendition_id"] for x in members],
        document_version_ids=sorted(set(x["document_version_id"] for x in members if x.get("document_version_id"))),
        snapshot_hash=_hash({"authority_snapshot": authority.snapshot_hash, "members": members, "version": version}), supersedes_id=current.id if current else None, promoted_by=role.value)
    db.add(snapshot); db.flush(); item.current_design_snapshot_id = snapshot.id
    _lineage(db, item.project_id, "AuthorityApprovedDesignSnapshot", authority.id, "ConstructionDesignSnapshot", snapshot.id, _corr(request), authority.snapshot_hash)
    _lineage(db, item.project_id, "ApprovedDesignBaseline", baseline.id, "ConstructionDesignSnapshot", snapshot.id, _corr(request), baseline.manifest_hash)
    _audit(db, request, "CONSTRUCTION_DESIGN_SNAPSHOT_PROMOTED", "ConstructionDesignSnapshot", snapshot.id, _columns(snapshot), role)
    db.commit(); db.refresh(snapshot)
    return _columns(snapshot)


def _readiness(db: Session, item: ConstructionExecution, intended_start_date: date | None = None, project_activation_id: str | None = None, persist: bool = True, actor: str = "READINESS_ENGINE") -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    checks: dict[str, Any] = {}
    activation = db.get(ProjectActivation, project_activation_id) if project_activation_id else db.scalar(select(ProjectActivation).where(ProjectActivation.project_id == item.project_id, ProjectActivation.status == "ACTIVE"))
    checks["project_activation"] = bool(activation and activation.project_id == item.project_id and activation.status == "ACTIVE")
    if not checks["project_activation"]:
        blockers.append({"code": "PROJECT_ACTIVATION_REQUIRED", "message": "An active ProjectActivation is required"})
    contract_revision = db.get(ContractRevision, item.contract_revision_id) if item.contract_revision_id else (db.get(ContractRevision, activation.contract_revision_id) if activation else None)
    accepted_contract_states = {"FINAL", "FINALIZED", "ACCEPTED", "APPROVED", "EXECUTED", "SIGNED"}
    checks["contract_revision"] = bool(contract_revision and contract_revision.status in accepted_contract_states and contract_revision.agreement_type == "AMEC_PROFESSIONAL_SERVICES")
    if not checks["contract_revision"]:
        blockers.append({"code": "FINAL_AM​​EC_CONTRACT_REVISION_REQUIRED".replace("​​", ""), "message": "A finalized AMEC professional-services contract revision is required"})
    authority = db.get(AuthorityApprovedDesignSnapshot, item.current_authority_snapshot_id) if item.current_authority_snapshot_id else db.scalar(select(AuthorityApprovedDesignSnapshot).where(AuthorityApprovedDesignSnapshot.construction_execution_id == item.id, AuthorityApprovedDesignSnapshot.status == "CURRENT").order_by(AuthorityApprovedDesignSnapshot.captured_at.desc()))
    date_to_check = intended_start_date or (activation.start_date if activation else date.today())
    checks["authority_approval"] = bool(authority and authority.status == "CURRENT" and authority.authority_state in {"APPROVED", "ACTIVE"} and (not authority.effective_from or authority.effective_from <= date_to_check) and (not authority.effective_until or authority.effective_until >= date_to_check))
    if not checks["authority_approval"]:
        blockers.append({"code": "CURRENT_AUTHORITY_APPROVAL_REQUIRED", "message": "A current effective authority-approved design snapshot is required"})
    design = db.get(ConstructionDesignSnapshot, item.current_design_snapshot_id) if item.current_design_snapshot_id else db.scalar(select(ConstructionDesignSnapshot).where(ConstructionDesignSnapshot.construction_execution_id == item.id, ConstructionDesignSnapshot.status == "CURRENT").order_by(ConstructionDesignSnapshot.version_number.desc()))
    checks["construction_design"] = bool(design and design.status == "CURRENT" and authority and design.authority_approved_design_snapshot_id == authority.id)
    if not checks["construction_design"]:
        blockers.append({"code": "CURRENT_CONSTRUCTION_DESIGN_REQUIRED", "message": "A construction design snapshot must pin the current authority snapshot"})
    required_roles = sorted(set(role_code for definition in db.scalars(select(ConstructionObligationDefinition).where(ConstructionObligationDefinition.project_id == item.project_id, ConstructionObligationDefinition.status == "ACTIVE")).all() for role_code in (definition.required_role_codes or [])))
    assignments = db.scalars(select(ConstructionPartyAssignment).where(ConstructionPartyAssignment.construction_execution_id == item.id, ConstructionPartyAssignment.status == "ACTIVE")).all()
    active_roles = {assignment.role_code for assignment in assignments if not assignment.valid_until or assignment.valid_until >= date_to_check}
    missing_roles = [role_code for role_code in required_roles if role_code not in active_roles]
    checks["party_roles"] = {"required": required_roles, "active": sorted(active_roles), "missing": missing_roles}
    for role_code in missing_roles:
        blockers.append({"code": "REQUIRED_PARTY_ROLE_MISSING", "role_code": role_code, "message": f"Active construction party role {role_code} is required"})
    if item.authority_case_id:
        grants = db.scalars(select(AuthorizationGrant).where(AuthorizationGrant.project_id == item.project_id, AuthorizationGrant.authority_case_id == item.authority_case_id, AuthorizationGrant.status == "VERIFIED")).all()
        checks["authorization_grants"] = len(grants)
        if not grants:
            blockers.append({"code": "VERIFIED_AUTHORIZATION_REQUIRED", "message": "At least one verified authority authorization grant is required"})
    else:
        checks["authorization_grants"] = "NOT_APPLICABLE"
    blocking_issues = db.scalars(select(ConstructionIssue).where(ConstructionIssue.construction_execution_id == item.id, ConstructionIssue.status.not_in(["RESOLVED", "CLOSED"]), ConstructionIssue.severity == "BLOCKING")).all()
    checks["blocking_issues"] = len(blocking_issues)
    if blocking_issues:
        blockers.append({"code": "BLOCKING_CONSTRUCTION_ISSUES_OPEN", "count": len(blocking_issues), "message": "Blocking construction issues must be resolved"})
    result = "READY_FOR_AUTHORIZATION" if not blockers else "NOT_READY"
    payload = {"result": result, "blockers": blockers, "checks": checks, "intended_start_date": date_to_check.isoformat()}
    evaluation = ConstructionStartReadiness(project_id=item.project_id, construction_execution_id=item.id, result=result, blockers_json=blockers, checks_json=checks, evaluation_fingerprint=_hash(payload), evaluated_by=actor)
    if persist:
        db.add(evaluation); db.flush()
    payload["readiness_id"] = evaluation.id
    return payload


@router.post("/executions/{execution_id}/readiness")
def evaluate_readiness(execution_id: str, payload: ReadinessRequest | None = None, request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    item = _execution(db, execution_id); payload = payload or ReadinessRequest()
    result = _readiness(db, item, payload.intended_start_date, payload.project_activation_id, actor=role.value)
    _audit(db, request, "CONSTRUCTION_START_READINESS_EVALUATED", "ConstructionExecution", item.id, result, role)
    db.commit()
    return result


@router.post("/executions/{execution_id}/start-authorizations")
def authorize_start(execution_id: str, payload: StartAuthorizationCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES)
    item = _execution(db, execution_id)
    existing = db.scalar(select(ConstructionStartAuthorization).where(ConstructionStartAuthorization.idempotency_key == payload.idempotency_key))
    if existing:
        if existing.project_id != item.project_id or existing.construction_execution_id != item.id:
            raise HTTPException(409, "Idempotency key is already bound to another project")
        return _columns(existing)
    activation = db.get(ProjectActivation, payload.project_activation_id)
    if not activation or activation.project_id != item.project_id or activation.status != "ACTIVE":
        raise HTTPException(409, "Active ProjectActivation for this project is required")
    if activation.contract_revision_id != payload.contract_revision_id:
        raise HTTPException(409, "Start authorization contract revision must match ProjectActivation")
    item.contract_revision_id = payload.contract_revision_id
    readiness = _readiness(db, item, payload.intended_start_date, activation.id, actor=role.value)
    if readiness["result"] != "READY_FOR_AUTHORIZATION":
        db.rollback()
        raise HTTPException(409, {"code": "CONSTRUCTION_START_NOT_READY", "readiness": readiness})
    authority = db.get(AuthorityApprovedDesignSnapshot, payload.authority_approved_design_snapshot_id)
    design = db.get(ConstructionDesignSnapshot, payload.construction_design_snapshot_id)
    if not authority or authority.construction_execution_id != item.id or authority.status != "CURRENT" or not design or design.construction_execution_id != item.id or design.status != "CURRENT" or design.authority_approved_design_snapshot_id != authority.id:
        raise HTTPException(409, "Start authorization must pin the current authority and construction design snapshots")
    assignments = db.scalars(select(ConstructionPartyAssignment).where(ConstructionPartyAssignment.construction_execution_id == item.id, ConstructionPartyAssignment.status == "ACTIVE")).all()
    grants = db.scalars(select(AuthorizationGrant).where(AuthorizationGrant.project_id == item.project_id, AuthorizationGrant.authority_case_id == item.authority_case_id, AuthorizationGrant.status == "VERIFIED")).all() if item.authority_case_id else []
    authorization = ConstructionStartAuthorization(project_id=item.project_id, construction_execution_id=item.id, project_activation_id=activation.id, contract_revision_id=payload.contract_revision_id,
        authority_approved_design_snapshot_id=authority.id, construction_design_snapshot_id=design.id, intended_start_date=payload.intended_start_date or activation.start_date,
        readiness_snapshot=readiness, party_snapshot=[_columns(x) for x in assignments], authorization_snapshot=[_columns(x) for x in grants], reason=payload.reason,
        idempotency_key=payload.idempotency_key, authorized_by=role.value)
    db.add(authorization); db.flush(); item.status = "START_AUTHORIZED"
    _lineage(db, item.project_id, "ProjectActivation", activation.id, "ConstructionStartAuthorization", authorization.id, _corr(request))
    _lineage(db, item.project_id, "ConstructionDesignSnapshot", design.id, "ConstructionStartAuthorization", authorization.id, _corr(request), design.snapshot_hash)
    _audit(db, request, "CONSTRUCTION_START_AUTHORIZED", "ConstructionStartAuthorization", authorization.id, _columns(authorization), role)
    db.commit(); db.refresh(authorization)
    return _columns(authorization)


@router.post("/executions/{execution_id}/start-authorization")
def authorize_start_singular(execution_id: str, payload: StartAuthorizationCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    return authorize_start(execution_id, payload, request, db, role)


@router.post("/executions/{execution_id}/work-events")
def record_work_event(execution_id: str, payload: WorkEventCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES)
    item = _execution(db, execution_id)
    existing = db.scalar(select(ConstructionWorkControlEvent).where(ConstructionWorkControlEvent.idempotency_key == payload.idempotency_key))
    if existing:
        if existing.project_id != item.project_id:
            raise HTTPException(409, "Idempotency key is already bound to another project")
        return _columns(existing)
    event_type = payload.event_type.upper()
    transitions = {"START": ("NOT_STARTED", "WORK_ACTIVE"), "STOP": ("WORK_ACTIVE", "WORK_STOPPED"), "POSTPONE": (("WORK_ACTIVE", "WORK_STOPPED"), "POSTPONED"), "RESUME": (("WORK_STOPPED", "POSTPONED"), "WORK_ACTIVE")}
    if event_type not in transitions:
        raise HTTPException(422, "event_type must be START, STOP, POSTPONE, or RESUME")
    allowed_prior, new_state = transitions[event_type]
    if isinstance(allowed_prior, tuple):
        if item.work_state not in allowed_prior:
            raise HTTPException(409, {"code": "INVALID_WORK_STATE_TRANSITION", "state": item.work_state, "event_type": event_type})
    elif item.work_state != allowed_prior:
        raise HTTPException(409, {"code": "INVALID_WORK_STATE_TRANSITION", "state": item.work_state, "event_type": event_type})
    authorization = None
    if event_type in {"START", "RESUME"}:
        authorization = db.get(ConstructionStartAuthorization, payload.start_authorization_id) if payload.start_authorization_id else db.scalar(select(ConstructionStartAuthorization).where(ConstructionStartAuthorization.construction_execution_id == item.id, ConstructionStartAuthorization.status == "START_AUTHORIZED").order_by(ConstructionStartAuthorization.authorized_at.desc()))
        if not authorization or authorization.construction_execution_id != item.id or authorization.status != "START_AUTHORIZED":
            raise HTTPException(409, "Human ConstructionStartAuthorization is required")
    prior = item.work_state
    item.work_state = new_state
    item.status = "ACTIVE" if new_state == "WORK_ACTIVE" else "PAUSED" if new_state in {"WORK_STOPPED", "POSTPONED"} else item.status
    event = ConstructionWorkControlEvent(project_id=item.project_id, construction_execution_id=item.id, start_authorization_id=authorization.id if authorization else None,
        event_type=event_type, prior_state=prior, new_state=new_state, event_at=payload.event_at or datetime.now(timezone.utc), source_type=payload.source_type, source_id=payload.source_id,
        evidence_document_version_id=payload.evidence_document_version_id, notes=payload.notes, idempotency_key=payload.idempotency_key, recorded_by=role.value)
    db.add(event); db.flush()
    for obligation in db.scalars(select(ConstructionObligationInstance).where(ConstructionObligationInstance.construction_execution_id == item.id, ConstructionObligationInstance.status == "WAITING_TRIGGER")).all():
        definition = db.get(ConstructionObligationDefinition, obligation.definition_id)
        if definition and (definition.trigger_type == "WORK_START" and event_type == "START"):
            obligation.status = "DUE"; obligation.trigger_event_type = event_type; obligation.trigger_event_id = event.id
            offset = (definition.due_rule_json or {}).get("offset_days")
            if offset is not None:
                obligation.due_at = event.event_at + timedelta(days=int(offset))
            _lineage(db, item.project_id, "ConstructionWorkControlEvent", event.id, "ConstructionObligationInstance", obligation.id, _corr(request))
    _audit(db, request, f"CONSTRUCTION_WORK_{event_type}", "ConstructionWorkControlEvent", event.id, _columns(event), role, metadata={"prior_state": prior, "new_state": new_state})
    db.commit(); db.refresh(event)
    return _columns(event)


@router.post("/executions/{execution_id}/parties")
def assign_party(execution_id: str, payload: PartyAssignmentCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES)
    item = _execution(db, execution_id)
    if not db.get(Party, payload.party_id):
        raise HTTPException(409, "Canonical party does not exist")
    if payload.party_role_assignment_id:
        link = db.get(PartyRoleAssignment, payload.party_role_assignment_id)
        if not link or link.project_id != item.project_id or link.party_id != payload.party_id:
            raise HTTPException(409, "PartyRoleAssignment does not match the project and party")
    credential = db.get(ProfessionalCredential, payload.professional_credential_id) if payload.professional_credential_id else None
    if payload.professional_credential_id and (not credential or credential.project_id != item.project_id):
        raise HTTPException(409, "Professional credential does not match the project")
    assignment = ConstructionPartyAssignment(project_id=item.project_id, construction_execution_id=item.id, **payload.model_dump(), assigned_by=role.value)
    db.add(assignment); db.flush(); _audit(db, request, "CONSTRUCTION_PARTY_ASSIGNED", "ConstructionPartyAssignment", assignment.id, _columns(assignment), role)
    db.commit(); db.refresh(assignment); return _columns(assignment)


@router.post("/executions/{execution_id}/obligation-definitions")
def create_obligation_definition(execution_id: str, payload: ObligationDefinitionCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, ENGINEERING_ROLES)
    item = _execution(db, execution_id)
    definition = ConstructionObligationDefinition(project_id=item.project_id, **payload.model_dump(), created_by=role.value)
    db.add(definition); db.flush(); _audit(db, request, "CONSTRUCTION_OBLIGATION_DEFINED", "ConstructionObligationDefinition", definition.id, _columns(definition), role)
    db.commit(); db.refresh(definition); return _columns(definition)


@router.post("/executions/{execution_id}/obligations")
def create_obligation_instance(execution_id: str, payload: ObligationInstanceCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES)
    item = _execution(db, execution_id); definition = db.get(ConstructionObligationDefinition, payload.definition_id)
    if not definition or definition.project_id != item.project_id:
        raise HTTPException(409, "Obligation definition is outside the project")
    instance = ConstructionObligationInstance(project_id=item.project_id, construction_execution_id=item.id, definition_id=definition.id, authority_case_id=definition.authority_case_id, due_at=payload.due_at, created_by=role.value, instance_snapshot=_columns(definition))
    db.add(instance); db.flush()
    for party_id in payload.participant_party_ids:
        if not db.get(Party, party_id): raise HTTPException(409, f"Canonical party does not exist: {party_id}")
        db.add(ConstructionObligationParticipant(obligation_instance_id=instance.id, project_id=item.project_id, party_id=party_id, role_code="RESPONSIBLE", assigned_by=role.value))
    _audit(db, request, "CONSTRUCTION_OBLIGATION_CREATED", "ConstructionObligationInstance", instance.id, _columns(instance), role)
    db.commit(); db.refresh(instance); return _columns(instance)


@router.post("/executions/{execution_id}/notifications")
def prepare_notification(execution_id: str, payload: NotificationCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES)
    item = _execution(db, execution_id)
    existing = db.scalar(select(AuthorityNotification).where(AuthorityNotification.idempotency_key == payload.idempotency_key))
    if existing: return _columns(existing)
    notification = AuthorityNotification(project_id=item.project_id, construction_execution_id=item.id, authority_case_id=item.authority_case_id, **payload.model_dump(), prepared_by=role.value)
    db.add(notification); db.flush(); _audit(db, request, "AUTHORITY_NOTIFICATION_PREPARED", "AuthorityNotification", notification.id, _columns(notification), role)
    db.commit(); db.refresh(notification); return _columns(notification)


@router.post("/notifications/{notification_id}/send")
def record_notification_sent(notification_id: str, payload: NotificationSend, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES)
    notification = db.get(AuthorityNotification, notification_id)
    if not notification: raise HTTPException(404, "Authority notification not found")
    if notification.status == "SENT": return _columns(notification)
    if notification.status != "PREPARED": raise HTTPException(409, "Only a prepared notification can be recorded as sent")
    notification.status = "SENT"; notification.external_reference = payload.external_reference; notification.evidence_document_version_id = payload.evidence_document_version_id or notification.evidence_document_version_id; notification.sent_by = role.value; notification.sent_at = datetime.now(timezone.utc)
    _audit(db, request, "AUTHORITY_NOTIFICATION_SENT_RECORDED", "AuthorityNotification", notification.id, _columns(notification), role, metadata={"external_send_not_performed": True})
    db.commit(); db.refresh(notification); return _columns(notification)


@router.post("/executions/{execution_id}/correspondence")
def record_correspondence(execution_id: str, payload: CorrespondenceCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES)
    item = _execution(db, execution_id)
    record = ProjectCorrespondence(project_id=item.project_id, construction_execution_id=item.id, occurred_at=payload.occurred_at or datetime.now(timezone.utc), recorded_by=role.value, **payload.model_dump(exclude={"occurred_at"}))
    db.add(record); db.flush(); _audit(db, request, "CONSTRUCTION_CORRESPONDENCE_RECORDED", "ProjectCorrespondence", record.id, _columns(record), role)
    db.commit(); db.refresh(record); return _columns(record)


@router.post("/executions/{execution_id}/inspections")
def request_inspection(execution_id: str, payload: InspectionCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES)
    if payload.inspection_kind not in {"INTERNAL_SITE", "AUTHORITY"}:
        raise HTTPException(422, "inspection_kind must be INTERNAL_SITE or AUTHORITY")
    item = _execution(db, execution_id)
    if payload.idempotency_key:
        existing = db.scalar(select(ConstructionInspection).where(ConstructionInspection.construction_execution_id == item.id, ConstructionInspection.idempotency_key == payload.idempotency_key))
        if existing:
            return _columns(existing)
    inspection = ConstructionInspection(project_id=item.project_id, construction_execution_id=item.id, inspection_kind=payload.inspection_kind, requested_at=datetime.now(timezone.utc), recorded_by=role.value, **payload.model_dump(exclude={"inspection_kind"}))
    db.add(inspection)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        if payload.idempotency_key:
            existing = db.scalar(select(ConstructionInspection).where(ConstructionInspection.construction_execution_id == item.id, ConstructionInspection.idempotency_key == payload.idempotency_key))
            if existing:
                return _columns(existing)
        raise
    _audit(db, request, "CONSTRUCTION_INSPECTION_REQUESTED", "ConstructionInspection", inspection.id, _columns(inspection), role)
    db.commit(); db.refresh(inspection); return _columns(inspection)


@router.post("/inspections/{inspection_id}/record")
def record_inspection(inspection_id: str, payload: InspectionRecord, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES)
    inspection = db.get(ConstructionInspection, inspection_id)
    if not inspection: raise HTTPException(404, "Construction inspection not found")
    if inspection.status == "COMPLETED": return _columns(inspection)
    for key, value in payload.model_dump().items(): setattr(inspection, key, value)
    inspection.occurred_at = payload.occurred_at or datetime.now(timezone.utc); inspection.recorded_at = datetime.now(timezone.utc)
    _audit(db, request, "CONSTRUCTION_INSPECTION_RECORDED", "ConstructionInspection", inspection.id, _columns(inspection), role, metadata={"inspection_kind": inspection.inspection_kind, "authority_system_called": False})
    db.commit(); db.refresh(inspection); return _columns(inspection)


@router.post("/executions/{execution_id}/issues")
def create_issue(execution_id: str, payload: IssueCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES | {Role.RESPONSIBLE_ENGINEER})
    item = _execution(db, execution_id)
    if payload.authority_case_finding_id and not db.get(AuthorityCaseFinding, payload.authority_case_finding_id):
        raise HTTPException(409, "AuthorityCaseFinding does not exist")
    issue = ConstructionIssue(project_id=item.project_id, construction_execution_id=item.id, observed_by=role.value, **payload.model_dump())
    db.add(issue); db.flush(); _audit(db, request, "CONSTRUCTION_ISSUE_OPENED", "ConstructionIssue", issue.id, _columns(issue), role)
    db.commit(); db.refresh(issue); return _columns(issue)


@router.post("/issues/{issue_id}/resolve")
def resolve_issue(issue_id: str, payload: IssueResolve, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES | {Role.RESPONSIBLE_ENGINEER})
    issue = db.get(ConstructionIssue, issue_id)
    if not issue: raise HTTPException(404, "Construction issue not found")
    issue.status = "RESOLVED"; issue.resolution_notes = payload.resolution_notes; issue.evidence_document_version_ids = payload.evidence_document_version_ids; issue.resolved_by = role.value; issue.resolved_at = datetime.now(timezone.utc)
    _audit(db, request, "CONSTRUCTION_ISSUE_RESOLVED", "ConstructionIssue", issue.id, _columns(issue), role)
    db.commit(); db.refresh(issue); return _columns(issue)


@router.get("/executions/{execution_id}/readiness/latest")
def latest_readiness(execution_id: str, db: Session = Depends(get_db)):
    item = _execution(db, execution_id)
    result = db.scalar(select(ConstructionStartReadiness).where(ConstructionStartReadiness.construction_execution_id == item.id).order_by(ConstructionStartReadiness.evaluated_at.desc()))
    return _columns(result) if result else {"result": "NOT_EVALUATED", "blockers_json": []}


@router.get("/executions/{execution_id}/completion-context")
def completion_context(execution_id: str, db: Session = Depends(get_db)):
    """Read-only seam for the future completion/as-built/handover workstream."""
    item = _execution(db, execution_id)
    open_issues = db.scalars(select(ConstructionIssue).where(ConstructionIssue.construction_execution_id == item.id, ConstructionIssue.status.not_in(["RESOLVED", "CLOSED"]))).all()
    obligations = db.scalars(select(ConstructionObligationInstance).where(ConstructionObligationInstance.construction_execution_id == item.id)).all()
    inspections = db.scalars(select(ConstructionInspection).where(ConstructionInspection.construction_execution_id == item.id)).all()
    return {"construction_execution": _columns(item), "current_design_snapshot_id": item.current_design_snapshot_id, "work_state": item.work_state,
            "open_issue_ids": [x.id for x in open_issues], "obligation_ids": [x.id for x in obligations], "inspection_ids": [x.id for x in inspections],
            "completion_scope_deferred": True, "as_built_scope": "DEFERRED", "handover_scope": "DEFERRED", "financial_settlement_scope": "DEFERRED",
            "ready_for_future_completion_assessment": item.work_state in {"WORK_STOPPED", "POSTPONED"} and not open_issues}


@router.get("/executions/{execution_id}/history")
def execution_history(execution_id: str, db: Session = Depends(get_db)):
    item = _execution(db, execution_id)
    events = db.scalars(select(ConstructionWorkControlEvent).where(ConstructionWorkControlEvent.construction_execution_id == item.id).order_by(ConstructionWorkControlEvent.event_at)).all()
    return [_columns(event) for event in events]


class EvidenceLinkCreate(BaseModel):
    evidence_type: str
    document_version_id: str | None = None
    physical_evidence_item_id: str | None = None
    material_test_id: str | None = None
    description: str
    metadata_json: dict[str, Any] = Field(default_factory=dict)


@router.post("/executions/{execution_id}/evidence")
def link_evidence(execution_id: str, payload: EvidenceLinkCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES | ENGINEERING_ROLES)
    item = _execution(db, execution_id)
    if not any((payload.document_version_id, payload.physical_evidence_item_id, payload.material_test_id)):
        raise HTTPException(422, "At least one canonical evidence reference is required")
    if payload.document_version_id and not db.get(DocumentVersion, payload.document_version_id):
        raise HTTPException(409, "DocumentVersion does not exist")
    if payload.physical_evidence_item_id and not db.get(PhysicalEvidenceItem, payload.physical_evidence_item_id):
        raise HTTPException(409, "PhysicalEvidenceItem does not exist")
    if payload.material_test_id and not db.get(EngineeringMaterialTest, payload.material_test_id):
        raise HTTPException(409, "EngineeringMaterialTest does not exist")
    link = ConstructionEvidenceLink(project_id=item.project_id, construction_execution_id=item.id, captured_by=role.value, **payload.model_dump())
    db.add(link); db.flush(); _audit(db, request, "CONSTRUCTION_EVIDENCE_LINKED", "ConstructionEvidenceLink", link.id, _columns(link), role)
    db.commit(); db.refresh(link); return _columns(link)
