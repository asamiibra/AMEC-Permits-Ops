"""Dashboard Forms Governance Wave A commands and deterministic readiness."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..models import (
    DocumentVersion,
    MasterContentGovernanceProfile,
    MasterContentItem,
    MasterContentChangeEvent,
    MasterContentQualityFlag,
    MasterContentReadinessAssessment,
    MasterContentSourceProvenance,
    MasterContentSourceSection,
)

OWNERSHIP_VALUES = {"AMEC_OWNED", "EXTERNAL_OFFICIAL", "EXTERNAL_REFERENCE", "REFERENCE_SAMPLE", "NEEDS_REVIEW"}
ARTIFACT_KINDS = {"AUTHORITY_FORM", "AMEC_FORM", "CHECKLIST", "UNDERTAKING", "AUTHORIZATION", "SERVICE_REQUEST", "CERTIFICATE_DECLARATION", "TECHNICAL_WORKSHEET", "INVOICE", "HANDOVER", "OTHER", "UNKNOWN"}
CURRENTNESS_VALUES = {"UNVERIFIED", "VERIFIED_CURRENT", "VERIFIED_NOT_CURRENT", "NEEDS_REVIEW"}
LANGUAGE_VALUES = {"AR", "EN", "AR_EN_BILINGUAL", "OTHER"}
QUALITY_CODES = {
    "FILLED_SAMPLE", "PROJECT_SPECIFIC_DATA_PRESENT", "PII_PRESENT", "SIGNATURE_PRESENT", "STAMP_PRESENT", "FINANCIAL_DATA_PRESENT",
    "WATERMARK_PRESENT", "SCAN_ONLY", "CLEAN_MASTER_REQUIRED", "DUPLICATE_HASH", "DUPLICATE_HASH_CONTEXT_CONFLICT", "POSSIBLE_MISFILE", "MIXED_LOGICAL_CONTENT",
    "FORM_NUMBER_MISMATCH", "ISSUE_NUMBER_MISMATCH", "LANGUAGE_VARIANT_MISMATCH", "TRANSLATION_AMBIGUITY", "PDF_STRUCTURAL_WARNING", "CURRENTNESS_UNVERIFIED",
    "MISSING_REFERENCED_MASTER", "DOCX_NOT_PARAMETERIZED", "CONTENT_RECONCILIATION_REQUIRED", "SOR_MAPPING_DRIFT",
}
QUALITY_SEVERITIES = {"INFO", "WARNING", "BLOCKING"}
QUALITY_STATUSES = {"OPEN", "ACCEPTED_RISK", "RESOLVED", "NOT_APPLICABLE"}
LOCATOR_TYPES = {"PAGE_RANGE", "TEXT_LABEL", "TABLE_REGION", "OTHER"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _deny(code: str, status: int = 422, **details: Any) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, **details})


def ensure_profile(db: Session, item: MasterContentItem, *, ownership: str = "NEEDS_REVIEW") -> MasterContentGovernanceProfile:
    profile = db.scalar(select(MasterContentGovernanceProfile).where(MasterContentGovernanceProfile.master_content_item_id == item.id))
    if profile:
        return profile
    profile = MasterContentGovernanceProfile(master_content_item_id=item.id, content_ownership_class=ownership)
    db.add(profile)
    db.flush()
    return profile


def _profile_dict(profile: MasterContentGovernanceProfile | None) -> dict[str, Any]:
    if not profile:
        return {"content_ownership_class": "NEEDS_REVIEW", "artifact_kind": "UNKNOWN", "language_profile": "OTHER", "sensitivity_class": "NONE", "restricted_reference_sample": False, "currentness_status": "UNVERIFIED", "sensitivity_flags": []}
    flags = [name for name in ("contains_pii", "contains_signature", "contains_stamp", "contains_financial_data", "contains_project_specific_data") if getattr(profile, name)]
    return {
        "id": profile.id,
        "content_ownership_class": profile.content_ownership_class,
        "artifact_kind": profile.artifact_kind,
        "publisher_name": profile.publisher_name,
        "publisher_unit": profile.publisher_unit,
        "jurisdiction_text": profile.jurisdiction_text,
        "official_form_no": profile.official_form_no,
        "official_issue_no": profile.official_issue_no,
        "official_issue_date": profile.official_issue_date.isoformat() if profile.official_issue_date else None,
        "language_profile": profile.language_profile,
        "sensitivity_class": profile.sensitivity_class,
        "sensitivity_flags": flags,
        "contains_pii": profile.contains_pii,
        "contains_signature": profile.contains_signature,
        "contains_stamp": profile.contains_stamp,
        "contains_financial_data": profile.contains_financial_data,
        "contains_project_specific_data": profile.contains_project_specific_data,
        "restricted_reference_sample": profile.restricted_reference_sample,
        "currentness_status": profile.currentness_status,
        "currentness_verified_by": profile.currentness_verified_by,
        "currentness_verified_at": profile.currentness_verified_at.isoformat() if profile.currentness_verified_at else None,
        "currentness_verification_note": profile.currentness_verification_note,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    }


def _flag_dict(flag: MasterContentQualityFlag) -> dict[str, Any]:
    return {"id": flag.id, "code": flag.code, "severity": flag.severity, "status": flag.status, "description": flag.description, "evidence_note": flag.evidence_note, "recommended_next_action": flag.recommended_next_action, "document_version_id": flag.document_version_id, "raised_by": flag.raised_by, "raised_at": flag.raised_at.isoformat() if flag.raised_at else None, "resolved_by": flag.resolved_by, "resolved_at": flag.resolved_at.isoformat() if flag.resolved_at else None, "resolution": flag.resolution}


def _section_dict(section: MasterContentSourceSection) -> dict[str, Any]:
    return {"id": section.id, "section_key": section.section_key, "label": section.label, "document_version_id": section.document_version_id, "locator_type": section.locator_type, "page_start": section.page_start, "page_end": section.page_end, "locator_payload": section.locator_payload or {}, "description": section.description, "status": section.status, "created_by": section.created_by, "created_at": section.created_at.isoformat() if section.created_at else None, "updated_at": section.updated_at.isoformat() if section.updated_at else None}


def _provenance_dict(row: MasterContentSourceProvenance) -> dict[str, Any]:
    return {"id": row.id, "document_version_id": row.document_version_id, "obtained_from": row.obtained_from, "obtained_by": row.obtained_by, "obtained_at": row.obtained_at.isoformat() if row.obtained_at else None, "source_reference": row.source_reference, "ingest_batch": row.ingest_batch, "provenance_note": row.provenance_note, "evidence_reference": row.evidence_reference}


def evaluate_readiness(db: Session, item: MasterContentItem, version: DocumentVersion | None = None, *, persist: bool = True) -> dict[str, Any]:
    version = version or (db.get(DocumentVersion, item.current_document_version_id) if item.current_document_version_id else None)
    profile = ensure_profile(db, item)
    blockers: list[str] = []
    warnings: list[str] = []
    has_provenance = bool(version and db.scalar(select(MasterContentSourceProvenance.id).where(MasterContentSourceProvenance.document_version_id == version.id)))
    dimensions: dict[str, str] = {"SOURCE_IDENTITY": "PASS" if item.ref and version else "BLOCKED", "OWNERSHIP": "PASS" if profile.content_ownership_class != "NEEDS_REVIEW" else "BLOCKED", "PROVENANCE": "PASS" if has_provenance else "BLOCKED", "CURRENTNESS": "NOT_APPLICABLE_TO_MANUAL_READINESS", "SOURCE_QUALITY": "PASS", "SENSITIVITY_HANDLING": "PASS", "BASIC_APPLICABILITY": "PASS" if item.used_in else "WARNING", "DOWNSTREAM_MANUAL_USE_INTEGRATION": "NOT_APPLICABLE_TO_MANUAL_READINESS"}
    if not item.ref or not version:
        blockers.append("Source identity or current DocumentVersion is missing.")
    if not has_provenance:
        blockers.append("Source provenance has not been captured for the exact current version.")
    if profile.content_ownership_class == "NEEDS_REVIEW":
        blockers.append("Content ownership has not been established.")
    if profile.content_ownership_class in {"EXTERNAL_REFERENCE", "REFERENCE_SAMPLE"}:
        state = "REFERENCE_ONLY"
    elif profile.restricted_reference_sample:
        blockers.append("Restricted reference samples are excluded from production use.")
        state = "REFERENCE_ONLY"
    elif profile.content_ownership_class == "EXTERNAL_OFFICIAL":
        dimensions["CURRENTNESS"] = "PASS" if profile.currentness_status == "VERIFIED_CURRENT" else "BLOCKED"
        if profile.currentness_status != "VERIFIED_CURRENT":
            blockers.append("The external official source currentness is not verified.")
        state = "MANUAL_USE_READY" if profile.currentness_status == "VERIFIED_CURRENT" else "BLOCKED"
    else:
        state = "MANUAL_USE_READY"
    flags = db.scalars(select(MasterContentQualityFlag).where(MasterContentQualityFlag.master_content_item_id == item.id, MasterContentQualityFlag.status == "OPEN")).all()
    for flag in flags:
        if flag.severity == "BLOCKING":
            blockers.append(flag.description or flag.code)
        elif flag.severity in {"WARNING", "INFO"}:
            warnings.append(flag.description or flag.code)
    if any(getattr(profile, name) for name in ("contains_pii", "contains_signature", "contains_stamp", "contains_financial_data", "contains_project_specific_data")) and not profile.restricted_reference_sample:
        blockers.append("Sensitive or project-specific content requires approved restriction handling.")
        dimensions["SENSITIVITY_HANDLING"] = "BLOCKED"
    if profile.language_profile == "OTHER":
        warnings.append("Language profile needs review.")
    if blockers and state == "MANUAL_USE_READY":
        state = "BLOCKED"
    if profile.currentness_status == "VERIFIED_NOT_CURRENT" and state != "REFERENCE_ONLY":
        state = "SUPERSEDED"
    result = {"state": state, "blocking_reasons": list(dict.fromkeys(blockers)), "warnings": list(dict.fromkeys(warnings)), "last_evaluated_at": _now().isoformat(), "evaluator_version": "WAVE_A_1", "dimensions": dimensions, "document_version_id": version.id if version else None}
    if persist and version:
        assessment = MasterContentReadinessAssessment(master_content_item_id=item.id, document_version_id=version.id, evaluated_at=_now(), evaluator_version="WAVE_A_1", state=state, blocking_reasons=result["blocking_reasons"], warnings=result["warnings"], dimensions=dimensions, evidence={"ownership": profile.content_ownership_class, "currentness": profile.currentness_status})
        db.add(assessment)
        db.flush()
    return result


def governance_projection(db: Session, item: MasterContentItem, *, include_history: bool = False) -> dict[str, Any]:
    profile = db.scalar(select(MasterContentGovernanceProfile).where(MasterContentGovernanceProfile.master_content_item_id == item.id))
    version = db.get(DocumentVersion, item.current_document_version_id) if item.current_document_version_id else None
    flags = list(db.scalars(select(MasterContentQualityFlag).where(MasterContentQualityFlag.master_content_item_id == item.id).order_by(MasterContentQualityFlag.raised_at.desc())).all())
    sections = list(db.scalars(select(MasterContentSourceSection).where(MasterContentSourceSection.master_content_item_id == item.id, MasterContentSourceSection.status == "ACTIVE").order_by(MasterContentSourceSection.created_at)).all())
    provenance = list(db.scalars(select(MasterContentSourceProvenance).where(MasterContentSourceProvenance.document_version_id == version.id).order_by(MasterContentSourceProvenance.obtained_at.desc())).all()) if version else []
    readiness = evaluate_readiness(db, item, version, persist=False)
    result = {"profile": _profile_dict(profile), "provenance": [_provenance_dict(row) for row in provenance], "quality_flags": [_flag_dict(flag) for flag in flags], "source_sections": [_section_dict(row) for row in sections], "readiness": readiness, "badges": []}
    ownership = result["profile"]["content_ownership_class"]
    labels = {"AMEC_OWNED": "AMEC Owned", "EXTERNAL_OFFICIAL": "External Official", "EXTERNAL_REFERENCE": "Reference Only", "REFERENCE_SAMPLE": "Restricted Sample", "NEEDS_REVIEW": "Needs Review"}
    result["badges"].append(labels.get(ownership, ownership))
    if readiness["state"] == "BLOCKED": result["badges"].append("Blocked")
    if readiness["state"] == "MANUAL_USE_READY": result["badges"].append("Manual Use Ready")
    if include_history:
        result["readiness_history"] = [{"id": row.id, "state": row.state, "evaluated_at": row.evaluated_at.isoformat(), "document_version_id": row.document_version_id} for row in db.scalars(select(MasterContentReadinessAssessment).where(MasterContentReadinessAssessment.master_content_item_id == item.id).order_by(MasterContentReadinessAssessment.evaluated_at.desc()).limit(20)).all()]
    return result


def update_governance(db: Session, item: MasterContentItem, payload: dict[str, Any], *, actor: str, correlation_id: str) -> dict[str, Any]:
    profile = ensure_profile(db, item)
    before = _profile_dict(profile)
    for key in ("content_ownership_class", "artifact_kind", "publisher_name", "publisher_unit", "jurisdiction_text", "official_form_no", "official_issue_no", "language_profile", "sensitivity_class", "contains_pii", "contains_signature", "contains_stamp", "contains_financial_data", "contains_project_specific_data", "restricted_reference_sample", "currentness_verification_note"):
        if key in payload and payload[key] is not None:
            setattr(profile, key, payload[key])
    if profile.content_ownership_class not in OWNERSHIP_VALUES: raise _deny("OWNERSHIP_VALUE_INVALID")
    if profile.artifact_kind not in ARTIFACT_KINDS: raise _deny("ARTIFACT_KIND_INVALID")
    if profile.language_profile not in LANGUAGE_VALUES: raise _deny("LANGUAGE_PROFILE_INVALID")
    if "official_issue_date" in payload:
        value = payload["official_issue_date"]
        profile.official_issue_date = date.fromisoformat(value) if isinstance(value, str) else value
    audit(db, correlation_id=correlation_id, event_type="MASTER_CONTENT_GOVERNANCE_UPDATED", entity_type="MasterContentGovernanceProfile", entity_id=profile.id, actor_id=actor, before=before, after=_profile_dict(profile), metadata={"master_content_id": item.id})
    evaluate_readiness(db, item, persist=True)
    db.commit()
    return governance_projection(db, item, include_history=True)


def set_currentness(db: Session, item: MasterContentItem, *, action: str, actor: str, note: str | None, correlation_id: str) -> dict[str, Any]:
    profile = ensure_profile(db, item)
    action = action.upper()
    if action not in {"VERIFY_CURRENT", "MARK_NOT_CURRENT", "REVOKE"}: raise _deny("CURRENTNESS_ACTION_INVALID")
    previous = profile.currentness_status
    profile.currentness_status = {"VERIFY_CURRENT": "VERIFIED_CURRENT", "MARK_NOT_CURRENT": "VERIFIED_NOT_CURRENT", "REVOKE": "NEEDS_REVIEW"}[action]
    profile.currentness_verified_by = actor if action != "REVOKE" else None
    profile.currentness_verified_at = _now() if action != "REVOKE" else None
    profile.currentness_verification_note = note
    audit(db, correlation_id=correlation_id, event_type="MASTER_SOURCE_CURRENTNESS_CHANGED", entity_type="MasterContentGovernanceProfile", entity_id=profile.id, actor_id=actor, before={"currentness_status": previous}, after={"currentness_status": profile.currentness_status}, metadata={"action": action, "note": note})
    if previous != profile.currentness_status and item.current_document_version_id:
        event = MasterContentChangeEvent(master_content_id=item.id, previous_version_id=item.current_document_version_id, new_version_id=item.current_document_version_id, change_type="MASTER_CONTENT_CURRENTNESS_CHANGED", status="APPLIED", correlation_id=correlation_id, actor_or_system=actor, metadata_json={"ref": item.ref, "currentness_status": profile.currentness_status, "action": action}, event_type="MASTER_CONTENT_CURRENTNESS_REVOKED" if action == "REVOKE" else "MASTER_CONTENT_CURRENTNESS_CHANGED", content_type=item.content_type, business_ref=item.ref, change_kind="GOVERNANCE", change_reason=note or action, materiality="MATERIAL", source_hash=None)
        db.add(event)
        db.flush()
        from .master_content import propagate_master_change
        current = db.get(DocumentVersion, item.current_document_version_id)
        if current:
            propagate_master_change(db, event, item, current)
    evaluate_readiness(db, item, persist=True)
    db.commit()
    return governance_projection(db, item, include_history=True)


def add_provenance(db: Session, item: MasterContentItem, version: DocumentVersion, payload: dict[str, Any], *, actor: str, correlation_id: str) -> dict[str, Any]:
    obtained_at = payload.get("obtained_at")
    if isinstance(obtained_at, str):
        obtained_at = datetime.fromisoformat(obtained_at.replace("Z", "+00:00"))
    row = MasterContentSourceProvenance(id=str(uuid4()), document_version_id=version.id, obtained_from=payload["obtained_from"], obtained_by=payload.get("obtained_by") or actor, obtained_at=obtained_at or _now(), source_reference=payload.get("source_reference"), ingest_batch=payload.get("ingest_batch"), provenance_note=payload.get("provenance_note"), evidence_reference=payload.get("evidence_reference"))
    db.add(row)
    db.flush()
    audit(db, correlation_id=correlation_id, event_type="MASTER_SOURCE_PROVENANCE_RECORDED", entity_type="MasterContentSourceProvenance", entity_id=row.id, actor_id=actor, after={"document_version_id": version.id, "obtained_from": row.obtained_from})
    db.commit()
    return _provenance_dict(row)


def add_quality_flag(db: Session, item: MasterContentItem, payload: dict[str, Any], *, actor: str, correlation_id: str) -> dict[str, Any]:
    code = payload["code"].upper()
    severity = payload.get("severity", "WARNING").upper()
    if code not in QUALITY_CODES: raise _deny("QUALITY_FLAG_CODE_INVALID", code=code)
    if severity not in QUALITY_SEVERITIES: raise _deny("QUALITY_FLAG_SEVERITY_INVALID")
    duplicate = db.scalar(select(MasterContentQualityFlag).where(MasterContentQualityFlag.master_content_item_id == item.id, MasterContentQualityFlag.document_version_id == payload.get("document_version_id"), MasterContentQualityFlag.code == code, MasterContentQualityFlag.status == "OPEN"))
    if duplicate: return _flag_dict(duplicate)
    flag = MasterContentQualityFlag(id=str(uuid4()), master_content_item_id=item.id, document_version_id=payload.get("document_version_id") or item.current_document_version_id, code=code, severity=severity, status="OPEN", description=payload["description"], evidence_note=payload.get("evidence_note"), recommended_next_action=payload.get("recommended_next_action"), raised_by=actor)
    db.add(flag)
    db.flush()
    audit(db, correlation_id=correlation_id, event_type="MASTER_CONTENT_QUALITY_FLAG_RAISED", entity_type="MasterContentQualityFlag", entity_id=flag.id, actor_id=actor, after=_flag_dict(flag))
    evaluate_readiness(db, item, persist=True)
    db.commit()
    return _flag_dict(flag)


def resolve_quality_flag(db: Session, item: MasterContentItem, flag: MasterContentQualityFlag, *, status: str, resolution: str, actor: str, correlation_id: str) -> dict[str, Any]:
    status = status.upper()
    if status not in {"RESOLVED", "ACCEPTED_RISK", "NOT_APPLICABLE"}: raise _deny("QUALITY_FLAG_STATUS_INVALID")
    before = _flag_dict(flag)
    flag.status, flag.resolution, flag.resolved_by, flag.resolved_at = status, resolution, actor, _now()
    audit(db, correlation_id=correlation_id, event_type="MASTER_CONTENT_QUALITY_FLAG_RESOLVED" if status != "ACCEPTED_RISK" else "MASTER_CONTENT_QUALITY_RISK_ACCEPTED", entity_type="MasterContentQualityFlag", entity_id=flag.id, actor_id=actor, before=before, after=_flag_dict(flag))
    evaluate_readiness(db, item, persist=True)
    db.commit()
    return _flag_dict(flag)


def add_source_section(db: Session, item: MasterContentItem, payload: dict[str, Any], *, actor: str, correlation_id: str) -> dict[str, Any]:
    version = db.get(DocumentVersion, payload["document_version_id"])
    if not version or version.document_id != item.document_id: raise _deny("SOURCE_SECTION_VERSION_MISMATCH", 409)
    if payload.get("locator_type", "PAGE_RANGE").upper() not in LOCATOR_TYPES: raise _deny("SOURCE_SECTION_LOCATOR_INVALID")
    section = MasterContentSourceSection(id=str(uuid4()), master_content_item_id=item.id, document_version_id=version.id, section_key=payload["section_key"], label=payload["label"], locator_type=payload.get("locator_type", "PAGE_RANGE").upper(), page_start=payload.get("page_start"), page_end=payload.get("page_end"), locator_payload=payload.get("locator_payload") or {}, description=payload.get("description"), created_by=actor)
    db.add(section)
    db.flush()
    audit(db, correlation_id=correlation_id, event_type="MASTER_CONTENT_SOURCE_SECTION_CREATED", entity_type="MasterContentSourceSection", entity_id=section.id, actor_id=actor, after=_section_dict(section))
    db.commit()
    return _section_dict(section)


def update_source_section(db: Session, item: MasterContentItem, section: MasterContentSourceSection, payload: dict[str, Any], *, actor: str, correlation_id: str) -> dict[str, Any]:
    if "document_version_id" in payload:
        version = db.get(DocumentVersion, payload["document_version_id"])
        if not version or version.document_id != item.document_id:
            raise _deny("SOURCE_SECTION_VERSION_MISMATCH", 409)
        section.document_version_id = version.id
    for key in ("section_key", "label", "locator_type", "page_start", "page_end", "locator_payload", "description", "status"):
        if key in payload and payload[key] is not None:
            setattr(section, key, payload[key].upper() if key in {"locator_type", "status"} and isinstance(payload[key], str) else payload[key])
    if section.locator_type not in LOCATOR_TYPES: raise _deny("SOURCE_SECTION_LOCATOR_INVALID")
    audit(db, correlation_id=correlation_id, event_type="MASTER_CONTENT_SOURCE_SECTION_UPDATED", entity_type="MasterContentSourceSection", entity_id=section.id, actor_id=actor, after=_section_dict(section))
    db.commit()
    return _section_dict(section)


def source_blocker_rollup(db: Session) -> dict[str, int]:
    flags = db.scalars(select(MasterContentQualityFlag).where(MasterContentQualityFlag.status == "OPEN")).all()
    profiles = db.scalars(select(MasterContentGovernanceProfile)).all()
    return {"blocking": sum(1 for row in flags if row.severity == "BLOCKING"), "needs_review": sum(1 for row in flags if row.severity in {"WARNING", "INFO"}), "restricted_samples": sum(1 for row in profiles if row.restricted_reference_sample), "currentness_unknown": sum(1 for row in profiles if row.currentness_status in {"UNVERIFIED", "NEEDS_REVIEW"})}
