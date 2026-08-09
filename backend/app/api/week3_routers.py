import hashlib
import json
from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import *
from ..fixtures.canonical import fixture_metadata
from ..schemas.week3_api import *
from ..audit.service import audit

router = APIRouter(prefix="/api")


def cid(request: Request) -> str: return getattr(request.state, "correlation_id", "missing-correlation-id")
def row_dict(item):
    return jsonable_encoder({c.name: (getattr(item, c.name).value if hasattr(getattr(item, c.name), "value") else getattr(item, c.name)) for c in item.__table__.columns})
def rows(db, model): return [row_dict(item) for item in db.scalars(select(model)).all()]
def synthetic_actor_allowed(actor_id: str) -> bool:
    return any(token in actor_id.lower() for token in ("steward", "engineer", "admin", "reviewer"))


@router.get("/phase0/status")
def phase0_status(db: Session = Depends(get_db)):
    baseline = db.scalar(select(PhaseBaseline).where(PhaseBaseline.phase == Phase.PHASE_0).order_by(PhaseBaseline.created_at.desc()))
    recommendation = db.scalar(select(Phase0Decision).order_by(Phase0Decision.decision_date.desc()))
    return {"baseline": row_dict(baseline) if baseline else None, "recommendation": row_dict(recommendation) if recommendation else None, "synthetic": True}


@router.get("/evaluation/adjudications")
def adjudications(db: Session = Depends(get_db)):
    result = []
    for case in db.scalars(select(AdjudicationCase).order_by(AdjudicationCase.status, AdjudicationCase.opened_at)).all():
        version = db.get(DocumentVersion, case.document_version_id); document = db.get(Document, version.document_id) if version else None
        result.append({**row_dict(case), "document": row_dict(document) if document else None, "version": row_dict(version) if version else None})
    return result


@router.get("/evaluation/adjudications/{case_id}")
def adjudication_detail(case_id: str, db: Session = Depends(get_db)):
    case = db.get(AdjudicationCase, case_id)
    if not case: raise HTTPException(404, "Adjudication case not found")
    version = db.get(DocumentVersion, case.document_version_id); document = db.get(Document, version.document_id)
    classification = db.scalar(select(DocumentClassification).where(DocumentClassification.document_version_id == version.id).order_by(DocumentClassification.created_at.desc()))
    observations = [{**row_dict(o), "field_code": db.get(FieldDefinition, o.field_definition_id).field_code} for o in db.scalars(select(FieldObservation).where(FieldObservation.document_version_id == version.id)).all()]
    gold_fields = [{**row_dict(g), "field_code": db.get(FieldDefinition, g.field_definition_id).field_code} for g in db.scalars(select(GoldFieldLabel).where(GoldFieldLabel.document_version_id == version.id)).all()]
    history = rows(db, AdjudicationHistory)
    history = [h for h in history if h["case_id"] == case_id]
    return {**row_dict(case), "document": row_dict(document), "version": row_dict(version), "classification": row_dict(classification) if classification else None, "observations": observations, "gold_fields": gold_fields, "history": history}


