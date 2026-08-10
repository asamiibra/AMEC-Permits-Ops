from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import *
from ..schemas.week2_api import *
from ..audit.service import audit
from ..services.week2_workflows import register_version, classify_version, extract_version, verify_observation, compare_project_conflicts
from ..services.configuration import scenario, evaluate_requirements, evaluate_drawing_controls
from ..services.spike import run_spike
from ..services.week8 import ensure_project_lineage, record_material_change

router = APIRouter(prefix="/api")
mock_router = APIRouter(prefix="/mock-authority")


def cid(request: Request) -> str: return getattr(request.state, "correlation_id", "missing-correlation-id")
def model_dict(item):
    return {c.name: (getattr(item, c.name).value if hasattr(getattr(item, c.name), "value") else getattr(item, c.name)) for c in item.__table__.columns}


@router.get("/projects/{project_id}/documents")
def project_documents(project_id: str, db: Session = Depends(get_db)):
    # Keep deterministic semantic sources ahead of generic OTHER records so
    # callers never accidentally select a non-extractable placeholder merely
    # because a later user-uploaded filename sorts first.
    return [{**model_dict(d), "current_version": model_dict(db.get(DocumentVersion, d.current_version_id)) if d.current_version_id else None} for d in db.scalars(select(Document).where(Document.project_id == project_id).order_by(Document.document_type, Document.logical_name)).all()]


@router.post("/projects/{project_id}/documents")
def create_document(project_id: str, payload: DocumentCreate, request: Request, db: Session = Depends(get_db)):
    version = register_version(db, project_id=project_id, document_type=payload.document_type, logical_name=payload.logical_name, language=payload.language, source_system=payload.source_system, source_filename=payload.source_filename, source_path=payload.source_path_or_reference, content=payload.content, metadata=payload.metadata_json, correlation_id=cid(request))
    db.commit(); db.refresh(version)
    return {"document": model_dict(version.document), "version": model_dict(version)}


