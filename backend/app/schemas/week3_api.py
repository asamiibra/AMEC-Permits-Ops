from datetime import date
from typing import Any
from pydantic import BaseModel, Field
from ..models import AdjudicationStatus, ThresholdStatus, Tier1DecisionStatus, Tier2Status, DeliveryStatus, Phase0DecisionType, Stage2Status, SignoffStatus, PilotStatus


class AdjudicationPatch(BaseModel):
    action: str
    actor_id: str = "synthetic-steward"
    expected_class: str | None = None
    ambiguity: str | None = None
    notes: str | None = None


class ThresholdPatch(BaseModel):
    proposed_threshold: float | None = None
    status: ThresholdStatus | None = None
    notes: str | None = None


class Tier1Patch(BaseModel):
    status: Tier1DecisionStatus
    resolution: str | None = None
    fallback: str | None = None
    owner: str | None = None


class Tier2Create(BaseModel):
    category: str
    title: str
    description: str
    owner: str
    priority: str = "MEDIUM"
    due_build_week: int = Field(ge=1, le=6)
    blocking_week6: bool = False
    status: Tier2Status = Tier2Status.OPEN
    dependency: str | None = None
    notes: str = "Synthetic backlog item"


class Tier2Patch(BaseModel):
    status: Tier2Status | None = None
    owner: str | None = None
    due_build_week: int | None = Field(default=None, ge=1, le=6)
    blocking_week6: bool | None = None
    notes: str | None = None


class DeliveryPatch(BaseModel):
    status: DeliveryStatus


class Phase0Recommendation(BaseModel):
    decision: Phase0DecisionType
    summary: str
    conditions: list[str] = []
    blockers: list[str] = []
    fallbacks: list[str] = []
    evidence_refs: list[str] = []


class Phase0DecisionCreate(Phase0Recommendation):
    approved_by: str = "Synthetic Demo Approver"
    commercial_effect: str = "DEMO ONLY — no build authorization"
    next_action: str = "Review Stage 2 draft and Sign-off C proposal"


class BaselineGenerate(BaseModel):
    scenario_code: str = "DEMO_BUILDING_PERMIT_V1"
    created_by: str = "Synthetic Arkan Product Lead"


class BaselineApprove(BaseModel):
    status: Stage2Status = Stage2Status.APPROVED_WITH_CONDITIONS
    approved_by: str = "Synthetic Demo Approver"


class PilotPatch(BaseModel):
    status: PilotStatus


class SignoffGenerate(BaseModel):
    fixed_price_qar: float | None = None
    created_by: str = "Synthetic Arkan Product Lead"