@router.post("/evaluation/adjudications/{case_id}/resolve")
def resolve_adjudication(case_id: str, payload: AdjudicationPatch, request: Request, db: Session = Depends(get_db)):
    if not synthetic_actor_allowed(payload.actor_id): raise HTTPException(403, "ADJUDICATION_ROLE_REQUIRED")
    case = db.get(AdjudicationCase, case_id)
    if not case: raise HTTPException(404, "Adjudication case not found")
    before = row_dict(case); action = payload.action.upper()
    if action == "CONFIRM_GROUND_TRUTH": case.status = AdjudicationStatus.ADJUDICATED
    elif action == "CORRECT_GROUND_TRUTH":
        if not payload.expected_class: raise HTTPException(422, "expected_class required for correction")
        case.expected_class = payload.expected_class; case.status = AdjudicationStatus.ADJUDICATED
    elif action == "MARK_AMBIGUOUS": case.status = AdjudicationStatus.DISPUTED; case.ambiguity = payload.ambiguity or "Ambiguity requires review"
    elif action == "ESCALATE_TO_RESPONSIBLE_ENGINEER":
        case.status = AdjudicationStatus.ESCALATED
        case.responsible_engineer_user_id = case.responsible_engineer_user_id or db.scalar(select(User.id).where(User.role == Role.RESPONSIBLE_ENGINEER))
    elif action == "RESOLVE_DISPUTE": case.status = AdjudicationStatus.ADJUDICATED; case.completed_at = datetime.now(timezone.utc)
    else: raise HTTPException(422, "Unknown adjudication action")
    if payload.notes: case.notes = payload.notes
    db.flush(); after = row_dict(case)
    db.add(AdjudicationHistory(case_id=case.id, action=action, actor_id=payload.actor_id, before_json=before, after_json=after, notes=payload.notes))
    audit(db, correlation_id=cid(request), event_type={"CONFIRM_GROUND_TRUTH":"GROUND_TRUTH_CONFIRMED","CORRECT_GROUND_TRUTH":"GROUND_TRUTH_CORRECTED","ESCALATE_TO_RESPONSIBLE_ENGINEER":"ADJUDICATION_ESCALATED","RESOLVE_DISPUTE":"ADJUDICATION_RESOLVED"}.get(action,"GROUND_TRUTH_CORRECTED"), entity_type="AdjudicationCase", entity_id=case.id, actor_id=payload.actor_id, before=before, after=after)
    db.commit(); return after


def analysis_profile(db: Session):
    run = db.scalar(select(ExtractionSpikeRun).where(ExtractionSpikeRun.dataset_name == "SYNTHETIC_WORST_CASE_V1").order_by(ExtractionSpikeRun.completed_at.desc()))
    if run and run.metrics_json.get("week3_analysis"): return run, {**run.metrics_json["week3_analysis"], **fixture_metadata()}
    run = db.scalar(select(ExtractionSpikeRun).order_by(ExtractionSpikeRun.completed_at.desc()))
    if run and run.metrics_json: return run, {"dataset_code":run.dataset_name,"synthetic_demo":True,"not_client_performance":True,"classification":{"documents_evaluated":run.document_count,"agreement":run.metrics_json.get("classification_agreement",0)},"candidate_extraction":{"candidate_agreement":run.metrics_json.get("critical_candidate_agreement",0),"manual_keyed":0,"human_corrected":0},"final_control_quality":{"final_verified_agreement":0,"critical_false_accepts":None},"human_effort":{"field_verification_time_minutes":{"median":run.metrics_json.get("median_verification_time_seconds",0)/60}},"evidence_usability":run.metrics_json.get("evidence_usability",{}),"failure_modes":run.metrics_json.get("failure_modes",{}), **fixture_metadata()}
    return None, {"dataset_code":"SYNTHETIC_WORST_CASE_V1","synthetic_demo":True,"not_client_performance":True, **fixture_metadata()}


@router.get("/evaluation/analysis")
def evaluation_analysis(db: Session = Depends(get_db)):
    run, profile = analysis_profile(db)
    case_rows = db.scalars(select(AdjudicationCase)).all()
    return {"run":row_dict(run) if run else None,"profile":profile,"adjudication":{"total":len(case_rows),"adjudicated":sum(c.status == AdjudicationStatus.ADJUDICATED for c in case_rows),"open":sum(c.status != AdjudicationStatus.ADJUDICATED for c in case_rows)},"labels_are_adjudicated_truth":True,"synthetic_demo":True,"not_client_performance":True}


@router.get("/evaluation/metrics")
def evaluation_metrics(db: Session = Depends(get_db)): return evaluation_analysis(db)


@router.get("/stage2/thresholds")
def thresholds(db: Session = Depends(get_db)): return {"thresholds":rows(db, ThresholdDefinition),"synthetic_banner":"DEMONSTRATION MODE — THRESHOLDS ARE NOT CONTRACTUAL"}


@router.patch("/stage2/thresholds/{threshold_id}")
def update_threshold(threshold_id: str, payload: ThresholdPatch, request: Request, db: Session = Depends(get_db)):
    item = db.get(ThresholdDefinition, threshold_id)
    if not item: raise HTTPException(404, "Threshold not found")
    if payload.status == ThresholdStatus.APPROVED_STAGE_2: raise HTTPException(403, "SYNTHETIC_EVIDENCE_CANNOT_APPROVE_CONTRACTUAL_THRESHOLD")
    before = row_dict(item)
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(item, key, value)
    db.flush(); audit(db, correlation_id=cid(request), event_type="THRESHOLD_CHANGED", entity_type="ThresholdDefinition", entity_id=item.id, before=before, after=row_dict(item)); db.commit(); return row_dict(item)


