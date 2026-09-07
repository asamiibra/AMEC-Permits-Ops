import os
import re
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select, true
from sqlalchemy.orm import Session
from ..adapters.excel.adapter import MockExcelAdapter, WorkbookLockedError
from ..audit.service import audit
from ..config.settings import get_settings, repo_root
from ..db import get_db
from ..fixtures.canonical import *
from ..models import *
from ..schemas.week4_api import ExcelProjectionRequest, ProjectBootstrapCreate
from ..services.rendering import rendering_preview

router = APIRouter(prefix="/api/reconciliation")
settings = get_settings()


def correlation(request: Request) -> str:
    return getattr(request.state, "correlation_id", "missing-correlation-id")


def safe_row(item):
    return jsonable_encoder({column.name: getattr(item, column.name) for column in item.__table__.columns}) if item else None


def workbook_path() -> Path:
    return canonical_workbook_path()


def next_project_number(db: Session, year: int = 2026) -> str:
    used = []
    for value in db.scalars(select(Project.project_number)).all():
        match = re.fullmatch(r"GHCE-(\d{4})-(\d{4})", value)
        if match and int(match.group(1)) == year:
            used.append(int(match.group(2)))
    for value in db.scalars(select(ProjectNumberReservation.proposed_number)).all():
        match = re.fullmatch(r"GHCE-(\d{4})-(\d{4})", value)
        if match and int(match.group(1)) == year:
            used.append(int(match.group(2)))
    return f"GHCE-{year}-{(max(used, default=0) + 1):04d}"


def root_slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-")


@router.get("/fixture")
def canonical_fixture(db: Session = Depends(get_db)):
    fixture = db.scalar(select(SyntheticFixtureSet).where(SyntheticFixtureSet.fixture_set_id == CANONICAL_FIXTURE_ID))
    if not fixture:
        raise HTTPException(404, "Canonical fixture set is not seeded")
    active_count = db.scalar(select(func.count(SyntheticFixtureSet.id)).where(SyntheticFixtureSet.golden_path_authority == true()))
    return {**safe_row(fixture), **fixture_metadata(), "manifest": CANONICAL_FIXTURE_MANIFEST, "active_golden_path_authorities": active_count, "legacy_aliases": [safe_row(x) for x in db.scalars(select(LegacyFixtureAlias).order_by(LegacyFixtureAlias.legacy_id)).all()]}


@router.get("/governance")
def governance_status(db: Session = Depends(get_db)):
    statuses = [safe_row(item) for item in db.scalars(select(DeliveryAuthorityStatus).order_by(DeliveryAuthorityStatus.track)).all()]
    baseline = db.scalar(select(Stage2Baseline).order_by(Stage2Baseline.created_at.desc()))
    signoff = db.scalar(select(SignoffCProposal).order_by(SignoffCProposal.created_at.desc()))
    return {"environment_badge": "SYNTHETIC PROTOTYPE", "tracks": statuses, "stage2": {"status": baseline.status.value if baseline else "DRAFT", "version": baseline.version if baseline else "1.0", "checksum": baseline.checksum if baseline else None}, "signoff_c": {"status": signoff.status.value if signoff else "DRAFT"}, "real_data_approval": False, "production_g10": False, "labels": ["SYNTHETIC DEVELOPMENT / PROTOTYPE TRACK", "NOT CLIENT-APPROVED BUILD", "NOT PRODUCTION AUTHORIZATION"]}


@router.get("/configuration-bundle")
def configuration_bundle(db: Session = Depends(get_db)):
    bundle = db.scalar(select(ConfigurationBundle).where(ConfigurationBundle.status == "ACTIVE").order_by(ConfigurationBundle.effective_from.desc()))
    return {"bundle": safe_row(bundle), "artifacts": [safe_row(item) for item in db.scalars(select(ConfigurationArtifact).where(ConfigurationArtifact.status == "ACTIVE").order_by(ConfigurationArtifact.artifact_type)).all()], "fixture": fixture_metadata()}


@router.get("/excel-contract")
def excel_contract():
    adapter = MockExcelAdapter(str(workbook_path()))
    return {**adapter.contract(), **fixture_metadata()}


