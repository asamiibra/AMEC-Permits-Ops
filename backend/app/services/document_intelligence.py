import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..audit.service import audit
from ..models import CandidateAssertion, DocumentType, DocumentVersion, DocumentClassification, DocumentApprovalState, ClassificationReviewStatus, FieldDefinition, FieldObservation, ExtractionMethod
from .intelligence_contracts import IntelligenceContractError, create_candidate_assertion, stable_hash
from .normalization import normalize_candidate


@dataclass
class ClassificationResult:
    predicted_type: str
    confidence: float
    method: str
    model_version: str
    evidence: dict[str, Any]


class DocumentClassifier(Protocol):
    def classify(self, version: DocumentVersion) -> ClassificationResult: ...


class RuleBasedDocumentClassifier:
    version = "RULES-W2-1.0"
    markers = [(DocumentType.TITLE_DEED, ("TITLE_DEED", "TITLE DEED", "PROPERTY DEED")), (DocumentType.OWNER_QID, ("OWNER_QID", "OWNER ID", "QID")), (DocumentType.AUTHORIZATION, ("AUTHORIZATION", "AUTH LETTER")), (DocumentType.COMMERCIAL_REGISTRATION, ("COMMERCIAL REGISTRATION", "CR_NUMBER", "CR:")), (DocumentType.SURVEY_PLAN, ("SURVEY PLAN", "SURVEY_PLAN")), (DocumentType.COORDINATE_REPORT, ("COORDINATE REPORT", "COORDINATE_REPORT")), (DocumentType.DRAWING_SET, ("DRAWING SET", "DRAWING_SET", "REVISION:")), (DocumentType.NOC, ("NOC", "NO OBJECTION"))]

    def classify(self, version: DocumentVersion) -> ClassificationResult:
        text = str(version.metadata_json.get("synthetic_text", "")).upper()
        for doc_type, candidates in self.markers:
            for marker in candidates:
                if marker in text:
                    return ClassificationResult(doc_type.value, 0.96, "RULE", self.version, {"marker": marker, "page": 1})
        return ClassificationResult(DocumentType.OTHER.value, 0.2, "RULE", self.version, {"reason": "No configured marker"})


class ModelDocumentClassifier:
    def classify(self, version: DocumentVersion) -> ClassificationResult:
        raise NotImplementedError("External/model classification is an extension seam, not enabled in Week 2")


