from datetime import datetime, timezone, date
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException
from ..models import *
from ..audit.service import audit
from .document_intelligence import RuleBasedDocumentClassifier, LocalSyntheticExtractor, sha256_for_source
from .normalization import normalize_candidate


def register_version(db: Session, *, project_id: str, document_type: str, logical_name: str, language: str, source_system: str, source_filename: str, source_path: str, content: str | None, metadata: dict[str, Any], correlation_id: str) -> DocumentVersion:
    digest, size = sha256_for_source(source_path, content)
    existing = db.scalar(select(DocumentVersion).join(Document).where(Document.project_id == project_id, DocumentVersion.sha256 == digest))
    if existing: return existing
    document = db.scalar(select(Document).where(Document.project_id == project_id, Document.logical_name == logical_name))
    if not document:
        document = Document(project_id=project_id, document_type=DocumentType(document_type), logical_name=logical_name, language=language, source_system=source_system)
        db.add(document); db.flush()
        audit(db, correlation_id=correlation_id, event_type="DOCUMENT_REGISTERED", entity_type="Document", entity_id=document.id, after={"logical_name": logical_name, "document_type": document_type})
    previous = db.scalar(select(DocumentVersion).where(DocumentVersion.document_id == document.id).order_by(DocumentVersion.version_number.desc()))
    def as_date(value):
        return date.fromisoformat(value) if isinstance(value, str) else value
    version = DocumentVersion(document_id=document.id, version_number=(previous.version_number + 1 if previous else 1), source_filename=source_filename, source_path_or_reference=source_path, sha256=digest, mime_type="application/pdf" if source_filename.lower().endswith(".pdf") else "text/plain", file_size=size, language=language, revision_label=metadata.get("revision_label"), document_date=None, valid_from=as_date(metadata.get("valid_from")), valid_until=as_date(metadata.get("valid_until")), approval_state=DocumentApprovalState.WORKING, source_system=source_system, metadata_json={**metadata, "synthetic_text": content or metadata.get("synthetic_text", "")})
    db.add(version); db.flush(); document.current_version_id = version.id
    if previous: previous.superseded_by = version.id; previous.approval_state = DocumentApprovalState.SUPERSEDED
    audit(db, correlation_id=correlation_id, event_type="DOCUMENT_VERSION_CREATED", entity_type="DocumentVersion", entity_id=version.id, after={"document_id": document.id, "version_number": version.version_number, "sha256": digest})
    return version


def classify_version(db: Session, version: DocumentVersion, correlation_id: str) -> DocumentClassification:
    result = RuleBasedDocumentClassifier().classify(version)
    classification = DocumentClassification(document_version_id=version.id, predicted_type=result.predicted_type, classification_method=result.method, model_or_rule_version=result.model_version, confidence=result.confidence, final_type=None, review_status=ClassificationReviewStatus.PENDING, evidence_json=result.evidence)
    db.add(classification); db.flush(); audit(db, correlation_id=correlation_id, event_type="DOCUMENT_CLASSIFIED", entity_type="DocumentClassification", entity_id=classification.id, after={"predicted_type": result.predicted_type, "confidence": result.confidence})
    return classification


def extract_version(db: Session, version: DocumentVersion, correlation_id: str) -> list[FieldObservation]:
    observations = LocalSyntheticExtractor().extract_candidate_fields(db, version, correlation_id)
    db.add_all(observations); db.flush()
    for item in observations: audit(db, correlation_id=correlation_id, event_type="FIELD_OBSERVED", entity_type="FieldObservation", entity_id=item.id, after={"field": item.field_definition_id, "method": item.extraction_method.value})
    return observations


def verify_observation(db: Session, observation: FieldObservation, *, actor_id: str, method: VerificationMethod, correction: str | None, correlation_id: str) -> VerifiedAssertion:
    source_value = correction if correction is not None else observation.normalized_candidate_value or observation.raw_value
    definition = db.get(FieldDefinition, observation.field_definition_id)
    if not definition: raise HTTPException(404, "Field definition not found")
    if correction is not None:
        corrected = FieldObservation(project_id=observation.project_id, field_definition_id=observation.field_definition_id, document_version_id=observation.document_version_id, raw_value=correction, normalized_candidate_value=normalize_candidate(correction, definition.normalization_rule), structured_value_json={"value": correction}, page_number=observation.page_number, bounding_box_json=observation.bounding_box_json, source_region_text=observation.source_region_text, extraction_method=ExtractionMethod.MANUAL_KEYED, extractor_version="VERIFICATION-CONSOLE-1.0", confidence=1.0, correlation_id=correlation_id)
        db.add(corrected); db.flush(); source_value = corrected.normalized_candidate_value or corrected.raw_value; source_observation_id = corrected.id; audit(db, correlation_id=correlation_id, event_type="FIELD_CORRECTED", entity_type="FieldObservation", entity_id=corrected.id, after={"supersedes_observation_id": observation.id})
    else: source_observation_id = observation.id
    for current in db.scalars(select(VerifiedAssertion).where(VerifiedAssertion.project_id == observation.project_id, VerifiedAssertion.field_definition_id == observation.field_definition_id, VerifiedAssertion.status == AssertionStatus.CURRENT)).all(): current.status = AssertionStatus.SUPERSEDED
    assertion = VerifiedAssertion(project_id=observation.project_id, field_definition_id=observation.field_definition_id, semantic_value_json={"value": source_value}, display_value=correction or observation.raw_value, status=AssertionStatus.CURRENT, source_observation_id=source_observation_id, verification_method=VerificationMethod.MANUAL_KEYED_VERIFIED if correction is not None else method, verified_by=actor_id, verified_at=datetime.now(timezone.utc), reason="Week 2 synthetic verification")
    db.add(assertion); db.flush(); audit(db, correlation_id=correlation_id, event_type="FIELD_VERIFIED", entity_type="VerifiedAssertion", entity_id=assertion.id, after={"field": definition.field_code, "display_value": assertion.display_value})
    return assertion


def compare_project_conflicts(db: Session, project_id: str, correlation_id: str) -> list[Conflict]:
    observations = db.scalars(select(FieldObservation).where(FieldObservation.project_id == project_id)).all()
    by_field: dict[str, list[FieldObservation]] = {}
    for item in observations: by_field.setdefault(item.field_definition_id, []).append(item)
    created = []
    for field_id, items in by_field.items():
        values = {item.normalized_candidate_value or item.raw_value for item in items}
        if len(values) <= 1: continue
        definition = db.get(FieldDefinition, field_id)
        severity = ConflictSeverity.CRITICAL if definition and definition.criticality == Criticality.CRITICAL else ConflictSeverity.MAJOR
        conflict = Conflict(project_id=project_id, field_definition_id=field_id, observation_ids_json=[i.id for i in items], severity=severity, status=ConflictStatus.OPEN, reason="Distinct source candidates remain unresolved; no fuzzy identity resolution applied.")
        db.add(conflict); db.flush(); audit(db, correlation_id=correlation_id, event_type="CONFLICT_CREATED", entity_type="Conflict", entity_id=conflict.id, after={"field": definition.field_code if definition else field_id, "severity": severity.value}); created.append(conflict)
    return created