@router.get("/stage2/acceptance-corpus")
def acceptance_corpus(db: Session = Depends(get_db)):
    item = db.scalar(select(AcceptanceCorpusDefinition).limit(1));
    if not item: return {}
    profile = analysis_profile(db)[1]; required = item.required_case_types_json
    available = {"CLEAN_APPLICATION":True,"RETURNED_APPLICATION":True,"OWNER_IDENTITY_AMBIGUITY":True,"POOR_ARABIC_SCAN":True,"DOCUMENT_REVISION":True,"CONDITIONAL_ATTACHMENT":False,"EXTERNAL_DEPENDENCY":True,"REPEATING_GRID":True,"PORTAL_DERIVED_FIELD":True}
    return {**row_dict(item),"coverage":{"required":len(required),"available":sum(available.get(x,False) for x in required),"missing":[x for x in required if not available.get(x,False)],"case_status":available},"spike_documents":profile.get("classification",{}).get("documents_evaluated",0),"warning":"15 synthetic documents are not representative coverage."}


@router.patch("/stage2/acceptance-corpus")
def update_acceptance_corpus(payload: dict, request: Request, db: Session = Depends(get_db)):
    item = db.scalar(select(AcceptanceCorpusDefinition).limit(1))
    if not item: raise HTTPException(404, "Acceptance corpus not found")
    before=row_dict(item)
    for key in ("status","description","sampling_rule","minimum_cases","owner","notes"):
        if key in payload: setattr(item,key,payload[key])
    db.flush(); audit(db, correlation_id=cid(request), event_type="CONFIG_CHANGED", entity_type="AcceptanceCorpusDefinition", entity_id=item.id, before=before, after=row_dict(item)); db.commit(); return row_dict(item)


@router.get("/stage2/tier1-decisions")
def tier1_decisions(db: Session = Depends(get_db)): return rows(db, Tier1Decision)


@router.patch("/stage2/tier1-decisions/{decision_id}")
def update_tier1(decision_id: str, payload: Tier1Patch, request: Request, db: Session = Depends(get_db)):
    item=db.get(Tier1Decision,decision_id)
    if not item: raise HTTPException(404,"Tier 1 decision not found")
    before=row_dict(item)
    for key,value in payload.model_dump(exclude_unset=True).items(): setattr(item,key,value)
    db.flush(); audit(db, correlation_id=cid(request), event_type="TIER1_DECISION_FALLBACK" if item.status == Tier1DecisionStatus.RESOLVED_WITH_FALLBACK else "TIER1_DECISION_RESOLVED", entity_type="Tier1Decision", entity_id=item.id, before=before, after=row_dict(item)); db.commit(); return row_dict(item)


@router.get("/stage2/tier2-backlog")
def tier2_backlog(db: Session = Depends(get_db)): return rows(db, Tier2BacklogItem)


@router.post("/stage2/tier2-backlog")
def create_tier2(payload: Tier2Create, request: Request, db: Session = Depends(get_db)):
    warning = any(token in (payload.title + " " + payload.description).lower() for token in ("new municipality","new permit","new owner","authority automation"))
    item=Tier2BacklogItem(**payload.model_dump(), scenario_expansion_warning=warning); db.add(item); db.flush(); audit(db, correlation_id=cid(request), event_type="TIER2_ITEM_CREATED", entity_type="Tier2BacklogItem", entity_id=item.id, after=row_dict(item)); db.commit(); return row_dict(item)


@router.patch("/stage2/tier2-backlog/{item_id}")
def update_tier2(item_id: str, payload: Tier2Patch, request: Request, db: Session = Depends(get_db)):
    item=db.get(Tier2BacklogItem,item_id)
    if not item: raise HTTPException(404,"Tier 2 item not found")
    before=row_dict(item)
    for key,value in payload.model_dump(exclude_unset=True).items(): setattr(item,key,value)
    db.flush(); audit(db, correlation_id=cid(request), event_type="TIER2_ITEM_CHANGED", entity_type="Tier2BacklogItem", entity_id=item.id, before=before, after=row_dict(item)); db.commit(); return row_dict(item)