class DocumentIntelligenceService:
    """Normalize governed document intelligence into P02 candidate envelopes.

    This boundary owns candidate identity and source-version supersession only.
    It never invokes review, promotion, projection, provider, retrieval, or
    module business commands.
    """

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _scope(*, scope_type: str, scope_id: str, project_id: str | None) -> tuple[str, str, str | None]:
        if not scope_type or not scope_id:
            raise IntelligenceContractError("DOCUMENT_INTELLIGENCE_SCOPE_REQUIRED")
        scope_type = scope_type.upper()
        if scope_type == "PROJECT":
            if project_id is None:
                project_id = scope_id
            if project_id != scope_id:
                raise IntelligenceContractError("DOCUMENT_INTELLIGENCE_PROJECT_SCOPE_MISMATCH")
        elif project_id is not None:
            raise IntelligenceContractError("DOCUMENT_INTELLIGENCE_NON_PROJECT_HAS_PROJECT_ID")
        return scope_type, scope_id, project_id

    def _validate_source_scope(self, *, scope_type: str, scope_id: str, project_id: str | None, observation: FieldObservation | None = None, version: DocumentVersion | None = None) -> None:
        if observation is not None and observation.project_id != project_id:
            raise IntelligenceContractError("DOCUMENT_INTELLIGENCE_OBSERVATION_PROJECT_MISMATCH")
        source_project_id = version.document.project_id if version is not None and version.document is not None else None
        if source_project_id is not None and source_project_id != project_id:
            raise IntelligenceContractError("DOCUMENT_INTELLIGENCE_SOURCE_PROJECT_MISMATCH")
        if project_id is not None and scope_type != "PROJECT":
            raise IntelligenceContractError("DOCUMENT_INTELLIGENCE_NON_PROJECT_SOURCE_MISMATCH")
        if project_id is not None and scope_id != project_id:
            raise IntelligenceContractError("DOCUMENT_INTELLIGENCE_PROJECT_SCOPE_MISMATCH")

    @staticmethod
    def _source_identity(candidate: CandidateAssertion) -> tuple[str | None, str | None, str | None]:
        return (
            candidate.source_document_version_id,
            candidate.source_observation_id,
            candidate.evidence_envelope_id,
        )

    def _mark_superseded(self, prior: list[CandidateAssertion]) -> None:
        for candidate in prior:
            candidate.status = "SUPERSEDED"

    def _persist_candidate(self, values: dict[str, Any]) -> CandidateAssertion:
        idempotency_key = values["idempotency_key"]
        existing = self.db.scalar(select(CandidateAssertion).where(CandidateAssertion.idempotency_key == idempotency_key))
        with self.db.begin_nested():
            candidate = create_candidate_assertion(self.db, values)
            if existing is not None:
                return candidate
            family = self.db.scalars(
                select(CandidateAssertion).where(
                    CandidateAssertion.scope_type == candidate.scope_type,
                    CandidateAssertion.scope_id == candidate.scope_id,
                    CandidateAssertion.subject_type == candidate.subject_type,
                    CandidateAssertion.subject_id == candidate.subject_id,
                    CandidateAssertion.assertion_code == candidate.assertion_code,
                    CandidateAssertion.producer_kind == candidate.producer_kind,
                    CandidateAssertion.producer_version == candidate.producer_version,
                    CandidateAssertion.producer_hash == candidate.producer_hash,
                    CandidateAssertion.status == "CURRENT",
                    CandidateAssertion.id != candidate.id,
                )
            ).all()
            prior = [item for item in family if self._source_identity(item) != self._source_identity(candidate)]
            self._mark_superseded(prior)
            audit(
                self.db,
                correlation_id=candidate.correlation_id,
                event_type="DOCUMENT_INTELLIGENCE_CANDIDATE_CREATED",
                entity_type="CandidateAssertion",
                entity_id=candidate.id,
                after={
                    "assertion_code": candidate.assertion_code,
                    "scope_type": candidate.scope_type,
                    "scope_id": candidate.scope_id,
                    "source_document_version_id": candidate.source_document_version_id,
                    "source_observation_id": candidate.source_observation_id,
                    "evidence_envelope_id": candidate.evidence_envelope_id,
                    "superseded_candidate_ids": [item.id for item in prior],
                    "verified_assertion_created": False,
                    "projection_created": False,
                },
            )
            if prior:
                candidate.supersedes_candidate_assertion_id = prior[-1].id
                self.db.flush()
            return candidate

    def from_field_observation(self, observation: FieldObservation, *, target_module: str | None = None, evidence_envelope_id: str | None = None) -> CandidateAssertion:
        version = self.db.get(DocumentVersion, observation.document_version_id)
        if version is None:
            raise IntelligenceContractError("DOCUMENT_INTELLIGENCE_SOURCE_VERSION_NOT_FOUND")
        definition = self.db.get(FieldDefinition, observation.field_definition_id)
        if definition is None:
            raise IntelligenceContractError("DOCUMENT_INTELLIGENCE_FIELD_DEFINITION_NOT_FOUND")
        if observation.normalized_candidate_value is None and not observation.structured_value_json:
            raise IntelligenceContractError("DOCUMENT_INTELLIGENCE_CANDIDATE_VALUE_UNRESOLVED")
        project_id = observation.project_id
        scope_type, scope_id, project_id = self._scope(scope_type="PROJECT", scope_id=project_id, project_id=project_id)
        self._validate_source_scope(scope_type=scope_type, scope_id=scope_id, project_id=project_id, observation=observation, version=version)
        value_json = observation.structured_value_json or {"value": observation.normalized_candidate_value}
        producer_version = observation.extractor_version
        producer_hash = stable_hash({"producer_kind": "FIELD_OBSERVATION", "producer_version": producer_version})
        identity = {
            "scope_type": scope_type,
            "scope_id": scope_id,
            "subject_type": "PROJECT",
            "subject_id": project_id,
            "assertion_code": definition.field_code,
            "producer_kind": "FIELD_OBSERVATION",
            "producer_version": producer_version,
            "producer_hash": producer_hash,
            "source_document_version_id": version.id,
            "source_observation_id": observation.id,
            "evidence_envelope_id": evidence_envelope_id,
            "value_hash": stable_hash(value_json),
        }
        values = {
            "idempotency_key": f"di:{stable_hash(identity)}",
            "correlation_id": observation.correlation_id,
            "scope_type": scope_type,
            "scope_id": scope_id,
            "project_id": project_id,
            "target_module": target_module,
            "subject_type": "PROJECT",
            "subject_id": project_id,
            "assertion_code": definition.field_code,
            "field_definition_id": definition.id,
            "value_json": value_json,
            "display_value": observation.normalized_candidate_value or observation.raw_value,
            "value_hash": stable_hash(value_json),
            "confidence": observation.confidence,
            "producer_kind": "FIELD_OBSERVATION",
            "producer_version": producer_version,
            "producer_hash": producer_hash,
            "source_document_version_id": version.id,
            "source_observation_id": observation.id,
            "evidence_envelope_id": evidence_envelope_id,
            "data_classification": "SYNTHETIC" if observation.document_version.metadata_json.get("synthetic_non_business_fixture") else "INTERNAL",
            "contains_sensitive_data": False,
            "status": "CURRENT",
        }
        return self._persist_candidate(values)

    def from_classifier_proposal(self, *, scope_type: str, scope_id: str, correlation_id: str, source_artifact_id: str, proposal: dict[str, Any], classifier_version: str, rules_version: str, taxonomy_revision: str, evidence_envelope_id: str | None = None, source_document_version_id: str | None = None, target_module: str | None = None) -> list[CandidateAssertion]:
        project_id = scope_id if scope_type == "PROJECT" else None
        scope_type, scope_id, project_id = self._scope(scope_type=scope_type, scope_id=scope_id, project_id=project_id)
        if not source_artifact_id:
            raise IntelligenceContractError("DOCUMENT_INTELLIGENCE_SOURCE_ID_REQUIRED")
        producer_hash = stable_hash({"classifier_version": classifier_version, "rules_version": rules_version, "taxonomy_revision": taxonomy_revision})
        common = {
            "correlation_id": correlation_id,
            "scope_type": scope_type,
            "scope_id": scope_id,
            "project_id": project_id,
            "target_module": target_module,
            "subject_type": "DOCUMENT",
            "subject_id": source_artifact_id,
            "field_definition_id": None,
            "producer_kind": "DOCUMENT_CLASSIFIER",
            "producer_version": classifier_version,
            "producer_hash": producer_hash,
            "source_document_version_id": source_document_version_id,
            "source_observation_id": None,
            "evidence_envelope_id": evidence_envelope_id,
            "data_classification": "SYNTHETIC" if proposal.get("semantic_lane", {}).get("real_content") is False else "INTERNAL",
            "contains_sensitive_data": False,
            "status": "CURRENT",
        }
        outputs: list[CandidateAssertion] = []
        for assertion_code, value_json in [("DOCUMENT_CLASSIFICATION_CANDIDATE", proposal)]:
            identity = {key: common[key] for key in ("scope_type", "scope_id", "subject_type", "subject_id", "producer_kind", "producer_version", "producer_hash", "source_document_version_id", "source_observation_id", "evidence_envelope_id")}
            identity.update({"assertion_code": assertion_code, "value_hash": stable_hash(value_json)})
            outputs.append(self._persist_candidate({**common, "idempotency_key": f"di:{stable_hash(identity)}", "assertion_code": assertion_code, "value_json": value_json, "display_value": None, "value_hash": stable_hash(value_json), "confidence": None}))
        relationship = proposal.get("relationship_resolution")
        if isinstance(relationship, dict) and relationship:
            assertion_code = "DOCUMENT_RELATIONSHIP_CANDIDATE"
            identity = {key: common[key] for key in ("scope_type", "scope_id", "subject_type", "subject_id", "producer_kind", "producer_version", "producer_hash", "source_document_version_id", "source_observation_id", "evidence_envelope_id")}
            identity.update({"assertion_code": assertion_code, "value_hash": stable_hash(relationship)})
            outputs.append(self._persist_candidate({**common, "idempotency_key": f"di:{stable_hash(identity)}", "assertion_code": assertion_code, "value_json": relationship, "display_value": None, "value_hash": stable_hash(relationship), "confidence": None}))
        return outputs


