"""Read-only E0/E1 expansion foundation APIs."""

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..expansion.fixture import EXPANDED_FIXTURE_MANIFEST, expanded_fixture_metadata
from ..expansion.governance import ASSISTANT_IDS, validate_governance
from ..models import *

router = APIRouter(prefix="/api/expansion")


def row(item):
    return jsonable_encoder({column.name: getattr(item, column.name) for column in item.__table__.columns}) if item else None


@router.get("/requirements")
def expansion_requirements():
    governance = validate_governance()
    return {"registry": "A12B", "count": governance["a12b_count"], "requirements": governance["owner_requirements"], "synthetic": True}


@router.get("/clarifications")
def expansion_clarifications():
    governance = validate_governance()
    return {"registry": "A15", "count": governance["a15_count"], "clarifications": governance["clarifications"], "synthetic": True}


@router.get("/capabilities")
def expansion_capabilities(db: Session = Depends(get_db)):
    governance = validate_governance()
    rows = [row(item) for item in db.scalars(select(AssistantCapabilityDefinition).order_by(AssistantCapabilityDefinition.assistant_id, AssistantCapabilityDefinition.capability_id)).all()]
    return {"assistant_ids": ASSISTANT_IDS, "capabilities": rows, "stage2_approval": "NOT_PRESENT", "synthetic": True}


@router.get("/fixture")
def expansion_fixture(db: Session = Depends(get_db)):
    resources = [row(item) for item in db.scalars(select(ExpansionFixtureResource).where(ExpansionFixtureResource.fixture_version == "1.2.0").order_by(ExpansionFixtureResource.resource_path)).all()]
    return {**expanded_fixture_metadata(), "manifest": EXPANDED_FIXTURE_MANIFEST, "resources": resources, "synthetic_only": True}


@router.get("/opportunities")
def expansion_opportunities(db: Session = Depends(get_db)):
    return [row(item) for item in db.scalars(select(Opportunity).order_by(Opportunity.opportunity_reference)).all()]


@router.get("/clients")
def expansion_clients(db: Session = Depends(get_db)):
    return [row(item) for item in db.scalars(select(ClientAccount).order_by(ClientAccount.client_reference)).all()]


@router.get("/domain-summary")
def expansion_domain_summary(db: Session = Depends(get_db)):
    entities = [
        Opportunity, RFQ, TenderDocument, ClientAccount, ClientContact, Quotation, QuotationRevision, CommercialTerm, QuotationApproval,
        Contract, ContractRevision, ContractMilestone, ContractApproval, ChecklistItem, DocumentRequest, ReferenceNumber, ProjectAdministrationRecord,
        CommunicationDraft, CommunicationApproval, CommunicationDelivery, Invoice, InvoiceRevision, InvoiceMilestone, InvoiceApproval, AccountingHandoff,
        ProjectHandover, EngineeringReview, EngineeringReviewRun, RegulationSource, RegulationVersion, RegulationApplicability, EngineeringComment,
        DrawingReviewCycle, TemplateDefinition, TemplateVersion, RenderedArtifact, AssistantCapabilityDefinition,
    ]
    counts = {model.__tablename__: db.scalar(select(func.count(model.id))) or 0 for model in entities}
    return {"counts": counts, "shared_primitives": ["Document", "DocumentVersion", "EvidenceArtifact", "Approval", "WorkflowTask", "NotificationEvent", "AuditEvent", "LineageEdge", "MaterialChangeEvent", "TargetRenderingRule", "DocumentValidity"], "external_actions": {"email": False, "accounting_write": False, "government_write": False, "machine_final_submit": False}, "fixture": expanded_fixture_metadata(), "synthetic_only": True}
