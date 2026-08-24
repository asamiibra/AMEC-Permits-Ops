"""Owner-safe Handover and administrative closeout API."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from sqlalchemy import func, select, true
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..db import get_db
from ..models import *
from .dependencies import current_user_role


router = APIRouter(prefix="/api/handover", tags=["handover-admin-closeout"])
OWNER_ROLES = {Role.SYSTEM_ADMIN, Role.OWNER_SPONSOR}
ENGINEERING_ROLES = OWNER_ROLES | {Role.RESPONSIBLE_ENGINEER}
VIEW_ROLES = ENGINEERING_ROLES | {Role.PROCESS_CHAMPION, Role.REQUIREMENT_STEWARD, Role.PERMIT_PREPARER}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(jsonable_encoder(value), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _require(role: Role, allowed: set[Role], capability: str = "HANDOVER_CLOSEOUT") -> None:
    if role not in allowed:
        raise HTTPException(403, {"code": "CAPABILITY_DENIED", "capability": capability})


def _row(item: Any) -> dict[str, Any]:
    return jsonable_encoder({column.name: getattr(item, column.name) for column in item.__table__.columns})


def _audit(db: Session, request: Request, event: str, entity_type: str, entity_id: str, role: Role, after: Any, before: Any = None) -> None:
    audit(db, correlation_id=getattr(request.state, "correlation_id", "handover-missing"), event_type=event, entity_type=entity_type, entity_id=entity_id, actor_id=role.value, before=before, after=after, metadata={"synthetic_only": True, "handover_closeout": True})


def _package(db: Session, package_id: str, lock: bool = False) -> HandoverPackage:
    query = select(HandoverPackage).where(HandoverPackage.id == package_id)
    if lock:
        query = query.with_for_update()
    package = db.scalar(query)
    if not package:
        raise HTTPException(404, "Handover package not found")
    return package


def _revision(db: Session, revision_id: str, lock: bool = False) -> HandoverPackageRevision:
    query = select(HandoverPackageRevision).where(HandoverPackageRevision.id == revision_id)
    if lock:
        query = query.with_for_update()
    revision = db.scalar(query)
    if not revision:
        raise HTTPException(404, "Handover package revision not found")
    return revision


def _service(db: Session, service_id: str, lock: bool = False) -> ServiceEngagement:
    query = select(ServiceEngagement).where(ServiceEngagement.id == service_id)
    if lock:
        query = query.with_for_update()
    service = db.scalar(query)
    if not service:
        raise HTTPException(404, "Service engagement not found")
    return service


class ServiceEngagementCreate(BaseModel):
    project_id: str
    contract_id: str
    contract_revision_id: str
    service_ref: str
    service_offering_code: str
    scope_category_code: str | None = None
    description: str
    proposal_scope_item_id: str | None = None


class PolicyCreate(BaseModel):
    policy_code: str
    version: str
    required_renditions_json: dict[str, Any] = Field(default_factory=dict)
    distribution_rules_json: dict[str, Any] = Field(default_factory=dict)
    acceptance_rules_json: dict[str, Any] = Field(default_factory=dict)
    closeout_rules_json: dict[str, Any] = Field(default_factory=dict)
    source_document_version_id: str | None = None


class PackageCreate(BaseModel):
    project_id: str
    service_engagement_id: str
    contract_id: str
    package_ref: str
    contract_revision_id: str
    policy_version_id: str | None = None
    authority_case_outcome_id: str | None = None
    approved_design_baseline_id: str | None = None
    as_built_baseline_id: str | None = None


class ItemCreate(BaseModel):
    item_type: str
    label: str
    discipline: str | None = None
    required: bool = True
    required_renditions: list[str] = Field(default_factory=list)
    available_renditions: list[str] = Field(default_factory=list)
    source_type: str
    document_version_id: str | None = None
    rendered_artifact_id: str | None = None
    engineering_revision_id: str | None = None
    engineering_rendition_id: str | None = None
    as_built_baseline_id: str | None = None
    authority_case_id: str | None = None
    form_instance_id: str | None = None
    source_ref: str | None = None


class DistributionRequirementCreate(BaseModel):
    recipient_party_id: str | None = None
    recipient_role: str
    medium: str
    copy_type: str = "COPY"
    copy_count: int = Field(default=1, ge=1)
    item_ids: list[str] = Field(default_factory=list)
    acknowledgement_required: bool = True


class DistributionCreate(BaseModel):
    distribution_requirement_id: str | None = None
    recipient_party_id: str | None = None
    recipient_role: str
    medium: str
    copy_type: str = "COPY"
    copy_count: int = 1
    delivery_reference: str | None = None
    evidence_document_version_id: str | None = None
    idempotency_key: str


class ReceiptCreate(BaseModel):
    received_by_party_id: str | None = None
    received_by_ref: str
    evidence_document_version_id: str | None = None
    idempotency_key: str


class ParticipantCreate(BaseModel):
    party_id: str | None = None
    participant_ref: str
    participant_role: str
    authority_snapshot_json: dict[str, Any] = Field(default_factory=dict)
    required_signer: bool = False


class PunchCreate(BaseModel):
    package_item_id: str | None = None
    category: str = "REMARK"
    remark: str
    blocking: bool = True
    owner_ref: str | None = None


class PunchResolve(BaseModel):
    resolution: str
    evidence_document_version_id: str | None = None
    accepted_as_remark: bool = False


class AcceptanceCreate(BaseModel):
    acceptance_status: str
    signed_form_document_version_id: str | None = None
    signature_packet_id: str | None = None
    accepted_by_party_id: str | None = None
    evidence_reference: str | None = None
    idempotency_key: str


class CloseoutPolicyCreate(BaseModel):
    policy_code: str
    version: str
    required_axes: list[str]


class FinancialSettle(BaseModel):
    basis: str
    notes: str | None = None


class ArchiveRequest(BaseModel):
    reason: str


class RegulatoryAssessmentCreate(BaseModel):
    state: str = "CLOSED"
    authority_case_ids: list[str] = Field(default_factory=list)
    blocking_case_ids: list[str] = Field(default_factory=list)
    basis: str


def _readiness(db: Session, revision: HandoverPackageRevision, role: Role) -> HandoverReadiness:
    items = db.scalars(select(HandoverPackageItem).where(HandoverPackageItem.handover_package_revision_id == revision.id).order_by(HandoverPackageItem.display_order)).all()
    requirements = db.scalars(select(DistributionRequirement).where(DistributionRequirement.handover_package_revision_id == revision.id, DistributionRequirement.status == "REQUIRED")).all()
    checks: list[dict[str, Any]] = []
    item_ok = True
    for item in items:
        missing = sorted(set(item.required_renditions_json) - set(item.available_renditions_json))
        ok = item.status == "READY" and not missing
        item_ok = item_ok and (not item.required or ok)
        checks.append({"kind": "MANIFEST_ITEM", "item_id": item.id, "ready": ok, "missing_renditions": missing})
    # Release readiness is a readiness-to-release decision, not proof that a
    # future delivery has already happened. Delivery and receipt are later
    # immutable events and are checked by the acceptance route.
    physical_ok = True
    for requirement in requirements:
        ok = requirement.copy_count > 0 and bool(requirement.medium.strip())
        physical_ok = physical_ok and ok
        delivered = bool(db.scalar(select(func.count(HandoverDistribution.id)).where(HandoverDistribution.distribution_requirement_id == requirement.id, HandoverDistribution.status == "DELIVERED")))
        checks.append({"kind": "DISTRIBUTION_PLAN", "requirement_id": requirement.id, "ready": ok, "medium": requirement.medium, "delivery_recorded": delivered})
    digital_ok = item_ok
    state = "READY_FOR_RELEASE" if digital_ok and physical_ok else "NOT_READY"
    existing = db.scalar(select(HandoverReadiness).where(HandoverReadiness.handover_package_revision_id == revision.id).with_for_update())
    if not existing:
        existing = HandoverReadiness(handover_package_revision_id=revision.id, state=state, digital_ready=digital_ok, physical_ready=physical_ok, checks_json=checks, evaluated_by=role.value)
        db.add(existing)
    else:
        existing.state, existing.digital_ready, existing.physical_ready, existing.checks_json, existing.evaluated_at, existing.evaluated_by = state, digital_ok, physical_ok, checks, _now(), role.value
    return existing


def _validate_item_source(db: Session, data: dict[str, Any]) -> bool:
    source_map = {
        "DOCUMENT_VERSION": (DocumentVersion, "document_version_id"),
        "RENDERED_ARTIFACT": (RenderedArtifact, "rendered_artifact_id"),
        "ENGINEERING_REVISION": (EngineeringDeliverableRevision, "engineering_revision_id"),
        "ENGINEERING_RENDITION": (EngineeringRendition, "engineering_rendition_id"),
        "AS_BUILT_BASELINE": (AsBuiltBaseline, "as_built_baseline_id"),
        "AUTHORITY_CASE": (AuthorityCase, "authority_case_id"),
        "FORM_INSTANCE": (FormInstance, "form_instance_id"),
    }
    model_and_field = source_map.get(data.get("source_type"))
    if model_and_field:
        model, field = model_and_field
        source_id = data.get(field)
        if not source_id or not db.get(model, source_id):
            raise HTTPException(404, {"code": "HANDOVER_SOURCE_NOT_FOUND", "source_type": data.get("source_type"), "source_id": source_id})
        return True
    return bool(data.get("source_ref"))


@router.get("")
def list_handover(project_id: str | None = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, VIEW_ROLES)
    query = select(HandoverPackage).order_by(HandoverPackage.created_at.desc())
    if project_id:
        query = query.where(HandoverPackage.project_id == project_id)
    packages = db.scalars(query).all()
    return {"items": [_row(item) for item in packages], "count": len(packages)}


@router.post("/service-engagements")
def create_service_engagement(payload: ServiceEngagementCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES | ENGINEERING_ROLES, "SERVICE_SCOPE_CREATE")
    if not db.get(Project, payload.project_id) or not db.get(Contract, payload.contract_id) or not db.get(ContractRevision, payload.contract_revision_id):
        raise HTTPException(404, "Project, Contract, or exact ContractRevision not found")
    service = ServiceEngagement(created_by=role.value, **payload.model_dump())
    db.add(service)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(ServiceEngagement).where(ServiceEngagement.project_id == payload.project_id, ServiceEngagement.contract_id == payload.contract_id, ServiceEngagement.service_ref == payload.service_ref))
        if existing:
            return {"service_engagement": _row(existing), "idempotent": True}
        raise HTTPException(409, "Service engagement identity already exists")
    db.refresh(service)
    _audit(db, request, "SERVICE_ENGAGEMENT_CREATED", "ServiceEngagement", service.id, role, _row(service))
    db.commit()
    return {"service_engagement": _row(service), "idempotent": False}


@router.post("/policies")
def create_policy(payload: PolicyCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES, "HANDOVER_POLICY_MANAGE")
    policy = HandoverPolicyVersion(created_by=role.value, status="APPROVED", **payload.model_dump())
    db.add(policy); db.commit(); db.refresh(policy)
    _audit(db, request, "HANDOVER_POLICY_VERSIONED", "HandoverPolicyVersion", policy.id, role, _row(policy)); db.commit()
    return {"policy": _row(policy)}


@router.post("/packages")
def create_package(payload: PackageCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES | ENGINEERING_ROLES, "HANDOVER_CREATE")
    service = _service(db, payload.service_engagement_id)
    if service.project_id != payload.project_id or service.contract_id != payload.contract_id or service.contract_revision_id != payload.contract_revision_id:
        raise HTTPException(409, "Service scope and exact ContractRevision do not match")
    package = HandoverPackage(project_id=payload.project_id, service_engagement_id=payload.service_engagement_id, contract_id=payload.contract_id, package_ref=payload.package_ref, created_by=role.value)
    db.add(package); db.flush()
    revision = HandoverPackageRevision(handover_package_id=package.id, service_engagement_id=service.id, project_id=service.project_id, contract_id=service.contract_id, contract_revision_id=service.contract_revision_id, policy_version_id=payload.policy_version_id, authority_case_outcome_id=payload.authority_case_outcome_id, approved_design_baseline_id=payload.approved_design_baseline_id, as_built_baseline_id=payload.as_built_baseline_id, revision_number=1, manifest_hash=_hash({"package": package.id, "revision": 1}), created_by=role.value)
    db.add(revision); db.flush(); package.current_revision_id = revision.id
    _readiness(db, revision, role); db.commit(); db.refresh(package); db.refresh(revision)
    _audit(db, request, "HANDOVER_PACKAGE_CREATED", "HandoverPackage", package.id, role, {"package": _row(package), "revision": _row(revision)}); db.commit()
    return {"package": _row(package), "revision": _row(revision), "readiness": _row(_readiness(db, revision, role))}


@router.get("/{package_id}")
def get_package(package_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, VIEW_ROLES)
    package = _package(db, package_id)
    revision = _revision(db, package.current_revision_id) if package.current_revision_id else None
    if not revision:
        return {"package": _row(package), "revision": None, "axes": _project_axes(db, package.project_id)}
    return _workspace(db, package, revision, role)


@router.post("/{package_id}/revisions")
def create_revision(package_id: str, payload: PackageCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES | ENGINEERING_ROLES, "HANDOVER_MANIFEST_EDIT")
    package = _package(db, package_id, True)
    service = _service(db, package.service_engagement_id, True)
    latest = _revision(db, package.current_revision_id) if package.current_revision_id else None
    if latest and latest.status not in {"LOCKED", "RELEASED", "ACCEPTED", "ACCEPTED_WITH_REMARKS"}:
        raise HTTPException(409, "Current working revision must be locked before a new revision")
    number = (latest.revision_number + 1) if latest else 1
    revision = HandoverPackageRevision(handover_package_id=package.id, service_engagement_id=service.id, project_id=service.project_id, contract_id=service.contract_id, contract_revision_id=service.contract_revision_id, policy_version_id=payload.policy_version_id, authority_case_outcome_id=payload.authority_case_outcome_id, approved_design_baseline_id=payload.approved_design_baseline_id, as_built_baseline_id=payload.as_built_baseline_id, revision_number=number, manifest_hash=_hash({"package": package.id, "revision": number}), created_by=role.value)
    db.add(revision); db.flush(); package.current_revision_id = revision.id; _readiness(db, revision, role); db.commit(); db.refresh(revision)
    _audit(db, request, "HANDOVER_PACKAGE_REVISION_CREATED", "HandoverPackageRevision", revision.id, role, _row(revision)); db.commit()
    return {"revision": _row(revision)}


@router.post("/{package_id}/items")
def add_item(package_id: str, payload: ItemCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES | ENGINEERING_ROLES, "HANDOVER_MANIFEST_EDIT")
    package = _package(db, package_id, True); revision = _revision(db, package.current_revision_id, True)
    if revision.status != "DRAFT": raise HTTPException(409, "Locked package revisions are immutable; create HP2")
    order = (db.scalar(select(func.max(HandoverPackageItem.display_order)).where(HandoverPackageItem.handover_package_revision_id == revision.id)) or 0) + 1
    data = payload.model_dump(); required = set(data.pop("required_renditions")); available = set(data.pop("available_renditions")); source_ok = _validate_item_source(db, data); data["required_renditions_json"] = sorted(required); data["available_renditions_json"] = sorted(available); data["display_order"] = order; data["status"] = "READY" if (not required or required <= available) and source_ok else "MISSING"
    item = HandoverPackageItem(**data, handover_package_revision_id=revision.id); db.add(item); db.flush(); revision.manifest_hash = _hash([_row(x) for x in db.scalars(select(HandoverPackageItem).where(HandoverPackageItem.handover_package_revision_id == revision.id)).all()]); _readiness(db, revision, role); db.commit(); db.refresh(item)
    _audit(db, request, "HANDOVER_MANIFEST_ITEM_ADDED", "HandoverPackageItem", item.id, role, _row(item)); db.commit()
    return {"item": _row(item), "readiness": _row(_readiness(db, revision, role))}


@router.post("/{package_id}/lock")
def lock_package(package_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES, "HANDOVER_LOCK")
    package = _package(db, package_id, True); revision = _revision(db, package.current_revision_id, True)
    if revision.status != "DRAFT": raise HTTPException(409, "Only a working revision can be locked")
    readiness = _readiness(db, revision, role)
    if readiness.state != "READY_FOR_RELEASE": raise HTTPException(409, {"code": "HANDOVER_NOT_READY", "readiness": _row(readiness)})
    revision.status, revision.locked_by, revision.locked_at = "LOCKED", role.value, _now(); package.status = "READY_FOR_RELEASE"; db.commit()
    _audit(db, request, "HANDOVER_PACKAGE_LOCKED", "HandoverPackageRevision", revision.id, role, _row(revision)); db.commit()
    return {"revision": _row(revision), "readiness": _row(readiness)}


@router.post("/{package_id}/release")
def authorize_release(package_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES, "HANDOVER_RELEASE_AUTHORIZE")
    package = _package(db, package_id, True); revision = _revision(db, package.current_revision_id, True); readiness = _readiness(db, revision, role)
    if revision.status != "LOCKED" or readiness.state != "READY_FOR_RELEASE": raise HTTPException(409, "Locked and ready revision required")
    release = HandoverReleaseAuthorization(handover_package_revision_id=revision.id, readiness_id=readiness.id, authorized_by=role.value, delivery_plan_json={"human_authorized": True}); db.add(release); revision.status = "RELEASED"; package.status = "RELEASED"; db.commit(); db.refresh(release)
    _audit(db, request, "HANDOVER_RELEASE_AUTHORIZED", "HandoverReleaseAuthorization", release.id, role, _row(release)); db.commit()
    return {"release": _row(release), "revision": _row(revision)}


@router.post("/{package_id}/distribution-requirements")
def add_distribution_requirement(package_id: str, payload: DistributionRequirementCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES, "HANDOVER_DISTRIBUTION_PLAN")
    package = _package(db, package_id, True); revision = _revision(db, package.current_revision_id, True)
    if revision.status not in {"DRAFT", "LOCKED"}: raise HTTPException(409, "Distribution requirements require an unreleased revision")
    requirement = DistributionRequirement(handover_package_revision_id=revision.id, recipient_party_id=payload.recipient_party_id, recipient_role=payload.recipient_role, medium=payload.medium, copy_type=payload.copy_type, copy_count=payload.copy_count, item_ids_json=payload.item_ids, acknowledgement_required=payload.acknowledgement_required, created_by=role.value); db.add(requirement); db.commit(); db.refresh(requirement)
    return {"requirement": _row(requirement), "physical_ready": False}


@router.post("/{package_id}/distributions")
def record_distribution(package_id: str, payload: DistributionCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES, "HANDOVER_DISTRIBUTION_RECORD")
    package = _package(db, package_id, True); revision = _revision(db, package.current_revision_id, True)
    if revision.status not in {"RELEASED", "DELIVERED"}: raise HTTPException(409, "Human release authorization required before delivery")
    existing = db.scalar(select(HandoverDistribution).where(HandoverDistribution.idempotency_key == payload.idempotency_key))
    if existing: return {"distribution": _row(existing), "idempotent": True}
    event = HandoverDistribution(**payload.model_dump(), handover_package_revision_id=revision.id, status="DELIVERED", delivered_by=role.value, delivered_at=_now()); db.add(event); revision.status = "DELIVERED"; package.status = "DELIVERED"; db.commit(); db.refresh(event)
    _audit(db, request, "HANDOVER_DISTRIBUTION_RECORDED", "HandoverDistribution", event.id, role, _row(event)); db.commit()
    return {"distribution": _row(event), "idempotent": False}


@router.post("/distributions/{distribution_id}/receipt")
def record_receipt(distribution_id: str, payload: ReceiptCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES, "HANDOVER_RECEIPT_RECORD")
    event = db.scalar(select(HandoverDistribution).where(HandoverDistribution.id == distribution_id).with_for_update())
    if not event: raise HTTPException(404, "Distribution not found")
    existing = db.scalar(select(HandoverReceipt).where(HandoverReceipt.idempotency_key == payload.idempotency_key))
    if existing: return {"receipt": _row(existing), "idempotent": True}
    receipt = HandoverReceipt(**payload.model_dump(), distribution_id=event.id, received_at=_now(), recorded_by=role.value); db.add(receipt); db.commit(); db.refresh(receipt)
    _audit(db, request, "HANDOVER_RECEIPT_RECORDED", "HandoverReceipt", receipt.id, role, _row(receipt)); db.commit()
    return {"receipt": _row(receipt), "idempotent": False}


@router.post("/{package_id}/participants")
def add_participant(package_id: str, payload: ParticipantCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES | ENGINEERING_ROLES, "HANDOVER_PARTICIPANTS")
    package = _package(db, package_id, True); revision = _revision(db, package.current_revision_id, True)
    if revision.status != "DRAFT": raise HTTPException(409, "Participants are pinned before lock; create HP2")
    participant = HandoverParticipant(**payload.model_dump(), handover_package_revision_id=revision.id); db.add(participant); db.commit(); db.refresh(participant)
    return {"participant": _row(participant)}


@router.post("/{package_id}/punch")
def add_punch(package_id: str, payload: PunchCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES | ENGINEERING_ROLES, "HANDOVER_PUNCH_MANAGE")
    package = _package(db, package_id, True); revision = _revision(db, package.current_revision_id, True)
    punch = HandoverPunchItem(**payload.model_dump(), handover_package_revision_id=revision.id, created_by=role.value); db.add(punch); db.commit(); db.refresh(punch)
    return {"punch": _row(punch), "service_close_blocked": bool(punch.blocking)}


@router.post("/punch/{punch_id}/resolve")
def resolve_punch(punch_id: str, payload: PunchResolve, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES | ENGINEERING_ROLES, "HANDOVER_PUNCH_MANAGE")
    punch = db.scalar(select(HandoverPunchItem).where(HandoverPunchItem.id == punch_id).with_for_update())
    if not punch: raise HTTPException(404, "Handover punch item not found")
    punch.resolution, punch.resolution_evidence_document_version_id, punch.resolved_by, punch.resolved_at = payload.resolution, payload.evidence_document_version_id, role.value, _now(); punch.status = "ACCEPTED_AS_REMARK" if payload.accepted_as_remark else "RESOLVED"; db.commit(); db.refresh(punch)
    return {"punch": _row(punch)}


@router.post("/{package_id}/acceptance")
def record_acceptance(package_id: str, payload: AcceptanceCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES, "HANDOVER_ACCEPTANCE_RECORD")
    package = _package(db, package_id, True); revision = _revision(db, package.current_revision_id, True)
    if revision.status not in {"DELIVERED", "RECEIVED"}: raise HTTPException(409, "Distribution and delivery are required before acceptance")
    if payload.acceptance_status == "ACCEPTED_WITH_REMARKS":
        policy = db.get(HandoverPolicyVersion, revision.policy_version_id) if revision.policy_version_id else None
        if not policy or not policy.acceptance_rules_json.get("accepted_with_remarks"):
            raise HTTPException(409, "Acceptance with remarks is disabled by policy")
    open_blocking = db.scalar(select(func.count(HandoverPunchItem.id)).where(HandoverPunchItem.handover_package_revision_id == revision.id, HandoverPunchItem.blocking == true(), HandoverPunchItem.status.in_({"OPEN", "ACTION_REQUIRED", "UNDER_REVIEW"}))) or 0
    if open_blocking and payload.acceptance_status == "ACCEPTED": raise HTTPException(409, "Blocking Handover punch remains open")
    existing = db.scalar(select(HandoverAcceptance).where(HandoverAcceptance.idempotency_key == payload.idempotency_key))
    if existing: return {"acceptance": _row(existing), "idempotent": True}
    participant_snapshot = [_row(x) for x in db.scalars(select(HandoverParticipant).where(HandoverParticipant.handover_package_revision_id == revision.id)).all()]; punch_snapshot = [_row(x) for x in db.scalars(select(HandoverPunchItem).where(HandoverPunchItem.handover_package_revision_id == revision.id)).all()]
    acceptance = HandoverAcceptance(**payload.model_dump(), handover_package_revision_id=revision.id, participant_snapshot_json=participant_snapshot, punch_snapshot_json=punch_snapshot, accepted_at=_now(), recorded_by=role.value); db.add(acceptance); revision.status = payload.acceptance_status; package.status = payload.acceptance_status; db.commit(); db.refresh(acceptance)
    _audit(db, request, "HANDOVER_ACCEPTANCE_RECORDED", "HandoverAcceptance", acceptance.id, role, _row(acceptance)); db.commit()
    return {"acceptance": _row(acceptance), "idempotent": False}


@router.post("/{package_id}/service-close")
def close_service(package_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES, "SERVICE_SCOPE_CLOSE")
    package = _package(db, package_id, True); revision = _revision(db, package.current_revision_id, True); service = _service(db, package.service_engagement_id, True)
    acceptance = db.scalar(select(HandoverAcceptance).where(HandoverAcceptance.handover_package_revision_id == revision.id))
    if not acceptance or acceptance.acceptance_status not in {"ACCEPTED", "ACCEPTED_WITH_REMARKS"}: raise HTTPException(409, "External Handover acceptance is required")
    existing = db.scalar(select(ServiceScopeClosure).where(ServiceScopeClosure.service_engagement_id == service.id))
    if existing: return {"service_scope_closure": _row(existing), "idempotent": True}
    closure = ServiceScopeClosure(service_engagement_id=service.id, project_id=service.project_id, contract_id=service.contract_id, contract_revision_id=service.contract_revision_id, handover_package_revision_id=revision.id, handover_acceptance_id=acceptance.id, closure_basis="EXPLICIT_HANDOVER_ACCEPTANCE", closed_by=role.value); db.add(closure); service.status, service.closed_at = "CLOSED", _now(); db.commit(); db.refresh(closure)
    _audit(db, request, "SERVICE_SCOPE_CLOSED", "ServiceScopeClosure", closure.id, role, _row(closure)); db.commit()
    return {"service_scope_closure": _row(closure), "other_active_services": [_row(x) for x in db.scalars(select(ServiceEngagement).where(ServiceEngagement.contract_id == service.contract_id, ServiceEngagement.status == "ACTIVE")).all()]}


@router.post("/{package_id}/contract-admin-close")
def close_contract_admin(package_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES, "CONTRACT_ADMIN_CLOSE")
    package = _package(db, package_id, True); service = _service(db, package.service_engagement_id, True)
    services = db.scalars(select(ServiceEngagement).where(ServiceEngagement.contract_id == service.contract_id)).all()
    if any(x.status != "CLOSED" for x in services): raise HTTPException(409, "Required service engagements remain active")
    if not db.get(ContractRevision, service.contract_revision_id): raise HTTPException(409, "Exact ContractRevision is missing")
    existing = db.scalar(select(ContractAdministrativeClosure).where(ContractAdministrativeClosure.contract_id == service.contract_id))
    if existing: return {"contract_administrative_closure": _row(existing), "idempotent": True}
    closure = ContractAdministrativeClosure(contract_id=service.contract_id, project_id=service.project_id, contract_revision_id=service.contract_revision_id, service_closure_ids_json=[x.id for x in services], closed_by=role.value, evidence_json={"financial_settlement_separate": True, "project_archive_separate": True}); db.add(closure); db.commit(); db.refresh(closure)
    return {"contract_administrative_closure": _row(closure), "financial_settlement": "SEPARATE", "project_archive": "SEPARATE"}


@router.post("/projects/{project_id}/regulatory-assessment")
def assess_regulatory_closeout(project_id: str, payload: RegulatoryAssessmentCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES | ENGINEERING_ROLES, "REGULATORY_CLOSEOUT_ASSESS")
    if not db.get(Project, project_id):
        raise HTTPException(404, "Project not found")
    if payload.state == "CLOSED" and payload.blocking_case_ids:
        raise HTTPException(409, "Blocking AuthorityCases prevent regulatory closeout")
    assessment = db.scalar(select(RegulatoryCloseoutAssessment).where(RegulatoryCloseoutAssessment.project_id == project_id, RegulatoryCloseoutAssessment.service_engagement_id.is_(None)).with_for_update())
    data = {"state": payload.state, "authority_case_ids_json": payload.authority_case_ids, "blocking_case_ids_json": payload.blocking_case_ids, "assessment_json": {"basis": payload.basis, "authority_case_mutated": False}, "assessed_by": role.value, "assessed_at": _now()}
    if not assessment:
        assessment = RegulatoryCloseoutAssessment(project_id=project_id, service_engagement_id=None, **data)
        db.add(assessment)
    else:
        for key, value in data.items():
            setattr(assessment, key, value)
    db.commit(); db.refresh(assessment)
    return {"assessment": _row(assessment), "authority_case_mutated": False, "completion_certificate_not_substituted": True}


def _project_axes(db: Session, project_id: str) -> dict[str, Any]:
    services = db.scalars(select(ServiceEngagement).where(ServiceEngagement.project_id == project_id)).all(); contracts = {x.contract_id for x in services}; closed_contracts = {x.contract_id for x in db.scalars(select(ContractAdministrativeClosure).where(ContractAdministrativeClosure.project_id == project_id)).all()}; financial = db.scalar(select(FinancialSettlementRecord).where(FinancialSettlementRecord.project_id == project_id)); regulatory = db.scalar(select(RegulatoryCloseoutAssessment).where(RegulatoryCloseoutAssessment.project_id == project_id, RegulatoryCloseoutAssessment.service_engagement_id.is_(None), RegulatoryCloseoutAssessment.state == "CLOSED")); archived = db.scalar(select(ProjectArchiveRecord).where(ProjectArchiveRecord.project_id == project_id)); return {"service_scope": "CLOSED" if services and all(x.status == "CLOSED" for x in services) else "ACTIVE", "handover": "ACCEPTED" if db.scalar(select(func.count(HandoverAcceptance.id)).join(HandoverPackageRevision, HandoverAcceptance.handover_package_revision_id == HandoverPackageRevision.id).where(HandoverPackageRevision.project_id == project_id)) else "NEEDS_REVIEW", "contract_admin": "CLOSED" if contracts and contracts <= closed_contracts else "OPEN", "financial": "SETTLED" if financial else "NEEDS_REVIEW", "regulatory": "CLOSED" if regulatory else "NEEDS_REVIEW", "archive": "ARCHIVED" if archived else "NOT_ARCHIVED"}


@router.get("/projects/{project_id}/closeout")
def get_project_closeout(project_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, VIEW_ROLES)
    assessment = db.scalar(select(ProjectCloseoutAssessment).where(ProjectCloseoutAssessment.project_id == project_id).with_for_update())
    axes = _project_axes(db, project_id)
    if not assessment:
        assessment = ProjectCloseoutAssessment(project_id=project_id, axes_json=axes, assessed_by=role.value); db.add(assessment); db.commit(); db.refresh(assessment)
    return {"assessment": _row(assessment), "axes": axes, "archive_allowed": assessment.archive_state == "READY"}


@router.post("/projects/{project_id}/closeout-policy")
def create_closeout_policy(project_id: str, payload: CloseoutPolicyCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES, "PROJECT_CLOSEOUT_POLICY")
    policy = ProjectCloseoutPolicyVersion(policy_code=payload.policy_code, version=payload.version, required_axes_json=payload.required_axes, status="APPROVED", created_by=role.value); db.add(policy); db.flush()
    assessment = db.scalar(select(ProjectCloseoutAssessment).where(ProjectCloseoutAssessment.project_id == project_id).with_for_update())
    if not assessment:
        assessment = ProjectCloseoutAssessment(project_id=project_id, assessed_by=role.value)
        db.add(assessment)
    assessment.policy_version_id = policy.id
    assessment.archive_state = "NEEDS_REVIEW"
    assessment.axes_json = _project_axes(db, project_id)
    db.commit(); db.refresh(policy)
    return {"policy": _row(policy)}


def _financial_context(db: Session, project_id: str, contract_id: str, role: Role) -> FinancialSettlementContext:
    invoices = db.scalars(select(Invoice).where(Invoice.project_id == project_id, Invoice.contract_id == contract_id)).all()
    terminal = {"PAID", "SETTLED", "CLOSED"}
    open_invoices = [invoice for invoice in invoices if invoice.status not in terminal]
    unsupported = []
    if not invoices:
        unsupported.append("ZERO_RECEIVABLE_IS_NOT_SETTLED")
    if open_invoices:
        unsupported.append("OPEN_OR_UNVERIFIED_INVOICES")
    state = "READY_FOR_SETTLEMENT" if invoices and not unsupported else "NEEDS_REVIEW"
    snapshot = {"billing_source": "CANONICAL_BILLING_READ_ONLY", "invoice_count": len(invoices), "invoice_statuses": {invoice.id: invoice.status for invoice in invoices}, "open_invoice_ids": [invoice.id for invoice in open_invoices]}
    context = db.scalar(select(FinancialSettlementContext).where(FinancialSettlementContext.project_id == project_id, FinancialSettlementContext.contract_id == contract_id).with_for_update())
    if not context:
        context = FinancialSettlementContext(contract_id=contract_id, project_id=project_id, readiness_state=state, snapshot_json=snapshot, snapshot_hash=_hash(snapshot), unsupported_conditions_json=unsupported, assessed_by=role.value)
        db.add(context)
    else:
        context.readiness_state, context.snapshot_json, context.snapshot_hash, context.unsupported_conditions_json, context.assessed_by, context.assessed_at = state, snapshot, _hash(snapshot), unsupported, role.value, _now()
    db.flush()
    return context


@router.get("/projects/{project_id}/financial-settlement")
def get_financial_settlement_context(project_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, VIEW_ROLES)
    contract_id = db.scalar(select(ServiceEngagement.contract_id).where(ServiceEngagement.project_id == project_id).limit(1))
    if not contract_id:
        raise HTTPException(409, "No scoped Contract is available")
    context = _financial_context(db, project_id, contract_id, role)
    db.commit(); db.refresh(context)
    return {"context": _row(context), "billing_mutated": False, "settlement_is_human_event": True}


@router.post("/projects/{project_id}/financial-settlement")
def confirm_financial_settlement(project_id: str, payload: FinancialSettle, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES, "FINANCIAL_SETTLEMENT_CONFIRM")
    contract_id = db.scalar(select(ServiceEngagement.contract_id).where(ServiceEngagement.project_id == project_id).limit(1))
    if not contract_id: raise HTTPException(409, "No scoped Contract is available")
    context = _financial_context(db, project_id, contract_id, role)
    if context.readiness_state != "READY_FOR_SETTLEMENT": raise HTTPException(409, "Financial settlement is not ready")
    existing = db.scalar(select(FinancialSettlementRecord).where(FinancialSettlementRecord.project_id == project_id, FinancialSettlementRecord.contract_id == contract_id))
    if existing: return {"settlement": _row(existing), "idempotent": True}
    record = FinancialSettlementRecord(contract_id=contract_id, project_id=project_id, context_id=context.id, snapshot_hash=context.snapshot_hash, basis=payload.basis, notes=payload.notes, settled_by=role.value); db.add(record); db.commit(); db.refresh(record)
    return {"settlement": _row(record), "idempotent": False, "billing_mutated": False}


@router.post("/projects/{project_id}/archive")
def archive_project(project_id: str, payload: ArchiveRequest, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _require(role, OWNER_ROLES, "PROJECT_ARCHIVE")
    if db.scalar(select(ProjectArchiveRecord).where(ProjectArchiveRecord.project_id == project_id)): raise HTTPException(409, "Project is already archived")
    assessment = db.scalar(select(ProjectCloseoutAssessment).where(ProjectCloseoutAssessment.project_id == project_id).with_for_update())
    if not assessment or not assessment.policy_version_id: raise HTTPException(409, "NEEDS_CLOSEOUT_POLICY")
    policy = db.get(ProjectCloseoutPolicyVersion, assessment.policy_version_id); axes = _project_axes(db, project_id)
    if any(axes.get(axis.lower(), axes.get(axis, "NEEDS_REVIEW")) not in {"CLOSED", "SETTLED", "ACCEPTED", "ARCHIVED"} for axis in policy.required_axes_json): raise HTTPException(409, {"code": "PROJECT_ARCHIVE_NOT_READY", "axes": axes})
    record = ProjectArchiveRecord(project_id=project_id, assessment_id=assessment.id, archived_by=role.value, reason=payload.reason); db.add(record); db.commit(); db.refresh(record)
    return {"archive": _row(record), "non_destructive": True, "property_preserved": True, "authority_cases_unchanged": True}


def _workspace(db: Session, package: HandoverPackage, revision: HandoverPackageRevision, role: Role) -> dict[str, Any]:
    readiness = _readiness(db, revision, role); return {"package": _row(package), "revision": _row(revision), "readiness": _row(readiness), "items": [_row(x) for x in db.scalars(select(HandoverPackageItem).where(HandoverPackageItem.handover_package_revision_id == revision.id).order_by(HandoverPackageItem.display_order)).all()], "requirements": [_row(x) for x in db.scalars(select(DistributionRequirement).where(DistributionRequirement.handover_package_revision_id == revision.id)).all()], "distributions": [_row(x) for x in db.scalars(select(HandoverDistribution).where(HandoverDistribution.handover_package_revision_id == revision.id)).all()], "receipts": [_row(x) for x in db.scalars(select(HandoverReceipt).join(HandoverDistribution, HandoverReceipt.distribution_id == HandoverDistribution.id).where(HandoverDistribution.handover_package_revision_id == revision.id)).all()], "participants": [_row(x) for x in db.scalars(select(HandoverParticipant).where(HandoverParticipant.handover_package_revision_id == revision.id)).all()], "punch": [_row(x) for x in db.scalars(select(HandoverPunchItem).where(HandoverPunchItem.handover_package_revision_id == revision.id)).all()], "acceptance": _row(db.scalar(select(HandoverAcceptance).where(HandoverAcceptance.handover_package_revision_id == revision.id))) if db.scalar(select(HandoverAcceptance).where(HandoverAcceptance.handover_package_revision_id == revision.id)) else None, "axes": _project_axes(db, package.project_id)}
