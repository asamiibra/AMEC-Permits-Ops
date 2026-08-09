import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import DocumentType, DocumentVersion, DocumentClassification, DocumentApprovalState, ClassificationReviewStatus, FieldDefinition, FieldObservation, ExtractionMethod
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
