import shutil
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone, date
from types import SimpleNamespace
from sqlalchemy import delete, select, text, update
from reportlab.pdfgen.canvas import Canvas
from ..config.settings import get_settings, repo_root
from ..db import engine, SessionLocal, init_db
from ..models import *
from ..services.business_case import DEFAULT_BUSINESS_CASE
from ..services.week2_workflows import register_version, classify_version, extract_version, compare_project_conflicts, verify_observation
from ..models.week2_entities import *
from ..fixtures.canonical import *
from ..services.canonical_workbook import ensure_canonical_workbook, canonical_workbook_contract
from ..adapters.excel.adapter import MockExcelAdapter
from ..audit.service import audit
from ..services.configuration_lineage import ensure_configuration_bundle, stable_hash
from .expansion import EXPANSION_RESET_MODELS, seed_expansion
from .persona_issues_notifications import seed_persona_issues_notifications
from ..services.permit_workflow import ensure_project_sources_task
from ..services.proposals_sor import ACTION_CONFIG, ingest_project_artifact


def seed(
    *,
    initialize_schema: bool = True,
    reset_existing: bool = True,
    clean_fixtures: bool = True,
):
    if initialize_schema:
        init_db()

    with SessionLocal() as db:
        if reset_existing:
            db.execute(
                update(
                    EngineeringReview
                ).values(
                    current_scope_id=None
                )
            )
            db.execute(
                update(
                    Invoice
                ).values(
                    requirement_decision_id=None
                )
            )
        reset_order = [
            # Shared-domain foundation records are reset before their
            # canonical master-content/project parents in disposable TEST.
            SignaturePacket, FormSignatureRequirement, FormMappingReleaseQAGate, AutomationReadinessAssessment, FormQARun, FormValidationResult, GeneratedArtifact, FormInstance,
            FormMappingRule, FormMappingRelease, SemanticValueAssertion, SemanticKeyDefinition, FormAutomationProfile,
            MasterContentApplicability,
            TechnicalRuleEvaluation, TechnicalRuleLineage, TechnicalRule, TechnicalRuleSetVersion,
            RequirementDecision, RequirementEvidenceEvaluation, RequirementEvaluation, RequirementApplicabilityDecision,
            RequirementPolicyLineage, RequirementEvidenceConstraint, RequirementPolicyItem, RequirementGroup, RequirementPolicyVersion, RequirementDefinition,
            AuthorityOutcome, ExternalInteractionProfile, AuthorityCaseWorkPeriod, AuthorityCaseIdentifier, AuthorityCase,
            RegulatoryJourney, RegulatoryLifecyclePhase, ServiceTypeVersion, ServiceType, ExternalBodyUnit, ExternalBody, Jurisdiction,
            *EXPANSION_RESET_MODELS,
            ProductionModeDecision, G10EvidenceItem, RoleReadinessMatrix, PilotWorkflowApproval, ShadowDefectDisposition, AcceptanceMetric, AcceptanceRehearsalRun,
            RoleTrainingChecklist, KillSwitchReadiness, RestoreRehearsal, RecoveryManifest, IncidentImpactAssessment, WorkflowSafetyHold, IntegrityIncident, SupportCase,
            FindingPreventionControl, PriorFindingPreventiveCheck, FindingRecurrenceAnalysisItem, FindingRecurrenceAnalysisRun,
            HumanTakeoverEvent, MfaChallengeEvent, AttendedAuthSession, TargetRenderingCoverage, VariantCompatibilityResult, ScenarioVariant,
            OperatorTaskTiming, NotificationDeliveryAttempt, ExternalMutationObservation, HumanMonitoringCapture, AuthorityStateComparison, MonitoringStateSnapshot,
            AuthorityCommentObservation, AuthorityStatusObservation, PortalContractValidationRun, PortalDriftEvent, PortalReadContract,
            MonitoringCheck, MonitoringExecutionDecision, MonitoringRun, MonitoringPolicy,
            GridFieldDiff, GridRowReconciliationResult, GridReconciliationRun, GridPersistenceEvidence, PortalGridRowObservation, PortalDerivedFieldReconciliation, PortalStructureFingerprint, AttachmentReconciliationResult, AttachmentPersistenceEvidence, AttachmentAssociationIntent, AttachmentManifestItem, AttachmentCategoryRule, FieldMatrixCoverage, RequirementMatrixCoverage, RuleCandidate, ControlRun, ControlDefinition, ResubmissionReadinessEvaluation, ApprovalApplicabilityEvaluation, SubmittedSnapshot, PrecheckClearanceEvaluation, FindingHistoryLink, FindingReopenEvent, FindingDispute, FindingClosureEvaluation, FindingResolutionEvidence, FindingResolution, CorpusCaseResult, CorpusCase, CorpusRun, ShadowCorrection, StaleReason, MaterialChangeEvent, LineageEdge, ConfigurationChangeImpactPolicy, AuthorityApprovalValidity, DocumentValidity,
            NotificationReadState, NotificationEvent, WorkflowTask, Finding, AuthorityEvent, SubmissionCycle, PortalValidationFindingRule, FindingRoutingRule, FindingSlaPolicy, FindingCode,
            OperatorExerciseEvidence, SubmissionConfirmation, MunicipalityPreparationException, SubmissionHandoff, AttendedSession, AuthorityPrecheckItem, AuthorityPrecheckRun, HumanPortalVerification, PortalReconciliationResult, PortalSnapshot, PortalIntendedState, PortalGridRowIntent, PreparationSnapshot, PreparationRevision, Approval, ExcelProjection, RenderedForm, FormTemplateVersion, FormTemplate, AttachmentManifest, PackageItem, Package, ReadinessResultItem, PackageReadinessEvaluation, MinimumPackageDefinition, OfficeCredential, ProfessionalCredential, ApplicableRuleSet, ConfigurationBundle, ConfigurationArtifact,
            AuditEvent, StorageOutboxEvent, StorageOperation,
            SignoffCProposal, Stage2ReviewAcknowledgement, Stage2Baseline, DeliveryAuthorityStatus, Phase0Decision, PilotCohort, PrecheckDecision, MunicipalityOperationDecision, DeliveryScenario, BusinessKpiTarget, BusinessBaseline, Tier2BacklogItem, Tier1Decision, AcceptanceCorpusDefinition, ThresholdDefinition, AdjudicationHistory, AdjudicationCase, PhaseBaseline,
            Representation, Authorization, PropertyOwnership, ExcelProjectionRule, ExcelProjectRow, SynologyProjectBootstrap, ProjectNumberReservation, ProjectInitiation, TargetRenderingRule, Party, Property, LegacyFixtureAlias, SyntheticFixtureSet,
            SpikeFieldResult, SpikeDocumentResult, ExtractionSpikeRun, GoldFieldLabel, GoldDocumentLabel, RealDocumentTestGate, MunicipalityDraft, MunicipalityConfig, Conflict, DrawingMetadataControl, AttachmentCategoryConfig, ApprovalDependency, RequirementConfig, FieldAuthorityRule, VerifiedAssertion, FieldObservation, DocumentClassification, DocumentVersion, Document, FieldDefinition, ScenarioConfig,
            ExternalSystemLink, PermitApplication, Project, User, ConsultancyOffice, DiscoveryDecision, BusinessCase, VolumeBaseline, MinistryInquiry, RaidItem,
        ]
        # PostgreSQL enforces the complete FK graph while SQLite's reset path
        # historically relied on the hand-maintained model order.  Disposable
        # local TEST databases can be reset atomically; Vercel/bootstrap never
        # takes this path, so a deployment cannot accidentally truncate data.
settings = get_settings()

if reset_existing:
    if (
        db.bind.dialect.name == "postgresql"
        and settings.app_env.upper() == "TEST"
        and settings.synthetic_only
        and not os.getenv("VERCEL")
    ):
        tables = ", ".join(
            f'"{name}"'
            for name in Base.metadata.tables
        )

        db.execute(
            text(
                f"TRUNCATE TABLE {tables} "
                "RESTART IDENTITY CASCADE"
            )
        )
    else:
        for model in reset_order:
            db.execute(
                delete(model)
            )
else:
    occupied_tables = []

    for table in Base.metadata.sorted_tables:
        if (
            db.execute(
                select(table).limit(1)
            ).first()
            is not None
        ):
            occupied_tables.append(
                table.name
            )

    if occupied_tables:
        raise RuntimeError(
            "Non-destructive synthetic seed "
            "requires an empty migrated database; "
            "existing application data was found."
        )
        office = ConsultancyOffice(office_code="QEC-DOHA", name_en="AMEC Engineering", name_ar="مكتب آفاق الخليج للاستشارات الهندسية", status="ACTIVE"); db.add(office); db.flush()
        users = [("owner@amec.synthetic", "Maha Al-Khatri", Role.OWNER_SPONSOR), ("champion@amec.synthetic", "Yousef Nasser", Role.PROCESS_CHAMPION), ("steward@amec.synthetic", "Noura Salem", Role.REQUIREMENT_STEWARD), ("engineer@amec.synthetic", "Omar Haddad", Role.RESPONSIBLE_ENGINEER), ("preparer@amec.synthetic", "Rana Faisal", Role.PERMIT_PREPARER), ("submitter@amec.synthetic", "Khalid Mansour", Role.FINAL_SUBMITTER), ("admin@amec.synthetic", "Samir Qasem", Role.SYSTEM_ADMIN)]
        db.add_all([User(email=e, display_name=n, role=r, office_id=office.id) for e,n,r in users]); db.flush()
        projects = [Project(project_number=CANONICAL_PROJECT_IDS[0], project_name="Al Noor Villa", office_id=office.id, workstream="RESIDENTIAL", status="ACTIVE", municipality="Doha", permit_type="Building Permit", assigned_engineer="Omar Haddad"), Project(project_number=CANONICAL_PROJECT_IDS[1], project_name="West Bay Residence", office_id=office.id, workstream="RESIDENTIAL", status="ACTIVE", municipality="Doha", permit_type="Building Permit", assigned_engineer="Rana Faisal"), Project(project_number=CANONICAL_PROJECT_IDS[2], project_name="Lusail Office Annex", office_id=office.id, workstream="COMMERCIAL", status="ACTIVE", municipality="Lusail", permit_type="Fit-out Permit", assigned_engineer="Omar Haddad"), Project(project_number=CANONICAL_PROJECT_IDS[3], project_name="Pearl Community Clinic", office_id=office.id, workstream="COMMERCIAL", status="ON_HOLD", municipality="Doha", permit_type="Renovation Permit", assigned_engineer="Noura Salem")]
        db.add_all(projects); db.flush()
        apps = [PermitApplication(project_id=projects[0].id, authority="Permit Authority Simulator", municipality="Doha", permit_type="Building Permit", external_request_number=CANONICAL_APPLICATION_IDS[0], application_status=ApplicationStatus.DRAFT, repetition_count=0), PermitApplication(project_id=projects[1].id, authority="Permit Authority Simulator", municipality="Doha", permit_type="Building Permit", external_request_number=CANONICAL_APPLICATION_IDS[1], application_status=ApplicationStatus.RETURNED, repetition_count=2), PermitApplication(project_id=projects[2].id, authority="Permit Authority Simulator", municipality="Lusail", permit_type="Fit-out Permit", external_request_number=CANONICAL_APPLICATION_IDS[2], application_status=ApplicationStatus.UNDER_REVIEW, repetition_count=1), PermitApplication(project_id=projects[3].id, authority="Permit Authority Simulator", municipality="Doha", permit_type="Renovation Permit", external_request_number=CANONICAL_APPLICATION_IDS[3], application_status=ApplicationStatus.APPROVED, repetition_count=1)]
        db.add_all(apps); db.flush()
        for p, app, root, row in [(projects[0], apps[0], f"2026/{CANONICAL_PROJECT_IDS[0]}_Al-Noor-Villa", 2), (projects[1], apps[1], f"2026/{CANONICAL_PROJECT_IDS[1]}_West-Bay-Residence", 3), (projects[2], apps[2], f"2026/{CANONICAL_PROJECT_IDS[2]}_Lusail-Office-Annex", 4), (projects[3], apps[3], f"2026/{CANONICAL_PROJECT_IDS[3]}_Pearl-Community-Clinic", 5)]:
            db.add_all([ExternalSystemLink(project_id=p.id, system_type=SystemType.SYNOLOGY, external_reference=root, display_reference=root, metadata_json={"synthetic": True}), ExternalSystemLink(project_id=p.id, system_type=SystemType.EXCEL, external_reference=f"GENERAL FOLLOW UP / row {row}", display_reference=f"GENERAL FOLLOW UP / row {row}", metadata_json={"synthetic": True}), ExternalSystemLink(project_id=p.id, system_type=SystemType.MUNICIPALITY, external_reference=app.external_request_number, display_reference=f"Permit Authority Simulator / {app.external_request_number}", metadata_json={"synthetic": True})])
        decisions = [("PRIVACY", "third_party_processing", DecisionStatus.UNKNOWN, "Can PermitOps process QIDs/title deeds?"), ("DATA_LOCATION", "approved_data_location", DecisionStatus.UNKNOWN, "Which approved environment may hold test real documents?"), ("AI_EGRESS", "external_ai_route", DecisionStatus.BLOCKED, "External AI route disabled until approved."), ("DELIVERY_LOCATION", "approved_test_real_document_location", DecisionStatus.UNKNOWN, "Approved TEST real-document location."), ("PORTAL_ACCESS", "preparer_submitter_separation", DecisionStatus.UNKNOWN, "Can preparer and final submitter roles be separated?"), ("BUSINESS_PROCESS", "assisted_entry_baseline", DecisionStatus.PROVISIONAL, "Assisted entry is the MVP planning default."), ("VOLUME", "applications_month", DecisionStatus.PROVISIONAL, "Synthetic volume input only."), ("EXCEL", "excel_canonical_truth", DecisionStatus.CONFIRMED, "Excel is an external representation, not canonical truth."), ("SYNOLOGY", "project_root_pattern", DecisionStatus.PROVISIONAL, "2026/PRJ-number_Name pattern is a synthetic hypothesis."), ("AUTHORITY", "api_availability", DecisionStatus.UNKNOWN, "Authority API availability has not been confirmed.")]
        db.add_all([DiscoveryDecision(category=c, key=k, status=s, value_json={"synthetic": True}, owner="TBD", notes=n) for c,k,s,n in decisions])
        db.add(BusinessCase(values_json=DEFAULT_BUSINESS_CASE)); db.add(VolumeBaseline(values_json={"applications_per_month":25,"active_permit_preparers":3,"average_open_applications":18,"peak_concurrent_applications":8,"portal_accounts":3,"sessions_per_day":10,"relogin_frequency":"UNKNOWN","excel_simultaneous_users":4}))
        questions = [("PREPARER_ROLE", "Can a user prepare a draft without final-submission authority?"), ("SUBMITTER_SEPARATION", "Can another authorized user submit a prepared draft?"), ("SANDBOX", "Is a training/test environment available?"), ("STATUS_READ", "Is read-only application status access available?"), ("COMMENTS_READ", "Can comments/results be exported/read electronically?"), ("PRECHECK_RESULTS", "Can authority AI/precheck results be exported or accessed?"), ("API", "Is a consultancy-facing integration/API available and what is the onboarding process?")]
        db.add_all([MinistryInquiry(question_code=c, question=q, status=InquiryStatus.NOT_ASKED, client_owner="TBD") for c,q in questions])
        raid = [(RaidType.RISK,"R1 - Client data processing permissions unknown","Real sensitive-document processing approval is not established.","HIGH","TBD","Synthetic only until decision"),(RaidType.RISK,"R2 - Ministry automation permissions unknown","Authority automation boundaries are unknown.","HIGH","TBD","Use read-only simulator"),(RaidType.ISSUE,"R3 - Real portal behavior not yet mapped","No official portal has been contacted.","MEDIUM","TBD","Discovery inquiry"),(RaidType.RISK,"R4 - Arabic OCR performance unknown","OCR is deferred.","MEDIUM","TBD","Create synthetic acceptance corpus later"),(RaidType.ASSUMPTION,"R5 - Pilot project not yet frozen","No candidate is automatically selected.","MEDIUM","Client","Review candidate list"),(RaidType.ISSUE,"R6 - Excel locking behavior not yet validated","Workbook lock behavior is simulated only.","MEDIUM","TBD","Validate with client"),(RaidType.DEPENDENCY,"D1 - Responsible Engineer availability required","Pilot requires an available responsible engineer.","MEDIUM","Client","Confirm availability"),(RaidType.DEPENDENCY,"D2 - Client Ministry inquiry required","Narrow process questions need client ownership.","HIGH","Client","Assign inquiry owner"),(RaidType.DEPENDENCY,"D3 - Security/hosting approval required","Hosting and raw-data route remain open.","HIGH","Client","Obtain approval"),(RaidType.ASSUMPTION,"A1 - Assisted municipality preparation is planning default","Human final submission remains outside Week 1 scope.","LOW","Product","Validate in Phase 0")]
        db.add_all([RaidItem(type=t,title=title,description=desc,severity=sev,owner=owner,status="OPEN",mitigation=mit,phase0_close_impact=("BLOCKER" if title.startswith(("R1", "R5", "D2", "D3")) else "CONDITION" if title.startswith(("R2", "R4", "D1", "A1")) else "NONE")) for t,title,desc,sev,owner,mit in raid])
        seed_week2(db, projects)
        seed_week3(db, projects)
        seed_week4(db, projects)
        seed_week45(db, projects)
        seed_week7(db, projects)
        seed_week8(db, projects)
        seed_week9(db, projects)
        seed_week10(db, projects)
        seed_week11(db, projects)
        seed_week12(db, projects)
        seed_week13(db, projects)
        seed_week14(db, projects)
        seed_reconciliation(db, projects)
        seed_users = db.scalars(select(User).order_by(User.email)).all()
        seed_expansion(db, office, seed_users, projects, apps)
        seed_persona_issues_notifications(db)
        for project, application in zip(projects, apps):
            ensure_project_sources_task(db, project, application)
        db.commit()
    create_fixtures(
        synthetic_workspace_root(),
        clean=clean_fixtures,
    )
    ensure_primary_proposal_sources()
    ensure_proposals_contracts_demo_state()
    ensure_contract_center_golden_state()


