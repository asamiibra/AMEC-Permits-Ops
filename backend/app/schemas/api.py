from datetime import date, datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
from ..models import ApplicationStatus, DecisionStatus, InquiryStatus, RaidType, SystemType


class ProjectCreate(BaseModel):
    project_number: str = Field(min_length=3, max_length=50)
    project_name: str = Field(min_length=2, max_length=200)
    workstream: str = "BUILDING_PERMIT"
    status: str = "ACTIVE"
    municipality: str
    permit_type: str
    assigned_engineer: str | None = None


class ProjectOut(ProjectCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    office_id: str
    created_at: datetime
    updated_at: datetime


class LinkCreate(BaseModel):
    system_type: SystemType
    external_reference: str
    display_reference: str
    metadata_json: dict[str, Any] = {}
    confirm_mismatch: bool = False


class LinkOut(LinkCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    active: bool
    created_at: datetime
    mismatch: bool = False


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    authority: str
    municipality: str
    permit_type: str
    external_request_number: str
    application_status: ApplicationStatus
    repetition_count: int
    last_status_at: datetime


class DecisionPatch(BaseModel):
    status: DecisionStatus | None = None
    value_json: dict[str, Any] | None = None
    owner: str | None = None
    evidence_reference: str | None = None
    notes: str | None = None


class DecisionOut(DecisionPatch):
    model_config = ConfigDict(from_attributes=True)
    id: str
    category: str
    key: str
    updated_at: datetime


class ValuesPayload(BaseModel): values: dict[str, Any]


class InquiryPatch(BaseModel):
    status: InquiryStatus | None = None
    client_owner: str | None = None
    response_text: str | None = None
    notes: str | None = None


class InquiryOut(InquiryPatch):
    model_config = ConfigDict(from_attributes=True)
    id: str
    question_code: str
    question: str
    sent_at: datetime | None = None
    response_at: datetime | None = None


class RaidCreate(BaseModel):
    type: RaidType
    title: str
    description: str
    severity: str = "MEDIUM"
    owner: str = "TBD"
    status: str = "OPEN"
    mitigation: str = "To be confirmed"
    due_date: date | None = None
    phase0_close_impact: str = "NONE"


class RaidOut(RaidCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    correlation_id: str
    actor_type: str
    event_type: str
    entity_type: str
    entity_id: str
    before_json: dict[str, Any] | None
    after_json: dict[str, Any] | None
    occurred_at: datetime