def normalize_field_observation(db: Session, observation: FieldObservation, *, target_module: str | None = None, evidence_envelope_id: str | None = None) -> CandidateAssertion:
    return DocumentIntelligenceService(db).from_field_observation(observation, target_module=target_module, evidence_envelope_id=evidence_envelope_id)


def normalize_classifier_proposal(db: Session, **kwargs: Any) -> list[CandidateAssertion]:
    return DocumentIntelligenceService(db).from_classifier_proposal(**kwargs)


class DocumentExtractor(Protocol):
    def extract_text(self, version: DocumentVersion) -> str: ...
    def extract_candidate_fields(self, db: Session, version: DocumentVersion, correlation_id: str) -> list[FieldObservation]: ...


class LocalSyntheticExtractor:
    version = "LOCAL-SYNTHETIC-EXTRACTOR-1.0"
    patterns = {
        "PROPERTY.PLOT_NUMBER": r"(?:PLOT|PLOT_NUMBER)\s*:\s*([^\n]+)", "PROPERTY.PIN": r"PIN\s*:\s*([^\n]+)",
        "PROPERTY.ZONE": r"ZONE\s*:\s*([^\n]+)", "PROPERTY.MUNICIPALITY": r"MUNICIPALITY\s*:\s*([^\n]+)",
        "OWNER.NAME_AR": r"OWNER_AR\s*:\s*([^\n]+)", "OWNER.NAME_EN": r"OWNER_EN\s*:\s*([^\n]+)",
        "OWNER.QID": r"QID\s*:\s*([^\n]+)", "OWNER.CR_NUMBER": r"CR(?:_NUMBER)?\s*:\s*([^\n]+)",
        "PERMIT.TYPE": r"PERMIT_TYPE\s*:\s*([^\n]+)", "DRAWING.REVISION": r"REVISION\s*:\s*([^\n]+)",
        "DRAWING.PROJECT_NUMBER": r"PROJECT\s*:\s*([^\n]+)",
    }

    def extract_text(self, version: DocumentVersion) -> str:
        if version.metadata_json.get("synthetic_text") is not None:
            return str(version.metadata_json["synthetic_text"])
        path = Path(version.source_path_or_reference)
        return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""

    def extract_candidate_fields(self, db: Session, version: DocumentVersion, correlation_id: str) -> list[FieldObservation]:
        text = self.extract_text(version)
        result = []
        for field_code, pattern in self.patterns.items():
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match: continue
            definition = db.scalar(select(FieldDefinition).where(FieldDefinition.field_code == field_code))
            if not definition: continue
            raw = match.group(1).strip()
            normalized = normalize_candidate(raw, definition.normalization_rule)
            result.append(FieldObservation(project_id=version.document.project_id, field_definition_id=definition.id, document_version_id=version.id, raw_value=raw, normalized_candidate_value=normalized, structured_value_json={"value": normalized}, page_number=1, bounding_box_json={"x": 72, "y": 600, "width": 300, "height": 16}, source_region_text=match.group(0), extraction_method=ExtractionMethod.OCR_RULE if version.metadata_json.get("poor_ocr") else ExtractionMethod.RULE, extractor_version=self.version, confidence=0.94 if not version.metadata_json.get("poor_ocr") else 0.45, correlation_id=correlation_id))
        return result


def sha256_for_source(source_reference: str, content: str | None = None) -> tuple[str, int]:
    path = Path(source_reference)
    if content is not None:
        data = content.encode("utf-8")
    elif path.exists() and path.is_file():
        data = path.read_bytes()
    else:
        data = source_reference.encode("utf-8")
    return hashlib.sha256(data).hexdigest(), len(data)