def ensure_primary_proposal_sources():
    """Keep the canonical owner-demo Proposal source-driven and provenance-backed."""
    with SessionLocal() as db:
        proposal = db.scalar(select(Opportunity).where(Opportunity.opportunity_reference == "SYN-OPP-0001"))
        if not proposal or not proposal.project_id:
            return
        existing = {item.semantic_class for item in db.scalars(select(ProjectArtifactRecord).where(ProjectArtifactRecord.opportunity_id == proposal.id, ProjectArtifactRecord.status == "REGISTERED")).all()}
        source_specs = [
            ("TENDER_DOCUMENT", "tender_document_S1.txt", b"SYNTHETIC TENDER DOCUMENT\nOwner-demo source evidence."),
            ("CLIENT_INFORMATION", "client_information_S1.txt", b"SYNTHETIC CLIENT INFORMATION\nOwner-demo source evidence."),
            ("PROPOSAL_FORM", "proposal_form_S1.txt", b"SYNTHETIC PROPOSAL FORM\nOwner-demo source evidence."),
        ]
        for action, filename, content in source_specs:
            semantic_class = ACTION_CONFIG[action]["semantic_class"]
            if semantic_class in existing:
                continue
            # Include the current seeded lineage in the idempotency key.  The
            # expansion seed may be rerun inside the full test suite and
            # generates fresh Proposal IDs; a global action-only key would
            # incorrectly reuse a prior Proposal's artifact row.
            ingest_project_artifact(db, project_id=proposal.project_id, opportunity_id=proposal.id, action=action, source_filename=filename, content_type="text/plain", content=content, actor="owner@amec.synthetic", actor_role="SYSTEM_ADMIN", correlation_id="seed-primary-proposal-sources", project_reference=proposal.canonical_project_reference, idempotency_key=f"seed-primary:{proposal.id}:{proposal.project_id}:{action}:v1")
        db.commit()


def ensure_proposals_contracts_demo_state():
    """Keep one active pre-contract Proposal beside the contracted chain."""
    with SessionLocal() as db:
        primary = db.scalar(select(Opportunity).where(Opportunity.opportunity_reference == "SYN-OPP-0001"))
        if primary:
            contract = db.scalar(select(Contract).join(Quotation).where(Quotation.opportunity_id == primary.id).order_by(Contract.created_at))
            if contract and primary.status not in {"CONTRACT_HANDOVER", "CONTRACTED", "CLOSED"}:
                primary.status = "CONTRACT_HANDOVER"
            if contract and db.scalar(select(PermitApplication).where(PermitApplication.controlling_contract_id == contract.id)):
                # A Contract with a downstream Permit is already at the
                # handoff boundary; do not present it as an untouched draft.
                contract.status = "CONTRACT_HANDOVER"
        active = db.scalar(select(Opportunity).where(Opportunity.opportunity_reference == "SYN-OPP-0002"))
        if not active:
            office = db.scalar(select(ConsultancyOffice).where(ConsultancyOffice.office_code == "QEC-DOHA"))
            client = db.scalar(select(ClientAccount).where(ClientAccount.client_reference == "SYN-CLIENT-001"))
            project = db.scalar(select(Project).where(Project.project_number == "GHCE-2026-0187"))
            owner = db.scalar(select(User).where(User.email == "owner@amec.synthetic"))
            if office and client and project:
                active = Opportunity(office_id=office.id, client_account_id=client.id, opportunity_reference="SYN-OPP-0002", title="Synthetic Engineering Proposal Intake", status="IN_REVIEW", source_type="TENDER_DOCUMENT", current_owner_user_id=owner.id if owner else None, stage2_capability_scope="UNDECIDED_STAGE2", project_id=project.id, reference_state="CANONICAL", proposal_fields_json={"client_name": client.display_name, "project_description": "Synthetic engineering proposal preparation", "client_scope_of_work": "Synthetic client scope reviewed for engineering preparation", "location": "Synthetic Doha project site", "price": "QAR 98,000", "sow": "Synthetic engineering proposal preparation", "period": "8 weeks", "exclusions": "Authority fees"}, provisional_reference="SYN-OPP-0002", canonical_project_reference=project.project_number, canonicalized_by=owner.email if owner else "owner@amec.synthetic")
                db.add(active)
                db.flush()
                source_content = b"SYNTHETIC GOLDEN PROPOSAL\nStage 1 intake evidence for Engineering Preparation."
                source_hash = hashlib.sha256(source_content).hexdigest()
                db.add(ProposalSourceEvidence(proposal_id=active.id, source_type="TENDER_DOCUMENT", source_filename="tender_document_S2.txt", source_reference=f"synthetic://proposal-source/{active.opportunity_reference}/tender-document/{source_hash}", content_hash=source_hash, content_type="text/plain", source_revision="S2", provenance={"kind": "source", "semantic_class": "TENDER_DOCUMENT_SOURCE", "verification": "READ_BACK_VERIFIED", "golden_fixture": True}, conflict_key="TENDER_DOCUMENT", status="CURRENT", verification_state="READ_BACK_VERIFIED", created_by="owner@amec.synthetic"))
                db.flush()
                # Exercise the same governed command used by the Owner UI. The
                # fixture is not allowed to become Engineering Preparation by
                # assigning the status directly.
                from ..api.bd_proposal_routers import proceed_to_engineering
                proceed_to_engineering(
                    active.id,
                    SimpleNamespace(state=SimpleNamespace(correlation_id="seed-golden-proposal-transition")),
                    db,
                    Role.SYSTEM_ADMIN,
                    "owner@amec.synthetic",
                )
        # The authority comment is a separate returned application so its
        # Comments & Corrections target has a truthful persisted lifecycle.
        authority_application = db.scalar(select(PermitApplication).where(PermitApplication.external_request_number == "GHCE-APP-0142-AUTH"))
        base_application = db.scalar(select(PermitApplication).where(PermitApplication.project_id == (primary.project_id if primary else None)).order_by(PermitApplication.external_request_number)) if primary else None
        if not authority_application and base_application:
            authority_application = PermitApplication(
                project_id=base_application.project_id,
                authority=base_application.authority,
                municipality=base_application.municipality,
                permit_type=base_application.permit_type,
                external_request_number="GHCE-APP-0142-AUTH",
                application_status=ApplicationStatus.RETURNED,
                repetition_count=1,
                controlling_contract_id=base_application.controlling_contract_id,
                workflow_stage="COMMENTS_AND_CORRECTIONS",
            )
            db.add(authority_application)
            db.flush()
        if authority_application:
            authority_finding = db.scalar(select(Finding).where(Finding.correlation_id == "persona-issues-notifications-v1", Finding.title == "Authority returned a technical comment"))
            if authority_finding:
                authority_finding.application_id = authority_application.id
                authority_finding.permit_id = authority_application.id
            authority_task = db.scalar(select(WorkflowTask).where(WorkflowTask.correlation_id == "persona-issues-notifications-v1", WorkflowTask.title == "Authority returned a technical comment"))
            if authority_task:
                authority_task.application_id = authority_application.id
            authority_notification = db.scalar(select(NotificationEvent).where(NotificationEvent.correlation_id == "persona-issues-notifications-v1", NotificationEvent.event_type == "AUTHORITY_COMMENT_CAPTURED"))
            if authority_notification:
                authority_notification.permit_id = authority_application.id
                authority_notification.deep_link = f"/proposals-contracts/{authority_application.project_id}/comments-and-corrections"
        if active:
            active_application = db.scalar(select(PermitApplication).where(PermitApplication.project_id == active.project_id).order_by(PermitApplication.external_request_number))
            technical_finding = db.scalar(select(Finding).where(Finding.correlation_id == "persona-issues-notifications-v1", Finding.title == "Proposal SOW needs engineering confirmation"))
            if technical_finding:
                technical_finding.proposal_id = active.id
                technical_finding.project_id = active.project_id
                if active_application:
                    technical_finding.application_id = active_application.id
            technical_task = db.scalar(select(WorkflowTask).where(WorkflowTask.correlation_id == "persona-issues-notifications-v1", WorkflowTask.title == "Proposal SOW needs engineering confirmation"))
            if technical_task:
                technical_task.context_id = active.id
                technical_task.project_id = active.project_id
                if active_application:
                    technical_task.application_id = active_application.id
            technical_notification = db.scalar(select(NotificationEvent).where(NotificationEvent.correlation_id == "persona-issues-notifications-v1", NotificationEvent.event_type == "ENGINEERING_PROPOSAL_READY"))
            if technical_notification:
                technical_notification.proposal_id = active.id
        db.commit()


def ensure_contract_center_golden_state():
    """Keep the default Contract workspace Proposal-derived and deterministic."""
    from ..services.contract_workspace import create_contract_from_proposal
    from ..services.master_content import create_master_content

    with SessionLocal() as db:
        if db.bind.dialect.name != "postgresql":
            return
        base = db.scalar(select(Opportunity).where(Opportunity.opportunity_reference == "SYN-OPP-0002"))
        proposal = db.scalar(select(Opportunity).where(Opportunity.opportunity_reference == "SYN-OPP-0007"))
        if not proposal and base:
            proposal = Opportunity(office_id=base.office_id, client_account_id=base.client_account_id, opportunity_reference="SYN-OPP-0007", title="Synthetic Engineering Advisory Proposal", status="CONTRACT_HANDOVER", source_type="TENDER_DOCUMENT", current_owner_user_id=base.current_owner_user_id, stage2_capability_scope=base.stage2_capability_scope, project_id=base.project_id, reference_state="CANONICAL", proposal_fields_json=dict(base.proposal_fields_json or {}), provisional_reference="SYN-OPP-0007", canonical_project_reference=base.canonical_project_reference, canonicalized_by="owner@amec.synthetic")
            db.add(proposal)
            db.flush()
            source_content = b"SYNTHETIC GOLDEN CONTRACT PROPOSAL\nProposal-derived Contract owner demo evidence."
            source_hash = hashlib.sha256(source_content).hexdigest()
            db.add(ProposalSourceEvidence(proposal_id=proposal.id, source_type="TENDER_DOCUMENT", source_filename="golden_contract_proposal.txt", source_reference=f"synthetic://proposal-source/{proposal.opportunity_reference}/{source_hash}", content_hash=source_hash, content_type="text/plain", source_revision="S1", provenance={"golden_fixture": True, "verification": "READ_BACK_VERIFIED"}, conflict_key="TENDER_DOCUMENT", status="CURRENT", verification_state="READ_BACK_VERIFIED", created_by="owner@amec.synthetic"))
            db.flush()
        if not proposal or not proposal.client_account_id:
            return
        fields = dict(proposal.proposal_fields_json or {})
        fields.update({
            "client_name": fields.get("client_name") or "Synthetic Client Account",
            "project_description": fields.get("project_description") or "Synthetic engineering advisory scope",
            "client_scope_of_work": fields.get("client_scope_of_work") or "Synthetic client scope confirmed for engineering preparation",
            "scope_of_work": fields.get("scope_of_work") or fields.get("sow") or "Synthetic engineering proposal preparation",
            "price": fields.get("price") or "QAR 98,000",
            "currency": fields.get("currency") or "QAR",
            "duration": fields.get("duration") or fields.get("period") or "8 weeks",
            "payment_condition": fields.get("payment_condition") or "30% on commencement; balance on deliverable acceptance",
        })
        proposal.proposal_fields_json = fields
        accepted = db.scalar(select(ProposalAcceptedRevision).where(ProposalAcceptedRevision.proposal_id == proposal.id).order_by(ProposalAcceptedRevision.revision_number.desc()))
        if not accepted:
            source_ids = [item.id for item in db.scalars(select(ProposalSourceEvidence).where(ProposalSourceEvidence.proposal_id == proposal.id, ProposalSourceEvidence.status == "CURRENT")).all()]
            snapshot = {
                "proposal_id": proposal.id,
                "proposal_reference": proposal.opportunity_reference,
                "title": proposal.title,
                "project_reference": proposal.canonical_project_reference or proposal.provisional_reference,
                "client_account_id": proposal.client_account_id,
                "project_description": fields["project_description"],
                "fields": fields,
                "source_ids": source_ids,
                "template": None,
                "checklist": None,
                "synthetic_only": True,
                "golden_fixture": "contract-center-final-owner-hardening",
            }
            content_hash = stable_hash(snapshot)
            accepted = ProposalAcceptedRevision(proposal_id=proposal.id, revision_number=1, snapshot=snapshot, validation_snapshot={"ready": True, "synthetic_fixture": True}, content_hash=content_hash, accepted_by="owner@amec.synthetic", accepted_at=datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc), status="ACCEPTED")
            db.add(accepted)
            db.flush()
        contract = db.scalar(select(Contract).where(Contract.contract_reference == "SYN-CTR-0007"))
        if not contract:
            contract = create_contract_from_proposal(db, proposal=proposal, accepted=accepted, actor="owner@amec.synthetic", correlation_id="seed-contract-center-golden", requested_reference="SYN-CTR-0007")
        template_item = db.scalar(select(MasterContentItem).where(MasterContentItem.ref == "CT-TEST-001"))
        if not template_item:
            create_master_content(db, content_type="FORM", ref="CT-TEST-001", title="Synthetic Test Contract Template", category_id=None, description="Synthetic test-only Contract Template", filename="CT-TEST-001.txt", mime_type="text/plain", content=b"SYNTHETIC TEST CONTRACT TEMPLATE", actor="owner-demo-seed", idempotency_key="seed-contract-center-template-v1", correlation_id="seed-contract-center-golden", used_in=["ADMIN"])
            template_item = db.scalar(select(MasterContentItem).where(MasterContentItem.ref == "CT-TEST-001"))
        template_version = db.get(DocumentVersion, template_item.current_document_version_id) if template_item and template_item.current_document_version_id else None
        if template_item and template_version and not db.scalar(select(ContractTemplateSnapshot).where(ContractTemplateSnapshot.contract_id == contract.id)):
            db.add(ContractTemplateSnapshot(contract_id=contract.id, contract_revision_id=contract.current_revision_id, master_content_id=template_item.id, master_content_ref=template_item.ref, document_version_id=template_version.id, version=str(template_version.version_number), content_hash=template_version.sha256, captured_by="owner@amec.synthetic"))
        proposal.status = "CONTRACT_HANDOVER"
        db.commit()