@router.get("/stage2/delivery-scenarios")
def delivery_scenarios(db: Session = Depends(get_db)): return rows(db, DeliveryScenario)


@router.patch("/stage2/delivery-scenarios/{scenario_id}")
def select_delivery(scenario_id: str, payload: DeliveryPatch, request: Request, db: Session = Depends(get_db)):
    item=db.get(DeliveryScenario,scenario_id)
    if not item: raise HTTPException(404,"Delivery scenario not found")
    for other in db.scalars(select(DeliveryScenario)).all():
        if other.id != scenario_id and payload.status == DeliveryStatus.SELECTED_DEMO and other.status == DeliveryStatus.SELECTED_DEMO: other.status=DeliveryStatus.CANDIDATE
    before=row_dict(item); item.status=payload.status; db.flush(); audit(db, correlation_id=cid(request), event_type="DELIVERY_SCENARIO_SELECTED", entity_type="DeliveryScenario", entity_id=item.id, before=before, after=row_dict(item)); db.commit(); return row_dict(item)


@router.get("/stage2/municipality-operations")
def municipality_operations(db: Session = Depends(get_db)): return rows(db, MunicipalityOperationDecision)


@router.get("/stage2/precheck-decision")
def precheck_decision(db: Session = Depends(get_db)):
    item=db.scalar(select(PrecheckDecision).limit(1)); return row_dict(item) if item else {}


@router.get("/stage2/pilot-cohort")
def pilot_cohort(db: Session = Depends(get_db)):
    item=db.scalar(select(PilotCohort).limit(1));
    if not item:return {}
    result=row_dict(item); result["preparers"]=[row_dict(db.get(User,user_id)) for user_id in item.preparer_user_ids_json if db.get(User,user_id)]
    for key in ("super_user_id","process_champion_id","requirement_steward_id","responsible_engineer_id","final_submitter_id"): result[key.replace("_id","")]=row_dict(db.get(User,getattr(item,key))) if db.get(User,getattr(item,key)) else None
    return result


@router.get("/stage2/business-baseline")
def business_baseline(db: Session = Depends(get_db)):
    return {"baseline": rows(db, BusinessBaseline), "targets": rows(db, BusinessKpiTarget), "synthetic_banner": "DEMONSTRATION WITH SYNTHETIC DATA — NOT CLIENT BUSINESS CASE"}


def recommend_phase0(*, approved_data: bool, pilot_available: bool, bounded_scenario: bool, assisted_viable: bool, tier1_blocker: bool, automation_available: bool, candidate_agreement: float, keyed_fallback: bool) -> Phase0DecisionType:
    if not approved_data or not pilot_available or not bounded_scenario:
        return Phase0DecisionType.PAUSE
    if not assisted_viable:
        return Phase0DecisionType.NO_GO
    if candidate_agreement < 0.90 and keyed_fallback:
        return Phase0DecisionType.GO_WITH_REDUCED_DEPTH
    if tier1_blocker:
        return Phase0DecisionType.PAUSE
    if not automation_available:
        return Phase0DecisionType.GO_WITH_FALLBACK
    return Phase0DecisionType.GO


