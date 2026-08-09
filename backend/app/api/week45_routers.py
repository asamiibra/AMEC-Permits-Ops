"""Focused Week 4–5 package and assisted municipality APIs."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..db import get_db
from ..fixtures.canonical import CANONICAL_PROJECTION_SHEET, CANONICAL_WORKBOOK, fixture_metadata
from ..models import *
from ..services.rendering import render_target_value
from ..services.week45 import build_package, current_assertions, evaluate_readiness, latest_evaluation, revision_view, row, snapshot_for_revision, stable_hash
from ..services.week7 import ingest_precheck_findings
from ..services.week8 import ensure_project_lineage
from ..services.configuration_lineage import ensure_configuration_bundle
from ..adapters.excel.adapter import MockExcelAdapter, WorkbookLockedError
from ..config.settings import repo_root, get_settings

router = APIRouter(prefix="/api")
settings = get_settings()


def cid(request: Request) -> str:
    return getattr(request.state, "correlation_id", "missing-correlation-id")


def require_project(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


def revision_or_404(db: Session, revision_id: str) -> PreparationRevision:
    revision = db.get(PreparationRevision, revision_id)
    if not revision:
        raise HTTPException(404, "Preparation revision not found")
    return revision


def evaluation_payload(db: Session, evaluation: PackageReadinessEvaluation):
    return {"evaluation": row(evaluation), "items": [row(x) for x in db.scalars(select(ReadinessResultItem).where(ReadinessResultItem.evaluation_id == evaluation.id)).all()], "fixture": fixture_metadata()}


@router.get("/projects/{project_id}/requirements")
def requirements(project_id: str, db: Session = Depends(get_db)):
    require_project(db, project_id)
    scenario = db.scalar(select(ScenarioConfig).where(ScenarioConfig.scenario_code == "DEMO_BUILDING_PERMIT_V1"))
    return {"requirements": [row(x) for x in db.scalars(select(RequirementConfig).where(RequirementConfig.scenario_id == scenario.id)).all()], "minimum_package_definition": row(db.scalar(select(MinimumPackageDefinition).order_by(MinimumPackageDefinition.version.desc()))), "fixture": fixture_metadata()}


@router.get("/projects/{project_id}/dependencies")
def dependencies(project_id: str, db: Session = Depends(get_db)):
    require_project(db, project_id)
    return {"dependencies": [row(x) for x in db.scalars(select(ApprovalDependency).where(ApprovalDependency.project_id == project_id)).all()], "professional_credentials": [row(x) for x in db.scalars(select(ProfessionalCredential).where(ProfessionalCredential.project_id == project_id)).all()], "fixture": fixture_metadata()}


@router.post("/projects/{project_id}/readiness/evaluate")
def readiness_evaluate(project_id: str, request: Request, db: Session = Depends(get_db)):
    require_project(db, project_id)
    evaluation, _ = evaluate_readiness(db, project_id, actor="operator")
    db.commit()
    return evaluation_payload(db, evaluation)


@router.get("/projects/{project_id}/readiness")
def readiness(project_id: str, db: Session = Depends(get_db)):
    require_project(db, project_id)
    evaluation = latest_evaluation(db, project_id)
    if not evaluation:
        evaluation, _ = evaluate_readiness(db, project_id)
        db.commit()
    return evaluation_payload(db, evaluation)


@router.post("/projects/{project_id}/package")
def create_package(project_id: str, request: Request, db: Session = Depends(get_db)):
    require_project(db, project_id)
    try:
        package = build_package(db, project_id, created_by="synthetic-preparer")
    except ValueError as exc:
        db.rollback()
        raise HTTPException(409, str(exc))
    ensure_project_lineage(db, project_id, cid(request))
    db.commit(); db.refresh(package)
    return package_detail(package.id, db)


def package_detail(package_id: str, db: Session):
    package = db.get(Package, package_id)
    if not package:
        raise HTTPException(404, "Package not found")
    return {"package": row(package), "items": [row(x) for x in db.scalars(select(PackageItem).where(PackageItem.package_id == package_id).order_by(PackageItem.order)).all()], "manifest": row(db.scalar(select(AttachmentManifest).where(AttachmentManifest.package_id == package_id))), "forms": [row(x) for x in db.scalars(select(RenderedForm).where(RenderedForm.package_id == package_id)).all()], "approvals": [row(x) for x in db.scalars(select(Approval).where(Approval.entity_type == "Package", Approval.entity_id == package_id)).all()], "fixture": fixture_metadata()}


@router.get("/projects/{project_id}/package")
def get_package(project_id: str, db: Session = Depends(get_db)):
    require_project(db, project_id)
    package = db.scalar(select(Package).where(Package.project_id == project_id).order_by(Package.created_at.desc()))
    if not package:
        raise HTTPException(404, "Package not found")
    return package_detail(package.id, db)


@router.post("/packages/{package_id}/refresh")
def refresh_package(package_id: str, request: Request, db: Session = Depends(get_db)):
    package = db.get(Package, package_id)
    if not package: raise HTTPException(404, "Package not found")
    if package.status == "APPROVED": raise HTTPException(409, "APPROVED_PACKAGE_IS_IMMUTABLE")
    if package.status in {"STALE", "SUPERSEDED"}: raise HTTPException(409, "PACKAGE_STALE_REVALIDATION_REQUIRED")
    evaluation, _ = evaluate_readiness(db, package.project_id)
    if evaluation.overall_status == "BLOCKED": package.status = "DRAFT"
    db.commit()
    return {**package_detail(package_id, db), "readiness": evaluation_payload(db, evaluation)}


@router.post("/packages/{package_id}/approve")
def approve_package(package_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    package = db.get(Package, package_id)
    if not package: raise HTTPException(404, "Package not found")
    if package.status in {"STALE", "SUPERSEDED"}: raise HTTPException(409, "PACKAGE_STALE_REVALIDATION_REQUIRED")
    evaluation = latest_evaluation(db, package.project_id)
    package_approvals = db.scalars(select(Approval).where(Approval.entity_id == package_id, Approval.status == "APPROVED")).all()
    prior_approved = db.scalar(select(Package).where(Package.project_id == package.project_id, Package.id != package.id, Package.status == "APPROVED"))
    if prior_approved and not package_approvals:
        raise HTTPException(409, "PACKAGE_REAPPROVAL_REQUIRED")
    approvals = package_approvals or db.scalars(select(Approval).where(Approval.entity_id == package.project_id, Approval.status == "APPROVED")).all()
    if not evaluation or evaluation.overall_status == "BLOCKED": raise HTTPException(409, "PACKAGE_READINESS_BLOCKED")
    if not {a.approval_type for a in approvals}.issuperset({"DATA_VERIFICATION_COMPLETE", "TECHNICAL_REVIEW_COMPLETE"}): raise HTTPException(409, "INTERNAL_HUMAN_GATES_REQUIRED")
    package.status = "APPROVED"; package.approved_at = datetime.now(timezone.utc); package.approved_by = payload.get("approved_by", "synthetic-requirement-steward")
    audit(db, correlation_id=cid(request), event_type="PACKAGE_APPROVED", entity_type="Package", entity_id=package.id, after={"approved_by": package.approved_by, "manifest_hash": package.manifest_hash}, metadata=fixture_metadata())
    db.commit()
    return package_detail(package_id, db)


@router.get("/packages/{package_id}/manifest")
def package_manifest(package_id: str, db: Session = Depends(get_db)):
    package = db.get(Package, package_id)
    if not package: raise HTTPException(404, "Package not found")
    manifest = db.scalar(select(AttachmentManifest).where(AttachmentManifest.package_id == package_id))
    return {"package": row(package), "manifest": row(manifest), "items": manifest.items if manifest else [], "fixture": fixture_metadata()}


@router.get("/projects/{project_id}/forms")
def forms(project_id: str, db: Session = Depends(get_db)):
    require_project(db, project_id)
    templates = db.scalars(select(FormTemplate).order_by(FormTemplate.template_code)).all()
    return {"templates": [{**row(t), "versions": [row(v) for v in db.scalars(select(FormTemplateVersion).where(FormTemplateVersion.template_id == t.id)).all()]} for t in templates], "rendered": [row(x) for x in db.scalars(select(RenderedForm).where(RenderedForm.project_id == project_id)).all()], "fixture": fixture_metadata()}


@router.post("/projects/{project_id}/forms/{template_code}/render")
def render_form(project_id: str, template_code: str, request: Request, db: Session = Depends(get_db)):
    require_project(db, project_id)
    template = db.scalar(select(FormTemplate).where(FormTemplate.template_code == template_code))
    if not template: raise HTTPException(404, "Form template not found")
    version = db.scalar(select(FormTemplateVersion).where(FormTemplateVersion.template_id == template.id, FormTemplateVersion.status == "ACTIVE").order_by(FormTemplateVersion.version.desc()))
    assertions = current_assertions(db, project_id)
    owners = []
    property_record = db.scalar(select(Property).where(Property.project_id == project_id))
    if property_record:
        for ownership in db.scalars(select(PropertyOwnership).where(PropertyOwnership.property_id == property_record.id)).all():
            party = db.get(Party, ownership.party_id)
            owners.append({"party_id": party.id, "name_en": party.name_en, "name_ar": party.name_ar, "share": ownership.normalized_share})
    values = {"project_number": assertions.get("DRAWING.PROJECT_NUMBER").display_value if assertions.get("DRAWING.PROJECT_NUMBER") else None, "plot_number": assertions.get("PROPERTY.PLOT_NUMBER").display_value if assertions.get("PROPERTY.PLOT_NUMBER") else None, "owners": owners, "source_assertions": [x.id for x in assertions.values()]}
    truth_hash = stable_hash(values)
    output_hash = stable_hash({"template_version": version.version, "values": values})
    rendered = RenderedForm(project_id=project_id, template_version_id=version.id, configuration_bundle_id=ensure_configuration_bundle(db).id, rendering_rule_versions=[r.version for r in db.scalars(select(TargetRenderingRule).where(TargetRenderingRule.target_system == RenderingTarget.FORM, TargetRenderingRule.status == RenderingStatus.ACTIVE)).all()], input_truth_hash=truth_hash, output_file_hash=output_hash, rendered_values=values, review_state="PENDING_HUMAN_REVIEW")
    db.add(rendered); db.flush(); audit(db, correlation_id=cid(request), event_type="FORM_RENDERED", entity_type="RenderedForm", entity_id=rendered.id, after={"template_code": template_code, "output_file_hash": output_hash}, metadata=fixture_metadata()); db.commit()
    return {"rendered_form": row(rendered), "template": row(template), "template_version": row(version), "fixture": fixture_metadata()}


@router.get("/projects/{project_id}/excel-projections")
def excel_projections(project_id: str, db: Session = Depends(get_db)):
    require_project(db, project_id)
    return {"projections": [row(x) for x in db.scalars(select(ExcelProjection).where(ExcelProjection.project_id == project_id).order_by(ExcelProjection.id)).all()], "fixture": fixture_metadata()}


@router.post("/projects/{project_id}/excel-projections")
def create_excel_projection(project_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    project = require_project(db, project_id)
    projection = ExcelProjection(project_id=project_id, workbook_ref=payload.get("workbook_ref", CANONICAL_WORKBOOK), sheet=payload.get("sheet", CANONICAL_PROJECTION_SHEET), row_key=project.project_number, target_column=payload.get("target_column", "Canonical Plot Number"), ownership=payload.get("ownership", "PERMITOPS_OWNED"), rendered_value=payload.get("rendered_value"), source_verified_assertion_id=payload.get("source_verified_assertion_id"), rendering_rule_version=payload.get("rendering_rule_version", "1.0"), status="PENDING", configuration_bundle_id=ensure_configuration_bundle(db).id)
    db.add(projection); db.flush(); audit(db, correlation_id=cid(request), event_type="EXCEL_PROJECTION_CREATED", entity_type="ExcelProjection", entity_id=projection.id, after={"target_column": projection.target_column, "ownership": projection.ownership}, metadata=fixture_metadata()); db.commit()
    return row(projection)


@router.post("/excel-projections/{projection_id}/apply")
def apply_excel_projection(projection_id: str, request: Request, db: Session = Depends(get_db)):
    projection = db.get(ExcelProjection, projection_id)
    if not projection: raise HTTPException(404, "Excel projection not found")
    if projection.ownership != "PERMITOPS_OWNED":
        projection.status = "BLOCKED_OWNERSHIP"; audit(db, correlation_id=cid(request), event_type="EXCEL_PROJECTION_BLOCKED", entity_type="ExcelProjection", entity_id=projection.id, after={"reason": "HUMAN_OWNED_OR_NON_SYSTEM_REGION"}, metadata=fixture_metadata()); db.commit(); raise HTTPException(409, "EXCEL_PROJECTION_BLOCKED_OWNERSHIP")
    path = repo_root() / projection.workbook_ref
    if not path.exists(): raise HTTPException(404, "Workbook not found")
    try:
        result = MockExcelAdapter(str(path)).write_system_projection(projection.row_key, {projection.target_column: projection.rendered_value or "PENDING", "Projection Status": "WEEK45_WRITTEN"})
    except WorkbookLockedError:
        projection.status = "BLOCKED_LOCK"; db.commit(); raise HTTPException(409, "EXCEL_PROJECTION_BLOCKED_LOCK")
    projection.status = "VERIFIED"; audit(db, correlation_id=cid(request), event_type="EXCEL_PROJECTION_WRITTEN", entity_type="ExcelProjection", entity_id=projection.id, after=result, metadata=fixture_metadata()); audit(db, correlation_id=cid(request), event_type="EXCEL_PROJECTION_VERIFIED", entity_type="ExcelProjection", entity_id=projection.id, after={"human_owned_cells_changed": False}, metadata=fixture_metadata()); db.commit()
    return {"projection": row(projection), "write": result, "human_owned_cells_changed": False, "fixture": fixture_metadata()}


@router.get("/projects/{project_id}/drawing-controls")
def drawing_controls(project_id: str, db: Session = Depends(get_db)):
    require_project(db, project_id)
    from ..services.configuration import evaluate_drawing_controls
    return {"controls": evaluate_drawing_controls(db, project_id), "fixture": fixture_metadata()}


@router.get("/projects/{project_id}/approvals")
def approvals(project_id: str, db: Session = Depends(get_db)):
    require_project(db, project_id)
    return {"approvals": [row(x) for x in db.scalars(select(Approval).where(Approval.entity_id == project_id).order_by(Approval.decided_at)).all()], "fixture": fixture_metadata()}


@router.post("/projects/{project_id}/approvals")
def record_approval(project_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    require_project(db, project_id)
    approval_type = payload.get("approval_type")
    role = payload.get("role_at_decision", "REQUIREMENT_STEWARD")
    if approval_type == "TECHNICAL_REVIEW_COMPLETE" and role != "RESPONSIBLE_ENGINEER": raise HTTPException(403, "RESPONSIBLE_ENGINEER_REQUIRED")
    approval = Approval(approval_type=approval_type, entity_type=payload.get("entity_type", "Project"), entity_id=payload.get("entity_id", project_id), preparation_revision_id=payload.get("preparation_revision_id"), status=payload.get("status", "APPROVED"), decided_by=payload.get("decided_by", "synthetic-reviewer"), decided_at=datetime.now(timezone.utc), role_at_decision=role, reason=payload.get("reason"), evidence_refs=payload.get("evidence_refs", []))
    db.add(approval); db.flush(); audit(db, correlation_id=cid(request), event_type="APPROVAL_RECORDED", entity_type="Approval", entity_id=approval.id, after={"approval_type": approval.approval_type, "role": role}, metadata=fixture_metadata()); db.commit(); return row(approval)


@router.post("/projects/{project_id}/preparation-revisions")
def create_revision(project_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    project = require_project(db, project_id)
    package_id = payload.get("package_id")
    package = db.get(Package, package_id) if package_id else db.scalar(select(Package).where(Package.project_id == project_id, Package.status == "APPROVED").order_by(Package.created_at.desc()))
    if not package or package.status != "APPROVED": raise HTTPException(409, "APPROVED_PACKAGE_REQUIRED")
    application = db.get(PermitApplication, payload.get("application_id")) if payload.get("application_id") else db.scalar(select(PermitApplication).where(PermitApplication.project_id == project_id).order_by(PermitApplication.external_request_number))
    if not application: raise HTTPException(409, "MUNICIPALITY_APPLICATION_REQUIRED")
    sequence = (db.scalar(select(func.max(PreparationRevision.sequence)).where(PreparationRevision.project_id == project_id)) or 0) + 1
    revision = PreparationRevision(project_id=project_id, application_id=application.id, sequence=sequence, status="READY_FOR_ASSISTED_PREPARATION", scenario_version="DEMO_BUILDING_PERMIT_V1.0", field_authority_version="FIELD-AUTH-1.0", requirement_config_version=package.package_definition_version, rendering_config_version="RENDER-1.0", package_id=package.id, package_manifest_hash=package.manifest_hash, created_by=payload.get("created_by", "synthetic-preparer"), configuration_bundle_id=package.configuration_bundle_id)
    db.add(revision); db.flush(); package.preparation_revision_id = revision.id; snapshot = snapshot_for_revision(db, revision); session = AttendedSession(application_id=application.id, preparation_revision_id=revision.id, mfa_mode="USER_PLUS_OTP", attendance_required=True); db.add(session); db.flush(); audit(db, correlation_id=cid(request), event_type="PREPARATION_REVISION_CREATED", entity_type="PreparationRevision", entity_id=revision.id, after={"package_id": package.id, "snapshot_hash": snapshot.snapshot_hash}, metadata=fixture_metadata()); db.commit()
    ensure_project_lineage(db, project_id, cid(request)); db.commit()
    return revision_view(db, revision.id)


@router.get("/preparation-revisions/{revision_id}")
def get_revision(revision_id: str, db: Session = Depends(get_db)):
    return revision_view(db, revision_id)


@router.get("/preparation-revisions/{revision_id}/snapshot")
def get_snapshot(revision_id: str, db: Session = Depends(get_db)):
    revision_or_404(db, revision_id); snapshot = db.scalar(select(PreparationSnapshot).where(PreparationSnapshot.preparation_revision_id == revision_id)); return {"snapshot": row(snapshot), "fixture": fixture_metadata()}


@router.get("/preparation-revisions/{revision_id}/municipality/fields")
def municipality_fields(revision_id: str, db: Session = Depends(get_db)):
    revision = revision_or_404(db, revision_id); snapshot = db.scalar(select(PreparationSnapshot).where(PreparationSnapshot.preparation_revision_id == revision.id)); return {"fields": list(snapshot.verified_field_values.values()) if snapshot else [], "fixture": fixture_metadata()}


@router.get("/preparation-revisions/{revision_id}/municipality/grids")
def municipality_grids(revision_id: str, db: Session = Depends(get_db)):
    revision = revision_or_404(db, revision_id); return {"rows": [row(x) for x in db.scalars(select(PortalGridRowIntent).where(PortalGridRowIntent.preparation_revision_id == revision.id)).all()] or (row(db.scalar(select(PreparationSnapshot).where(PreparationSnapshot.preparation_revision_id == revision.id))) or {}).get("repeating_rows", []), "fixture": fixture_metadata()}


@router.get("/preparation-revisions/{revision_id}/municipality/attachments")
def municipality_attachments(revision_id: str, db: Session = Depends(get_db)):
    revision = revision_or_404(db, revision_id); snapshot = db.scalar(select(PreparationSnapshot).where(PreparationSnapshot.preparation_revision_id == revision.id)); return {"attachments": snapshot.attachment_manifest if snapshot else [], "fixture": fixture_metadata()}


@router.post("/preparation-revisions/{revision_id}/intended-state")
def intended_state(revision_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    revision = revision_or_404(db, revision_id); existing = db.scalar(select(PortalIntendedState).where(PortalIntendedState.preparation_revision_id == revision.id)); data = {"application_identity": payload.get("application_identity", {"application_id": revision.application_id}), "fields": payload.get("fields", {}), "repeating_rows": payload.get("repeating_rows", []), "attachments": payload.get("attachments", [])}; state = existing or PortalIntendedState(preparation_revision_id=revision.id, configuration_bundle_id=revision.configuration_bundle_id, **data); state.application_identity = data["application_identity"]; state.fields = data["fields"]; state.repeating_rows = data["repeating_rows"]; state.attachments = data["attachments"]; state.state_hash = stable_hash(data); db.add(state); db.flush(); audit(db, correlation_id=cid(request), event_type="PORTAL_INTENDED_STATE_CAPTURED", entity_type="PortalIntendedState", entity_id=state.id, after={"state_hash": state.state_hash, "configuration_bundle_id": state.configuration_bundle_id}, metadata=fixture_metadata()); db.commit(); return row(state)


@router.post("/preparation-revisions/{revision_id}/portal-snapshots")
def portal_snapshot(revision_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    revision = revision_or_404(db, revision_id); draft = db.scalar(select(MunicipalityDraft).where(MunicipalityDraft.application_id == revision.application_id)); state = draft.state_json if draft else {}; data = {"field_state": payload.get("field_state", state), "grid_state": payload.get("grid_state", state.get("buildings", [])), "attachment_state": payload.get("attachment_state", []), "validation_state": payload.get("validation_state", {}), "precheck_state": payload.get("precheck_state", {})}; snapshot = PortalSnapshot(application_id=revision.application_id, preparation_revision_id=revision.id, snapshot_type=payload.get("snapshot_type", "REOPENED"), capture_method=payload.get("capture_method", "SIMULATOR_READ"), **data, snapshot_hash=stable_hash(data)); db.add(snapshot); db.flush(); audit(db, correlation_id=cid(request), event_type="PORTAL_SNAPSHOT_CAPTURED", entity_type="PortalSnapshot", entity_id=snapshot.id, after={"snapshot_hash": snapshot.snapshot_hash, "snapshot_type": snapshot.snapshot_type}, metadata=fixture_metadata()); db.commit(); return row(snapshot)


@router.post("/preparation-revisions/{revision_id}/reconcile")
def reconcile(revision_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    revision = revision_or_404(db, revision_id); intended = db.scalar(select(PortalIntendedState).where(PortalIntendedState.preparation_revision_id == revision.id)); snapshot = db.get(PortalSnapshot, payload.get("portal_snapshot_id")) if payload.get("portal_snapshot_id") else db.scalar(select(PortalSnapshot).where(PortalSnapshot.preparation_revision_id == revision.id).order_by(PortalSnapshot.captured_at.desc()))
    if not intended or not snapshot: raise HTTPException(409, "INTENDED_STATE_AND_PORTAL_SNAPSHOT_REQUIRED")
    observed_fields = snapshot.field_state if isinstance(snapshot.field_state, dict) else {}; results = []
    for key, expected in intended.fields.items():
        expected_value = expected.get("rendered_value", expected.get("canonical_value", expected)) if isinstance(expected, dict) else expected
        observed = observed_fields.get(key, observed_fields.get(expected.get("portal_key") if isinstance(expected, dict) else key))
        status = "MATCH" if observed == expected_value else "MISMATCH"
        results.append(PortalReconciliationResult(preparation_revision_id=revision.id, identity_type="FIELD", identity_key=key, expected=expected_value, observed=observed, status=status, severity="BLOCKING" if status == "MISMATCH" else "NONE", evidence=[snapshot.id]))
    if intended.repeating_rows:
        status = "MATCH" if intended.repeating_rows == snapshot.grid_state else "MISMATCH"
        results.append(PortalReconciliationResult(preparation_revision_id=revision.id, identity_type="GRID", identity_key="repeating_rows", expected=intended.repeating_rows, observed=snapshot.grid_state, status=status, severity="BLOCKING" if status == "MISMATCH" else "NONE", evidence=[snapshot.id]))
    if intended.attachments:
        status = "MATCH" if intended.attachments == snapshot.attachment_state else "MISMATCH"
        results.append(PortalReconciliationResult(preparation_revision_id=revision.id, identity_type="ATTACHMENT", identity_key="attachment_manifest", expected=intended.attachments, observed=snapshot.attachment_state, status=status, severity="BLOCKING" if status == "MISMATCH" else "NONE", evidence=[snapshot.id]))
    db.add_all(results); db.flush(); mismatches = [x for x in results if x.status == "MISMATCH"]
    if mismatches:
        revision.status = "IN_PREPARATION"
        for result in mismatches: db.add(MunicipalityPreparationException(application_id=revision.application_id, preparation_revision_id=revision.id, exception_type="PORTAL_VALUE_MISMATCH" if result.identity_type == "FIELD" else f"{result.identity_type}_MISMATCH", severity="BLOCKING", expected=result.expected, observed=result.observed, evidence=[snapshot.id], owner="Permit Preparer", status="OPEN"))
    else: revision.status = "VERIFIED_DRAFT"
    audit(db, correlation_id=cid(request), event_type="PORTAL_RECONCILIATION_COMPLETED", entity_type="PreparationRevision", entity_id=revision.id, after={"status": revision.status, "mismatch_count": len(mismatches)}, metadata=fixture_metadata());
    if mismatches: audit(db, correlation_id=cid(request), event_type="PORTAL_MISMATCH_DETECTED", entity_type="PreparationRevision", entity_id=revision.id, after={"mismatch_count": len(mismatches)}, metadata=fixture_metadata())
    db.commit(); return {"revision": row(revision), "results": [row(x) for x in results], "fixture": fixture_metadata()}


@router.get("/preparation-revisions/{revision_id}/validation")
def revision_validation(revision_id: str, db: Session = Depends(get_db)):
    revision = revision_or_404(db, revision_id); draft = db.scalar(select(MunicipalityDraft).where(MunicipalityDraft.application_id == revision.application_id)); state = draft.state_json if draft else {}; errors = []
    if not state.get("owner_name"): errors.append({"code": "REQUIRED_OWNER", "message": "Owner field is required."})
    if state.get("plot_number") and not str(state["plot_number"]).startswith("0"): errors.append({"code": "INVALID_IDENTIFIER", "message": "Synthetic plot identifier format is invalid."})
    refs = [r.get("building_ref") for r in state.get("buildings", [])];
    if len(refs) != len(set(refs)): errors.append({"code": "DUPLICATE_GRID_ROW", "message": "Building row identity must be unique."})
    return {"status": "FINDINGS" if errors else "CLEAR", "errors": errors, "revision_id": revision.id, "synthetic": True, "fixture": fixture_metadata()}


@router.post("/preparation-revisions/{revision_id}/human-portal-verifications")
def human_verification(revision_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    revision = revision_or_404(db, revision_id)
    if not payload.get("evidence_artifact_id") or payload.get("result") != "VERIFIED": raise HTTPException(422, "EVIDENCE_BACKED_VERIFICATION_REQUIRED")
    verification = HumanPortalVerification(application_id=revision.application_id, preparation_revision_id=revision.id, verifier=payload.get("verifier", "synthetic-preparer"), verifier_role=payload.get("verifier_role", "PERMIT_PREPARER"), verification_scope=payload.get("verification_scope", ["FIELDS", "GRIDS", "ATTACHMENTS"]), evidence_artifact_id=payload["evidence_artifact_id"], result="VERIFIED")
    revision.status = "VERIFIED_DRAFT"; db.add(verification); db.flush(); audit(db, correlation_id=cid(request), event_type="HUMAN_PORTAL_VERIFICATION_RECORDED", entity_type="HumanPortalVerification", entity_id=verification.id, after={"evidence_artifact_id": verification.evidence_artifact_id}, metadata=fixture_metadata()); db.commit(); return {"verification": row(verification), "revision": row(revision), "fixture": fixture_metadata()}


@router.get("/preparation-revisions/{revision_id}/precheck")
def precheck(revision_id: str, db: Session = Depends(get_db)):
    revision_or_404(db, revision_id); run = db.scalar(select(AuthorityPrecheckRun).where(AuthorityPrecheckRun.preparation_revision_id == revision_id).order_by(AuthorityPrecheckRun.run_at.desc())); return {"run": row(run), "items": [row(x) for x in db.scalars(select(AuthorityPrecheckItem).where(AuthorityPrecheckItem.precheck_run_id == run.id)).all()] if run else [], "fixture": fixture_metadata()}


@router.post("/preparation-revisions/{revision_id}/precheck/capture")
def capture_precheck(revision_id: str, request: Request, db: Session = Depends(get_db)):
    revision = revision_or_404(db, revision_id); app = db.get(PermitApplication, revision.application_id); findings = [] if app and app.application_status != ApplicationStatus.RETURNED else [{"code": "SYN-DRAWING-001", "message": "Synthetic drawing revision requires review."}]; payload = {"status": "FINDINGS" if findings else "CLEAR", "items": findings}; run = AuthorityPrecheckRun(application_id=revision.application_id, preparation_revision_id=revision.id, run_reference=f"PRECHECK-{revision.id[:8]}", source="AUTHORITY_PRECHECK", status=payload["status"], raw_evidence_artifact_id=f"synthetic://precheck/{revision.id}", result_hash=stable_hash(payload), configuration_bundle_id=revision.configuration_bundle_id); db.add(run); db.flush(); db.add_all([AuthorityPrecheckItem(precheck_run_id=run.id, source_type="AUTHORITY_PRECHECK", code=item["code"], message=item["message"], severity="BLOCKING", status="OPEN") for item in findings]); db.flush(); generated = ingest_precheck_findings(db, run, correlation_id=cid(request)) if findings else []; ensure_project_lineage(db, revision.project_id, cid(request)); audit(db, correlation_id=cid(request), event_type="PRECHECK_RUN_CAPTURED", entity_type="AuthorityPrecheckRun", entity_id=run.id, after={"status": run.status, "revision_id": revision.id, "findings_created": len(generated), "configuration_bundle_id": run.configuration_bundle_id}, metadata=fixture_metadata()); db.commit(); return precheck(revision_id, db)


@router.post("/preparation-revisions/{revision_id}/session/attendance")
def session_attendance(revision_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    revision = revision_or_404(db, revision_id); session = db.scalar(select(AttendedSession).where(AttendedSession.preparation_revision_id == revision.id).order_by(AttendedSession.session_started.desc()))
    if not session: session = AttendedSession(application_id=revision.application_id, preparation_revision_id=revision.id, mfa_mode="USER_PLUS_OTP", attendance_required=True); db.add(session)
    session.human_attendance_confirmed = bool(payload.get("human_attendance_confirmed", True)); session.session_established = session.human_attendance_confirmed and not session.session_expired; db.flush(); audit(db, correlation_id=cid(request), event_type="MFA_ATTENDANCE_CONFIRMED" if session.human_attendance_confirmed else "MFA_ATTENDANCE_REQUIRED", entity_type="AttendedSession", entity_id=session.id, after={"session_established": session.session_established, "otp_stored": False}, metadata=fixture_metadata()); db.commit(); return row(session)


@router.post("/preparation-revisions/{revision_id}/handoff")
def handoff(revision_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    revision = revision_or_404(db, revision_id); package = db.get(Package, revision.package_id) if revision.package_id else None
    if revision.status != "VERIFIED_DRAFT": raise HTTPException(409, "VERIFIED_DRAFT_REQUIRED_FOR_HANDOFF")
    submitter = db.get(User, payload.get("final_submitter_user_id")) if payload.get("final_submitter_user_id") else db.scalar(select(User).where(User.role == Role.FINAL_SUBMITTER))
    if not submitter or submitter.role != Role.FINAL_SUBMITTER: raise HTTPException(422, "FINAL_SUBMITTER_REQUIRED")
    snapshot = db.scalar(select(PortalSnapshot).where(PortalSnapshot.preparation_revision_id == revision.id).order_by(PortalSnapshot.captured_at.desc()))
    item = SubmissionHandoff(application_id=revision.application_id, preparation_revision_id=revision.id, package_id=package.id, portal_snapshot_id=snapshot.id if snapshot else None, handoff_status="READY_FOR_FINAL_HUMAN_REVIEW", final_submitter_user_id=submitter.id, prepared_by=revision.created_by, readiness_summary={"revision_status": revision.status, "human_submission_required": True}, unresolved_nonblocking_items=[], evidence_refs=[snapshot.id] if snapshot else [])
    db.add(item); db.flush(); audit(db, correlation_id=cid(request), event_type="SUBMISSION_HANDOFF_CREATED", entity_type="SubmissionHandoff", entity_id=item.id, after={"final_submitter_user_id": submitter.id, "human_submission_required": True}, metadata=fixture_metadata()); db.commit(); return {"handoff": row(item), "statement": "HUMAN SUBMISSION REQUIRED", "machine_submit_operation": False, "fixture": fixture_metadata()}


@router.get("/preparation-revisions/{revision_id}/handoff")
def get_handoff(revision_id: str, db: Session = Depends(get_db)):
    revision_or_404(db, revision_id); item = db.scalar(select(SubmissionHandoff).where(SubmissionHandoff.preparation_revision_id == revision_id).order_by(SubmissionHandoff.prepared_at.desc())); return {"handoff": row(item), "machine_submit_operation": False, "fixture": fixture_metadata()}


@router.post("/preparation-revisions/{revision_id}/submission-confirmation")
def preparation_confirmation(revision_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    revision = revision_or_404(db, revision_id)
    if not payload.get("evidence_artifact_id") or payload.get("method") not in {"MACHINE_READ", "HUMAN_EVIDENCE"}: raise HTTPException(422, "SUBMISSION_EVIDENCE_REQUIRED")
    confirmation = SubmissionConfirmation(application_id=revision.application_id, mode=payload["method"], request_reference=payload.get("submission_reference", f"SYNTHETIC-{revision.application_id[:8]}"), visible_status=payload.get("observed_status", "SUBMITTED"), evidence_reference=payload["evidence_artifact_id"], second_verifier=payload.get("independent_verifier"), notes="No machine submit operation.", preparation_revision_id=revision.id, application_identity_json=payload.get("application_identity", {"application_id": revision.application_id}), confirmed_by=payload.get("confirmed_by", "synthetic-final-submitter"), status="SUBMITTED_CONFIRMED")
    db.add(confirmation); db.flush(); audit(db, correlation_id=cid(request), event_type="SUBMISSION_CONFIRMATION_RECORDED", entity_type="SubmissionConfirmation", entity_id=confirmation.id, after={"method": confirmation.mode, "evidence": confirmation.evidence_reference, "machine_submit_operation": False}, metadata=fixture_metadata()); db.commit(); return {"confirmation": row(confirmation), "machine_submit_operation": False, "fixture": fixture_metadata()}


@router.get("/preparation-revisions/{revision_id}/exceptions")
def preparation_exceptions(revision_id: str, db: Session = Depends(get_db)):
    revision_or_404(db, revision_id); return {"exceptions": [row(x) for x in db.scalars(select(MunicipalityPreparationException).where(MunicipalityPreparationException.preparation_revision_id == revision_id).order_by(MunicipalityPreparationException.id)).all()], "fixture": fixture_metadata()}