def create_fixtures(
    root: Path,
    *,
    clean: bool = True,
):
    synology_year = (
        root
        / "mock-systems"
        / "synology"
        / "2026"
    )
    synology_year.mkdir(
        parents=True,
        exist_ok=True,
    )

    if clean:
        for stale_root in synology_year.glob(
            "PRJ-*"
        ):
            if stale_root.is_dir():
                shutil.rmtree(
                    stale_root
                )
    (root / "mock-systems/municipality").mkdir(parents=True, exist_ok=True)
    (root / "synthetic-data/fixtures").mkdir(parents=True, exist_ok=True)
    for folder in ["master-content/forms", "master-content/reports", "master-content/engineering-works", "proposal-intake"]:
        (root / "mock-systems/synology" / folder).mkdir(parents=True, exist_ok=True)
    for project_number, name in zip(CANONICAL_PROJECT_IDS, ["Al-Noor-Villa", "West-Bay-Residence", "Lusail-Office-Annex", "Pearl-Community-Clinic"]):
        base = root / f"mock-systems/synology/2026/{project_number}_{name}"
        for folder in ["01_Client", "02_Property", "03_Design", "04_Permits", "05_Correspondence"]: (base / folder).mkdir(parents=True, exist_ok=True)
        for rel in ["01_Client/authorization_SAMPLE.pdf", "02_Property/title_deed_SAMPLE.pdf", "03_Design/drawing_R01_SAMPLE.pdf"]:
            target = base / rel
            if target.exists():
                continue
            canvas = Canvas(str(target), pagesize=(612, 792))
            canvas.setFont("Helvetica-Bold", 16); canvas.drawString(72, 700, "SYNTHETIC TEST DOCUMENT")
            canvas.setFont("Helvetica", 12); canvas.drawString(72, 675, "NOT A REAL QATAR GOVERNMENT DOCUMENT")
            canvas.drawString(72, 645, "PermitOps Week 1 fixture - synthetic data only")
            canvas.save()
    (root / "mock-systems/municipality/README.md").write_text("PERMIT AUTHORITY SIMULATOR\nLOCAL SYNTHETIC TEST SYSTEM - NOT AN OFFICIAL GOVERNMENT SERVICE\n", encoding="utf-8")


def seed_week2(db, projects):
    # Deterministic synthetic rebuild; raw document contents never enter audit metadata.
    for model in [SubmissionConfirmation, SpikeFieldResult, SpikeDocumentResult, ExtractionSpikeRun, GoldFieldLabel, GoldDocumentLabel, RealDocumentTestGate, MunicipalityDraft, MunicipalityConfig, Conflict, DrawingMetadataControl, AttachmentCategoryConfig, ApprovalDependency, RequirementConfig, FieldAuthorityRule, FieldObservation, DocumentClassification, DocumentVersion, Document, FieldDefinition, ScenarioConfig]:
        db.execute(delete(model))
    scenario = ScenarioConfig(scenario_code="DEMO_BUILDING_PERMIT_V1", display_name="Demo Building Permit - Synthetic", version="DEMO_BUILDING_PERMIT_V1.0", office_workstream="QEC-DOHA / BUILDING_PERMIT", municipality="Demo Municipality A", permit_type="Building Permit", application_transaction_type="NEW", supported_owner_variants=["INDIVIDUAL", "COMPANY"], supported_languages=["AR", "EN"], supported_complexity_notes="Synthetic Tier 1 configuration example; not a client decision.", interaction_mode=InteractionMode.ASSISTED, status=ConfigStatus.PROVISIONAL)
    db.add(scenario); db.flush()
    field_specs = [("PROPERTY.PIN","Property PIN","IDENTIFIER",Criticality.CRITICAL,"PIN_EXACT"),("PROPERTY.PLOT_NUMBER","Plot number","IDENTIFIER",Criticality.CRITICAL,"IDENTIFIER_EXACT"),("PROPERTY.ZONE","Zone","STRING",Criticality.MAJOR,"TEXT"),("PROPERTY.MUNICIPALITY","Municipality","STRING",Criticality.MAJOR,"TEXT"),("PROPERTY.LAND_AREA","Land area","NUMBER",Criticality.MAJOR,"DECIMAL_2"),("OWNER.TYPE","Owner type","CODE",Criticality.MAJOR,"TEXT"),("OWNER.NAME_AR","Owner Arabic name","STRING",Criticality.CRITICAL,"ARABIC_NAME_COMPARISON"),("OWNER.NAME_EN","Owner English name","STRING",Criticality.MAJOR,"TEXT"),("OWNER.QID","Synthetic owner ID","IDENTIFIER",Criticality.CRITICAL,"QID_EXACT"),("OWNER.CR_NUMBER","Synthetic CR","IDENTIFIER",Criticality.CRITICAL,"CR_EXACT"),("REPRESENTATIVE.FLAG","Representative present","BOOLEAN",Criticality.MAJOR,"TEXT"),("PERMIT.TYPE","Permit type","CODE",Criticality.MAJOR,"TEXT"),("DRAWING.REVISION","Drawing revision","STRING",Criticality.MAJOR,"TEXT"),("DRAWING.PROJECT_NUMBER","Drawing project number","IDENTIFIER",Criticality.CRITICAL,"IDENTIFIER_EXACT")]
    fields = {}
    for code, name, dtype, criticality, rule in field_specs:
        fd = FieldDefinition(field_code=code, name_en=name, data_type=DataType(dtype), criticality=criticality, normalization_rule=rule, description=f"Synthetic Tier 1 field: {name}", active=True); db.add(fd); fields[code] = fd
    db.flush()
    authority = [("PROPERTY.PIN","TITLE_DEED","SURVEY_PLAN","BLOCK"),("PROPERTY.PLOT_NUMBER","TITLE_DEED","SURVEY_PLAN","BLOCK"),("PROPERTY.ZONE","TITLE_DEED","SURVEY_PLAN","BLOCK"),("OWNER.NAME_AR","TITLE_DEED","OWNER_QID","BLOCK"),("OWNER.QID","OWNER_QID","TITLE_DEED","BLOCK"),("DRAWING.REVISION","DRAWING_SET",None,"BLOCK_PACKAGE"),("DRAWING.PROJECT_NUMBER","DRAWING_SET",None,"BLOCK_PACKAGE")]
    for code, primary, fallback, behavior in authority: db.add(FieldAuthorityRule(scenario_id=scenario.id, field_definition_id=fields[code].id, purpose="PERMIT_PREPARATION", primary_source_type=primary, fallback_source_type=fallback, conflict_behavior=behavior, human_verifier_role="REQUIREMENT_STEWARD", notes="Synthetic configuration example", status=ConfigStatus.PROVISIONAL))
    reqs = [("OWNER_ID_INDIVIDUAL","Individual owner synthetic ID is required",RequirementType.FIELD,{"owner_type":"INDIVIDUAL"},None,None,False,True),("COMPANY_CR","Company commercial registration is required",RequirementType.DOCUMENT,{"owner_type":"COMPANY"},"COMMERCIAL_REGISTRATION",None,False,True),("AUTHORIZATION_REPRESENTATIVE","Representative authorization is required",RequirementType.DOCUMENT,{"representative":True},"AUTHORIZATION",None,True,True),("CIVIL_DEFENCE_NOC","Civil Defence NOC must be current",RequirementType.DEPENDENCY,{},None,"CIVIL_DEFENCE_NOC",False,True)]
    db.add_all([RequirementConfig(scenario_id=scenario.id, requirement_code=c, description=d, requirement_type=t, applicability_expression_json=e, required_document_type=dt, required_dependency_type=dep, human_decision_required=hd, blocking=b, status=ConfigStatus.PROVISIONAL) for c,d,t,e,dt,dep,hd,b in reqs])
    categories = [("OWNER_ID","Owner ID","REQUIRED",["OWNER_QID"],False,"AR/EN",["PDF"]),("TITLE_DEED","Title deed","REQUIRED",["TITLE_DEED"],False,"AR/EN",["PDF"]),("AUTHORIZATION","Authorization","CONDITIONAL",["AUTHORIZATION"],False,"AR/EN",["PDF"]),("COMMERCIAL_REGISTRATION","Commercial registration","CONDITIONAL",["COMMERCIAL_REGISTRATION"],False,"AR/EN",["PDF"]),("SURVEY_PLAN","Survey plan","REQUIRED",["SURVEY_PLAN"],False,None,["PDF"]),("COORDINATES","Coordinate report","REQUIRED",["COORDINATE_REPORT"],False,None,["PDF"]),("ARCHITECTURAL_DRAWING","Architectural drawing","REQUIRED",["DRAWING_SET"],True,None,["PDF"]),("STRUCTURAL_DRAWING","Structural drawing","OPTIONAL",["DRAWING_SET"],True,None,["PDF"]),("NOC_CIVIL_DEFENCE","Civil Defence NOC","CONDITIONAL",["NOC"],False,None,["PDF"]),("NOC_KAHRAMAA","Kahramaa NOC","OPTIONAL",["NOC"],True,None,["PDF"]),("CONSULTANT_REGISTRATION","Consultant registration","REQUIRED",["OTHER"],False,"EN",["PDF"]),("ENGINEER_REGISTRATION","Engineer registration","REQUIRED",["OTHER"],False,"EN",["PDF"]),("OWNER_UNDERTAKING","Owner undertaking","CONDITIONAL",["OTHER"],False,"AR/EN",["PDF"]),("CONSULTANT_UNDERTAKING","Consultant undertaking","CONDITIONAL",["OTHER"],False,"EN",["PDF"]),("ENGINEER_UNDERTAKING","Engineer undertaking","CONDITIONAL",["OTHER"],False,"EN",["PDF"]),("PROFESSIONAL_DECLARATION","Professional declaration","CONDITIONAL",["OTHER"],False,"EN",["PDF"]),("AUTHORITY_DECLARATION","Authority declaration","CONDITIONAL",["OTHER"],False,"EN",["PDF"])]
    for order,(code,label,required,allowed,multiple,lang,formats) in enumerate(categories,1): db.add(AttachmentCategoryConfig(scenario_id=scenario.id, category_code=code, label_en=label, required_state=required, applicability_json={}, allowed_document_types=allowed, multiple_files_allowed=multiple, language_requirement=lang, max_size_mb=20, allowed_formats_json=formats, portal_order=order, notes="Synthetic configuration example"))
    controls = [("DRAWING_PROJECT_NUMBER_MATCH","DRAWING.PROJECT_NUMBER"),("DRAWING_OWNER_MATCH","OWNER.NAME_EN"),("DRAWING_PLOT_MATCH","PROPERTY.PLOT_NUMBER"),("DRAWING_REVISION_MATCH","DRAWING.REVISION"),("DRAWING_ZONE_MATCH","PROPERTY.ZONE")]
    for code, field_code in controls: db.add(DrawingMetadataControl(scenario_id=scenario.id, control_code=code, field_definition_id=fields[field_code].id, drawing_source="DRAWING_SET", canonical_field_code=field_code, comparison_type="IDENTIFIER" if "PLOT" in code or "PROJECT" in code else "EXACT", blocking=True, notes="Administrative consistency only; no geometry validation."))
    tabs = [{"key":k,"label":k.title()} for k in ["application","property","owner","building","floors","units","attachments","validation","precheck","status_comments"]]
    portal_fields = [{"field_key":"plot_number","tab":"property","label":"Plot number","type":"string","required":True,"source_mode":"OFFICE_SUPPLIED","editable":True,"portal_order":1,"validation":"synthetic identifier"},{"field_key":"municipality","tab":"property","label":"Municipality","type":"dropdown","required":True,"source_mode":"PORTAL_DERIVED","editable":False,"portal_order":2},{"field_key":"final_professional_declaration","tab":"application","label":"Final professional declaration","type":"human_decision","required":True,"source_mode":"HUMAN_DECISION","editable":True,"portal_order":3}]
    dropdowns = {"permit_type":[{"code":"BP_NEW","label":"New Building Permit"},{"code":"BP_AMEND","label":"Amendment"}],"municipality":[{"code":"MUN_A","label":"Demo Municipality A"},{"code":"MUN_B","label":"Demo Municipality B"}]}
    grids = [{"key":"buildings","columns":["building_ref","building_type","floors","use"]},{"key":"floors","columns":["building_ref","floor_ref","floor_type","area"]}]
    operations = [{"operation":op,"mode":"MOCK","authorization_status":"UNKNOWN","machine_read_supported":True,"human_fallback":True,"mfa_requirement":"USER_PLUS_OTP","session_requirement":"ATTENDED","evidence_requirement":"REFERENCE_ONLY","notes":"Synthetic contract"} for op in ["READ_APPLICATION","READ_CURRENT_STATE","READ_DRAFT","READ_STATUS","READ_COMMENTS","READ_AI_RESULTS","PREPARE_DRAFT","UPLOAD_ATTACHMENT","VALIDATE_DRAFT"]]
    attachments = [{"category_code":c[0],"required_state":c[2],"portal_order":i} for i,c in enumerate(categories,1)]
    db.add(MunicipalityConfig(scenario_id=scenario.id, tabs_json=tabs, fields_json=portal_fields, dropdowns_json=dropdowns, grids_json=grids, attachments_json=attachments, operations_json=operations, mfa_mode="USER_PLUS_OTP", attended_session_required=True, session_notes="OTP to a named human means attended session is required.", precheck_json={"statuses":["NOT_RUN","RUNNING","CLEAR","FINDINGS"]}, submission_confirmation_json={"modes":["MACHINE_READ","HUMAN_EVIDENCE"],"default":"HUMAN_EVIDENCE","submit_capability":False}))
    db.add(RealDocumentTestGate(real_document_test_approved=False, approved_test_location=None, raw_access_roles=[], remote_raw_access_allowed=False, external_ai_allowed=False))
    corpus = [
        (0,"title_deed_clean.pdf","TITLE_DEED",f"TITLE_DEED\nPLOT: 001234\nPIN: PIN-000123\nZONE: Z-07\nMUNICIPALITY: Demo Municipality A\nOWNER_AR: يوسف أحمد علي\nOWNER_EN: Yousef Ahmed Ali\nQID: QID-000001\nOWNER_AR_2: مريم أحمد علي\nOWNER_EN_2: Maryam Ahmed Ali\nQID_2: QID-000004\nSHARE_1: 1/2\nSHARE_2: 1/2\nREPRESENTATIVE: Synthetic Representative LLC\nPROJECT: {CANONICAL_PROJECT_IDS[0]}",{}),
        (0,"title_deed_scan_arabic.pdf","TITLE_DEED","TITLE_DEED\nPLOT: ٠٠١٢٣٤\nPIN: PIN-000123\nZONE: Z-07\nOWNER_AR: يوسف أحمد علي\nOWNER_EN: Yousef Ahmed Ali\nQID: QID-000001",{"poor_ocr":True,"rotation_degrees":2,"low_resolution":True,"stamp_occlusion":True,"ocr_noise":True}),
        (0,"owner_id_bilingual.pdf","OWNER_QID","OWNER_QID\nOWNER_AR: يوسف أحمد علي\nOWNER_EN: Yousef Ahmed Ali\nQID: QID-000001",{}),
        (0,"authorization_bilingual.pdf","AUTHORIZATION",f"AUTHORIZATION\nOWNER_EN: Yousef Ahmed Ali\nPROJECT: {CANONICAL_PROJECT_IDS[0]}",{}),
        (0,"survey_plan.pdf","SURVEY_PLAN",f"SURVEY_PLAN\nPLOT: 001234\nPIN: PIN-000123\nZONE: Z-07\nPROJECT: {CANONICAL_PROJECT_IDS[0]}",{}),
        (0,"coordinate_report.pdf","COORDINATE_REPORT",f"COORDINATE REPORT\nPLOT: 001234\nPIN: PIN-000123\nPROJECT: {CANONICAL_PROJECT_IDS[0]}",{}),
        (0,"drawing_package_R01.pdf","DRAWING_SET",f"DRAWING SET\nPROJECT: {CANONICAL_PROJECT_IDS[0]}\nPLOT: 001234\nOWNER_EN: Yousef Ahmed Ali\nREVISION: R01\nZONE: Z-07",{"revision_label":"R01"}),
        (0,"drawing_package_R02.pdf","DRAWING_SET",f"DRAWING SET\nPROJECT: {CANONICAL_PROJECT_IDS[0]}\nPLOT: 001234\nREVISION: R02\nZONE: Z-07",{"revision_label":"R02"}),
        (1,"title_deed_west_bay.pdf","TITLE_DEED",f"TITLE_DEED\nPLOT: 001234\nPIN: PIN-000223\nZONE: Z-05\nOWNER_AR: يوسف أحمد علي\nOWNER_EN: Youssef Ahmed Ali\nQID: QID-000002\nPROJECT: {CANONICAL_PROJECT_IDS[1]}",{}),
        (1,"owner_id_west_bay.pdf","OWNER_QID","OWNER_QID\nOWNER_AR: يوسف أحمد علي\nOWNER_EN: Youssef Ahmed Ali\nQID: QID-000099",{"poor_ocr":True}),
        (1,"drawing_west_bay_R02.pdf","DRAWING_SET",f"DRAWING SET\nPROJECT: {CANONICAL_PROJECT_IDS[1]}\nPLOT: 001243\nREVISION: R02\nZONE: Z-05",{"revision_label":"R02"}),
        (1,"noc_expired.pdf","NOC",f"NOC\nNOC_TYPE: CIVIL_DEFENCE\nVALID_UNTIL: 2025-12-31\nPROJECT: {CANONICAL_PROJECT_IDS[1]}",{"valid_until":"2025-12-31"}),
        (1,"renamed_duplicate.pdf","TITLE_DEED",f"TITLE_DEED\nPLOT: 001234\nPIN: PIN-000223\nZONE: Z-05\nOWNER_AR: يوسف أحمد علي\nOWNER_EN: Youssef Ahmed Ali\nQID: QID-000002\nPROJECT: {CANONICAL_PROJECT_IDS[1]}",{"duplicate_of":"title_deed_west_bay.pdf"}),
        (1,"wrong_project_document.pdf","SURVEY_PLAN","SURVEY_PLAN\nPLOT: 001243\nPIN: PIN-000223\nPROJECT: GHCE-2026-099",{"wrong_project":True}),
        (2,"lusail_title_deed.pdf","TITLE_DEED",f"TITLE_DEED\nPLOT: 009876\nPIN: PIN-000323\nZONE: Z-11\nOWNER_EN: Noura Salem\nQID: QID-000003\nPROJECT: {CANONICAL_PROJECT_IDS[2]}",{}),
        (2,"lusail_cr.pdf","COMMERCIAL_REGISTRATION",f"COMMERCIAL REGISTRATION\nCR_NUMBER: CR-000003\nOWNER_EN: AMEC Engineering\nPROJECT: {CANONICAL_PROJECT_IDS[2]}",{}),
        (2,"lusail_drawing.pdf","DRAWING_SET",f"DRAWING SET\nPROJECT: {CANONICAL_PROJECT_IDS[2]}\nPLOT: 009876\nREVISION: R03\nZONE: Z-11",{"revision_label":"R03"}),
        (2,"missing_data.pdf","OTHER",f"OTHER\nSTAMP OCCLUSION\nPROJECT: {CANONICAL_PROJECT_IDS[2]}",{"poor_ocr":True}),
    ]
    corpus_root = synthetic_documents_root(); corpus_root.mkdir(parents=True, exist_ok=True)
    for idx,(project_idx, filename, type_code, text, metadata) in enumerate(corpus):
        path = corpus_root / filename
        if not path.exists():
            canvas = Canvas(str(path), pagesize=(612,792)); canvas.setFont("Helvetica-Bold", 13); canvas.drawString(54, 735, "SYNTHETIC TEST DOCUMENT - NOT A REAL GOVERNMENT OR CLIENT DOCUMENT"); canvas.setFont("Helvetica", 10); y=700
            for line in text.splitlines(): canvas.drawString(60,y,line); y-=16
            canvas.save()
        logical = filename.rsplit(".",1)[0].replace("_R02","").replace("_R01","")
        version = register_version(db, project_id=projects[project_idx].id, document_type=type_code, logical_name=logical, language="AR/EN" if "arabic" in filename or "bilingual" in filename else "EN", source_system="SYNTHETIC_SYNOLOGY", source_filename=filename, source_path=str(path), content=text, metadata={**metadata,"gold_class":type_code,"synthetic":True}, correlation_id="seed-week2")
        if type_code == "NOC":
            version.approval_state = DocumentApprovalState.APPROVED
        if type_code == "DRAWING_SET" and "_R01" in filename:
            version.approval_state = DocumentApprovalState.APPROVED
        if version.id == version.document.current_version_id and not version.classifications:
            classify_version(db, version, "seed-week2"); observations = extract_version(db, version, "seed-week2")
            for obs in observations: db.add(GoldFieldLabel(document_version_id=version.id, field_definition_id=obs.field_definition_id, expected_semantic_value={"value":obs.normalized_candidate_value or obs.raw_value}, source_page=1, source_region=obs.source_region_text, adjudicated_by="Synthetic Senior Reviewer", notes="Synthetic gold label"))
            db.add(GoldDocumentLabel(document_version_id=version.id, expected_class=type_code, adjudicated_by="Synthetic Senior Reviewer"))
    db.flush()
    expired_noc = db.scalar(select(Document).where(Document.logical_name == "noc_expired"))
    db.add(ApprovalDependency(project_id=projects[1].id, dependency_type="CIVIL_DEFENCE_NOC", authority_or_owner="Synthetic Civil Defence", reference_number="NOC-DEMO-002", status="CURRENT", valid_from=date(2025,1,1), valid_until=date(2025,12,31), blocking=True, evidence_document_id=expired_noc.id if expired_noc else None, notes="Synthetic expired dependency for readiness test."))
    for project in projects[:2]:
        title_docs = db.scalars(select(Document).where(Document.project_id == project.id, Document.document_type == DocumentType.TITLE_DEED)).all()
        if title_docs:
            version = db.get(DocumentVersion, title_docs[0].current_version_id)
            for observation in db.scalars(select(FieldObservation).where(FieldObservation.document_version_id == version.id)).all():
                verify_observation(db, observation, actor_id="synthetic-reviewer", method=VerificationMethod.SOURCE_CONFIRMED, correction=None, correlation_id="seed-week2")
    for p in projects[:3]: compare_project_conflicts(db, p.id, "seed-week2")


