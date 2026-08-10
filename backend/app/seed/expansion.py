"""Synthetic-only seed for the E1 shared AMEC domain foundation."""

import hashlib
from datetime import datetime, timezone

from sqlalchemy import delete, select

from ..expansion.fixture import EXPANDED_FIXTURE_MANIFEST, EXPANDED_FIXTURE_MANIFEST_HASH, EXPANDED_FIXTURE_VERSION
from ..models import *
from ..services.proposals_sor import ingest_project_artifact


EXPANSION_RESET_MODELS = [
    ProjectArtifactRecord, ExpansionFixtureResource, ProposalIntakeArtifact, EvidenceArtifact, QuotationRelease, ProjectStatusProjection, AdminDocumentComment, SystemBlock,
    ContractExecutionEvidence, ClientResponse, QuotationFieldObservation, ExecutionAuthorityConfig,
    ExpansionFixtureResource, AssistantCapabilityDefinition,
    DrawingReviewCycle, EngineeringComment, EngineeringReviewRun, RegulationApplicability, EngineeringReviewScope, EngineeringReview, RegulationVersion, RegulationSource,
    ProjectHandover, FinanceEvidence, InvoiceRequirementDecision, AccountingHandoff, InvoiceApproval, InvoiceMilestone, InvoiceRevision, Invoice,
    CommunicationDelivery, CommunicationApproval, CommunicationDraft, ProjectAdministrationRecord, ReferenceNumber,
    DocumentRequest, ChecklistItem, ContractApproval, ContractMilestone, ContractRevision, Contract,
    CapabilityInvocationRecord, AssistantHandoff,
    QuotationApproval, CommercialTerm, QuotationRevision, Quotation, TenderDocument, RFQ, Opportunity, ClientContact, ClientAccount,
    RenderedArtifact, TemplateVersion, TemplateDefinition,
]


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def seed_expansion(db, office, users, projects, apps):
    for model in EXPANSION_RESET_MODELS:
        db.execute(delete(model))

    owner = users[0]
    engineer = next(user for user in users if user.email == "engineer@amec.synthetic")
    project = projects[0]
    application = apps[0]
    drawing = db.scalar(select(Document).where(Document.project_id == project.id, Document.document_type == DocumentType.DRAWING_SET).order_by(Document.created_at)) or db.scalar(select(Document).where(Document.project_id == project.id).order_by(Document.created_at))
    drawing_version = db.scalar(select(DocumentVersion).where(DocumentVersion.document_id == drawing.id).order_by(DocumentVersion.version_number))
    source_version = db.scalar(select(DocumentVersion).where(DocumentVersion.document_id != drawing.id).order_by(DocumentVersion.ingested_at))
    shared_approval = Approval(approval_type="EXPANSION_FOUNDATION", entity_type="E1_FOUNDATION", entity_id=project.id, status="NOT_APPROVED", decided_by="synthetic-seed", role_at_decision="REQUIREMENT_STEWARD", reason="Synthetic foundation placeholder; not a client approval.", evidence_refs=[])
    db.add(shared_approval)
    db.flush()

    client = ClientAccount(client_reference="SYN-CLIENT-001", legal_name="Synthetic Client Holdings", display_name="Synthetic Client Holdings", client_type="COMPANY", commercial_registration_number="SYN-CR-0001", data_classification="SYNTHETIC", status="ACTIVE")
    db.add(client)
    db.flush()
    contact = ClientContact(client_account_id=client.id, name="Synthetic Client Contact", email="contact@client.synthetic", role_title="Synthetic Project Contact", language_preference="EN", status="ACTIVE")
    db.add(contact)
    db.flush()

    opportunity = Opportunity(office_id=office.id, client_account_id=client.id, opportunity_reference="SYN-OPP-0001", title="Synthetic Building Advisory Opportunity", status="IN_REVIEW", source_type="RFQ_EMAIL", current_owner_user_id=owner.id, stage2_capability_scope="UNDECIDED_STAGE2", project_id=project.id, reference_state="CANONICAL", proposal_fields_json={"price": "QAR 125,000", "sow": "Building advisory and permit coordination", "period": "12 weeks", "exclusions": "Authority fees"}, provisional_reference="SYN-OPP-0001", canonical_project_reference=project.project_number, canonicalized_by=owner.email)
    db.add(opportunity)
    db.flush()
    rfq = RFQ(opportunity_id=opportunity.id, source_document_version_id=source_version.id, sender_reference="SYN-RFQ-SENDER", source_reference="SYN-RFQ-0001", language="EN", status="RECEIVED")
    tender = TenderDocument(opportunity_id=opportunity.id, document_version_id=source_version.id, document_role="TENDER", status="RECEIVED")
    db.add_all([rfq, tender])
    db.flush()

    quotation = Quotation(opportunity_id=opportunity.id, quotation_reference="SYN-QTN-0001", status="DRAFT", client_account_id=client.id)
    db.add(quotation)
    db.flush()
    quotation_revision = QuotationRevision(quotation_id=quotation.id, revision_number=1, source_snapshot={"fixture": "1.2.0", "approval": "NOT_APPROVED"}, content_hash=_hash("SYN-QTN-0001-R1"), semantic_hash=_hash("SYN-QTN-SEMANTIC-0001"), status="DRAFT", created_by=owner.email)
    db.add(quotation_revision)
    db.flush()
    quotation.current_revision_id = quotation_revision.id
    db.add_all([
        CommercialTerm(quotation_revision_id=quotation_revision.id, term_type="SCOPE", value_text="Synthetic advisory and permit coordination scope.", source_document_version_id=source_version.id, status="PROPOSED"),
        CommercialTerm(quotation_revision_id=quotation_revision.id, term_type="PAYMENT_CONDITION", value_text="Synthetic milestone terms; not approved.", source_document_version_id=source_version.id, status="PROPOSED"),
        QuotationApproval(quotation_revision_id=quotation_revision.id, approval_id=shared_approval.id, approval_type="COMMERCIAL_QUOTATION_RELEASE"),
    ])

    contract = Contract(client_account_id=client.id, quotation_id=quotation.id, contract_reference="SYN-CTR-0001", status="DRAFT", project_id=project.id)
    db.add(contract)
    db.flush()
    contract_revision = ContractRevision(contract_id=contract.id, revision_number=1, controlling_quotation_revision_id=quotation_revision.id, status="DRAFT")
    db.add(contract_revision)
    db.flush()
    contract.current_revision_id = contract_revision.id
    # The primary owner-demo chain is already contracted.  Keep its proposal
    # lifecycle state aligned with that durable relationship.
    opportunity.status = "CONTRACT_HANDOVER"
    milestone = ContractMilestone(contract_id=contract.id, contract_revision_id=contract_revision.id, milestone_reference="SYN-M1", title="Synthetic permit package milestone", payment_condition="Synthetic tracking only; no accounting write.", amount_value="SYNTHETIC", status="PLANNED")
    db.add(milestone)
    db.flush()
    db.add(ContractApproval(contract_revision_id=contract_revision.id, approval_id=shared_approval.id, approval_type="CONTRACT_APPROVAL"))

    checklist = ChecklistItem(context_type="OPPORTUNITY", context_id=opportunity.id, requirement_code="SYN.CLIENT.DOCUMENT", title="Synthetic client supporting document", required_condition="Required before later quotation/contract gate.", required_document_type="OTHER", validity_policy_ref="SYNTHETIC_VALIDITY_POLICY", status="OPEN", blocking=True)
    db.add(checklist)
    db.flush()
    request = DocumentRequest(checklist_item_id=checklist.id, client_account_id=client.id, requested_from_contact_id=contact.id, status="OPEN")
    db.add(request)

    application.controlling_contract_id = contract.id
    reference = ReferenceNumber(reference_value="SYN-REF-0001", reference_type="EXPANSION_TRANSACTION", opportunity_id=opportunity.id, quotation_id=quotation.id, contract_id=contract.id, project_id=project.id, permit_application_id=application.id, status="RESERVED")
    db.add(reference)
    db.flush()
    admin_record = ProjectAdministrationRecord(project_id=project.id, reference_number_id=reference.id, client_account_id=client.id, payment_status="NOT_CONFIGURED", payment_followup_state="TRACK_ONLY", project_status="ACTIVE", engineer_email_projection=engineer.email, synology_linkage_reference="SYNTHETIC_ONLY", excel_linkage_reference="SYNTHETIC_ONLY")
    db.add(admin_record)

    communication = CommunicationDraft(communication_type="MISSING_DOCUMENT", context_type="DOCUMENT_REQUEST", context_id=request.id, recipient_contact_id=contact.id, subject="Synthetic missing document follow-up", body="SYNTHETIC DRAFT — HUMAN_SEND — NOT CLIENT APPROVED.", status="HUMAN_REVIEW", policy_state="HUMAN_SEND", created_by=owner.email)
    db.add(communication)
    db.flush()
    request.communication_draft_id = communication.id
    db.add_all([CommunicationApproval(communication_draft_id=communication.id, approval_id=shared_approval.id, approval_type="COMMUNICATION_RELEASE"), CommunicationDelivery(communication_draft_id=communication.id, delivery_channel="EMAIL", delivery_status="NOT_SENT")])

    invoice = Invoice(contract_id=contract.id, invoice_reference="SYN-INV-0001", status="DRAFT")
    db.add(invoice)
    db.flush()
    invoice_revision = InvoiceRevision(invoice_id=invoice.id, revision_number=1, controlling_contract_revision_id=contract_revision.id, controlling_milestone_id=milestone.id, status="DRAFT")
    db.add(invoice_revision)
    db.flush()
    invoice.current_revision_id = invoice_revision.id
    db.add_all([InvoiceMilestone(invoice_id=invoice.id, contract_milestone_id=milestone.id, status="TRACK_ONLY"), InvoiceApproval(invoice_revision_id=invoice_revision.id, approval_id=shared_approval.id, approval_type="FINANCE_INVOICE_APPROVAL"), AccountingHandoff(invoice_id=invoice.id, assigned_role="GENERIC_FINANCE_HANDOFF", status="TRACK_ONLY")])

    handover = ProjectHandover(project_id=project.id, status="NOT_READY", readiness_state="NOT_READY", communication_draft_id=communication.id)
    db.add(handover)

    regulation_source = RegulationSource(source_code="SYN-REG-PLACEHOLDER", title="Synthetic regulation metadata placeholder", jurisdiction="SYNTHETIC", authority_name="Synthetic Authority Placeholder", source_type="PLACEHOLDER", publication_state="SYNTHETIC_PLACEHOLDER")
    db.add(regulation_source)
    db.flush()
    regulation_version = RegulationVersion(regulation_source_id=regulation_source.id, edition="SYNTHETIC_EDITION_NOT_AUTHORITY", version="0.0", source_uri_or_reference="synthetic://not-authoritative", content_status="SYNTHETIC_PLACEHOLDER")
    db.add(regulation_version)
    db.flush()
    review = EngineeringReview(project_id=project.id, discipline="SYNTHETIC_DEMO_DISCIPLINE", drawing_document_id=drawing.id, current_drawing_version_id=drawing_version.id, status="SYNTHETIC_DEMO_DISCIPLINE", authorized_engineer_user_id=engineer.id)
    db.add(review)
    db.flush()
    review_run = EngineeringReviewRun(engineering_review_id=review.id, drawing_document_version_id=drawing_version.id, regulation_applicability_snapshot={"regulation_version_id": regulation_version.id, "trust": "NOT_AUTHORITATIVE"}, status="HUMAN_REVIEW_REQUIRED")
    db.add(review_run)
    db.flush()
    applicability = RegulationApplicability(regulation_version_id=regulation_version.id, context_type="ENGINEERING_REVIEW_RUN", context_id=review_run.id, discipline="SYNTHETIC_DEMO_DISCIPLINE", applicability_status="NOT_CONFIGURED")
    comment = EngineeringComment(engineering_review_run_id=review_run.id, drawing_document_version_id=drawing_version.id, comment_number=1, source_type="SYNTHETIC_PROPOSED", proposed_text="Synthetic comment placeholder; requires authorized engineer disposition.", evidence_reference="synthetic://comment-sheet", status="PROPOSED", engineer_disposition="NOT_DISPOSED")
    db.add_all([applicability, comment])
    db.flush()
    cycle = DrawingReviewCycle(project_id=project.id, discipline="SYNTHETIC_DEMO_DISCIPLINE", cycle_number=1, input_drawing_version_id=drawing_version.id, review_run_id=review_run.id, status="OPEN")
    db.add(cycle)

    template = TemplateDefinition(template_code="SYN-QUOTATION-TEMPLATE", artifact_type="QUOTATION", name="Synthetic quotation stand-in", language="EN", owner_role="COMMERCIAL_APPROVER", status="SYNTHETIC_STANDIN")
    db.add(template)
    db.flush()
    template_version = TemplateVersion(template_definition_id=template.id, version="0.1", status="SYNTHETIC_STANDIN", content_hash=_hash("SYN-QUOTATION-TEMPLATE-0.1"))
    db.add(template_version)
    db.flush()
    db.add(RenderedArtifact(template_version_id=template_version.id, context_type="QUOTATION_REVISION", context_id=quotation_revision.id, artifact_type="QUOTATION", content_hash=_hash("SYN-RENDERED-QUOTATION"), storage_reference="synthetic://rendered/quotation", status="DRAFT"))


    capability_rows = []
    capability_specs = {
        "BD_ASSISTANT": [("RFQ_INTAKE", ["OWN-NEW-01", "OWN-NEW-02"]), ("OPPORTUNITY_REVIEW", ["OWN-NEW-01", "OWN-NEW-03"]), ("BD_CHECKLIST", ["OWN-NEW-02", "OWN-NEW-04"]), ("QUOTATION_FIELD_REVIEW", ["OWN-NEW-04", "OWN-NEW-05"]), ("QUOTATION_PREPARATION", ["OWN-NEW-05", "OWN-NEW-06"]), ("COMMERCIAL_REVIEW_HANDOFF", ["OWN-NEW-07", "OWN-NEW-35", "OWN-NEW-38"]), ("CLIENT_RESPONSE_TRACKING", ["OWN-NEW-08", "OWN-NEW-39"])],
        "ADMIN_ASSISTANT": [("CONTRACT_PREPARATION", ["OWN-NEW-09", "OWN-NEW-10"]), ("CONTRACT_REVIEW_HANDOFF", ["OWN-NEW-11", "OWN-NEW-38"]), ("CLIENT_CHECKLIST", ["OWN-NEW-12", "OWN-NEW-21"]), ("MISSING_DOCUMENT_FOLLOWUP", ["OWN-NEW-13", "OWN-NEW-14"]), ("CONTRACT_MILESTONE_FOLLOWUP", ["OWN-NEW-15", "OWN-NEW-16"]), ("MUNICIPALITY_FORM_PREPARATION", ["OWN-NEW-22", "OWN-NEW-23"]), ("REFERENCE_PREPARATION", ["OWN-NEW-24", "OWN-NEW-25"]), ("ADMIN_COMMUNICATION_DRAFT", ["OWN-NEW-39"])],
        "ENGINEERING_REVIEW_ASSISTANT": [("ENGINEERING_REVIEW_PREPARATION", ["OWN-NEW-27"]), ("REGULATION_APPLICABILITY_REVIEW", ["OWN-NEW-28"]), ("ENGINEERING_ADVISORY_ANALYSIS", ["OWN-NEW-29"]), ("ENGINEER_COMMENT_REVIEW", ["OWN-NEW-30"]), ("COMMENT_SHEET_PREPARATION", ["OWN-NEW-31"]), ("DRAWING_REVISION_REVIEW", ["OWN-NEW-32"]), ("BLOCK_TIME_TRACKING", ["OWN-NEW-31", "OWN-NEW-32"])],
        "PROJECT_PERMIT_COORDINATION_ASSISTANT": [("REFERENCE_ASSIGNMENT", ["OWN-NEW-24"]), ("PROJECT_BOOTSTRAP", ["OWN-NEW-25"]), ("SERVER_SYNOLOGY_LINK", ["OWN-NEW-25"]), ("PROJECT_STATUS", ["OWN-NEW-36", "OWN-NEW-40"]), ("ADMIN_DOCUMENT_REVIEW", ["OWN-NEW-21", "OWN-NEW-22"]), ("SYSTEM_BLOCK_MANAGEMENT", ["OWN-NEW-23", "OWN-NEW-38"]), ("PERMIT_HANDOFF", ["OWN-NEW-40"]), ("PERMIT_WORKFLOW_COORDINATION", ["OWN-NEW-40"]), ("AUTHORITY_CHANGE_FOLLOWUP", ["OWN-NEW-40"]), ("FINANCE_HANDOFF", ["OWN-NEW-18", "OWN-NEW-19", "OWN-NEW-20"]), ("PROJECT_HANDOVER", ["OWN-NEW-26"])],
    }
    role_by_assistant = {"BD_ASSISTANT": "COMMERCIAL_APPROVER", "ADMIN_ASSISTANT": "ADMIN_PROJECT_COORDINATOR", "ENGINEERING_REVIEW_ASSISTANT": "AUTHORIZED_ENGINEER", "PROJECT_PERMIT_COORDINATION_ASSISTANT": "PERMIT_PREPARER"}
    for assistant, specs in capability_specs.items():
        for capability, ids in specs:
            capability_rows.append((assistant, capability, capability.replace("_", " ").title(), ids, role_by_assistant[assistant]))
    db.add(ExecutionAuthorityConfig(authority="PROTOTYPE_DEV_ONLY", evidence_class="SYNTHETIC_IMPLEMENTATION_EVIDENCE", production_enabled=False, external_actions_enabled=False, notes="Synthetic recovery implementation only; no formal build or production authority."))
    db.add_all([AssistantCapabilityDefinition(assistant_id=assistant, capability_id=capability, title=title, description="Shared synthetic runtime capability; no production workflow is enabled.", requirement_ids=ids, input_types=["shared evidence", "governed entity"], output_types=["candidate structured data", "draft", "evidence reference"], required_human_authority=authority, external_action_policy="HUMAN_SEND", stage2_disposition="UNDECIDED_STAGE2", execution_authority="PROTOTYPE_DEV_ONLY", enabled_in_prototype=True, enabled_in_production=False, enabled=True) for assistant, capability, title, ids, authority in capability_rows])

    for resource in EXPANDED_FIXTURE_MANIFEST["resources"]:
        db.add(ExpansionFixtureResource(fixture_version=EXPANDED_FIXTURE_VERSION, resource_path=resource["path"], source_family=resource["source_family"], scenario=resource["scenario"], synthetic_label=resource["synthetic_label"], content_hash=_hash(resource["path"])))

    lineage_rows = [
        ("DocumentVersion", source_version.id, "Opportunity", opportunity.id, "RFQ_SOURCE"),
        ("Opportunity", opportunity.id, "QuotationRevision", quotation_revision.id, "QUOTATION_FROM_OPPORTUNITY"),
        ("QuotationRevision", quotation_revision.id, "ContractRevision", contract_revision.id, "CONTRACT_FROM_QUOTATION"),
        ("ContractRevision", contract_revision.id, "ContractMilestone", milestone.id, "MILESTONE_FROM_CONTRACT"),
        ("ContractMilestone", milestone.id, "InvoiceRevision", invoice_revision.id, "INVOICE_FROM_MILESTONE"),
        ("Project", project.id, "EngineeringReview", review.id, "ENGINEERING_REVIEW_FOR_PROJECT"),
        ("DocumentVersion", drawing_version.id, "EngineeringReviewRun", review_run.id, "DRAWING_VERSION_REVIEWED"),
        ("RegulationVersion", regulation_version.id, "EngineeringReviewRun", review_run.id, "REGULATION_SNAPSHOT"),
        ("EngineeringReviewRun", review_run.id, "EngineeringComment", comment.id, "COMMENT_FROM_REVIEW_RUN"),
        ("Project", project.id, "ProjectHandover", handover.id, "HANDOVER_FOR_PROJECT"),
    ]
    db.add_all([LineageEdge(project_id=project.id, upstream_type=up, upstream_id=up_id, upstream_version_or_hash="E1", downstream_type=down, downstream_id=down_id, downstream_version_or_hash="E1", dependency_kind=kind, correlation_id="expansion-e1-seed") for up, up_id, down, down_id, kind in lineage_rows])