@router.post("/project-bootstrap")
def bootstrap_project(payload: ProjectBootstrapCreate, request: Request, db: Session = Depends(get_db)):
    fixture = db.scalar(select(SyntheticFixtureSet).where(SyntheticFixtureSet.status == FixtureStatus.ACTIVE_GOLDEN_PATH))
    if not fixture:
        raise HTTPException(409, "CANONICAL_FIXTURE_REQUIRED")
    project_number = payload.proposed_number or next_project_number(db)
    if not re.fullmatch(r"GHCE-\d{4}-\d{4}", project_number):
        raise HTTPException(422, "PROJECT_NUMBER_INVALID_FORMAT")
    existing_project = db.scalar(select(Project).where(Project.project_number == project_number))
    existing_reservation = db.scalar(select(ProjectNumberReservation).where(ProjectNumberReservation.proposed_number == project_number))
    initiation = ProjectInitiation(initiation_type=payload.initiation_type, initiation_reference=payload.initiation_reference, initiated_by=payload.initiated_by, status=InitiationStatus.RECEIVED, notes="Synthetic configured trigger; source rule remains a baseline assumption.")
    db.add(initiation); db.flush()
    if existing_project or existing_reservation:
        initiation.status = InitiationStatus.REJECTED
        audit(db, correlation_id=correlation(request), event_type="PROJECT_NUMBER_CONFLICT", entity_type="ProjectInitiation", entity_id=initiation.id, after={"proposed_number": project_number}, metadata=fixture_metadata())
        db.commit()
        raise HTTPException(409, "PROJECT_NUMBER_CONFLICT_EXPLICIT_RESOLUTION_REQUIRED")
    office = db.scalar(select(ConsultancyOffice).where(ConsultancyOffice.office_code == "QEC-DOHA"))
    project = Project(project_number=project_number, project_name=payload.project_name, office_id=office.id, workstream=payload.workstream, status="ACTIVE", municipality=payload.municipality, permit_type=payload.permit_type, assigned_engineer=payload.assigned_engineer)
    db.add(project); db.flush(); initiation.project_id = project.id; initiation.status = InitiationStatus.COMPLETED
    reservation = ProjectNumberReservation(proposed_number=project_number, status=ReservationStatus.CONFIRMED, source_authority="SYNTHETIC_CONFIGURED_SEQUENCE", initiation_id=initiation.id, project_id=project.id, confirmed_at=datetime.now(timezone.utc))
    db.add(reservation); db.flush()
    root_relative = f"2026/{project_number}_{root_slug(payload.project_name)}"
    root = repo_root() / settings.mock_systems_root / "synology" / root_relative if not Path(settings.mock_systems_root).is_absolute() else Path(settings.mock_systems_root) / "synology" / root_relative
    root.mkdir(parents=True, exist_ok=True)
    template_manifest = []
    for folder in CANONICAL_PROJECT_SUBFOLDERS:
        folder_path = root / folder; folder_path.mkdir(parents=True, exist_ok=True)
        template = folder_path / "TEMPLATE_APPLIED.txt"
        template.write_text("PERMITOPS SYNTHETIC TEMPLATE — NOT A CLIENT DOCUMENT\n", encoding="utf-8")
        template_manifest.append(f"{folder}/TEMPLATE_APPLIED.txt")
    bootstrap = SynologyProjectBootstrap(project_id=project.id, root_path=root_relative, subfolders_json=CANONICAL_PROJECT_SUBFOLDERS, template_applied=True, template_manifest_json=template_manifest, status="CREATED")
    db.add(bootstrap); db.flush()
    application = PermitApplication(project_id=project.id, authority="Permit Authority Simulator", municipality=payload.municipality, permit_type=payload.permit_type, external_request_number=f"REQ-BOOTSTRAP-{project_number}", application_status=ApplicationStatus.DRAFT, repetition_count=0)
    db.add(application); db.flush()
    adapter = MockExcelAdapter(str(workbook_path()))
    projection = adapter.write_system_projection(project_number, {"Canonical Plot Number": "PENDING", "Canonical PIN": "PENDING", "Rendering Version": "1.0", "Municipality Request": application.external_request_number, "Projection Status": "BOOTSTRAPPED"})
    excel_row = ExcelProjectRow(project_id=project.id, workbook_identity=CANONICAL_WORKBOOK, sheet_name=projection["sheet"], row_number=projection["row_number"], row_key=projection["row_key"], ownership_matrix_json={column: ExcelOwnership.PERMITOPS_OWNED.value for column in ["Canonical Plot Number", "Canonical PIN", "Rendering Version", "Municipality Request", "Projection Status"]}, projection_sheet=CANONICAL_PROJECTION_SHEET, human_cells_fingerprint="NO_HUMAN_CELLS_WRITTEN", read_policy="Human workbook sheets remain read-only", write_policy="System projection columns only", status="LINKED")
    db.add(excel_row); db.flush()
    links = [
        ExternalSystemLink(project_id=project.id, system_type=SystemType.SYNOLOGY, external_reference=root_relative, display_reference=root_relative, metadata_json={"synthetic": True, **fixture_metadata()}),
        ExternalSystemLink(project_id=project.id, system_type=SystemType.EXCEL, external_reference=f"{CANONICAL_PROJECTION_SHEET} / {project_number}", display_reference=f"{CANONICAL_WORKBOOK} / {CANONICAL_PROJECTION_SHEET} / {project_number}", metadata_json={"synthetic": True, **fixture_metadata()}),
        ExternalSystemLink(project_id=project.id, system_type=SystemType.MUNICIPALITY, external_reference=application.external_request_number, display_reference=f"Permit Authority Simulator / {application.external_request_number}", metadata_json={"synthetic": True, **fixture_metadata()}),
    ]
    db.add_all(links); db.flush()
    for event_type, entity_type, entity_id, after in [
        ("PROJECT_INITIATED", "ProjectInitiation", initiation.id, {"initiation_type": payload.initiation_type.value}),
        ("PROJECT_NUMBER_RESERVED", "ProjectNumberReservation", reservation.id, {"project_number": project_number}),
        ("PROJECT_CREATED", "Project", project.id, {"project_number": project_number}),
        ("SYNOLOGY_PROJECT_ROOT_CREATED", "SynologyProjectBootstrap", bootstrap.id, {"root_path": root_relative}),
        ("PROJECT_TEMPLATE_APPLIED", "SynologyProjectBootstrap", bootstrap.id, {"subfolders": CANONICAL_PROJECT_SUBFOLDERS}),
        ("EXCEL_PROJECT_ROW_LINKED", "ExcelProjectRow", excel_row.id, projection),
    ]:
        audit(db, correlation_id=correlation(request), event_type=event_type, entity_type=entity_type, entity_id=entity_id, after=after, metadata=fixture_metadata())
    audit(db, correlation_id=correlation(request), event_type="MUNICIPALITY_APPLICATION_LINKED", entity_type="PermitApplication", entity_id=application.id, after={"request_number": application.external_request_number}, metadata=fixture_metadata())
    db.commit(); db.refresh(project)
    return {"project": safe_row(project), "initiation": safe_row(initiation), "reservation": safe_row(reservation), "synology": safe_row(bootstrap), "excel": safe_row(excel_row), "application": safe_row(application), "fixture": fixture_metadata(), "audit": [event_type for event_type, *_ in [("PROJECT_INITIATED",), ("PROJECT_NUMBER_RESERVED",), ("PROJECT_CREATED",), ("SYNOLOGY_PROJECT_ROOT_CREATED",), ("PROJECT_TEMPLATE_APPLIED",), ("EXCEL_PROJECT_ROW_LINKED",), ("MUNICIPALITY_APPLICATION_LINKED",)]]}