def seed_week3(db, projects):
    for model in [SignoffCProposal, Stage2ReviewAcknowledgement, Stage2Baseline, Phase0Decision, PilotCohort, PrecheckDecision, MunicipalityOperationDecision, DeliveryScenario, BusinessKpiTarget, BusinessBaseline, Tier2BacklogItem, Tier1Decision, AcceptanceCorpusDefinition, ThresholdDefinition, AdjudicationHistory, AdjudicationCase, PhaseBaseline]:
        db.execute(delete(model))
    steward = db.scalar(select(User).where(User.role == Role.REQUIREMENT_STEWARD))
    engineer = db.scalar(select(User).where(User.role == Role.RESPONSIBLE_ENGINEER))
    champion = db.scalar(select(User).where(User.role == Role.PROCESS_CHAMPION))
    submitter = db.scalar(select(User).where(User.role == Role.FINAL_SUBMITTER))
    preparers = db.scalars(select(User).where(User.role == Role.PERMIT_PREPARER)).all()
    scenario = db.scalar(select(ScenarioConfig).where(ScenarioConfig.scenario_code == "DEMO_BUILDING_PERMIT_V1"))
    db.add(PhaseBaseline(phase=Phase.PHASE_0, version="v0.3", status=BaselineStatus.WORKING, created_by="Synthetic Arkan Product Lead", notes="DEMONSTRATION BASELINE — SYNTHETIC DATA — NOT CLIENT APPROVED"))
    profile = {
        "dataset_code":"SYNTHETIC_WORST_CASE_V1", "synthetic_demo":True, "not_client_performance":True,
        "classification":{"documents_evaluated":15,"correct":13,"incorrect":1,"abstained":1,"agreement":13/15,"by_class":{"TITLE_DEED":{"samples":3,"correct":3},"OWNER_QID":{"samples":2,"correct":2},"DRAWING_SET":{"samples":3,"correct":2},"OTHER":{"samples":2,"correct":2},"OTHER_CLASSES":{"samples":5,"correct":4}}},
        "candidate_extraction":{"samples":85,"candidate_present":75,"candidate_correct":67,"candidate_incorrect":8,"candidate_missing":10,"candidate_agreement":67/85,"manual_keyed":11,"human_corrected":15,"by_field":{"PROPERTY.PLOT_NUMBER":{"samples":15,"present":14,"correct":13,"incorrect":1,"missing":1,"manual_keyed":2,"corrected":3},"PROPERTY.PIN":{"samples":15,"present":14,"correct":13,"incorrect":1,"missing":1,"manual_keyed":2,"corrected":2},"OWNER.QID":{"samples":15,"present":13,"correct":11,"incorrect":2,"missing":2,"manual_keyed":3,"corrected":4},"OWNER.NAME_EN":{"samples":20,"present":18,"correct":16,"incorrect":2,"missing":2,"manual_keyed":2,"corrected":3},"DRAWING.REVISION":{"samples":20,"present":16,"correct":14,"incorrect":2,"missing":4,"manual_keyed":2,"corrected":3}}},
        "final_control_quality":{"verified_correct":85,"verified_total":85,"final_verified_agreement":1.0,"critical_false_accepts":0},
        "human_effort":{"classification_review_time_minutes":{"median":1.2,"p90":2.4},"field_verification_time_minutes":{"median":3.8,"p90":7.4},"manual_keyed_entry_time_minutes":{"median":2.6,"p90":5.1},"total_review_time_minutes_per_document":{"median":3.8,"p90":7.4}},
        "evidence_usability":{"GOOD":8,"USABLE":3,"POOR":3,"MISSING":1},
        "failure_modes":{"OCR_UNREADABLE":3,"STAMP_OCCLUSION":2,"ROTATION":1,"LOW_RESOLUTION":2,"ARABIC_SEGMENTATION":2,"LAYOUT_VARIATION":2,"FIELD_NOT_PRESENT":2,"WRONG_CLASSIFICATION":1}
    }
    run = ExtractionSpikeRun(dataset_name="SYNTHETIC_WORST_CASE_V1", dataset_type=DatasetType.SYNTHETIC, environment="TEST", document_count=15, extractor_config_version="LOCAL-SYNTHETIC-EXTRACTOR-1.0", classifier_config_version="RULES-W3-DEMO-1.0", status="COMPLETED", started_at=datetime.now(timezone.utc), completed_at=datetime.now(timezone.utc), metrics_json={"week3_analysis":profile,"automation_quality_note":"Candidate extraction measures automation assistance; it is not final verified-value correctness.","final_control_quality":"Adjudicated verification resulted in 85/85 correct critical values with zero critical false accepts."}, notes="DEMONSTRATION RESULTS — SYNTHETIC DATA — NOT CLIENT PERFORMANCE")
    db.add(run); db.flush()
    versions = db.scalars(select(DocumentVersion).order_by(DocumentVersion.source_filename)).all()[:15]
    for i, version in enumerate(versions):
        expected = version.document.document_type.value
        predicted = expected if i not in (3, 11) else ("OTHER" if i == 3 else "UNKNOWN")
        db.add(SpikeDocumentResult(spike_run_id=run.id, document_version_id=version.id, expected_class=expected, predicted_class=predicted, result="CORRECT" if predicted == expected else ("ABSTAINED" if predicted == "UNKNOWN" else "INCORRECT"), critical_fields_json={"synthetic_profile":True}, corrections=1 if i % 3 == 0 else 0, verification_time_seconds=3.8 * 60, evidence_usability=EvidenceUsability.GOOD if i % 5 else EvidenceUsability.POOR, failure_mode="WRONG_CLASSIFICATION" if predicted == "OTHER" else None))
    for code, samples, correct, wrong, missing, keyed, corrected in [("PROPERTY.PLOT_NUMBER",15,13,1,1,2,3),("PROPERTY.PIN",15,13,1,1,2,2),("OWNER.QID",15,11,2,2,3,4),("OWNER.NAME_EN",20,16,2,2,2,3),("DRAWING.REVISION",20,14,2,4,2,3)]:
        db.add(SpikeFieldResult(spike_run_id=run.id, field_code=code, samples=samples, correct_candidate=correct, wrong_candidate=wrong, missing_candidate=missing, keyed=keyed, corrected=corrected))
    for i, version in enumerate(versions):
        gold = db.scalar(select(GoldDocumentLabel).where(GoldDocumentLabel.document_version_id == version.id))
        expected = gold.expected_class if gold else version.document.document_type.value
        case_status = AdjudicationStatus.DISPUTED if i == 3 else (AdjudicationStatus.IN_REVIEW if i == 11 else AdjudicationStatus.ADJUDICATED)
        case = AdjudicationCase(dataset_id="SYNTHETIC_WORST_CASE_V1", document_version_id=version.id, status=case_status, steward_user_id=steward.id, responsible_engineer_user_id=engineer.id if version.document.document_type == DocumentType.DRAWING_SET else None, expected_class=expected, notes="Synthetic adjudication case; source text and evidence are synthetic.", ambiguity="Synthetic classification dispute" if case_status == AdjudicationStatus.DISPUTED else None)
        db.add(case); db.flush()
        db.add(AdjudicationHistory(case_id=case.id, action="GROUND_TRUTH_CONFIRMED" if case_status == AdjudicationStatus.ADJUDICATED else "CASE_OPENED", actor_id=steward.id, before_json=None, after_json={"status":case_status.value,"expected_class":expected}, notes="Synthetic adjudication history"))
    thresholds = [
        ("FINAL_CRITICAL_FIELD_AGREEMENT","Final critical-field agreement",ThresholdCategory.SAFETY,1.0,85,1.0,">=","HIGH","BLOCKING",ThresholdStatus.PROPOSED,"Synthetic adjudicated profile: 85/85 final verified values correct.","Needs approved client corpus before contractual use."),
        ("CRITICAL_FALSE_ACCEPT","Critical false accepts",ThresholdCategory.SAFETY,0.0,85,0.0,"=","HIGH","BLOCKING",ThresholdStatus.NEEDS_MORE_EVIDENCE,"Synthetic profile recorded zero escapes.","Zero-escape evidence needs broader adversarial sampling."),
        ("DOCUMENT_CLASSIFICATION_AGREEMENT","Document classification agreement",ThresholdCategory.QUALITY,13/15,15,.95,">=","MAJOR","REMEDIATION",ThresholdStatus.PROPOSED,"Synthetic worst-case demonstration profile.","Not representative of client documents."),
        ("CANDIDATE_EXTRACTION_AGREEMENT","Critical candidate extraction agreement",ThresholdCategory.QUALITY,67/85,85,.90,">=","MAJOR","REMEDIATION",ThresholdStatus.PROPOSED,"Synthetic candidate profile.","Candidate agreement is not final control quality."),
        ("MEDIAN_VERIFICATION_TIME","Median verification time",ThresholdCategory.EFFICIENCY,3.8,15,5.0,"<=","NORMAL","ADVISORY",ThresholdStatus.PROPOSED,"Synthetic timed review profile.","Human time must be measured with client users."),
        ("MANUAL_KEYED_PERCENTAGE","Manual keyed usage",ThresholdCategory.OPERATIONS,11/85,85,None,"REPORT","NORMAL","REPORT_ONLY",ThresholdStatus.MEASURED,"Synthetic degraded-path usage.","Not a target or failure condition."),
        ("ATTACHMENT_MAPPING_ERROR","Attachment mapping error",ThresholdCategory.QUALITY,None,None,0.0,"=","MAJOR","BLOCKING",ThresholdStatus.NEEDS_MORE_EVIDENCE,"No representative attachment corpus yet.","Requires municipality-mapped cases."),
        ("PORTAL_RECONCILIATION_ERROR","Portal persisted-state mismatch",ThresholdCategory.QUALITY,None,None,0.0,"=","MAJOR","BLOCKING",ThresholdStatus.NEEDS_MORE_EVIDENCE,"Simulator persistence tests only.","Real authority behavior unknown."),
        ("FINDING_TASK_CREATION","Finding task creation",ThresholdCategory.OPERATIONS,None,None,1.0,">=","NORMAL","ADVISORY",ThresholdStatus.NOT_APPLICABLE,"Finding closure is intentionally deferred.","Not in Week 3 scope."),
        ("RESTORE_TEST","Restore test",ThresholdCategory.SAFETY,None,None,1.0,"=","MAJOR","BLOCKING",ThresholdStatus.NEEDS_MORE_EVIDENCE,"No production restore environment.","Requires approved Stage 2 hosting path.")]
    for code,name,category,observed,sample,proposed,operator,severity,effect,status,basis,notes in thresholds: db.add(ThresholdDefinition(metric_code=code,metric_name=name,category=category,observed_value=observed,sample_size=sample,proposed_threshold=proposed,comparison_operator=operator,severity=severity,acceptance_effect=effect,status=status,basis=basis,notes=notes,owner="Synthetic Technical Lead"))
    db.add(AcceptanceCorpusDefinition(scenario_id=scenario.id, version="v0.1", status=AcceptanceCorpusStatus.DRAFT, description="Reproducible Stage 2 acceptance coverage for the bounded synthetic building-permit scenario.", sampling_rule="All safety-critical cases; all supported classes; difficult Arabic/stamped; returned; repeating grids; owner variants; known high-risk failures.", minimum_cases=25, required_case_types_json=["CLEAN_APPLICATION","RETURNED_APPLICATION","OWNER_IDENTITY_AMBIGUITY","POOR_ARABIC_SCAN","DOCUMENT_REVISION","CONDITIONAL_ATTACHMENT","EXTERNAL_DEPENDENCY","REPEATING_GRID","PORTAL_DERIVED_FIELD"], owner="Noura Salem", notes="15 synthetic spike documents are not representative coverage."))
    decisions = [("FIELD_AUTHORITY_PLOT","Field Authority","Which source is primary for plot number?",Tier1DecisionStatus.RESOLVED,"TITLE_DEED primary; SURVEY_PLAN fallback","Block critical conflict"),("DOCUMENT_NOC","Document Requirement","What proves a current Civil Defence NOC?",Tier1DecisionStatus.RESOLVED_WITH_FALLBACK,"Current approved dependency; human fallback","Readiness blocker if expired"),("ATTACHMENT_APPLICABILITY","Attachment Applicability","Which conditional categories apply by owner/permit scope?",Tier1DecisionStatus.OPEN,"Phase 0 steward review","Required checklist may be incomplete"),("DRAWING_METADATA","Drawing Metadata","Which title-block fields block package readiness?",Tier1DecisionStatus.RESOLVED,"Project, owner, plot, zone, revision","Technical package risk"),("MUNICIPALITY_MAPPING","Municipality Mapping","Is assisted preparation the viable mode?",Tier1DecisionStatus.RESOLVED_WITH_FALLBACK,"MOCK locally; ASSISTED for real authority","No API/browser authorization"),("PRECHECK","Precheck","Is precheck available in the real authority flow?",Tier1DecisionStatus.RESOLVED_WITH_FALLBACK,"Simulator available; real behavior UNKNOWN","Reduced-depth condition"),("SUBMISSION_CONFIRMATION","Submission Confirmation","What evidence confirms a human submission?",Tier1DecisionStatus.RESOLVED,"MACHINE_READ preferred; HUMAN_EVIDENCE fallback","No machine final submit"),("DATA_ACCESS","Data Access","Which approved TEST path permits real documents?",Tier1DecisionStatus.OPEN,"Synthetic-only until approved","Real spike blocker"),("PROFESSIONAL_RESPONSIBILITY","Professional Responsibility","Who owns technical interpretation and final declaration?",Tier1DecisionStatus.OPEN,"Responsible Engineer + Final Submitter roles seeded","Build governance condition")]
    for code,topic,question,status,recommendation,impact in decisions: db.add(Tier1Decision(decision_code=code,topic=topic,question=question,options_json=["CONFIRM","FALLBACK","DEFER"],recommendation=recommendation,owner="Synthetic Requirement Steward",due_date=date(2026,9,1),status=status,evidence="Synthetic configuration and Week 2 contract",impact_if_unresolved=impact,fallback="Assisted human review" if status == Tier1DecisionStatus.RESOLVED_WITH_FALLBACK else None))
    tier2 = [(Tier2Category.MUNICIPALITY_MAPPING,"Complete lower-risk municipality contact fields","Add remaining synthetic contact-field mappings.","Requirement Steward",3,False,"OPEN",None,False),(Tier2Category.EDGE_CASE,"Complete repeating-grid edge mappings","Cover row identity, floor-count, and unit edge cases.","Product + Engineer",4,True,"OPEN","Confirmed grid contract",True),(Tier2Category.FINDING_TAXONOMY,"Define finding taxonomy and closure handoff","Model findings without building the full closure workflow.","Product Lead",4,True,"OPEN","Precheck contract",False),(Tier2Category.KPI,"Connect weekly shadow metrics","Reuse spike definitions for future shadow evidence.","Technical Lead",5,False,"OPEN","Acceptance corpus",False),(Tier2Category.DOCUMENT,"Expand document class coverage","Add further synthetic class variants after Phase 0 confirmation.","Document Steward",3,False,"OPEN","Client taxonomy decision",False)]
    for category,title,description,owner,week,blocking,status,dependency,warning in tier2: db.add(Tier2BacklogItem(category=category,title=title,description=description,owner=owner,priority="HIGH" if blocking else "MEDIUM",due_build_week=week,blocking_week6=blocking,status=Tier2Status(status),dependency=dependency,notes="Synthetic backlog item; does not expand the Stage 2 envelope without explicit decision.",scenario_expansion_warning=warning))
    business = DEFAULT_BUSINESS_CASE
    db.add(BusinessBaseline(applications_per_month=business["applications_per_month"], applications_per_year=business["applications_per_month"]*12, manual_entry_minutes=business["manual_data_entry_minutes"], upload_minutes=business["upload_minutes"], status_check_minutes=business["status_check_minutes"], return_rate=business["return_rate"], average_submission_cycles=business["average_submission_cycles"], rework_hours_per_return=business["rework_hours_per_return"], delay_days_per_return=business["delay_days_per_return"], loaded_hourly_rate_qar=business["loaded_hourly_rate_qar"], optional_delay_value_per_day=business["optional_project_day_value_qar"], standing_classification_impact_status="UNKNOWN", source="Week 1 synthetic business baseline", measurement_period="Synthetic planning baseline", confidence="LOW", status="SYNTHETIC"))
    for category,baseline,target,unit,owner,method in [("REDUCE_MANUAL_PREPARATION_TIME",135.0,None,"minutes/application","Process Champion","Measure before/after shadow runs"),("REDUCE_REPEAT_DATA_ENTRY",1.0,None,"repeat entries/application","Requirement Steward","Count repeated semantic fields"),("REDUCE_ATTACHMENT_ERRORS",None,None,"errors/application","Document Steward","Adjudicated attachment corpus"),("REDUCE_CRITICAL_DATA_CORRECTIONS",15/85,None,"share of critical fields","Responsible Engineer","Compare verified corrections"),("REDUCE_REPEAT_FINDINGS",None,None,"findings/application","Process Champion","Returned-cycle measurement"),("IMPROVE_FIRST_PASS_RATE",None,None,"share of applications","Owner/Sponsor","Client-confirmed outcome data"),("REDUCE_FINDING_ASSIGNMENT_TIME",None,None,"minutes/finding","Product Lead","Shadow workflow timing")]: db.add(BusinessKpiTarget(category=category,baseline=baseline,target=target,unit=unit,status="PROVISIONAL_SYNTHETIC",owner=owner,measurement_method=method))
    db.add_all([DeliveryScenario(scenario_code="HYBRID_APPROVED",name="Hybrid approved-test delivery",description="Selected client-sensitive processing stays in an approved TEST location; remote engineers see redacted data unless explicitly approved.",delivery_location_model="Mixed local/remote",real_data_location="Approved TEST only",remote_raw_access="Restricted / explicit approval",external_ai_route="Disabled unless approved provider/region",test_environment="Client-approved TEST",commercial_range_min_qar=180000,commercial_range_max_qar=260000,schedule_weeks=12,status=DeliveryStatus.SELECTED_DEMO,notes="Illustrative selection — requires client Week 1 privacy/data decision."),DeliveryScenario(scenario_code="QATAR_LOCAL_ACCESS_HEAVY",name="Qatar-local-access-heavy delivery",description="Real sensitive document access restricted to Qatar/client-approved personnel with a heavier local delivery footprint.",delivery_location_model="Qatar/local-heavy",real_data_location="Client-approved Qatar location",remote_raw_access="No raw remote access",external_ai_route="Local or approved route only",test_environment="Client-approved TEST",commercial_range_min_qar=240000,commercial_range_max_qar=340000,schedule_weeks=14,status=DeliveryStatus.CANDIDATE,notes="Synthetic candidate; not a client approval." )])
    operation_names = ["READ_APPLICATION","READ_CURRENT_STATE","READ_DRAFT","PREPARE_DRAFT","UPLOAD_ATTACHMENT","VALIDATE_DRAFT","READ_AI_RESULTS","READ_STATUS","READ_COMMENTS"]
    for operation in operation_names: db.add(MunicipalityOperationDecision(operation=operation,selected_mode=SelectedMode.MOCK if operation.startswith("READ_") else SelectedMode.ASSISTED,authorization_status="UNKNOWN",reason="Synthetic local simulator only; real authorization is unknown.",fallback="Human attended session",evidence="Week 2 simulator contract",decision_owner="Process Champion",status="PROVISIONAL"))
    db.add(PrecheckDecision(available=True,trigger_method="Local simulator precheck endpoint",capture_method="Read structured precheck result",machine_readable=True,required_before_final_review=False,correction_loop_supported=False,fallback="Human review of findings",status="CONFIRMED",evidence="Synthetic simulator only; real authority behavior UNKNOWN"))
    db.add(PilotCohort(scenario_id=scenario.id,super_user_id=preparers[0].id,preparer_user_ids_json=[u.id for u in preparers],process_champion_id=champion.id,requirement_steward_id=steward.id,responsible_engineer_id=engineer.id,final_submitter_id=submitter.id,status=PilotStatus.PROPOSED))
    db.flush()


