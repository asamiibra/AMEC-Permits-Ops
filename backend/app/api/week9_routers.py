"""Week 9 attachment, repeating-grid, and portal-derived APIs."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..db import get_db
from ..fixtures.canonical import fixture_metadata
from ..models import *
from ..services.week45 import row, stable_hash
from ..services.week9 import (
    _is_current_revision, _rules, attachment_intent, ensure_grid_intents,
    manifest_items, observe_grid, reconcile_attachments, reconcile_grid,
    reconcile_portal_derived, refresh_manifest,
)
from ..services.week8 import ensure_lineage_edge

router = APIRouter(prefix="/api")


def cid(request: Request) -> str:
    return getattr(request.state, "correlation_id", "week9-api")


def revision_or_404(db: Session, revision_id: str) -> PreparationRevision:
    revision = db.get(PreparationRevision, revision_id)
    if not revision: raise HTTPException(404, "Preparation revision not found")
    return revision


@router.get("/preparation-revisions/{revision_id}/attachment-manifest")
def attachment_manifest(revision_id: str, db: Session = Depends(get_db)):
    revision = revision_or_404(db, revision_id)
    manifest = db.scalar(select(AttachmentManifest).where(AttachmentManifest.preparation_revision_id == revision_id))
    if not manifest:
        try: manifest = refresh_manifest(db, revision_id)
        except ValueError as exc: raise HTTPException(409, str(exc))
        db.commit()
    return {"manifest": row(manifest), "items": [row(x) for x in manifest_items(db, manifest.id)], "categories": [row(x) for x in _rules(db, revision)], "fixture": fixture_metadata()}


@router.post("/preparation-revisions/{revision_id}/attachment-manifest/refresh")
def attachment_manifest_refresh(revision_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    revision_or_404(db, revision_id)
    try: manifest = refresh_manifest(db, revision_id, actor=payload.get("actor", "operator"), correlation_id=cid(request))
    except ValueError as exc: raise HTTPException(409, str(exc))
    db.commit()
    revision = revision_or_404(db, revision_id)
    return {"manifest": row(manifest), "items": [row(x) for x in manifest_items(db, manifest.id)], "categories": [row(x) for x in _rules(db, revision)], "fixture": fixture_metadata()}


@router.get("/preparation-revisions/{revision_id}/attachments/intended")
def attachment_intended(revision_id: str, db: Session = Depends(get_db)):
    revision_or_404(db, revision_id)
    return {"intents": [row(x) for x in db.scalars(select(AttachmentAssociationIntent).where(AttachmentAssociationIntent.preparation_revision_id == revision_id).order_by(AttachmentAssociationIntent.created_at)).all()], "fixture": fixture_metadata()}


@router.post("/preparation-revisions/{revision_id}/attachments/associate")
def attachment_associate(revision_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    try: intent = attachment_intent(db, revision_id, payload, actor=payload.get("actor", "operator"), correlation_id=cid(request))
    except ValueError as exc: raise HTTPException(409, str(exc))
    db.commit()
    return {"intent": row(intent), "idempotent": bool(db.scalar(select(AttachmentAssociationIntent).where(AttachmentAssociationIntent.id == intent.id))), "fixture": fixture_metadata()}


def _snapshot(db: Session, revision: PreparationRevision, payload: dict, request: Request) -> PortalSnapshot:
    _is_current_revision(db, revision)
    attachment_state = payload.get("attachment_state", [])
    if isinstance(attachment_state, dict): attachment_state = [{"category_code": k, "files": v if isinstance(v, list) else [v]} for k, v in attachment_state.items()]
    normalized = sorted([{"category_code": x.get("category_code"), "files": sorted(x.get("files", []), key=lambda f: (f.get("filename", ""), f.get("document_version_id", "")))} for x in attachment_state], key=lambda x: x["category_code"] or "")
    data = {"field_state": payload.get("field_state", {}), "grid_state": payload.get("grid_state", []), "attachment_state": normalized, "validation_state": payload.get("validation_state", {}), "precheck_state": payload.get("precheck_state", {})}
    snapshot = PortalSnapshot(application_id=revision.application_id, preparation_revision_id=revision.id, snapshot_type=payload.get("snapshot_type", payload.get("phase", "REOPENED")), capture_method=payload.get("capture_method", "SIMULATOR_READ"), **data, snapshot_hash=stable_hash(data))
    db.add(snapshot); db.flush(); audit(db, correlation_id=cid(request), event_type="ATTACHMENT_STATE_CAPTURED", entity_type="PortalSnapshot", entity_id=snapshot.id, after={"snapshot_hash": snapshot.snapshot_hash, "phase": snapshot.snapshot_type}, metadata=fixture_metadata())
    ensure_lineage_edge(db, project_id=revision.project_id, upstream_type="PreparationRevision", upstream_id=revision.id, upstream_version_or_hash=revision.package_manifest_hash, downstream_type="PortalSnapshot", downstream_id=snapshot.id, downstream_version_or_hash=snapshot.snapshot_hash, dependency_kind="PORTAL_STATE_CAPTURE", correlation_id=cid(request))
    return snapshot


@router.post("/preparation-revisions/{revision_id}/attachments/capture-state")
def attachment_capture_state(revision_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    revision = revision_or_404(db, revision_id)
    try: snapshot = _snapshot(db, revision, payload, request)
    except ValueError as exc: raise HTTPException(409, str(exc))
    db.commit()
    return {"snapshot": row(snapshot), "state_hash": snapshot.snapshot_hash, "fixture": fixture_metadata()}


@router.post("/preparation-revisions/{revision_id}/attachments/reconcile")
def attachment_reconcile(revision_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    revision = revision_or_404(db, revision_id)
    snapshot = db.get(PortalSnapshot, payload.get("portal_snapshot_id")) if payload.get("portal_snapshot_id") else db.scalar(select(PortalSnapshot).where(PortalSnapshot.preparation_revision_id == revision_id).order_by(PortalSnapshot.captured_at.desc()))
    if not snapshot: raise HTTPException(409, "PORTAL_ATTACHMENT_SNAPSHOT_REQUIRED")
    try: results = reconcile_attachments(db, revision_id, snapshot, actor=payload.get("actor", "operator"), correlation_id=cid(request))
    except ValueError as exc: raise HTTPException(409, str(exc))
    db.commit()
    return {"snapshot": row(snapshot), "results": [row(x) for x in results], "status": "MATCH" if all(x.status == "MATCH" for x in results) else "EXCEPTION", "fixture": fixture_metadata()}


@router.get("/preparation-revisions/{revision_id}/attachments/persistence")
def attachment_persistence(revision_id: str, db: Session = Depends(get_db)):
    revision_or_404(db, revision_id)
    return {"evidence": [row(x) for x in db.scalars(select(AttachmentPersistenceEvidence).where(AttachmentPersistenceEvidence.preparation_revision_id == revision_id).order_by(AttachmentPersistenceEvidence.verified_at)).all()], "fixture": fixture_metadata()}


@router.get("/preparation-revisions/{revision_id}/grids")
def grids(revision_id: str, grid_code: str = "BUILDING_FLOOR_UNIT", db: Session = Depends(get_db)):
    revision_or_404(db, revision_id)
    try: intents = ensure_grid_intents(db, revision_id, grid_code=grid_code)
    except ValueError as exc: raise HTTPException(409, str(exc))
    db.commit()
    return {"grid_code": grid_code, "intents": [row(x) for x in intents], "fixture": fixture_metadata()}


@router.get("/preparation-revisions/{revision_id}/grids/{grid_code}/intent")
def grid_intent(revision_id: str, grid_code: str, db: Session = Depends(get_db)):
    return grids(revision_id, grid_code, db)


@router.post("/preparation-revisions/{revision_id}/grids/{grid_code}/capture")
def grid_capture(revision_id: str, grid_code: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    revision = revision_or_404(db, revision_id)
    try: _is_current_revision(db, revision)
    except ValueError as exc: raise HTTPException(409, str(exc))
    snapshot = _snapshot(db, revision, {"grid_state": payload.get("observed_rows", []), "attachment_state": payload.get("attachment_state", []), "snapshot_type": payload.get("snapshot_type", "REOPENED"), "capture_method": payload.get("capture_method", "SIMULATOR_READ")}, request)
    observations = observe_grid(db, revision_id, snapshot, payload.get("observed_rows", []), grid_code=grid_code, correlation_id=cid(request))
    db.commit()
    return {"snapshot": row(snapshot), "observations": [row(x) for x in observations], "fixture": fixture_metadata()}


@router.post("/preparation-revisions/{revision_id}/grids/{grid_code}/reconcile")
def grid_reconcile(revision_id: str, grid_code: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    revision = revision_or_404(db, revision_id)
    snapshot = db.get(PortalSnapshot, payload.get("portal_snapshot_id")) if payload.get("portal_snapshot_id") else db.scalar(select(PortalSnapshot).where(PortalSnapshot.preparation_revision_id == revision_id).order_by(PortalSnapshot.captured_at.desc()))
    if not snapshot: raise HTTPException(409, "PORTAL_GRID_SNAPSHOT_REQUIRED")
    try: run = reconcile_grid(db, revision_id, snapshot, grid_code=grid_code, correlation_id=cid(request))
    except ValueError as exc: raise HTTPException(409, str(exc))
    evidence = GridPersistenceEvidence(preparation_revision_id=revision_id, grid_code=grid_code, intended_state_hash=stable_hash([row(x) for x in ensure_grid_intents(db, revision_id, grid_code=grid_code)]), post_save_snapshot_id=snapshot.id, reopened_snapshot_id=snapshot.id, result="PERSISTED_MATCH" if run.result == "MATCH" else "ROW_CHANGED_AFTER_SAVE", evidence_artifact_id=snapshot.id)
    db.add(evidence); db.flush(); audit(db, correlation_id=cid(request), event_type="GRID_PERSISTENCE_VERIFIED" if run.result == "MATCH" else "GRID_PERSISTENCE_FAILED", entity_type="GridPersistenceEvidence", entity_id=evidence.id, after={"result": evidence.result}, metadata=fixture_metadata()); db.commit()
    return {"run": row(run), "results": [row(x) for x in db.scalars(select(GridRowReconciliationResult).where(GridRowReconciliationResult.run_id == run.id)).all()], "persistence": row(evidence), "fixture": fixture_metadata()}


@router.get("/preparation-revisions/{revision_id}/portal-derived-fields")
def portal_derived_fields(revision_id: str, db: Session = Depends(get_db)):
    revision_or_404(db, revision_id)
    return {"reconciliations": [row(x) for x in db.scalars(select(PortalDerivedFieldReconciliation).where(PortalDerivedFieldReconciliation.preparation_revision_id == revision_id).order_by(PortalDerivedFieldReconciliation.created_at)).all()], "fixture": fixture_metadata()}


@router.post("/preparation-revisions/{revision_id}/portal-derived-fields/reconcile")
def portal_derived_reconcile(revision_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    revision_or_404(db, revision_id)
    try: item = reconcile_portal_derived(db, revision_id, payload, correlation_id=cid(request))
    except ValueError as exc: raise HTTPException(409, str(exc))
    db.commit()
    return {"reconciliation": row(item), "canonical_overwrite": False, "fixture": fixture_metadata()}


def _structure_payload(db: Session, revision: PreparationRevision, scope: str) -> dict:
    if scope == "ATTACHMENT_TREE":
        return {"categories": [{"code": x.category_code, "label_en": x.portal_label_en, "label_ar": x.portal_label_ar, "order": x.portal_order, "requirement_state": x.requirement_state} for x in _rules(db, revision)]}
    if scope == "REPEATING_GRID_SCHEMA":
        cfg = db.scalar(select(MunicipalityConfig).join(ScenarioConfig).where(ScenarioConfig.version == revision.scenario_version))
        return {"grids": cfg.grids_json if cfg else []}
    cfg = db.scalar(select(MunicipalityConfig).join(ScenarioConfig).where(ScenarioConfig.version == revision.scenario_version))
    return {"fields": cfg.fields_json if cfg else []}


@router.get("/preparation-revisions/{revision_id}/portal-structure-fingerprint")
def structure_fingerprint(revision_id: str, scope: str = "ATTACHMENT_TREE", db: Session = Depends(get_db)):
    revision_or_404(db, revision_id)
    return {"fingerprints": [row(x) for x in db.scalars(select(PortalStructureFingerprint).where(PortalStructureFingerprint.preparation_revision_id == revision_id, PortalStructureFingerprint.scope == scope).order_by(PortalStructureFingerprint.captured_at.desc())).all()], "fixture": fixture_metadata()}


@router.post("/preparation-revisions/{revision_id}/portal-structure-fingerprint/capture")
def structure_fingerprint_capture(revision_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    revision = revision_or_404(db, revision_id); scope = payload.get("scope", "ATTACHMENT_TREE"); expected = _structure_payload(db, revision, scope); observed = payload.get("observed_structure", expected); expected_hash, observed_hash = stable_hash(expected), stable_hash(observed); status = "MATCH" if expected_hash == observed_hash else "DRIFTED"
    item = PortalStructureFingerprint(preparation_revision_id=revision_id, scope=scope, scenario_id=next((x.scenario_id for x in _rules(db, revision)), None) if scope == "ATTACHMENT_TREE" else None, contract_version="W9-STRUCTURE-1.0", expected_hash=expected_hash, observed_hash=observed_hash, expected_structure=expected, observed_structure=observed, status=status)
    db.add(item); db.flush(); audit(db, correlation_id=cid(request), event_type="PORTAL_STRUCTURE_FINGERPRINT_CAPTURED", entity_type="PortalStructureFingerprint", entity_id=item.id, after={"scope": scope, "status": status}, metadata=fixture_metadata())
    if status == "DRIFTED": audit(db, correlation_id=cid(request), event_type="PORTAL_STRUCTURE_DRIFT_DETECTED", entity_type="PortalStructureFingerprint", entity_id=item.id, after={"scope": scope, "assisted_fallback": True}, metadata=fixture_metadata()); audit(db, correlation_id=cid(request), event_type="ASSISTED_FALLBACK_ACTIVATED", entity_type="PortalStructureFingerprint", entity_id=item.id, after={"scope": scope}, metadata=fixture_metadata())
    db.commit()
    return {"fingerprint": row(item), "assisted_fallback": status == "DRIFTED", "fixture": fixture_metadata()}


@router.get("/week9/report")
def week9_report(db: Session = Depends(get_db)):
    return {
        "label": "DEMONSTRATION BASELINE — SYNTHETIC DATA — NOT CLIENT APPROVED",
        "attachment_categories": len(db.scalars(select(AttachmentCategoryRule)).all()),
        "manifest_items": len(db.scalars(select(AttachmentManifestItem)).all()),
        "attachment_mismatches": len(db.scalars(select(AttachmentReconciliationResult).where(AttachmentReconciliationResult.status != "MATCH")).all()),
        "grid_rows_intended": len(db.scalars(select(PortalGridRowIntent)).all()),
        "grid_rows_observed": len(db.scalars(select(PortalGridRowObservation)).all()),
        "grid_matches": len(db.scalars(select(GridRowReconciliationResult).where(GridRowReconciliationResult.status == "MATCH")).all()),
        "grid_missing": len(db.scalars(select(GridRowReconciliationResult).where(GridRowReconciliationResult.status == "MISSING")).all()),
        "grid_extra": len(db.scalars(select(GridRowReconciliationResult).where(GridRowReconciliationResult.status == "EXTRA")).all()),
        "grid_ambiguous": len(db.scalars(select(GridRowReconciliationResult).where(GridRowReconciliationResult.status.in_(["DUPLICATE_KEY", "AMBIGUOUS_IDENTITY"]))).all()),
        "structure_drift": len(db.scalars(select(PortalStructureFingerprint).where(PortalStructureFingerprint.status == "DRIFTED")).all()),
        "fixture": fixture_metadata(),
    }