def close_criteria(db: Session):
    decisions=db.scalars(select(Tier1Decision)).all(); backlog=db.scalars(select(Tier2BacklogItem)).all(); delivery=db.scalar(select(DeliveryScenario).where(DeliveryScenario.status == DeliveryStatus.SELECTED_DEMO)); pilot=db.scalar(select(PilotCohort).limit(1)); precheck=db.scalar(select(PrecheckDecision).limit(1)); data_gate=db.scalar(select(RealDocumentTestGate).limit(1)); approved_data=bool(data_gate and data_gate.real_document_test_approved)
    criteria=[
        {"criterion":"SCENARIO","status":"PASS","evidence":"DEMO_BUILDING_PERMIT_V1 bounded synthetic scenario","risk":"Not client approved","fallback":"Keep scope frozen","owner":"Product Lead"},
        {"criterion":"DATA_ACCESS","status":"UNKNOWN","evidence":"Real TEST location and raw access are not approved","risk":"Real spike blocked","fallback":"Synthetic-only / approved TEST later","owner":"Security/Hosting"},
        {"criterion":"PILOT","status":"PASS_WITH_CONDITION" if pilot else "FAIL","evidence":"Synthetic cohort seeded" if pilot else "No cohort","risk":"Client users not confirmed","fallback":"Demo cohort only","owner":"Process Champion"},
        {"criterion":"TIER_1","status":"PASS_WITH_CONDITION" if not any(d.status == Tier1DecisionStatus.BLOCKER for d in decisions) else "FAIL","evidence":f"{sum(d.status in (Tier1DecisionStatus.RESOLVED,Tier1DecisionStatus.RESOLVED_WITH_FALLBACK) for d in decisions)} resolved; {sum(d.status in (Tier1DecisionStatus.OPEN,Tier1DecisionStatus.ESCALATED) for d in decisions)} open","risk":"Open decisions remain","fallback":"Use assisted path","owner":"Requirement Steward"},
        {"criterion":"EXTRACTION","status":"PASS_WITH_CONDITION","evidence":"Adjudicated synthetic profile with keyed fallback","risk":"Synthetic corpus only","fallback":"Reduced depth + human verification","owner":"Technical Lead"},
        {"criterion":"MUNICIPALITY","status":"PASS_WITH_CONDITION","evidence":"Mock / assisted operations available","risk":"Real authorization unknown","fallback":"Assisted attended session","owner":"Process Champion"},
        {"criterion":"SUBMISSION","status":"PASS_WITH_CONDITION","evidence":"Machine-read preferred, human evidence fallback","risk":"No final submit capability","fallback":"Human confirmation ledger","owner":"Final Submitter"},
        {"criterion":"PROFESSIONAL_RESPONSIBILITY","status":"UNKNOWN","evidence":"Synthetic roles seeded","risk":"Client responsibility confirmation required","fallback":"Responsible Engineer review","owner":"Owner/Sponsor"},
        {"criterion":"ACCEPTANCE","status":"PASS_WITH_CONDITION","evidence":"Corpus definition exists; coverage gaps remain","risk":"Not contractual","fallback":"Expand/adjudicate corpus","owner":"Technical Lead"},
        {"criterion":"COMMERCIAL","status":"PASS_WITH_CONDITION","evidence":"Draft scenario and payment plan model available","risk":"No authorization in draft","fallback":"Sign-off C review","owner":"Arkan Product Lead"},
        {"criterion":"CLIENT_CAPACITY","status":"UNKNOWN","evidence":"Synthetic champion/steward/pilot only","risk":"Availability not confirmed","fallback":"Pause before real build","owner":"Owner/Sponsor"}]
    profile = analysis_profile(db)[1]
    candidate_agreement = profile.get("candidate_extraction", {}).get("candidate_agreement", 0.0)
    recommendation = recommend_phase0(
        approved_data=approved_data,
        pilot_available=bool(pilot),
        bounded_scenario=bool(delivery),
        assisted_viable=True,
        tier1_blocker=any(d.status == Tier1DecisionStatus.BLOCKER for d in decisions),
        automation_available=False,
        candidate_agreement=candidate_agreement,
        keyed_fallback=True,
    )
    return {"criteria":criteria,"system_recommendation":recommendation.value,"recommendation_reason":"The synthetic assisted path is viable for demonstration, but the system pauses real-data progression until an approved processing path and client capacity are confirmed.","blockers":["Real data-processing approval required before approved-real spike"],"conditions":["Stage 2 approval","Sign-off C signature","Client-confirmed privacy/data path","Expanded adjudicated acceptance corpus"],"synthetic_demo":True}


@router.get("/phase0/close")
def phase0_close(db: Session = Depends(get_db)): return close_criteria(db)


