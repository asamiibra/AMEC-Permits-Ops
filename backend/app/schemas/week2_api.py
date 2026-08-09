from typing import Any
from pydantic import BaseModel, Field
from ..models import DatasetType, VerificationMethod, DocumentApprovalState


class DocumentCreate(BaseModel):
    document_type: str
    logical_name: str
    language: str = "EN"
    source_system: str = "SYNTHETIC_SYNOLOGY"
    source_filename: str
    source_path_or_reference: str
    content: str | None = None
    metadata_json: dict[str, Any] = {}


class VersionCreate(DocumentCreate):
    pass


class ClassifyPayload(BaseModel):
    final_type: str | None = None
    review_status: str | None = None


class ApprovalPatch(BaseModel):
    approval_state: DocumentApprovalState
    actor_id: str = "synthetic-reviewer"


class ManualObservationCreate(BaseModel):
    document_version_id: str
    field_code: str
    raw_value: str
    page_number: int = 1
    bounding_box_json: dict[str, Any] | None = None
    source_region_text: str | None = None


class VerifyPayload(BaseModel):
    method: VerificationMethod = VerificationMethod.HUMAN_VERIFIED
    corrected_value: str | None = None
    actor_id: str = "synthetic-reviewer"


class ConflictResolvePayload(BaseModel):
    resolution: str
    resolver: str = "synthetic-reviewer"
    status: str = "RESOLVED"


class SpikeCreate(BaseModel):
    dataset_name: str = "Synthetic Week 2 Worst-Case Corpus"
    dataset_type: DatasetType = DatasetType.SYNTHETIC
    environment: str = "TEST"
    notes: str | None = None


class GatePatch(BaseModel):
    real_document_test_approved: bool
    approved_test_location: str | None = None
    raw_access_roles: list[str] = []
    remote_raw_access_allowed: bool = False
    external_ai_allowed: bool = False
    approved_ai_provider: str | None = None
    approved_region: str | None = None
    retention_policy_reference: str | None = None
    approval_reference: str | None = None


class DraftPayload(BaseModel):
    state_json: dict[str, Any]


class ConfirmationCreate(BaseModel):
    application_id: str
    mode: str = "HUMAN_EVIDENCE"
    request_reference: str
    visible_status: str
    evidence_reference: str | None = None
    second_verifier: str | None = None
    notes: str | None = None
