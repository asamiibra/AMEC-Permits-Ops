from pydantic import BaseModel, Field
from ..models import InitiationType


class ProjectBootstrapCreate(BaseModel):
    initiation_type: InitiationType = InitiationType.MANUAL_APPROVED_TRIGGER
    initiation_reference: str = Field(min_length=3, max_length=200)
    initiated_by: str = "synthetic-office-coordinator"
    project_name: str = Field(min_length=2, max_length=200)
    municipality: str = "Demo Municipality A"
    permit_type: str = "Building Permit"
    workstream: str = "BUILDING_PERMIT"
    assigned_engineer: str | None = None
    proposed_number: str | None = None


class ExcelProjectionRequest(BaseModel):
    canonical_plot_number: str | None = None
    canonical_pin: str | None = None
    rendering_version: str = "1.0"
    municipality_request: str | None = None