@router.get("/documents/{document_id}")
def document_detail(document_id: str, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document: raise HTTPException(404, "Document not found")
    return {**model_dict(document), "versions": [model_dict(v) for v in document.versions]}


@router.get("/documents/{document_id}/versions")
def document_versions(document_id: str, db: Session = Depends(get_db)): return [model_dict(v) for v in db.scalars(select(DocumentVersion).where(DocumentVersion.document_id == document_id).order_by(DocumentVersion.version_number)).all()]


@router.post("/documents/{document_id}/versions")
def create_document_version(document_id: str, payload: VersionCreate, request: Request, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document: raise HTTPException(404, "Document not found")
    previous = db.get(DocumentVersion, document.current_version_id) if document.current_version_id else None
    version = register_version(db, project_id=document.project_id, document_type=document.document_type.value, logical_name=document.logical_name, language=payload.language, source_system=payload.source_system, source_filename=payload.source_filename, source_path=payload.source_path_or_reference, content=payload.content, metadata=payload.metadata_json, correlation_id=cid(request))
    if previous and version.id != previous.id:
        ensure_project_lineage(db, document.project_id, cid(request))
        record_material_change(db, project_id=document.project_id, source_type="DocumentVersion", source_id=previous.id, previous_version_or_hash=previous.sha256, new_version_or_hash=version.sha256, change_type="DOCUMENT_NEW_VERSION", material=payload.metadata_json.get("semantic_change", True), actor_or_system="document-ingestion", correlation_id=cid(request), metadata={"new_document_version_id": version.id, **payload.metadata_json})
    db.commit(); return model_dict(version)


@router.get("/document-versions/{version_id}/classification")
def version_classification(version_id: str, db: Session = Depends(get_db)):
    item = db.scalar(select(DocumentClassification).where(DocumentClassification.document_version_id == version_id).order_by(DocumentClassification.created_at.desc()))
    return model_dict(item) if item else {"status": "NOT_CLASSIFIED"}


@router.post("/document-versions/{version_id}/classify")
def classify(version_id: str, request: Request, payload: ClassifyPayload | None = None, db: Session = Depends(get_db)):
    version = db.get(DocumentVersion, version_id)
    if not version: raise HTTPException(404, "Document version not found")
    item = classify_version(db, version, cid(request)); payload = payload or ClassifyPayload()
    before = model_dict(item)
    if payload.final_type: item.final_type = payload.final_type
    if payload.review_status: item.review_status = ClassificationReviewStatus(payload.review_status)
    if payload.final_type or payload.review_status:
        event_type = "DOCUMENT_CLASSIFICATION_CORRECTED" if payload.final_type and payload.final_type != item.predicted_type else "DOCUMENT_CLASSIFICATION_CONFIRMED"
        audit(db, correlation_id=cid(request), event_type=event_type, entity_type="DocumentClassification", entity_id=item.id, before=before, after=model_dict(item))
    db.commit(); return model_dict(item)


@router.patch("/document-versions/{version_id}/approval-state")
def approval_state(version_id: str, payload: ApprovalPatch, request: Request, db: Session = Depends(get_db)):
    version = db.get(DocumentVersion, version_id)
    if not version: raise HTTPException(404, "Document version not found")
    before = model_dict(version)
    version.approval_state = payload.approval_state
    db.flush()
    audit(db, correlation_id=cid(request), event_type="DOCUMENT_APPROVAL_STATE_CHANGED", entity_type="DocumentVersion", entity_id=version.id, actor_id=payload.actor_id, before=before, after=model_dict(version))
    db.commit(); return model_dict(version)


@router.get("/document-versions/{version_id}/observations")
def version_observations(version_id: str, db: Session = Depends(get_db)):
    return [{**model_dict(o), "field_code": db.get(FieldDefinition, o.field_definition_id).field_code} for o in db.scalars(select(FieldObservation).where(FieldObservation.document_version_id == version_id)).all()]


@router.post("/document-versions/{version_id}/extract")
def extract(version_id: str, request: Request, db: Session = Depends(get_db)):
    version = db.get(DocumentVersion, version_id)
    if not version: raise HTTPException(404, "Document version not found")
    items = extract_version(db, version, cid(request)); db.commit()
    return [{**model_dict(o), "field_code": db.get(FieldDefinition, o.field_definition_id).field_code} for o in items]


@router.post("/observations/{observation_id}/verify")
def verify(observation_id: str, payload: VerifyPayload, request: Request, db: Session = Depends(get_db)):
    observation = db.get(FieldObservation, observation_id)
    if not observation: raise HTTPException(404, "Observation not found")
    old = db.scalar(select(VerifiedAssertion).where(VerifiedAssertion.project_id == observation.project_id, VerifiedAssertion.field_definition_id == observation.field_definition_id, VerifiedAssertion.status == AssertionStatus.CURRENT))
    old_value = old.semantic_value_json if old else None
    assertion = verify_observation(db, observation, actor_id=payload.actor_id, method=payload.method, correction=payload.corrected_value, correlation_id=cid(request))
    ensure_project_lineage(db, observation.project_id, cid(request))
    source_id = old.id if old else assertion.id
    if old_value != assertion.semantic_value_json:
        audit(db, correlation_id=cid(request), event_type="VERIFIED_ASSERTION_SUPERSEDED", entity_type="VerifiedAssertion", entity_id=old.id if old else assertion.id, after={"replacement_assertion_id": assertion.id}, metadata={"correlation_id": cid(request)})
        record_material_change(db, project_id=observation.project_id, source_type="VerifiedAssertion", source_id=source_id, previous_version_or_hash=old.id if old else None, new_version_or_hash=assertion.id, change_type="VERIFIED_ASSERTION_CHANGED", material=True, actor_or_system=payload.actor_id, correlation_id=cid(request), metadata={"new_assertion_id": assertion.id, "old_assertion_id": old.id if old else None})
    db.commit(); return model_dict(assertion)


@router.post("/observations/{observation_id}/reject")
def reject(observation_id: str, request: Request, db: Session = Depends(get_db)):
    observation = db.get(FieldObservation, observation_id)
    if not observation: raise HTTPException(404, "Observation not found")
    audit(db, correlation_id=cid(request), event_type="FIELD_OBSERVATION_REJECTED", entity_type="FieldObservation", entity_id=observation.id, after={"rejected": True}); db.commit(); return {"status":"REJECTED","observation_id":observation.id}


@router.post("/observations/{observation_id}/flag-ambiguous")
def flag_ambiguous(observation_id: str, request: Request, db: Session = Depends(get_db)):
    observation = db.get(FieldObservation, observation_id)
    if not observation: raise HTTPException(404, "Observation not found")
    audit(db, correlation_id=cid(request), event_type="FIELD_OBSERVATION_AMBIGUOUS", entity_type="FieldObservation", entity_id=observation.id, after={"ambiguous": True}); db.commit(); return {"status":"AMBIGUOUS","observation_id":observation.id}


@router.post("/projects/{project_id}/manual-observations")
def manual_observation(project_id: str, payload: ManualObservationCreate, request: Request, db: Session = Depends(get_db)):
    version = db.get(DocumentVersion, payload.document_version_id); field = db.scalar(select(FieldDefinition).where(FieldDefinition.field_code == payload.field_code))
    if not version or not field: raise HTTPException(404, "Document version or field definition not found")
    from ..services.normalization import normalize_candidate
    observation = FieldObservation(project_id=project_id, field_definition_id=field.id, document_version_id=version.id, raw_value=payload.raw_value, normalized_candidate_value=normalize_candidate(payload.raw_value, field.normalization_rule), structured_value_json={"value":payload.raw_value}, page_number=payload.page_number, bounding_box_json=payload.bounding_box_json, source_region_text=payload.source_region_text, extraction_method=ExtractionMethod.MANUAL_KEYED, extractor_version="VERIFICATION-CONSOLE-1.0", confidence=1.0, correlation_id=cid(request)); db.add(observation); db.flush(); audit(db, correlation_id=cid(request), event_type="FIELD_MANUALLY_KEYED", entity_type="FieldObservation", entity_id=observation.id, after={"field_code":field.field_code,"page":payload.page_number}); db.commit(); return {**model_dict(observation), "field_code":field.field_code}


@router.get("/projects/{project_id}/verified-assertions")
def assertions(project_id: str, db: Session = Depends(get_db)):
    return [{**model_dict(a), "field_code": db.get(FieldDefinition, a.field_definition_id).field_code} for a in db.scalars(select(VerifiedAssertion).where(VerifiedAssertion.project_id == project_id).order_by(VerifiedAssertion.created_at.desc())).all()]


@router.get("/projects/{project_id}/conflicts")
def conflicts(project_id: str, request: Request, db: Session = Depends(get_db)):
    if not db.scalars(select(Conflict).where(Conflict.project_id == project_id)).first(): compare_project_conflicts(db, project_id, cid(request)); db.commit()
    return [{**model_dict(c), "field_code": db.get(FieldDefinition, c.field_definition_id).field_code} for c in db.scalars(select(Conflict).where(Conflict.project_id == project_id).order_by(Conflict.severity)).all()]


@router.post("/conflicts/{conflict_id}/resolve")
def resolve_conflict(conflict_id: str, payload: ConflictResolvePayload, request: Request, db: Session = Depends(get_db)):
    conflict = db.get(Conflict, conflict_id)
    if not conflict: raise HTTPException(404, "Conflict not found")
    before = model_dict(conflict); conflict.status = ConflictStatus(payload.status); conflict.resolution = payload.resolution; conflict.resolver = payload.resolver; conflict.resolved_at = datetime.now(timezone.utc); db.flush(); audit(db, correlation_id=cid(request), event_type="CONFLICT_RESOLVED", entity_type="Conflict", entity_id=conflict.id, before=before, after=model_dict(conflict)); db.commit(); return model_dict(conflict)


def config_rows(db, model): return [model_dict(x) for x in db.scalars(select(model)).all()]
@router.get("/config/scenarios/{scenario_code}/fields")
def config_fields(scenario_code: str, db: Session = Depends(get_db)): return {"scenario": scenario_code, "fields": [{**model_dict(f), "authority_rules":[model_dict(r) for r in db.scalars(select(FieldAuthorityRule).where(FieldAuthorityRule.field_definition_id == f.id)).all()]} for f in db.scalars(select(FieldDefinition).where(FieldDefinition.active == True).order_by(FieldDefinition.field_code)).all()]}
@router.get("/config/scenarios/{scenario_code}/documents")
def config_documents(scenario_code: str, db: Session = Depends(get_db)): return {"scenario": scenario_code, "documents": config_rows(db, AttachmentCategoryConfig)}
@router.get("/config/scenarios/{scenario_code}/requirements")
def config_requirements(scenario_code: str, db: Session = Depends(get_db)): return {"scenario": scenario_code, "requirements": config_rows(db, RequirementConfig)}
@router.get("/config/scenarios/{scenario_code}/attachments")
def config_attachments(scenario_code: str, db: Session = Depends(get_db)): return {"scenario": scenario_code, "attachments": config_rows(db, AttachmentCategoryConfig)}
@router.get("/config/scenarios/{scenario_code}/drawing-controls")
def config_drawing(scenario_code: str, db: Session = Depends(get_db)): return {"scenario": scenario_code, "controls": config_rows(db, DrawingMetadataControl)}
@router.get("/config/scenarios/{scenario_code}/municipality")
def config_municipality(scenario_code: str, db: Session = Depends(get_db)):
    cfg = db.scalar(select(MunicipalityConfig).join(ScenarioConfig).where(ScenarioConfig.scenario_code == scenario_code));
    if not cfg: raise HTTPException(404, "Municipality configuration not found")
    return model_dict(cfg)
@router.get("/config/scenarios/{scenario_code}/requirements/evaluate/{project_id}")
def config_evaluate_requirements(scenario_code: str, project_id: str, db: Session = Depends(get_db)): return evaluate_requirements(db, project_id)
@router.get("/config/scenarios/{scenario_code}/drawing-controls/evaluate/{project_id}")
def config_evaluate_drawing(scenario_code: str, project_id: str, db: Session = Depends(get_db)): return evaluate_drawing_controls(db, project_id)


@router.get("/evaluation/gate")
def evaluation_gate(db: Session = Depends(get_db)):
    item = db.scalar(select(RealDocumentTestGate).limit(1)); return model_dict(item) if item else {}
@router.patch("/evaluation/gate")
def update_evaluation_gate(payload: GatePatch, request: Request, db: Session = Depends(get_db)):
    item = db.scalar(select(RealDocumentTestGate).limit(1)) or RealDocumentTestGate(); db.add(item)
    for key,value in payload.model_dump().items(): setattr(item,key,value)
    db.flush(); audit(db, correlation_id=cid(request), event_type="CONFIG_CHANGED", entity_type="RealDocumentTestGate", entity_id=item.id, after={"real_document_test_approved":item.real_document_test_approved}); db.commit(); return model_dict(item)
@router.get("/evaluation/spikes")
def spikes(db: Session = Depends(get_db)): return config_rows(db, ExtractionSpikeRun)
@router.post("/evaluation/spikes")
def create_spike(payload: SpikeCreate, request: Request, db: Session = Depends(get_db)):
    settings = __import__("backend.app.config.settings", fromlist=["get_settings"]).get_settings()
    gate = db.scalar(select(RealDocumentTestGate).limit(1))
    if payload.dataset_type == DatasetType.APPROVED_REAL_TEST and (not gate or not gate.real_document_test_approved):
        audit(db, correlation_id=cid(request), event_type="REAL_DOCUMENT_SPIKE_DENIED", entity_type="ExtractionSpikeRun", entity_id="not-created", after={"reason":"REAL_DOCUMENT_TEST_NOT_APPROVED"}); db.commit(); raise HTTPException(403, "REAL_DOCUMENT_TEST_NOT_APPROVED")
    if payload.dataset_type == DatasetType.APPROVED_REAL_TEST and (settings.app_env != "TEST" or payload.environment != "TEST"): raise HTTPException(403, "Approved real-document spikes require TEST environment")
    run = ExtractionSpikeRun(dataset_name=payload.dataset_name, dataset_type=payload.dataset_type, environment=payload.environment, extractor_config_version="LOCAL-SYNTHETIC-EXTRACTOR-1.0", classifier_config_version="RULES-W2-1.0", notes=payload.notes); db.add(run); db.flush(); audit(db, correlation_id=cid(request), event_type="SPIKE_CREATED", entity_type="ExtractionSpikeRun", entity_id=run.id, after={"dataset_type":run.dataset_type.value}); db.commit(); return model_dict(run)
@router.get("/evaluation/spikes/{run_id}")
def spike_detail(run_id: str, db: Session = Depends(get_db)):
    run=db.get(ExtractionSpikeRun,run_id)
    if not run: raise HTTPException(404,"Spike not found")
    documents = [model_dict(item) for item in db.scalars(select(SpikeDocumentResult).where(SpikeDocumentResult.spike_run_id == run_id)).all()]
    fields = [model_dict(item) for item in db.scalars(select(SpikeFieldResult).where(SpikeFieldResult.spike_run_id == run_id)).all()]
    return {**model_dict(run),"documents":documents,"fields":fields}
@router.post("/evaluation/spikes/{run_id}/run")
def run_spike_endpoint(run_id: str, request: Request, db: Session = Depends(get_db)):
    run=db.get(ExtractionSpikeRun,run_id)
    if not run: raise HTTPException(404,"Spike not found")
    run_spike(db,run,cid(request)); audit(db, correlation_id=cid(request), event_type="SPIKE_RUN", entity_type="ExtractionSpikeRun", entity_id=run.id, after={"dataset_type":run.dataset_type.value,"document_count":run.document_count}); audit(db, correlation_id=cid(request), event_type="SPIKE_COMPLETED", entity_type="ExtractionSpikeRun", entity_id=run.id, after=run.metrics_json); db.commit(); return model_dict(run)


@router.get("/projects/{project_id}/submission-confirmations")
def confirmations(project_id: str, db: Session = Depends(get_db)): return config_rows(db, SubmissionConfirmation)
@router.post("/submission-confirmations")
def create_confirmation(payload: ConfirmationCreate, request: Request, db: Session = Depends(get_db)):
    confirmation = SubmissionConfirmation(**payload.model_dump()); db.add(confirmation); db.flush(); audit(db, correlation_id=cid(request), event_type="SUBMISSION_CONFIRMATION_RECORDED", entity_type="SubmissionConfirmation", entity_id=confirmation.id, after={"application_id":confirmation.application_id,"mode":confirmation.mode,"visible_status":confirmation.visible_status}); db.commit(); return model_dict(confirmation)


@mock_router.get("/applications/{application_id}/configuration")
def mock_configuration(application_id: str, db: Session = Depends(get_db)):
    cfg = db.scalar(select(MunicipalityConfig).limit(1));
    if not cfg: raise HTTPException(404,"Simulator configuration not found")
    return {"application_id":application_id,**model_dict(cfg),"synthetic":True}
@mock_router.get("/applications/{application_id}/draft")
def mock_draft(application_id: str, db: Session = Depends(get_db)):
    draft=db.scalar(select(MunicipalityDraft).where(MunicipalityDraft.application_id==application_id)); return {"application_id":application_id,"state_json":draft.state_json if draft else {},"persisted":bool(draft),"synthetic":True}
@mock_router.get("/applications/{application_id}/current-state")
def mock_current_state(application_id: str, db: Session = Depends(get_db)):
    app = db.get(PermitApplication, application_id)
    if not app: raise HTTPException(404, "Application not found")
    return {"application_id":application_id,"state":"DRAFT","application_status":app.application_status.value,"synthetic":True}
@mock_router.get("/applications/{application_id}/status")
def mock_status(application_id: str, db: Session = Depends(get_db)):
    app = db.get(PermitApplication, application_id)
    if not app: raise HTTPException(404, "Application not found")
    return {"application_id":application_id,"status":app.application_status.value,"repetition_count":app.repetition_count,"synthetic":True}
@mock_router.get("/applications/{application_id}/comments")
def mock_comments(application_id: str, db: Session = Depends(get_db)):
    app = db.get(PermitApplication, application_id)
    if not app: raise HTTPException(404, "Application not found")
    comments = [{"channel":"PORTAL","text":"Owner name differs from supporting document."},{"channel":"PORTAL","text":"Drawing revision does not match package revision."},{"channel":"MANUAL","text":"Required attachment missing."}] if app.application_status == ApplicationStatus.RETURNED else []
    return {"application_id":application_id,"comments":comments,"synthetic":True}
@mock_router.put("/applications/{application_id}/draft")
def mock_save_draft(application_id: str, payload: DraftPayload, request: Request, db: Session = Depends(get_db)):
    draft=db.scalar(select(MunicipalityDraft).where(MunicipalityDraft.application_id==application_id))
    if not draft: draft=MunicipalityDraft(application_id=application_id,state_json=payload.state_json); db.add(draft)
    else: draft.state_json=payload.state_json
    db.flush(); audit(db, correlation_id=cid(request), event_type="MOCK_DRAFT_SAVED", entity_type="MunicipalityDraft", entity_id=draft.id, after={"application_id":application_id}); db.commit(); return {"application_id":application_id,"state_json":draft.state_json,"persisted":True,"synthetic":True}
@mock_router.get("/applications/{application_id}/validation")
def mock_validation(application_id: str, db: Session = Depends(get_db)):
    draft=db.scalar(select(MunicipalityDraft).where(MunicipalityDraft.application_id==application_id)); state=draft.state_json if draft else {}; errors=[]
    if not state.get("owner_name"): errors.append({"code":"REQUIRED_OWNER","message":"Owner field is required."})
    if state.get("plot_number") and not str(state["plot_number"]).startswith("0"): errors.append({"code":"INVALID_IDENTIFIER","message":"Synthetic plot identifier format is invalid."})
    rows=state.get("buildings",[]); refs=[r.get("building_ref") for r in rows];
    if len(refs)!=len(set(refs)): errors.append({"code":"DUPLICATE_GRID_ROW","message":"Building row identity must be unique."})
    return {"application_id":application_id,"status":"FINDINGS" if errors else "CLEAR","errors":errors,"synthetic":True}
@mock_router.get("/applications/{application_id}/precheck-results")
def mock_precheck(application_id: str, db: Session = Depends(get_db)):
    app=db.get(PermitApplication,application_id); findings=[] if app and app.application_status != ApplicationStatus.RETURNED else [{"code":"TODO-DEMO-001","message":"Drawing revision does not match application revision."},{"code":"TODO-DEMO-002","message":"Required owner document is missing."}]
    return {"precheck_run_id":f"PRECHECK-{application_id[:8]}","status":"CLEAR" if not findings else "FINDINGS","timestamp":datetime.now(timezone.utc).isoformat(),"items":findings,"synthetic":True}
