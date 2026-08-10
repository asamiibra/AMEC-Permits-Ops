"""Typed response contract for the owner-facing Proposals & Contracts register.

These models deliberately require every field consumed by the register UI.  A
projection failure therefore becomes a server error instead of a partial 200
payload that could be rendered as fake zeros or an empty register.
"""

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field


class ProposalMainNextAction(BaseModel):
    model_config = ConfigDict(extra="allow")

    code: str = Field(description="Derived transition code.")
    label: str = Field(description="Owner-readable transition label.")
    eligible: bool = Field(description="Whether the transition is currently allowed.")


class ProposalMainProposalRow(BaseModel):
    model_config = ConfigDict(extra="allow")

    record_type: Literal["PROPOSAL_WORKSPACE"]
    id: str = Field(description="Opportunity/Proposal identity.")
    proposal_id: str = Field(description="Stable Proposal identity; same value as id.")
    contract_id: str | None = Field(description="Related Contract identity, nullable until handoff.")
    proposal_description: str = Field(description="Proposal description shown in the register.")
    project_id: str | None = Field(description="Canonical Project identity, nullable for provisional intake.")
    project_reference: str = Field(description="Canonical or provisional Project Reference.")
    project_name: str = Field(description="Owner-readable Project name or pending-context label.")
    proposal_status: str = Field(description="Persisted Proposal status.")
    contract_status: str | None = Field(description="Related Contract status, nullable without a Contract.")
    current_stage: str = Field(description="Derived owner-facing Proposal stage.")
    status: str = Field(description="Compatibility status projection; equal to proposal_status.")
    amount: str | None = Field(description="Commercial amount, nullable when not recorded.")
    last_activity: str = Field(description="ISO-8601 last-activity timestamp.")
    has_contract: bool = Field(description="Whether a related Contract exists.")
    open_path: str = Field(description="Current Proposal detail path.")
    source_count: int = Field(ge=0, description="Count of current verified source records.")
    source_types: list[str] = Field(description="Current verified source classes.")
    reference_state: str = Field(description="CANONICAL or PROVISIONAL reference state.")
    proposal_fields: dict[str, Any] = Field(description="Persisted Proposal field projection.")
    next_action: ProposalMainNextAction = Field(description="Derived next action.")
    allowed_actions: list[str] = Field(description="Derived row actions.")
    related_contract_id: str | None = Field(description="Related Contract identity, nullable until handoff.")
    contract_action_eligible: bool = Field(description="Whether Contract transition is available.")
    contract_action_label: str = Field(description="Owner-readable Contract action label.")
    permit_application_id: str | None = Field(description="Downstream Permit identity, nullable until linked.")


class ProposalMainContractRow(BaseModel):
    model_config = ConfigDict(extra="allow")

    record_type: Literal["CONTRACT"]
    id: str = Field(description="Contract identity.")
    contract_description: str = Field(description="Owner-readable Contract description.")
    contract_reference: str = Field(description="Contract reference.")
    status: str = Field(description="Persisted Contract status.")
    contract_status: str = Field(description="Compatibility Contract status projection.")
    related_proposal_id: str | None = Field(description="Related Proposal identity, nullable if not linked.")
    proposal_id: str | None = Field(description="Compatibility Proposal identity, nullable if not linked.")
    related_proposal: str = Field(description="Owner-readable related Proposal label.")
    project_id: str | None = Field(description="Canonical Project identity, nullable until reconciled.")
    project_reference: str = Field(description="Canonical or unresolved Project Reference.")
    project_name: str = Field(description="Owner-readable Project name or pending-context label.")
    amount: str | None = Field(description="Contract amount, nullable when not recorded.")
    proposal_amount: str | None = Field(description="Related Proposal amount, nullable when not recorded.")
    contract_amount: str | None = Field(description="Contract amount projection, nullable when not recorded.")
    last_activity: str = Field(description="ISO-8601 last-activity timestamp.")
    end_date: str | None = Field(description="Contract end date, nullable when not recorded.")
    permit_count: int = Field(ge=0, description="Count of linked Permit records.")
    permit_id: str | None = Field(description="Linked Permit identity, nullable until linked.")
    permit_application_id: str | None = Field(description="Compatibility Permit identity, nullable until linked.")
    permit_eligible: bool = Field(description="Whether downstream Permit initiation is possible.")
    permit_action_eligible: bool = Field(description="Whether the Permit action is available.")
    permit_action_label: str = Field(description="Owner-readable Permit action label.")
    permit_action: dict[str, Any] = Field(description="Derived Permit transition state.")
    proposal_status: str | None = Field(description="Related Proposal status, nullable if not linked.")
    next_action: dict[str, Any] = Field(description="Derived Contract next action.")


ProposalMainRegisterRow = Annotated[
    Union[ProposalMainProposalRow, ProposalMainContractRow],
    Field(discriminator="record_type"),
]


class ProposalMainKpi(BaseModel):
    label: str = Field(description="Owner-readable KPI label.")
    count: int = Field(ge=0, description="System-derived record count.")
    states: list[str] = Field(description="Canonical states included in the count.")
    entity: Literal["proposal", "contract"] = Field(description="Register entity used for derivation.")


class ProposalMainKpis(BaseModel):
    OPEN_PROPOSALS: ProposalMainKpi
    OPEN_CONTRACTS: ProposalMainKpi
    PROPOSAL_HANDOVER: ProposalMainKpi
    CONTRACT_HANDOVER: ProposalMainKpi
    PROPOSALS_IN_PROCESS: ProposalMainKpi
    CONTRACTS_IN_PROCESS: ProposalMainKpi


class ProposalMainClient(BaseModel):
    id: str
    reference: str
    name: str
    status: str


class ProposalMainFilter(BaseModel):
    key: str
    label: str
    entity: Literal["proposal", "contract", "both"] | None = None
    states: list[str] | None = None


class ProposalMainPersona(BaseModel):
    persona: str
    allowed_actions: list[str]
    source_actions: list[str]
    amount_visible: bool


class ProposalMainResponse(BaseModel):
    """Complete response contract for ``GET /api/proposals-main``."""

    rows: list[ProposalMainRegisterRow] = Field(description="Rows for the requested register view.")
    proposals: list[ProposalMainProposalRow] = Field(description="Complete Proposal register.")
    contracts: list[ProposalMainContractRow] = Field(description="Complete Contract register.")
    contract_rows: list[ProposalMainContractRow] = Field(description="Compatibility Contract register.")
    view: Literal["proposals", "contracts"]
    clients: list[ProposalMainClient]
    kpis: ProposalMainKpis
    filters: list[ProposalMainFilter]
    filter_predicates: dict[str, dict[str, list[str] | None]]
    persona: ProposalMainPersona
    sor: dict[str, Any]
    lineage_model: str
    synthetic_only: bool
