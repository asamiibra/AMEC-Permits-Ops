"""Week 8 lineage, validity, revalidation, and corpus APIs."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..db import get_db
from ..fixtures.canonical import fixture_metadata
from ..models import *
from ..services.week45 import build_package, evaluate_readiness, row
from ..services.week8 import (
    ensure_project_lineage, evaluate_dependency_validity, evaluate_document_validity,
    evaluate_project_validity, impact_summary, precheck_validity, record_material_change,
    record_shadow_correction, revalidate_project, run_corpus,
)

router = APIRouter(prefix="/api")


def cid(request: Request) -> str:
    return getattr(request.state, "correlation_id", "week8-api")


def project_or_404(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.post("/material-changes/evaluate")
def material_change(payload: dict, request: Request, db: Session = Depends(get_db)):
    project_id = payload.get("project_id")
    project_or_404(db, project_id)
    ensure_project_lineage(db, project_id, cid(request))
    event = record_material_change(db, project_id=project_id, source_type=payload["source_type"], source_id=str(payload["source_id"]), previous_version_or_hash=payload.get("previous_version_or_hash"), new_version_or_hash=payload.get("new_version_or_hash"), change_type=payload.get("change_type", "UPSTREAM_CHANGED"), material=payload.get("material"), actor_or_system=payload.get("actor_or_system", "operator"), correlation_id=cid(request), metadata=payload.get("metadata", {}))
    db.commit()
    return impact_summary(db, event.id)


@router.get("/projects/{project_id}/lineage")
def project_lineage(project_id: str, db: Session = Depends(get_db)):
    project_or_404(db, project_id)
    ensure_project_lineage(db, project_id)
    db.commit()
    return {"project_id": project_id, "edges": [row(x) for x in db.scalars(select(LineageEdge).where(LineageEdge.project_id == project_id).order_by(LineageEdge.created_at, LineageEdge.id)).all()], "fixture": fixture_metadata()}


@router.get("/entities/{entity_type}/{entity_id}/lineage")
def entity_lineage(entity_type: str, entity_id: str, db: Session = Depends(get_db)):
    edges = db.scalars(select(LineageEdge).where(or_((LineageEdge.upstream_type == entity_type) & (LineageEdge.upstream_id == entity_id), (LineageEdge.downstream_type == entity_type) & (LineageEdge.downstream_id == entity_id)))).all()
    return {"entity_type": entity_type, "entity_id": entity_id, "edges": [row(x) for x in edges], "fixture": fixture_metadata()}


@router.get("/projects/{project_id}/stale-items")
def stale_items(project_id: str, db: Session = Depends(get_db)):
    project_or_404(db, project_id)
    ensure_project_lineage(db, project_id)
    reasons = db.scalars(select(StaleReason).where(StaleReason.project_id == project_id, StaleReason.cleared_at.is_(None)).order_by(StaleReason.detected_at.desc())).all()
    packages = db.scalars(select(Package).where(Package.project_id == project_id, Package.status.in_(["STALE", "SUPERSEDED"]))).all()
    revisions = db.scalars(select(PreparationRevision).where(PreparationRevision.project_id == project_id, PreparationRevision.status.in_(["STALE", "SUPERSEDED", "NEEDS_REVALIDATION"]))).all()
    return {"reasons": [row(x) for x in reasons], "packages": [row(x) for x in packages], "preparation_revisions": [row(x) for x in revisions], "fixture": fixture_metadata()}


@router.post("/projects/{project_id}/revalidate")
def revalidate(project_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    project_or_404(db, project_id)
    result = revalidate_project(db, project_id, payload.get("action", "RE_EVALUATE_READINESS"), payload.get("actor", "operator"), cid(request))
    db.commit()
    return {**result, "fixture": fixture_metadata()}


@router.get("/document-versions/{version_id}/validity")
def document_validity(version_id: str, db: Session = Depends(get_db)):
    version = db.get(DocumentVersion, version_id)
    if not version: raise HTTPException(404, "Document version not found")
    item = db.scalar(select(DocumentValidity).where(DocumentValidity.document_version_id == version_id))
    return {"validity": row(item), "document_version": row(version), "fixture": fixture_metadata()}


@router.post("/document-versions/{version_id}/validity/evaluate")
def document_validity_evaluate(version_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    try:
        item = evaluate_document_validity(db, version_id, actor=payload.get("actor", "operator"), correlation_id=cid(request), overrides=payload)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    db.commit()
    version = db.get(DocumentVersion, version_id)
    return {"validity": row(item), "staleness": stale_items(version.document.project_id, db), "fixture": fixture_metadata()}


@router.get("/dependencies/{dependency_id}/validity")
def dependency_validity(dependency_id: str, db: Session = Depends(get_db)):
    dependency = db.get(ApprovalDependency, dependency_id)
    if not dependency: raise HTTPException(404, "Approval dependency not found")
    return {"validity": row(db.scalar(select(AuthorityApprovalValidity).where(AuthorityApprovalValidity.approval_dependency_id == dependency_id))), "dependency": row(dependency), "fixture": fixture_metadata()}


@router.post("/dependencies/{dependency_id}/validity/evaluate")
def dependency_validity_evaluate(dependency_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    try:
        item = evaluate_dependency_validity(db, dependency_id, actor=payload.get("actor", "operator"), correlation_id=cid(request), overrides=payload)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    db.commit()
    dependency = db.get(ApprovalDependency, dependency_id)
    return {"validity": row(item), "staleness": stale_items(dependency.project_id, db), "fixture": fixture_metadata()}


@router.get("/projects/{project_id}/validity-dashboard")
def validity_dashboard(project_id: str, db: Session = Depends(get_db)):
    project_or_404(db, project_id)
    return {"project_id": project_id, "validity": evaluate_project_validity(db, project_id), "stale_items": stale_items(project_id, db), "fixture": fixture_metadata()}


@router.post("/projects/{project_id}/validity/evaluate")
def validity_evaluate(project_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    project_or_404(db, project_id)
    result = evaluate_project_validity(db, project_id, actor=payload.get("actor", "operator"), correlation_id=cid(request), overrides=payload.get("overrides", {}))
    db.commit()
    return {"project_id": project_id, "validity": result, "stale_items": stale_items(project_id, db), "fixture": fixture_metadata()}


@router.get("/packages/{package_id}/staleness")
def package_staleness(package_id: str, db: Session = Depends(get_db)):
    package = db.get(Package, package_id)
    if not package: raise HTTPException(404, "Package not found")
    reasons = db.scalars(select(StaleReason).where(StaleReason.target_type == "Package", StaleReason.target_id == package_id, StaleReason.cleared_at.is_(None))).all()
    return {"package": row(package), "status": package.status, "reasons": [row(x) for x in reasons], "requires_rebuild": package.status in {"STALE", "SUPERSEDED"}, "fixture": fixture_metadata()}


@router.post("/packages/{package_id}/rebuild")
def rebuild_package(package_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    old = db.get(Package, package_id)
    if not old: raise HTTPException(404, "Package not found")
    if old.status not in {"STALE", "SUPERSEDED"}: raise HTTPException(409, "PACKAGE_REBUILD_REQUIRES_STALE_PACKAGE")
    evaluation, _ = evaluate_readiness(db, old.project_id, actor=payload.get("actor", "operator"))
    if evaluation.overall_status == "BLOCKED":
        db.commit()
        raise HTTPException(409, "PACKAGE_READINESS_BLOCKED")
    replacement = build_package(db, old.project_id, created_by=payload.get("created_by", "operator"))
    ensure_project_lineage(db, old.project_id, cid(request))
    audit(db, correlation_id=cid(request), event_type="PACKAGE_REBUILT", entity_type="Package", entity_id=replacement.id, after={"replaced_package_id": old.id, "manifest_hash": replacement.manifest_hash}, metadata=fixture_metadata())
    audit(db, correlation_id=cid(request), event_type="PACKAGE_REAPPROVAL_REQUIRED", entity_type="Package", entity_id=replacement.id, after={"human_gate_required": True}, metadata=fixture_metadata())
    _ = [x for x in db.scalars(select(StaleReason).where(StaleReason.target_type == "Package", StaleReason.target_id == old.id, StaleReason.cleared_at.is_(None))).all()]
    db.commit()
    return {"replaced_package_id": old.id, "package": row(replacement), "readiness": row(evaluation), "auto_approved": False, "fixture": fixture_metadata()}


@router.get("/preparation-revisions/{revision_id}/staleness")
def revision_staleness(revision_id: str, db: Session = Depends(get_db)):
    revision = db.get(PreparationRevision, revision_id)
    if not revision: raise HTTPException(404, "Preparation revision not found")
    reasons = db.scalars(select(StaleReason).where(StaleReason.target_type == "PreparationRevision", StaleReason.target_id == revision_id, StaleReason.cleared_at.is_(None))).all()
    return {"revision": row(revision), "pinned_package_id": revision.package_id, "pinned_package_manifest_hash": revision.package_manifest_hash, "reasons": [row(x) for x in reasons], "requires_new_revision": revision.status in {"STALE", "SUPERSEDED", "NEEDS_REVALIDATION"}, "fixture": fixture_metadata()}


@router.post("/preparation-revisions/{revision_id}/supersede")
def supersede_revision(revision_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    revision = db.get(PreparationRevision, revision_id)
    if not revision: raise HTTPException(404, "Preparation revision not found")
    replacement_id = payload.get("replacement_revision_id")
    if not replacement_id: raise HTTPException(422, "REPLACEMENT_REVISION_REQUIRED")
    replacement = db.get(PreparationRevision, replacement_id)
    if not replacement or replacement.project_id != revision.project_id: raise HTTPException(422, "VALID_REPLACEMENT_REVISION_REQUIRED")
    revision.status = "SUPERSEDED"
    reasons = db.scalars(select(StaleReason).where(StaleReason.target_type == "PreparationRevision", StaleReason.target_id == revision.id, StaleReason.cleared_at.is_(None))).all()
    for reason in reasons: reason.replacement_target_id = replacement.id
    audit(db, correlation_id=cid(request), event_type="PREPARATION_REVISION_SUPERSEDED", entity_type="PreparationRevision", entity_id=revision.id, after={"replacement_revision_id": replacement.id}, metadata=fixture_metadata())
    db.commit()
    return {"revision": row(revision), "replacement": row(replacement), "pinned_fields_preserved": True, "fixture": fixture_metadata()}


@router.get("/precheck-runs/{run_id}/validity")
def precheck_run_validity(run_id: str, db: Session = Depends(get_db)):
    try: return {**precheck_validity(db, run_id), "fixture": fixture_metadata()}
    except ValueError as exc: raise HTTPException(404, str(exc))


@router.post("/corpus-runs")
def corpus_run(payload: dict, request: Request, db: Session = Depends(get_db)):
    if payload.get("project_id"): project_or_404(db, payload["project_id"])
    run = run_corpus(db, project_id=payload.get("project_id"), fixture_set=payload.get("fixture_set", "WEEK8_SYNTHETIC_CORPUS"), fixture_version=payload.get("fixture_version", "1.0"), corpus_version=payload.get("corpus_version", "1.0"), label=payload.get("label", "SYNTHETIC / NON-CONTRACTUAL"), correlation_id=cid(request))
    db.commit()
    return corpus_detail(run.id, db)


def corpus_detail(run_id: str, db: Session):
    run = db.get(CorpusRun, run_id)
    if not run: raise HTTPException(404, "Corpus run not found")
    cases = db.scalars(select(CorpusCase).where(CorpusCase.corpus_run_id == run_id).order_by(CorpusCase.case_key)).all()
    return {"run": row(run), "cases": [{"case": row(case), "result": row(db.scalar(select(CorpusCaseResult).where(CorpusCaseResult.corpus_case_id == case.id)))} for case in cases], "fixture": fixture_metadata()}


@router.get("/corpus-runs/{run_id}")
def corpus_run_detail(run_id: str, db: Session = Depends(get_db)): return corpus_detail(run_id, db)


@router.post("/projects/{project_id}/shadow-corrections")
def shadow_correction(project_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    project_or_404(db, project_id)
    item = record_shadow_correction(db, project_id, payload, cid(request)); db.commit()
    return {"correction": row(item), "fixture": fixture_metadata()}


@router.get("/projects/{project_id}/shadow-corrections")
def shadow_corrections(project_id: str, db: Session = Depends(get_db)):
    project_or_404(db, project_id)
    return {"corrections": [row(x) for x in db.scalars(select(ShadowCorrection).where(ShadowCorrection.project_id == project_id).order_by(ShadowCorrection.recorded_at.desc())).all()], "fixture": fixture_metadata()}


@router.get("/shadow-corrections")
def all_shadow_corrections(db: Session = Depends(get_db)):
    return {"corrections": [row(x) for x in db.scalars(select(ShadowCorrection).order_by(ShadowCorrection.recorded_at.desc())).all()], "fixture": fixture_metadata()}