def seed_week4(db, projects):
    """Reconcile the Week 1–3 seed into one recording-derived synthetic universe."""
    workbook_path = canonical_workbook_path()
    if not workbook_path.exists():
        ensure_canonical_workbook(workbook_path)
    fixture = SyntheticFixtureSet(
        fixture_set_id=CANONICAL_FIXTURE_ID,
        name=CANONICAL_FIXTURE_ID,
        semantic_version=CANONICAL_FIXTURE_VERSION,
        manifest_sha256=CANONICAL_FIXTURE_MANIFEST_HASH,
        source="RECORDING_DERIVED_SYNTHETIC",
        status=FixtureStatus.ACTIVE_GOLDEN_PATH,
        manifest_json=CANONICAL_FIXTURE_MANIFEST,
        notes="One canonical E2E fixture authority; legacy inline fixtures are unit-test-only.",
    )
    db.add(fixture); db.flush()
    scenario = db.scalar(select(ScenarioConfig).where(ScenarioConfig.scenario_code == "DEMO_BUILDING_PERMIT_V1"))
    canonical_root_names = ["Al-Noor-Villa", "West-Bay-Residence", "Lusail-Office-Annex", "Pearl-Community-Clinic"]
    adapter = MockExcelAdapter(str(workbook_path))
    ownership = {
        "Project Number": ExcelOwnership.READ_ONLY_REFERENCE.value,
        "Project Name": ExcelOwnership.HUMAN_OWNED.value,
        "Client/Owner": ExcelOwnership.HUMAN_OWNED.value,
        "Status": ExcelOwnership.HUMAN_OWNED.value,
        "Permit Type": ExcelOwnership.READ_ONLY_REFERENCE.value,
        "Human Notes": ExcelOwnership.HUMAN_OWNED.value,
    }
    for index, project in enumerate(projects):
        initiation = ProjectInitiation(initiation_type=InitiationType.MANUAL_APPROVED_TRIGGER, initiation_reference=f"SYNTHETIC-FIXTURE-{project.project_number}", initiated_by="Synthetic Office Coordinator", status=InitiationStatus.COMPLETED, project_id=project.id, notes="Configured synthetic assumption; not a claim about the client trigger.")
        db.add(initiation); db.flush()
        reservation = ProjectNumberReservation(proposed_number=project.project_number, status=ReservationStatus.CONFIRMED, source_authority="SYNTHETIC_FIXTURE_MANIFEST", initiation_id=initiation.id, project_id=project.id, confirmed_at=datetime.now(timezone.utc))
        db.add(reservation); db.flush()
        root_path = f"2026/{project.project_number}_{canonical_root_names[index]}"
        bootstrap = SynologyProjectBootstrap(project_id=project.id, root_path=root_path, subfolders_json=CANONICAL_PROJECT_SUBFOLDERS, template_applied=True, template_manifest_json=[f"{folder}/TEMPLATE_APPLIED.txt" for folder in CANONICAL_PROJECT_SUBFOLDERS], status="CREATED")
        db.add(bootstrap); db.flush()
        row = adapter.resolve_row_identity(project.project_number)
        if not row:
            raise RuntimeError(f"Canonical workbook row missing for {project.project_number}")
        excel_row = ExcelProjectRow(project_id=project.id, workbook_identity=CANONICAL_WORKBOOK, sheet_name=row["sheet_name"], row_number=row["row_number"], row_key=row["row_key"], ownership_matrix_json=ownership, projection_sheet=CANONICAL_PROJECTION_SHEET, human_cells_fingerprint=f"SYNTHETIC-HUMAN-CELL-{project.project_number}", read_policy="Read GENERAL FOLLOW UP and preserve human-owned cells", write_policy="Write only PERMITOPS SYSTEM PROJECTION", status="LINKED")
        db.add(excel_row); db.flush()
        for event_type, entity_type, entity_id, after in [
            ("PROJECT_INITIATED", "ProjectInitiation", initiation.id, {"initiation_type": initiation.initiation_type.value}),
            ("PROJECT_NUMBER_RESERVED", "ProjectNumberReservation", reservation.id, {"project_number": project.project_number}),
            ("PROJECT_CREATED", "Project", project.id, {"project_number": project.project_number}),
            ("SYNOLOGY_PROJECT_ROOT_CREATED", "SynologyProjectBootstrap", bootstrap.id, {"root_path": root_path}),
            ("PROJECT_TEMPLATE_APPLIED", "SynologyProjectBootstrap", bootstrap.id, {"subfolders": CANONICAL_PROJECT_SUBFOLDERS}),
            ("EXCEL_PROJECT_ROW_LINKED", "ExcelProjectRow", excel_row.id, {"sheet": row["sheet_name"], "row_number": row["row_number"], "row_key": row["row_key"]}),
        ]:
            audit(db, correlation_id="seed-canonical-fixture", event_type=event_type, entity_type=entity_type, entity_id=entity_id, after=after, metadata=fixture_metadata())
        plot = ["001234", "001234", "009876", "UNSET"][index]
        adapter.write_system_projection(project.project_number, {"Canonical Plot Number": plot, "Canonical PIN": ["PIN-000123", "PIN-000223", "PIN-000323", "UNSET"][index], "Rendering Version": "R1.0", "Municipality Request": CANONICAL_APPLICATION_IDS[index], "Projection Status": "SEEDED"})

    # The canonical recording-derived title deed is deliberately multi-owner.
    title_version = db.scalar(select(DocumentVersion).join(Document).where(Document.logical_name == "title_deed_clean").order_by(DocumentVersion.version_number.desc()))
    plot_assertion = db.scalar(select(VerifiedAssertion).join(FieldDefinition, VerifiedAssertion.field_definition_id == FieldDefinition.id).where(VerifiedAssertion.project_id == projects[0].id, FieldDefinition.field_code == "PROPERTY.PLOT_NUMBER", VerifiedAssertion.status == AssertionStatus.CURRENT))
    property_record = Property(project_id=projects[0].id, pin="PIN-000123", plot_number="001234", zone="Z-07", municipality="Demo Municipality A", plan_reference="PLAN-SYN-07", land_area=500.0, land_area_unit="m2", source_document_version_id=title_version.id if title_version else None, source_observation_id=plot_assertion.source_observation_id if plot_assertion else None, source_assertion_id=plot_assertion.id if plot_assertion else None, status=OwnershipStatus.CURRENT)
    db.add(property_record); db.flush()
    owner_one = Party(party_type=PartyType.INDIVIDUAL, name_ar="يوسف أحمد علي", name_en="Yousef Ahmed Ali", identifier_type="QID", identifier_value="QID-000001", source_document_version_id=title_version.id if title_version else None)
    owner_two = Party(party_type=PartyType.INDIVIDUAL, name_ar="مريم أحمد علي", name_en="Maryam Ahmed Ali", identifier_type="QID", identifier_value="QID-000004", source_document_version_id=title_version.id if title_version else None)
    representative = Party(party_type=PartyType.COMPANY, name_ar="شركة وكيل اصطناعية", name_en="Synthetic Representative LLC", identifier_type="CR", identifier_value="CR-000001", source_document_version_id=title_version.id if title_version else None)
    db.add_all([owner_one, owner_two, representative]); db.flush()
    db.add_all([
        PropertyOwnership(property_id=property_record.id, party_id=owner_one.id, share_numerator=1, share_denominator=2, normalized_share=0.5, source_document_version_id=title_version.id if title_version else None, source_assertion_id=plot_assertion.id if plot_assertion else None, status=OwnershipStatus.CURRENT),
        PropertyOwnership(property_id=property_record.id, party_id=owner_two.id, share_numerator=1, share_denominator=2, normalized_share=0.5, source_document_version_id=title_version.id if title_version else None, source_assertion_id=plot_assertion.id if plot_assertion else None, status=OwnershipStatus.CURRENT),
    ])
    authorization = Authorization(principal_party_id=owner_one.id, representative_party_id=representative.id, authorization_type="LIMITED_PERMIT_PREPARATION", scope="Synthetic application preparation only", valid_from=date(2026, 1, 1), valid_until=date(2026, 12, 31), evidence_document_version_id=title_version.id if title_version else None, status=AuthorizationStatus4.VALID, notes="Synthetic evidence; expiry must be evaluated before later readiness.")
    db.add(authorization); db.flush()
    db.add(Representation(principal_party_id=owner_one.id, representative_party_id=representative.id, authorization_type=authorization.authorization_type, scope=authorization.scope, valid_from=authorization.valid_from, valid_until=authorization.valid_until, evidence_document_version_id=authorization.evidence_document_version_id, authorization_id=authorization.id, status=AuthorizationStatus4.VALID))
    # Target rendering is target-specific presentation over the same verified semantic fact.
    plot_field = db.scalar(select(FieldDefinition).where(FieldDefinition.field_code == "PROPERTY.PLOT_NUMBER"))
    permit_field = db.scalar(select(FieldDefinition).where(FieldDefinition.field_code == "PERMIT.TYPE"))
    area_field = db.scalar(select(FieldDefinition).where(FieldDefinition.field_code == "PROPERTY.LAND_AREA"))
    render_specs = [
        (plot_field, RenderingTarget.FORM, "plot_number", "IDENTIFIER_EXACT", None, None, {}, "PRESERVE_NULL", "1.0"),
        (plot_field, RenderingTarget.EXCEL, "Canonical Plot Number", "IDENTIFIER_EXACT", None, None, {}, "PRESERVE_NULL", "1.0"),
        (plot_field, RenderingTarget.MUNICIPALITY, "property.plot_number", "IDENTIFIER_EXACT", None, None, {}, "PRESERVE_NULL", "1.0"),
        (area_field, RenderingTarget.FORM, "land_area", "DECIMAL_2", "EN", "m2", {}, "PRESERVE_NULL", "1.0"),
        (area_field, RenderingTarget.EXCEL, "Canonical Land Area", "DECIMAL_2", "EN", "m2", {}, "PRESERVE_NULL", "1.0"),
        (area_field, RenderingTarget.MUNICIPALITY, "property.land_area", "DECIMAL_0", "EN", "m2", {}, "PRESERVE_NULL", "1.0"),
        (permit_field, RenderingTarget.MUNICIPALITY, "application.permit_type", "CODE", "EN", None, {"Building Permit": "BP_NEW", "Fit-out Permit": "BP_FITOUT", "Renovation Permit": "BP_RENOVATION"}, "PRESERVE_NULL", "1.0"),
    ]
    for field, target, location, fmt, language, unit, code_map, null_behavior, version in render_specs:
        if field:
            db.add(TargetRenderingRule(scenario_id=scenario.id, field_definition_id=field.id, target_system=target, target_location=location, format_rule=fmt, language_rule=language, unit_rule=unit, dropdown_code_map=code_map, null_behavior=null_behavior, version=version, status=RenderingStatus.ACTIVE))
    db.add_all([
        ExcelProjectionRule(scenario_id=scenario.id, sheet_name=CANONICAL_PROJECTION_SHEET, row_key_rule="Project Number exact match", target_column="Canonical Plot Number", ownership=ExcelOwnership.PERMITOPS_OWNED, source_field="PROPERTY.PLOT_NUMBER", write_allowed=True),
        ExcelProjectionRule(scenario_id=scenario.id, sheet_name=CANONICAL_PROJECTION_SHEET, row_key_rule="Project Number exact match", target_column="Canonical PIN", ownership=ExcelOwnership.PERMITOPS_OWNED, source_field="PROPERTY.PIN", write_allowed=True),
        ExcelProjectionRule(scenario_id=scenario.id, sheet_name="GENERAL FOLLOW UP", row_key_rule="Project Number exact match", target_column="Human Notes", ownership=ExcelOwnership.HUMAN_OWNED, source_field="PROJECT.NOTES", write_allowed=False),
    ])
    # Disposition every generated synthetic conflict: canonical path is resolved; other variants are intentionally ambiguous.
    for conflict in db.scalars(select(Conflict)).all():
        conflict.status = ConflictStatus.RESOLVED if conflict.project_id == projects[0].id else ConflictStatus.ACCEPTED
        conflict.resolver = "Synthetic Requirement Steward"
        conflict.resolution = "Canonical title-deed evidence selected for the golden path." if conflict.project_id == projects[0].id else "Intentionally ambiguous synthetic variant retained outside the golden path; later human review required."
        conflict.resolved_at = datetime.now(timezone.utc)
        audit(db, correlation_id="seed-canonical-fixture", event_type="CONFLICT_DISPOSITIONED", entity_type="Conflict", entity_id=conflict.id, after={"status": conflict.status.value, "resolution": conflict.resolution}, metadata=fixture_metadata())
    db.flush()