@router.post("/phase0/recommendation")
def phase0_recommendation(payload: Phase0Recommendation, request: Request, db: Session = Depends(get_db)):
    item=Phase0Decision(decision=payload.decision,decision_date=date.today(),recommended_by="Synthetic System Recommendation",summary=payload.summary,conditions_json=payload.conditions,blockers_json=payload.blockers,fallbacks_json=payload.fallbacks,evidence_refs_json=payload.evidence_refs,commercial_effect="DEMO ONLY",next_action="Human review required",status="RECOMMENDATION")
    db.add(item); db.flush(); audit(db, correlation_id=cid(request), event_type="PHASE0_RECOMMENDATION_CREATED", entity_type="Phase0Decision", entity_id=item.id, after=row_dict(item)); db.commit(); return row_dict(item)


@router.post("/phase0/decision")
def phase0_decision(payload: Phase0DecisionCreate, request: Request, db: Session = Depends(get_db)):
    item=Phase0Decision(decision=payload.decision,decision_date=date.today(),recommended_by="Synthetic System Recommendation",approved_by=payload.approved_by,summary=payload.summary,conditions_json=payload.conditions,blockers_json=payload.blockers,fallbacks_json=payload.fallbacks,evidence_refs_json=payload.evidence_refs,commercial_effect=payload.commercial_effect,next_action=payload.next_action,status="AUTHORIZED_DEMO")
    db.add(item); db.flush(); audit(db, correlation_id=cid(request), event_type="PHASE0_DECISION_RECORDED", entity_type="Phase0Decision", entity_id=item.id, actor_id=payload.approved_by, after=row_dict(item)); db.commit(); return row_dict(item)


def snapshot_payload(db: Session, scenario_code: str):
    scenario=db.scalar(select(ScenarioConfig).where(ScenarioConfig.scenario_code == scenario_code))
    delivery=rows(db,DeliveryScenario); selected=[x for x in delivery if x["status"] == DeliveryStatus.SELECTED_DEMO.value]
    corpus=acceptance_corpus(db); profile=analysis_profile(db)[1]
    payload={"scenario":row_dict(scenario),"tier1":rows(db,Tier1Decision),"thresholds":rows(db,ThresholdDefinition),"municipality_modes":rows(db,MunicipalityOperationDecision),"data_delivery":selected,"security":{"synthetic_only":True,"real_documents_approved":False,"external_ai_allowed":False},"pilot":phase_pilot(db),"acceptance":corpus,"tier2":rows(db,Tier2BacklogItem),"business_kpis":{"baseline":rows(db,BusinessBaseline),"targets":rows(db,BusinessKpiTarget)},"decision_log":{"phase0":rows(db,Phase0Decision)},"spike":profile}
    return payload


def phase_pilot(db):
    item=db.scalar(select(PilotCohort).limit(1)); return row_dict(item) if item else {}


@router.get("/stage2/baseline")
def stage2_baseline(db: Session = Depends(get_db)):
    item=db.scalar(select(Stage2Baseline).order_by(Stage2Baseline.created_at.desc()))
    return {"baseline":row_dict(item) if item else None,"sections":{k:("COMPLETE" if v else "OPEN") for k,v in (("Scenario Envelope",True),("Critical Field Matrix",True),("Spike Results",True),("Technical Thresholds",True),("Acceptance Corpus",bool(db.scalar(select(AcceptanceCorpusDefinition).limit(1)))), ("Municipality Modes",bool(db.scalar(select(MunicipalityOperationDecision).limit(1)))), ("Tier 2 Backlog",bool(db.scalar(select(Tier2BacklogItem).limit(1)))), ("Open Conditions",True))},"synthetic_banner":"DEMONSTRATION BASELINE — SYNTHETIC DATA — NOT CLIENT APPROVED"}