@router.get("/projects/{project_id}")
def reconciliation_project(project_id: str, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project: raise HTTPException(404, "Project not found")
    application = db.scalar(select(PermitApplication).where(PermitApplication.project_id == project_id))
    return {"project": safe_row(project), "initiation": safe_row(db.scalar(select(ProjectInitiation).where(ProjectInitiation.project_id == project_id))), "reservation": safe_row(db.scalar(select(ProjectNumberReservation).where(ProjectNumberReservation.project_id == project_id))), "synology": safe_row(db.scalar(select(SynologyProjectBootstrap).where(SynologyProjectBootstrap.project_id == project_id))), "excel": safe_row(db.scalar(select(ExcelProjectRow).where(ExcelProjectRow.project_id == project_id))), "links": [safe_row(x) for x in db.scalars(select(ExternalSystemLink).where(ExternalSystemLink.project_id == project_id)).all()], "application": safe_row(application), "fixture": fixture_metadata()}


@router.get("/properties/{project_id}")
def property_parties(project_id: str, db: Session = Depends(get_db)):
    property_record = db.scalar(select(Property).where(Property.project_id == project_id))
    if not property_record: return {"property": None, "owners": [], "representations": [], "authorizations": []}
    ownerships = db.scalars(select(PropertyOwnership).where(PropertyOwnership.property_id == property_record.id)).all()
    party_ids = {o.party_id for o in ownerships}
    representations = db.scalars(select(Representation).where((Representation.principal_party_id.in_(party_ids)) | (Representation.representative_party_id.in_(party_ids)))).all()
    auth_ids = [x.authorization_id for x in representations if x.authorization_id]
    parties = {party.id: safe_row(party) for party in db.scalars(select(Party).where(Party.id.in_(party_ids | {x.representative_party_id for x in representations}))).all()}
    return {"property": safe_row(property_record), "owners": [{**safe_row(o), "party": parties.get(o.party_id)} for o in ownerships], "representations": [{**safe_row(r), "principal": parties.get(r.principal_party_id), "representative": parties.get(r.representative_party_id)} for r in representations], "authorizations": [safe_row(a) for a in db.scalars(select(Authorization).where(Authorization.id.in_(auth_ids))).all()], "source_evidence": {"document_version_id": property_record.source_document_version_id, "observation_id": property_record.source_observation_id, "assertion_id": property_record.source_assertion_id}, "fixture": fixture_metadata()}


@router.get("/rendering-preview")
def rendering_preview_endpoint(project_id: str, field_code: str, db: Session = Depends(get_db)):
    field = db.scalar(select(FieldDefinition).where(FieldDefinition.field_code == field_code))
    if not field: raise HTTPException(404, "Field definition not found")
    observation = db.scalar(select(FieldObservation).where(FieldObservation.project_id == project_id, FieldObservation.field_definition_id == field.id).order_by(FieldObservation.observed_at.desc()))
    assertion = db.scalar(select(VerifiedAssertion).where(VerifiedAssertion.project_id == project_id, VerifiedAssertion.field_definition_id == field.id, VerifiedAssertion.status == AssertionStatus.CURRENT).order_by(VerifiedAssertion.verified_at.desc()))
    if not assertion: raise HTTPException(409, "VERIFIED_CANONICAL_VALUE_REQUIRED")
    rules = db.scalars(select(TargetRenderingRule).where(TargetRenderingRule.field_definition_id == field.id, TargetRenderingRule.status == RenderingStatus.ACTIVE).order_by(TargetRenderingRule.target_system)).all()
    canonical = assertion.semantic_value_json.get("value")
    return {"raw_observation": safe_row(observation), "canonical_verified_value": {"value": canonical, "assertion_id": assertion.id, "target_neutral": True}, "target_renderings": rendering_preview(canonical, rules), "fixture": fixture_metadata()}


@router.post("/excel-projection/{project_id}")
def excel_projection(project_id: str, payload: ExcelProjectionRequest, request: Request, db: Session = Depends(get_db)):
    if os.getenv("VERCEL"):
        raise HTTPException(503, "EXCEL_PROJECTION_UNAVAILABLE_ON_SERVERLESS_RUNTIME")
    project = db.get(Project, project_id)
    if not project: raise HTTPException(404, "Project not found")
    try:
        result = MockExcelAdapter(str(workbook_path())).write_system_projection(project.project_number, {"Canonical Plot Number": payload.canonical_plot_number or "PENDING", "Canonical PIN": payload.canonical_pin or "PENDING", "Rendering Version": payload.rendering_version, "Municipality Request": payload.municipality_request or "PENDING", "Projection Status": "WRITTEN"})
    except WorkbookLockedError as error:
        audit(db, correlation_id=correlation(request), event_type="EXCEL_PROJECTION_BLOCKED_LOCK", entity_type="Project", entity_id=project_id, after={"reason": str(error)}, metadata=fixture_metadata()); db.commit()
        raise HTTPException(409, str(error))
    audit(db, correlation_id=correlation(request), event_type="EXCEL_SYSTEM_PROJECTION_WRITTEN", entity_type="Project", entity_id=project_id, after=result, metadata=fixture_metadata()); db.commit()
    return {**result, "fixture": fixture_metadata(), "human_owned_cells_changed": False}


@router.get("/golden-path")
def golden_path(db: Session = Depends(get_db)):
    project = db.scalar(select(Project).where(Project.project_number == CANONICAL_PROJECT_IDS[0]))
    if not project: raise HTTPException(404, "Canonical golden-path project not seeded")
    return {"fixture": fixture_metadata(), "project": reconciliation_project(project.id, db), "property_parties": property_parties(project.id, db), "rendering": rendering_preview_endpoint(project.id, "PROPERTY.PLOT_NUMBER", db), "audit_events": len(db.scalars(select(AuditEvent).where(AuditEvent.entity_id == project.id)).all())}