def seed_week45(db, projects):
    """Seed the bounded Week 4–5 configuration seam for the canonical case."""
    scenario = db.scalar(select(ScenarioConfig).where(ScenarioConfig.scenario_code == "DEMO_BUILDING_PERMIT_V1"))
    office = db.scalar(select(ConsultancyOffice).where(ConsultancyOffice.office_code == "QEC-DOHA"))
    engineer = db.scalar(select(User).where(User.email == "engineer@amec.synthetic"))
    title_version = db.scalar(select(DocumentVersion).join(Document).where(Document.logical_name == "title_deed_clean").order_by(DocumentVersion.version_number.desc()))
    db.add(MinimumPackageDefinition(
        scenario_id=scenario.id, version="PKG-1.0", status="ACTIVE",
        required_field_codes=["PROPERTY.PLOT_NUMBER", "PROPERTY.PIN", "OWNER.NAME_AR", "OWNER.QID", "DRAWING.PROJECT_NUMBER", "DRAWING.REVISION"],
        required_document_rules=[{"requirement_code":"TITLE_DEED_CURRENT_APPROVED","document_type":"TITLE_DEED","blocking":True},{"requirement_code":"OWNER_ID_PER_OWNER","document_type":"OWNER_QID","blocking":True}],
        required_attachment_rules=[{"category_code":"TITLE_DEED","required":True},{"category_code":"OWNER_ID","required":True},{"category_code":"ARCHITECTURAL_DRAWING","required":True}],
        required_dependency_rules=[{"dependency_type":"RESPONSIBLE_ENGINEER_REGISTRATION","blocking":True}],
        required_drawing_controls=["DRAWING_PROJECT_NUMBER_MATCH", "DRAWING_PLOT_MATCH", "DRAWING_REVISION_MATCH"],
        required_human_gates=["DATA_VERIFICATION_COMPLETE", "TECHNICAL_REVIEW_COMPLETE", "PACKAGE_APPROVED"],
        unresolved_conflict_policy="BLOCK_CRITICAL_UNRESOLVED", package_approver_role="REQUIREMENT_STEWARD",
        notes="Synthetic Week 4 minimum package definition; later municipality-specific variants require controlled configuration release.",
    ))
    if engineer and title_version:
        db.add(ProfessionalCredential(project_id=projects[0].id, credential_type="RESPONSIBLE_ENGINEER_REGISTRATION", holder=engineer.display_name, registration_number="SYN-ENG-0001", authority="Synthetic Engineering Authority", valid_from=datetime(2026,1,1,tzinfo=timezone.utc), valid_until=datetime(2026,12,31,23,59,59,tzinfo=timezone.utc), status="CURRENT", evidence_document_version_id=title_version.id))
    if office and title_version:
        db.add(OfficeCredential(office_id=office.id, credential_type="CONSULTANCY_OFFICE_REGISTRATION", holder=office.name_en, registration_number="SYN-OFFICE-0001", authority="Synthetic Consultancy Authority", valid_from=datetime(2026,1,1,tzinfo=timezone.utc), valid_until=datetime(2026,12,31,23,59,59,tzinfo=timezone.utc), status="CURRENT", evidence_document_version_id=title_version.id))
    form_specs = [
        ("CONSULTANT_AUTH_ARCH", "Consultant Authorization — Architectural", {"project_number":"DRAWING.PROJECT_NUMBER", "plot_number":"PROPERTY.PLOT_NUMBER", "owners":"PROPERTY.OWNERS"}),
        ("OWNER_UNDERTAKING", "Owner Undertaking", {"owners":"PROPERTY.OWNERS", "plot_number":"PROPERTY.PLOT_NUMBER"}),
        ("CONTRACTOR_UNDERTAKING", "Contractor Undertaking", {"project_number":"DRAWING.PROJECT_NUMBER"}),
        ("CONTRACTOR_AUTH", "Contractor Authorization", {"project_number":"DRAWING.PROJECT_NUMBER"}),
        ("CONSULTANT_UNDERTAKING_SUP", "Consultant Undertaking — Supervision", {"engineer":"RESPONSIBLE_ENGINEER"}),
        ("CONSULTANT_AUTH_SUP", "Consultant Authorization — Supervision", {"engineer":"RESPONSIBLE_ENGINEER", "owners":"PROPERTY.OWNERS"}),
    ]
    for code, name, mapping in form_specs:
        template = FormTemplate(template_code=code, name=name, status="ACTIVE")
        db.add(template); db.flush()
        db.add(FormTemplateVersion(template_id=template.id, version="1.0", source_field_mapping_version="FIELD-MAP-1.0", mapping_json=mapping, status="ACTIVE"))
    for project in projects:
        if project.id == projects[0].id:
            db.add(ApprovalDependency(project_id=project.id, dependency_type="RESPONSIBLE_ENGINEER_REGISTRATION", authority_or_owner="Synthetic Engineering Authority", reference_number="SYN-ENG-0001", status="CURRENT", valid_from=date(2026,1,1), valid_until=date(2026,12,31), blocking=True, evidence_document_id=title_version.document_id if title_version else None, notes="Synthetic dependency; validity is evaluated at readiness."))
    db.flush()


def seed_week7(db, projects):
    """Seed controlled synthetic finding taxonomy, routing, SLA, and portal rules."""
    existing = db.scalar(select(FindingCode).limit(1))
    if existing:
        return
    sources = [FindingSourceType.AUTHORITY_PRECHECK, FindingSourceType.PORTAL_VALIDATION, FindingSourceType.OFFICIAL_MUNICIPALITY_COMMENT, FindingSourceType.MANUAL_OPERATOR_CAPTURE]
    specs = [
        ("PROPERTY_IDENTITY_MISMATCH", "Property identity mismatch", "عدم تطابق هوية العقار", "Canonical property identity differs from source or portal evidence.", "تختلف هوية العقار الأساسية عن الدليل أو بيانات البوابة.", [FindingSourceType.INTERNAL_PREFLIGHT, FindingSourceType.PORTAL_VALIDATION, FindingSourceType.OFFICIAL_MUNICIPALITY_COMMENT], "PROPERTY", FindingSeverity.BLOCKING, True, Role.REQUIREMENT_STEWARD.value, "PROPERTY_IDENTITY", "DOCUMENT_EVIDENCE"),
        ("OWNER_AUTHORIZATION_MISSING", "Owner authorization missing", "تفويض المالك مفقود", "Required owner authorization evidence is missing or not approved.", "دليل تفويض المالك المطلوب مفقود أو غير معتمد.", sources, "DOCUMENT", FindingSeverity.BLOCKING, True, Role.REQUIREMENT_STEWARD.value, "OWNER_AUTHORIZATION", "DOCUMENT_EVIDENCE"),
        ("DRAWING_REVISION_MISMATCH", "Drawing revision mismatch", "عدم تطابق إصدار الرسم", "Drawing revision does not match the approved package or authority requirement.", "إصدار الرسم لا يطابق الحزمة المعتمدة أو متطلب الجهة.", sources, "TECHNICAL", FindingSeverity.BLOCKING, True, Role.RESPONSIBLE_ENGINEER.value, "DRAWING_REVISION", "DRAWING_REVISION"),
        ("ATTACHMENT_MISSING", "Required attachment missing", "مرفق مطلوب مفقود", "A required attachment is not present in the prepared package.", "مرفق مطلوب غير موجود في الحزمة المعدة.", [FindingSourceType.PORTAL_VALIDATION, FindingSourceType.OFFICIAL_MUNICIPALITY_COMMENT, FindingSourceType.INTERNAL_PREFLIGHT], "DOCUMENT", FindingSeverity.BLOCKING, True, Role.PERMIT_PREPARER.value, "ATTACHMENT_MISSING", "DOCUMENT_EVIDENCE"),
        ("ATTACHMENT_WRONG_CATEGORY", "Attachment category is incorrect", "تصنيف المرفق غير صحيح", "The supplied attachment category does not match the configured requirement.", "تصنيف المرفق لا يطابق المتطلب المكوّن.", sources, "DOCUMENT", FindingSeverity.MAJOR, True, Role.PERMIT_PREPARER.value, "ATTACHMENT_CATEGORY", "DOCUMENT_EVIDENCE"),
        ("PORTAL_REQUIRED_FIELD_MISSING", "Portal required field missing", "حقل مطلوب في البوابة مفقود", "A configured required portal field is empty.", "حقل مطلوب مكوّن في البوابة فارغ.", [FindingSourceType.PORTAL_VALIDATION], "PORTAL", FindingSeverity.BLOCKING, True, Role.PERMIT_PREPARER.value, "PORTAL_FIELD", "TEXT_JUSTIFICATION"),
        ("PRECHECK_TECHNICAL_TODO", "Authority precheck technical action", "إجراء فني من الفحص المسبق", "Authority AI/precheck returned a technical action for human review.", "أعاد الفحص المسبق إجراءً فنياً للمراجعة البشرية.", [FindingSourceType.AUTHORITY_PRECHECK], "TECHNICAL", FindingSeverity.BLOCKING, True, Role.RESPONSIBLE_ENGINEER.value, "PRECHECK_TECHNICAL", "AUTHORITY_RECHECK"),
        ("PRECHECK_DOCUMENT_TODO", "Authority precheck document action", "إجراء مستندي من الفحص المسبق", "Authority AI/precheck returned a document action for human review.", "أعاد الفحص المسبق إجراءً مستندياً للمراجعة البشرية.", [FindingSourceType.AUTHORITY_PRECHECK], "DOCUMENT", FindingSeverity.MAJOR, True, Role.PERMIT_PREPARER.value, "PRECHECK_DOCUMENT", "DOCUMENT_EVIDENCE"),
        ("OFFICIAL_DRAWING_COMMENT", "Official drawing comment", "تعليق رسمي على الرسم", "An official municipality reviewer commented on a drawing.", "أبدى مراجع البلدية الرسمي تعليقاً على الرسم.", [FindingSourceType.OFFICIAL_MUNICIPALITY_COMMENT], "TECHNICAL", FindingSeverity.BLOCKING, True, Role.RESPONSIBLE_ENGINEER.value, "OFFICIAL_DRAWING", "AUTHORITY_RECHECK"),
        ("OFFICIAL_DOCUMENT_COMMENT", "Official document comment", "تعليق رسمي على المستند", "An official municipality reviewer commented on a document.", "أبدى مراجع البلدية الرسمي تعليقاً على مستند.", [FindingSourceType.OFFICIAL_MUNICIPALITY_COMMENT], "DOCUMENT", FindingSeverity.MAJOR, True, Role.PERMIT_PREPARER.value, "OFFICIAL_DOCUMENT", "DOCUMENT_EVIDENCE"),
        ("OTHER_AUTHORITY_COMMENT", "Other authority comment", "تعليق رسمي آخر من الجهة", "An official authority comment requires operator classification.", "تعليق رسمي من الجهة يحتاج إلى تصنيف المشغل.", [FindingSourceType.OFFICIAL_MUNICIPALITY_COMMENT, FindingSourceType.EMAIL_NOTICE, FindingSourceType.MANUAL_OPERATOR_CAPTURE], "GENERAL", FindingSeverity.MAJOR, True, Role.PROCESS_CHAMPION.value, "OTHER_AUTHORITY", "TEXT_JUSTIFICATION"),
    ]
    codes: dict[str, FindingCode] = {}
    for code, title_en, title_ar, desc_en, desc_ar, allowed, discipline, severity, blocking, owner, control, evidence in specs:
        item = FindingCode(code=code, version="1.0", title_en=title_en, title_ar=title_ar, description_en=desc_en, description_ar=desc_ar, source_classes_allowed=allowed, discipline=discipline, default_severity=severity, blocking_default=blocking, required_owner_role=owner, default_sla_hours=48 if severity != FindingSeverity.BLOCKING else 24, closure_evidence_policy=evidence, internal_preflight_control_code=control, status=FindingCodeStatus.ACTIVE, effective_from=datetime(2026, 1, 1, tzinfo=timezone.utc))
        db.add(item); db.flush(); codes[code] = item
    for severity, ack, assign, target, escalation in [(FindingSeverity.BLOCKING, 4, 8, 24, 48), (FindingSeverity.MAJOR, 8, 24, 48, 72), (FindingSeverity.ADVISORY, 24, 48, 120, 168)]:
        db.add(FindingSlaPolicy(scenario_id="DEMO_BUILDING_PERMIT_V1", severity=severity, acknowledgment_hours=ack, assignment_hours=assign, target_action_hours=target, escalation_hours=escalation, business_calendar_mode="CALENDAR_HOURS", version="1.0", active=True, policy_label="PROVISIONAL_SYNTHETIC"))
    engineer = db.scalar(select(User).where(User.email == "engineer@amec.synthetic"))
    preparer = db.scalar(select(User).where(User.email == "preparer@amec.synthetic"))
    steward = db.scalar(select(User).where(User.email == "steward@amec.synthetic"))
    routes = [("DRAWING_REVISION_MISMATCH", Role.RESPONSIBLE_ENGINEER.value, engineer), ("PRECHECK_TECHNICAL_TODO", Role.RESPONSIBLE_ENGINEER.value, engineer), ("OFFICIAL_DRAWING_COMMENT", Role.RESPONSIBLE_ENGINEER.value, engineer), ("ATTACHMENT_MISSING", Role.PERMIT_PREPARER.value, preparer), ("ATTACHMENT_WRONG_CATEGORY", Role.PERMIT_PREPARER.value, preparer), ("PORTAL_REQUIRED_FIELD_MISSING", Role.PERMIT_PREPARER.value, preparer), ("OWNER_AUTHORIZATION_MISSING", Role.REQUIREMENT_STEWARD.value, steward), ("PRECHECK_DOCUMENT_TODO", Role.PERMIT_PREPARER.value, preparer), ("OFFICIAL_DOCUMENT_COMMENT", Role.PERMIT_PREPARER.value, preparer)]
    for code, role, user in routes:
        db.add(FindingRoutingRule(scenario_id="DEMO_BUILDING_PERMIT_V1", finding_code_id=codes[code].id, owner_role=role, preferred_user_id=user.id if user else None, escalation_role=Role.PROCESS_CHAMPION.value, active=True, version="1.0"))
    for validation_code, code, severity, role in [("ATTACHMENT_MISSING", "ATTACHMENT_MISSING", FindingSeverity.BLOCKING, Role.PERMIT_PREPARER.value), ("REQUIRED_FIELD_MISSING", "PORTAL_REQUIRED_FIELD_MISSING", FindingSeverity.BLOCKING, Role.PERMIT_PREPARER.value), ("PORTAL_REQUIRED_FIELD_MISSING", "PORTAL_REQUIRED_FIELD_MISSING", FindingSeverity.BLOCKING, Role.PERMIT_PREPARER.value), ("WRONG_ATTACHMENT_CATEGORY", "ATTACHMENT_WRONG_CATEGORY", FindingSeverity.MAJOR, Role.PERMIT_PREPARER.value)]:
        db.add(PortalValidationFindingRule(validation_code=validation_code, create_finding=True, severity=severity, finding_code_id=codes[code].id, owner_role=role, active=True))
    db.flush()