@router.post("/stage2/baseline/generate")
def generate_stage2(payload: BaselineGenerate, request: Request, db: Session = Depends(get_db)):
    data=snapshot_payload(db,payload.scenario_code); existing=db.scalars(select(Stage2Baseline).order_by(Stage2Baseline.created_at)).all(); version=f"v1.{len(existing)}"; checksum=hashlib.sha256(json.dumps(data,sort_keys=True,default=str).encode()).hexdigest()
    item=Stage2Baseline(version=version,scenario_id=data["scenario"]["id"],status=Stage2Status.DRAFT,scenario_snapshot_json=data["scenario"],tier1_snapshot_json=data["tier1"],threshold_snapshot_json=data["thresholds"],municipality_mode_snapshot_json=data["municipality_modes"],data_delivery_snapshot_json=data["data_delivery"],security_snapshot_json=data["security"],pilot_snapshot_json=data["pilot"],acceptance_snapshot_json=data["acceptance"],tier2_backlog_snapshot_json=data["tier2"],business_kpi_snapshot_json=data["business_kpis"],decision_log_snapshot_json=data["decision_log"],checksum=checksum)
    db.add(item); db.flush(); audit(db, correlation_id=cid(request), event_type="STAGE2_BASELINE_GENERATED", entity_type="Stage2Baseline", entity_id=item.id, after={"version":version,"checksum":checksum}); db.commit(); return row_dict(item)


@router.post("/stage2/baseline/{baseline_id}/approve")
def approve_stage2(baseline_id: str, payload: BaselineApprove, request: Request, db: Session = Depends(get_db)):
    item=db.get(Stage2Baseline,baseline_id)
    if not item: raise HTTPException(404,"Stage 2 baseline not found")
    if item.status in (Stage2Status.APPROVED,Stage2Status.APPROVED_WITH_CONDITIONS): raise HTTPException(409,"APPROVED_BASELINE_IMMUTABLE")
    item.status=payload.status; item.approved_at=datetime.now(timezone.utc); db.flush(); audit(db, correlation_id=cid(request), event_type="STAGE2_BASELINE_APPROVED", entity_type="Stage2Baseline", entity_id=item.id, actor_id=payload.approved_by, after={"status":item.status.value,"checksum":item.checksum}); db.commit(); return row_dict(item)


@router.get("/stage2/baseline/{baseline_id}/acknowledgements")
def stage2_acknowledgements(baseline_id: str, db: Session = Depends(get_db)):
    baseline = db.get(Stage2Baseline, baseline_id)
    if not baseline: raise HTTPException(404, "Stage 2 baseline not found")
    return {"baseline": {"id": baseline.id, "version": baseline.version, "checksum": baseline.checksum, "status": baseline.status.value}, "reviewed_not_approved": [row_dict(item) for item in db.scalars(select(Stage2ReviewAcknowledgement).where(Stage2ReviewAcknowledgement.baseline_id == baseline.id).order_by(Stage2ReviewAcknowledgement.created_at)).all()]}