def seed_week8(db, projects):
    """Seed validity snapshots and deterministic configuration impact policy."""
    if db.scalar(select(ConfigurationChangeImpactPolicy).limit(1)):
        return
    now = datetime.now(timezone.utc)
    for version in db.scalars(select(DocumentVersion)).all():
        status = DocumentValidityStatus.SUPERSEDED if version.approval_state == DocumentApprovalState.SUPERSEDED else DocumentValidityStatus.VALID
        db.add(DocumentValidity(document_version_id=version.id, effective_from=datetime.combine(version.valid_from, datetime.min.time(), tzinfo=timezone.utc) if version.valid_from else None, expires_at=datetime.combine(version.valid_until, datetime.max.time(), tzinfo=timezone.utc) if version.valid_until else None, validity_status=status, evaluated_at=now, rule_version="DOC-VALIDITY-1.0"))
    for dependency in db.scalars(select(ApprovalDependency)).all():
        db.add(AuthorityApprovalValidity(approval_dependency_id=dependency.id, valid_from=datetime.combine(dependency.valid_from, datetime.min.time(), tzinfo=timezone.utc) if dependency.valid_from else None, valid_until=datetime.combine(dependency.valid_until, datetime.max.time(), tzinfo=timezone.utc) if dependency.valid_until else None, status="VALID" if dependency.status == "CURRENT" else "UNKNOWN_REVIEW_REQUIRED", evaluated_at=now, evidence_document_version_id=None))
    policies = [
        ("REQUIREMENT_SET", "MATERIAL", "REQUIRE_NEW_PREPARATION_REVISION", True, True),
        ("TARGET_RENDERING_RULE", "MATERIAL", "MARK_STALE", True, False),
        ("FIELD_AUTHORITY_RULE", "MATERIAL", "MARK_STALE", True, False),
        ("SCENARIO_CONFIG", "MATERIAL", "REQUIRE_NEW_PREPARATION_REVISION", True, True),
    ]
    for config_type, severity, active_policy, reevaluate, new_revision in policies:
        db.add(ConfigurationChangeImpactPolicy(config_type=config_type, change_severity=severity, active_revision_policy=active_policy, requires_re_evaluation=reevaluate, requires_new_revision=new_revision, effective_from=now, version="1.0", active=True))
    db.flush()


def seed_week9(db, projects):
    """Seed the signed synthetic 17-category attachment contract."""
    if db.scalar(select(AttachmentCategoryRule).limit(1)):
        return
    scenario = db.scalar(select(ScenarioConfig).where(ScenarioConfig.scenario_code == "DEMO_BUILDING_PERMIT_V1"))
    if not scenario:
        return
    categories = [
        ("ORIGINAL_LETTER", "Original Letter", "OPTIONAL", ["OTHER"], 0, 1, False),
        ("TITLE_DEED_PROPERTY_PLAN", "Title Deed + Property Plan", "REQUIRED", ["TITLE_DEED", "SURVEY_PLAN"], 1, 2, True),
        ("OWNER_REPRESENTATIVE_ID", "Owner / Representative ID", "REQUIRED", ["OWNER_QID", "AUTHORIZATION"], 1, None, True),
        ("OWNER_AUTHORIZATION", "Owner Authorization for Engineering Consultant", "CONDITIONAL", ["AUTHORIZATION"], 0, 1, False),
        ("COMMERCIAL_REGISTRATION", "Commercial Registration / Establishment Documents", "CONDITIONAL", ["COMMERCIAL_REGISTRATION"], 0, None, True),
        ("DXF_REPORT", "DXF Report", "OPTIONAL", ["DRAWING_SET"], 0, None, True),
        ("COORDINATE_REPORT", "Coordinate Report", "OPTIONAL", ["COORDINATE_REPORT"], 0, 1, False),
        ("GOVERNMENT_HOUSING", "Government Housing Documents", "OPTIONAL", ["OTHER"], 0, None, True),
        ("STATE_PROPERTY_ALLOCATION", "State Property Allocation Letter", "OPTIONAL", ["OTHER"], 0, 1, False),
        ("THIRD_PARTY_NOC", "Third-Party NOC", "CONDITIONAL", ["NOC"], 0, None, True),
        ("PLANNING_ZONING", "Planning / Zoning Conditions", "CONDITIONAL", ["NOC", "OTHER"], 0, None, True),
        ("SITE_INSPECTION", "Site Inspection", "OPTIONAL", ["OTHER"], 0, None, True),
        ("PRELIMINARY_ARCHITECTURAL_DRAWINGS", "Preliminary Architectural Drawings", "REQUIRED", ["DRAWING_SET"], 1, 1, False),
        ("CONCEPT_GUIDANCE_PLAN", "Concept / Guidance Plan", "OPTIONAL", ["DRAWING_SET", "OTHER"], 0, None, True),
        ("OTHER_APPROVALS", "Other Approvals", "OPTIONAL", ["OTHER", "NOC"], 0, None, True),
        ("PREVIOUS_APPROVALS", "Previous Approvals", "OPTIONAL", ["OTHER", "NOC"], 0, None, True),
        ("SERVICE_REQUIREMENTS_PRELIMINARY", "Service Requirements for Preliminary Approval", "OPTIONAL", ["OTHER"], 0, None, True),
    ]
    for order, (code, label, state, types, minimum, maximum, multiple) in enumerate(categories, 1):
        db.add(AttachmentCategoryRule(scenario_id=scenario.id, scenario_version=scenario.version, category_code=code, portal_label_en=label, portal_label_ar=None, portal_order=order, requirement_state=state, applicability_expression_json={}, allowed_document_types=types, min_files=minimum, max_files=maximum, multiple_files_allowed=multiple, allowed_languages=["AR", "EN", "AR/EN", "ANY"], required_language_combination=None, allowed_mime_types=["application/pdf", "text/plain"], allowed_extensions=[".pdf", ".txt"], max_file_size_bytes=20 * 1024 * 1024, revision_policy="CURRENT_APPROVED_ONLY", reuse_policy="REUSE_REQUIRES_EXPLICIT_RULE", replacement_policy="MANUAL_REPLACEMENT_REQUIRED", evidence_policy="PERSISTENCE_READ_REQUIRED", status="ACTIVE", rule_version="W9-CATEGORY-1.0"))
    db.flush()


def seed_week10(db, projects):
    """Seed the bounded Week 10 control catalogue and closure policies."""
    codes = {item.code: item for item in db.scalars(select(FindingCode)).all()}
    class_map = {
        "PROPERTY_IDENTITY_MISMATCH": ("DATA_INTEGRITY", "VERIFICATION_ERROR", "REQUIREMENT_STEWARD", ["DOCUMENT_EVIDENCE"]),
        "OWNER_AUTHORIZATION_MISSING": ("DOCUMENT_COMPLETENESS", "ATTACHMENT_MISSING", "REQUIREMENT_STEWARD", ["DOCUMENT_EVIDENCE"]),
        "DRAWING_REVISION_MISMATCH": ("DESIGN_COMPLIANCE", "DRAWING_REVISION_ERROR", "RESPONSIBLE_ENGINEER", ["DRAWING_REVISION", "ENGINEER_VERIFICATION"]),
        "ATTACHMENT_MISSING": ("DOCUMENT_COMPLETENESS", "ATTACHMENT_MISSING", "PERMIT_PREPARER", ["DOCUMENT_EVIDENCE"]),
        "ATTACHMENT_WRONG_CATEGORY": ("DOCUMENT_COMPLETENESS", "ATTACHMENT_WRONG_CATEGORY", "PERMIT_PREPARER", ["DOCUMENT_EVIDENCE"]),
        "PRECHECK_TECHNICAL_TODO": ("DATA_INTEGRITY", "AUTHORITY_CHANGE", "RESPONSIBLE_ENGINEER", ["AUTHORITY_RECHECK"]),
        "PRECHECK_DOCUMENT_TODO": ("DOCUMENT_COMPLETENESS", "AUTHORITY_CHANGE", "PERMIT_PREPARER", ["AUTHORITY_RECHECK", "DOCUMENT_EVIDENCE"]),
        "OFFICIAL_DRAWING_COMMENT": ("DESIGN_COMPLIANCE", "AUTHORITY_CHANGE", "RESPONSIBLE_ENGINEER", ["DRAWING_REVISION", "AUTHORITY_RESPONSE"]),
        "OFFICIAL_DOCUMENT_COMMENT": ("DOCUMENT_COMPLETENESS", "AUTHORITY_CHANGE", "REQUIREMENT_STEWARD", ["DOCUMENT_EVIDENCE", "AUTHORITY_RESPONSE"]),
        "OTHER_AUTHORITY_COMMENT": ("ADMINISTRATIVE", "AUTHORITY_CHANGE", "PROCESS_CHAMPION", ["AUTHORITY_RESPONSE"]),
    }
    for code, item in codes.items():
        finding_class, root_cause, verifier, evidence = class_map.get(code, ("DATA_INTEGRITY", "UNKNOWN_REVIEW_REQUIRED", item.required_owner_role, [item.closure_evidence_policy]))
        item.finding_class = finding_class
        item.typical_root_cause_category = root_cause
        item.closure_verifier_role = verifier
        item.closure_evidence_policy = evidence[0]
        item.allowed_dispositions = ["CORRECTED", "AUTHORITY_RECHECK_CLEAR"] + (["FORMALLY_DISPUTED"] if code == "OTHER_AUTHORITY_COMMENT" else [])
        item.resubmission_gate_effect = "ALLOWED_FORMAL_DISPUTE" if code == "OTHER_AUTHORITY_COMMENT" else "STILL_BLOCKS"
        item.precheck_gate_effect = "BLOCKS_PRECHECK" if item.source_classes_allowed and FindingSourceType.AUTHORITY_PRECHECK in item.source_classes_allowed else "NOT_APPLICABLE"
        item.recurrence_key_strategy = "CODE_OBJECT"
        if item.internal_preflight_control_code and FindingSourceType.INTERNAL_PREFLIGHT not in item.source_classes_allowed:
            item.source_classes_allowed = [*item.source_classes_allowed, FindingSourceType.INTERNAL_PREFLIGHT]
    if not db.scalar(select(ControlDefinition).limit(1)):
        controls = [
            ("CTRL_PROJECT_IDENTITY_MATCH", "Project identity agrees across verified source, drawing and package.", ["DRAWING.PROJECT_NUMBER"], "BLOCKING", True, "PROPERTY_IDENTITY_MISMATCH", "REQUIREMENT_STEWARD"),
            ("CTRL_PROPERTY_IDENTITY_MATCH", "Property/PIN/plot identity agrees across configured evidence.", ["PROPERTY.PIN", "PROPERTY.PLOT_NUMBER"], "BLOCKING", True, "PROPERTY_IDENTITY_MISMATCH", "REQUIREMENT_STEWARD"),
            ("CTRL_OWNER_REPRESENTATION_VALID", "Owner and representative authorization remain current and evidenced.", ["OWNER.NAME_EN", "REPRESENTATIVE.FLAG"], "BLOCKING", True, "OWNER_AUTHORIZATION_MISSING", "REQUIREMENT_STEWARD"),
            ("CTRL_REQUIRED_DOCUMENTS_CURRENT", "Required document and dependency validity is current.", [], "BLOCKING", True, "OWNER_AUTHORIZATION_MISSING", "REQUIREMENT_STEWARD"),
            ("CTRL_DRAWING_METADATA_MATCH", "Signed-scenario drawing metadata matches current canonical truth.", ["DRAWING.REVISION", "DRAWING.PROJECT_NUMBER"], "BLOCKING", True, "DRAWING_REVISION_MISMATCH", "RESPONSIBLE_ENGINEER"),
            ("CTRL_ATTACHMENT_MANIFEST_COMPLETE", "Locked attachment manifest is complete and persisted.", [], "BLOCKING", True, "ATTACHMENT_MISSING", "PERMIT_PREPARER"),
            ("CTRL_PORTAL_PERSISTENCE_MATCH", "Observed simulator state matches intended state.", [], "BLOCKING", True, "PORTAL_REQUIRED_FIELD_MISSING", "PERMIT_PREPARER"),
            ("CTRL_PRECHECK_CURRENT", "Current preparation revision has current precheck evidence.", [], "BLOCKING", True, "PRECHECK_TECHNICAL_TODO", "RESPONSIBLE_ENGINEER"),
            ("CTRL_PRIOR_BLOCKING_FINDINGS_CLOSED", "Applicable prior official blocking findings satisfy closure/dispute policy.", [], "BLOCKING", True, "OFFICIAL_DRAWING_COMMENT", "RESPONSIBLE_ENGINEER"),
        ]
        db.add_all([ControlDefinition(control_code=c, version="1.0", description=d, source_fields=f, severity=s, blocking=b, finding_code_on_fail=fc, verifier_role=vr, status="ACTIVE") for c,d,f,s,b,fc,vr in controls])
    # Week 10 closes the signed field matrix with explicit authority and
    # target rules for every supported field. These are synthetic baseline
    # rules, not client decisions or office-wide requirements.
    scenario = db.scalar(select(ScenarioConfig).where(ScenarioConfig.scenario_code == "DEMO_BUILDING_PERMIT_V1"))
    if scenario:
        matrix_requirements = [
            ("ATTACHMENT_MANIFEST_COMPLETE", "Signed attachment manifest is complete and current.", RequirementType.ATTACHMENT, False),
            ("PROFESSIONAL_CREDENTIAL_CURRENT", "Responsible Engineer credential is current.", RequirementType.HUMAN_DECISION, True),
            ("OFFICE_CREDENTIAL_CURRENT", "Consultancy office credential is current.", RequirementType.HUMAN_DECISION, True),
            ("FINAL_HUMAN_SUBMISSION", "Final submission is a named human decision and evidence event.", RequirementType.HUMAN_DECISION, True),
            ("PORTAL_DRAFT_PERSISTENCE", "Assisted municipality draft persists and reconciles.", RequirementType.PORTAL_SECTION, True),
            ("DRAWING_METADATA_CONTROLS", "Signed-scenario drawing metadata controls run deterministically.", RequirementType.FIELD, True),
        ]
        existing_requirement_codes = {x.requirement_code for x in db.scalars(select(RequirementConfig).where(RequirementConfig.scenario_id == scenario.id)).all()}
        db.add_all([RequirementConfig(scenario_id=scenario.id, requirement_code=code, description=description, requirement_type=kind, applicability_expression_json={"signed_scenario": True}, human_decision_required=human, blocking=True, effective_from=date(2026, 1, 1), status=ConfigStatus.PROVISIONAL) for code, description, kind, human in matrix_requirements if code not in existing_requirement_codes])
        for field in db.scalars(select(FieldDefinition).where(FieldDefinition.active.is_(True))).all():
            authority = db.scalar(select(FieldAuthorityRule).where(FieldAuthorityRule.scenario_id == scenario.id, FieldAuthorityRule.field_definition_id == field.id))
            if not authority:
                db.add(FieldAuthorityRule(scenario_id=scenario.id, field_definition_id=field.id, purpose="PERMIT_PREPARATION", primary_source_type="SYNTHETIC_CANONICAL", fallback_source_type=None, conflict_behavior="BLOCK_CRITICAL_CONFLICT", human_verifier_role=Role.RESPONSIBLE_ENGINEER.value if field.criticality == Criticality.CRITICAL else Role.REQUIREMENT_STEWARD.value, notes="Synthetic Week 10 signed-scenario matrix rule.", status=ConfigStatus.PROVISIONAL))
            for target, location in [(RenderingTarget.FORM, f"forms.{field.field_code}"), (RenderingTarget.EXCEL, f"projection.{field.field_code}"), (RenderingTarget.MUNICIPALITY, f"portal.{field.field_code}")]:
                if not db.scalar(select(TargetRenderingRule).where(TargetRenderingRule.scenario_id == scenario.id, TargetRenderingRule.field_definition_id == field.id, TargetRenderingRule.target_system == target, TargetRenderingRule.status == RenderingStatus.ACTIVE)):
                    db.add(TargetRenderingRule(scenario_id=scenario.id, field_definition_id=field.id, target_system=target, target_location=location, format_rule=field.normalization_rule, language_rule="EN/AR", unit_rule=field.unit, dropdown_code_map={}, null_behavior="PRESERVE_NULL", version="W10-1.0", status=RenderingStatus.ACTIVE))
    db.flush()


def seed_reconciliation(db, projects):
    """Seed only deterministic governance/configuration authority records."""
    fixture = db.scalar(select(SyntheticFixtureSet).where(SyntheticFixtureSet.fixture_set_id == CANONICAL_FIXTURE_ID))
    if fixture:
        fixture.source_manifest_path = "backend/app/fixtures/canonical.py"
        fixture.synthetic_only = True
        fixture.golden_path_authority = True
        fixture.status = FixtureStatus.ACTIVE_GOLDEN_PATH
    for legacy_id, canonical_id in LEGACY_FIXTURE_ALIASES.items():
        db.add(LegacyFixtureAlias(legacy_id=legacy_id, canonical_id=canonical_id, purpose="Historical compatibility/unit-test migration map", temporary=True, remove_by=date(2027, 1, 31), classification="LEGACY_UNIT_TEST_ONLY"))
    db.add_all([
        DeliveryAuthorityStatus(track="TRACK_A", status="ACTIVE_SYNTHETIC", basis_artifact="docs/reconciliation/build-authorization-boundary.md", basis_version="reconciliation-v1", evidence_reference="Synthetic repository evidence only"),
        DeliveryAuthorityStatus(track="TRACK_B", status="NOT_AUTHORIZED", basis_artifact="docs/week-3/stage2/stage2-baseline.json", basis_version="1.0", evidence_reference="Stage 2 DRAFT; no signed client authorization"),
        DeliveryAuthorityStatus(track="TRACK_C", status="NOT_AUTHORIZED", basis_artifact="docs/week-3/signoff-c-draft.md", basis_version="draft", evidence_reference="No G10/live authorization or production permissions"),
    ])
    for code in db.scalars(select(FindingCode)).all():
        code.checksum = stable_hash({"code": code.code, "version": code.version, "title_en": code.title_en, "title_ar": code.title_ar, "severity": code.default_severity, "blocking": code.blocking_default})
    ensure_configuration_bundle(db)
    db.flush()


def seed_week11(db, projects):
    """Seed one safe synthetic monitoring policy and versioned read contracts."""
    scenario = db.scalar(select(ScenarioConfig).where(ScenarioConfig.scenario_code == "DEMO_BUILDING_PERMIT_V1"))
    applications = list(db.scalars(select(PermitApplication).order_by(PermitApplication.external_request_number)).all())
    if not scenario or not applications:
        return
    adapter_id, adapter_version, contract_version = "mock-authority-read", "W11-1.0", "W11-READ-1.0"
    contract_payload = {
        "route": "/mock-authority/applications/{application_id}",
        "fields": ["external_request_number", "status", "repetition_count", "comments"],
        "status_semantics": ["DRAFT", "SUBMITTED", "UNDER_REVIEW", "RETURNED", "APPROVED"],
        "comment_structure": {"id": "optional", "text": "required", "language": "optional"},
        "identity": ["external_request_number", "project_number"],
    }
    expected = stable_hash(contract_payload)
    for operation in ["READ_CURRENT_STATE", "READ_STATUS", "READ_COMMENTS"]:
        db.add(PortalReadContract(adapter_id=adapter_id, adapter_version=adapter_version, contract_version=contract_version, operation=operation, expected_route_or_section=contract_payload["route"], expected_field_keys=contract_payload["fields"], expected_status_semantics=contract_payload["status_semantics"], expected_comment_structure=contract_payload["comment_structure"], expected_identity_assertions=contract_payload["identity"], expected_structural_fingerprint=expected, parser_version="W11-PARSER-1.0", status="ACTIVE"))
    db.flush()
    db.add(MonitoringPolicy(scenario_id=scenario.id, application_id=applications[1].id, environment="TEST", enabled=True, evidence_class="SYNTHETIC_MEASURED", operations_allowed=["READ_CURRENT_STATE", "READ_STATUS", "READ_COMMENTS"], cadence_mode="MANUAL_DUE_RUN", cadence_value=None, business_hours_policy=None, jitter_policy={"mode": "NONE", "reason": "Synthetic deterministic evidence"}, max_failures_before_pause=3, adapter_id=adapter_id, adapter_version=adapter_version, portal_contract_version=contract_version, fallback_mode="ASSISTED_MANUAL_CAPTURE", status="SYNTHETIC_ACTIVE"))


def seed_week12(db, projects):
    """Seed two owner variants inside the existing Building Permit envelope."""
    scenario = db.scalar(select(ScenarioConfig).where(ScenarioConfig.scenario_code == "DEMO_BUILDING_PERMIT_V1"))
    if not scenario:
        return
    variants = [
        ScenarioVariant(scenario_id=scenario.id, variant_code="INDIVIDUAL_OWNER", name="Individual owner", description="Base signed-scenario owner path.", applicability={"owner_type": "INDIVIDUAL", "representative": False}, canonical_fixture_project_id=projects[0].id, included=True, signed_scope_basis="Stage 1 Building Permit / Demo Municipality A / assisted simulator", rule_set_version="W10-1.0", field_set_version="W10-1.0", rendering_set_version="W10-1.0", attachment_rule_set_version="W9-1.0", grid_rule_set_version="W9-1.0", status="SUPPORTED"),
        ScenarioVariant(scenario_id=scenario.id, variant_code="COMPANY_OWNER", name="Company owner", description="Second in-envelope owner representation with company registration.", applicability={"owner_type": "COMPANY", "representative": True}, canonical_fixture_project_id=projects[1].id, included=True, signed_scope_basis="Stage 1 Building Permit / Demo Municipality A / assisted simulator", rule_set_version="W10-1.0", field_set_version="W10-1.0", rendering_set_version="W12-1.0", attachment_rule_set_version="W12-1.0", grid_rule_set_version="W12-1.0", status="SUPPORTED"),
    ]
    db.add_all(variants); db.flush()
    db.add(VariantCompatibilityResult(scenario_id=scenario.id, base_variant=variants[0].variant_code, second_variant=variants[1].variant_code, domain_schema_change_required=False, new_semantic_fields=["OWNER.CR_NUMBER"], new_rendering_rules=["OWNER.TYPE", "OWNER.CR_NUMBER"], new_requirement_rules=["COMPANY_CR"], new_attachment_rules=["COMMERCIAL_REGISTRATION"], new_grid_rules=[], new_human_decisions=["company registration applicability"], core_code_fork_required=False, result="CONFIGURATION_ONLY"))
    fields = [x.field_code for x in db.scalars(select(FieldDefinition).where(FieldDefinition.active.is_(True)).order_by(FieldDefinition.field_code)).all()]
    for variant in variants:
        for target in ["FORM", "EXCEL", "MUNICIPALITY_SCALAR", "MUNICIPALITY_DROPDOWN", "MUNICIPALITY_GRID_FIELD"]:
            mapped = fields
            db.add(TargetRenderingCoverage(scenario_id=scenario.id, variant_id=variant.id, target_type=target, supported_fields=fields, mapped_fields=mapped, missing_fields=[], blocked_external=[], not_applicable=[], coverage_percent=100))
    db.flush()


def seed_week13(db, projects):
    """Seed deterministic recurrence controls, role boundaries, and recovery scope."""
    scenario = db.scalar(select(ScenarioConfig).where(ScenarioConfig.scenario_code == "DEMO_BUILDING_PERMIT_V1"))
    if not scenario:
        return
    codes = db.scalars(select(FindingCode).where(FindingCode.status == FindingCodeStatus.ACTIVE)).all()
    for code in codes:
        db.add(FindingPreventionControl(finding_code_id=code.id, version="W13-1.0", control_code=f"PREVENT_{code.code}", description=f"Review evidence and current-state control for {code.code} before a gate.", evidence_requirement=code.closure_evidence_policy, owner_role=code.closure_verifier_role or code.required_owner_role, required_before_gate="RESUBMISSION_READY", status="ACTIVE"))
    roles = [
        (Role.PERMIT_PREPARER.value, ["prepare evidence and assisted draft", "cannot final-submit", "cannot close professional finding"], ["verified source and correction evidence"], ["wrong identity", "stale package", "portal drift"], "L1 then L2"),
        (Role.PROCESS_CHAMPION.value, ["triage and route", "monitor operations", "cannot make professional closure"], ["case correlation and routing evidence"], ["P1 integrity signal", "unresolved blocker"], "L2 / Responsible Engineer"),
        (Role.REQUIREMENT_STEWARD.value, ["review configuration and administrative evidence", "package approval within role"], ["applicability and approval evidence"], ["missing requirement evidence", "stale approval"], "Responsible Engineer where technical"),
        (Role.RESPONSIBLE_ENGINEER.value, ["technical review and professional decision"], ["technical correction and verification evidence"], ["wrong critical verified value", "drawing mismatch"], "P1 / Process Champion"),
        (Role.FINAL_SUBMITTER.value, ["independently review and human-submit"], ["current revision/package confirmation"], ["stale handoff", "MFA timeout"], "Process Champion"),
        (Role.SYSTEM_ADMIN.value, ["support/configuration/infrastructure handling"], ["audit and support correlation"], ["professional decision request"], "Responsible Engineer"),
    ]
    for role, boundaries, evidence, stops, escalation in roles:
        db.add(RoleTrainingChecklist(role=role, checklist_version="W13-1.0", boundaries=boundaries, evidence_requirements=evidence, stop_conditions=stops, escalation_route=escalation, evidence_class="SYNTHETIC_IMPLEMENTATION_EVIDENCE"))
    config_path = repo_root() / "config/recording_fidelity_requirements_v2_5.yaml"
    config_hash = hashlib.sha256(config_path.read_bytes()).hexdigest() if config_path.exists() else stable_hash({"config": "missing"})
    fixture = fixture_metadata()
    db.add(RecoveryManifest(environment="TEST", backup_set_id="W13-TEST-SYNTHETIC-001", database_backup_ref="synthetic://recovery/postgresql-test-backup", evidence_store_backup_ref="synthetic://recovery/artifacts", config_snapshot_ref="config/recording_fidelity_requirements_v2_5.yaml", schema_migration_head="0015_week14_acceptance", fixture_manifest_hash=fixture["fixture_manifest_hash"], config_manifest_hash=config_hash, encryption_handling_status="TEST_LOCAL_ARTIFACTS_NO_PRODUCTION_DATA", evidence_class="SYNTHETIC_IMPLEMENTATION_EVIDENCE"))
    db.add(KillSwitchReadiness(environment="TEST", mode="ASSISTED", write_kill_switch="NOT_APPLICABLE_CURRENT_MODE", tested=True, retained_capabilities=["verified_permit_record", "package_preparation", "assisted_entry", "finding_closure", "manual_status_capture"], disabled_capabilities=["machine_final_submit", "automated_external_write"], evidence_class="SYNTHETIC_IMPLEMENTATION_EVIDENCE", result_hash=stable_hash({"mode": "ASSISTED", "write_kill_switch": "NOT_APPLICABLE_CURRENT_MODE"})))
    db.flush()


def seed_week14(db, projects):
    """Seed an empty defect ledger and the two supported role-rehearsal variants."""
    if db.scalar(select(ShadowDefectDisposition).limit(1)):
        return
    for severity, defect_id, description in [("P1", "W14-P1-COUNT", "No open P1 integrity defects in the synthetic acceptance state."), ("P2", "W14-P2-COUNT", "No open P2 defects in the synthetic acceptance state.")]:
        db.add(ShadowDefectDisposition(defect_id=defect_id, severity=severity, description=description, affected_requirement="#20", scenario_variant="INDIVIDUAL_OWNER + COMPANY_OWNER", root_cause="NONE_OBSERVED", status="CLOSED", owner="synthetic-quality", fix="Regression baseline remains green.", test_reference="Week13-14 acceptance runner", acceptance_impact="NONE", g10_impact="NONE"))
    db.flush()


if __name__ == "__main__": seed()