@router.post("/stage2/baseline/{baseline_id}/acknowledgements")
def acknowledge_stage2(baseline_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    baseline = db.get(Stage2Baseline, baseline_id)
    if not baseline: raise HTTPException(404, "Stage 2 baseline not found")
    reviewer_name = str(payload.get("reviewer_name", "")).strip()
    reviewer_role = str(payload.get("reviewer_role", "")).strip()
    if not reviewer_name or not reviewer_role: raise HTTPException(422, "REVIEWER_IDENTITY_REQUIRED")
    acknowledgement = str(payload.get("acknowledgement", "REVIEWED")).upper()
    if acknowledgement != "REVIEWED": raise HTTPException(422, "ACKNOWLEDGEMENT_MUST_BE_REVIEWED")
    item = Stage2ReviewAcknowledgement(baseline_id=baseline.id, reviewer_role=reviewer_role, reviewer_name=reviewer_name, acknowledgement="REVIEWED", notes=payload.get("notes"))
    db.add(item); db.flush()
    audit(db, correlation_id=cid(request), event_type="STAGE2_BASELINE_REVIEW_ACKNOWLEDGED", entity_type="Stage2Baseline", entity_id=baseline.id, actor_id=reviewer_name, after={"reviewer_role": reviewer_role, "baseline_version": baseline.version, "baseline_checksum": baseline.checksum, "acknowledgement": "REVIEWED", "approval_unchanged": baseline.status.value})
    db.commit()
    return {"acknowledgement": row_dict(item), "baseline_version": baseline.version, "baseline_checksum": baseline.checksum, "baseline_status": baseline.status.value, "reviewed_is_not_approved": True}


@router.get("/commercial/signoff-c")
def signoff_c(db: Session = Depends(get_db)):
    item=db.scalar(select(SignoffCProposal).order_by(SignoffCProposal.created_at.desc())); return row_dict(item) if item else {"status":"NOT_GENERATED","synthetic_demo":True}


@router.post("/commercial/signoff-c/generate")
def generate_signoff(payload: SignoffGenerate, request: Request, db: Session = Depends(get_db)):
    baseline=db.scalar(select(Stage2Baseline).order_by(Stage2Baseline.created_at.desc()))
    if not baseline: raise HTTPException(409,"STAGE2_BASELINE_REQUIRED")
    payments=[{"milestone":"Build Start","percent":15},{"milestone":"Week 6 Assisted Vertical Slice","percent":20},{"milestone":"Trust/Package Hardening","percent":20},{"milestone":"Production-Mode Maturity","percent":15},{"milestone":"G10","percent":15},{"milestone":"Technical Acceptance","percent":10},{"milestone":"Operational Observation Holdback","percent":5}]
    if sum(p["percent"] for p in payments) != 100: raise HTTPException(500,"PAYMENT_PLAN_MUST_TOTAL_100")
    item=SignoffCProposal(stage2_baseline_id=baseline.id,version="v0.1",status=SignoffStatus.DRAFT,scope_summary="Synthetic Stage 2 bounded building-permit vertical slice; no production authorization.",capability_depth_json={"municipality":"ASSISTED","documents":"verification_required","submission":"human_confirmation"},delivery_scenario="HYBRID_APPROVED",schedule_json={"phase0_complete":"2026-08-07","stage2_review":"2026-08-10","build_start":"2026-08-17","week6":"2026-09-25","g10":"2026-10-16","live_pilot":"2026-10-23","technical_acceptance":"2026-10-30","hypercare":"4 weeks","observation":"90 days","adjustment_factors":["RAMADAN_REDUCED_CAPACITY","SUMMER_REDUCED_CLIENT_AVAILABILITY","PUBLIC_HOLIDAY","CLIENT_BLACKOUT"]},fixed_price_qar=payload.fixed_price_qar,payment_plan_json=payments,holdback_percent=5,client_staffing_json={"super_user":"Synthetic","preparers":3,"champion":"Synthetic","steward":"Synthetic","engineer":"Synthetic","submitter":"Synthetic"},technical_thresholds_json=rows(db,ThresholdDefinition),remediation_commitment="No-fee re-presentation within 10 business days for supplier-attributable threshold failure where scope and baseline are unchanged.",g10_conditions_json=["Stage 2 approved","Acceptance evidence complete","Operational monitoring configured"],hypercare_weeks=4,operational_observation_days=90,support_terms="L1 client super-user; L2 application/configuration support; L3 infrastructure/authority/client IT dependency.",warranty_terms="Draft only; subject to commercial review.",maintenance_terms="Draft only; subject to commercial review.",ip_terms="Client-specific configuration and agreed deliverables governed by signed terms.",data_exit_terms="Return/delete approved artifacts at exit; no secrets or raw documents in demo export.",exclusions_json=["Real Ministry integration","Browser automation","Production credentials","Unapproved real documents"])
    db.add(item); db.flush(); audit(db, correlation_id=cid(request), event_type="SIGNOFF_C_DRAFT_GENERATED", entity_type="SignoffCProposal", entity_id=item.id, after={"baseline_id":baseline.id,"holdback_percent":5,"hypercare_weeks":4}); db.commit(); return row_dict(item)


@router.get("/phase0/handoff-export")
def handoff_export(db: Session = Depends(get_db)):
    return {"export_type":"NO_GO_PAUSE_HANDOFF_DEMO","synthetic_only":True,"reports":["phase0-close-report.md","spike-analysis-v1.md","threshold-evidence-v1.md","tier1-resolution-log.md","tier2-backlog.md","business-case-snapshot-v1.md"],"configuration":{"tier1":rows(db,Tier1Decision),"thresholds":rows(db,ThresholdDefinition),"delivery":rows(db,DeliveryScenario),"municipality":rows(db,MunicipalityOperationDecision)},"raid":rows(db,RaidItem),"inquiries":rows(db,MinistryInquiry),"business":rows(db,BusinessBaseline),"phase0":close_criteria(db),"secrets_included":False,"raw_documents_included":False}
