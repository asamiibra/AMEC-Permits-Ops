"""Deterministic Week 9 attachment/grid preparation services."""

from datetime import datetime, timezone
from pathlib import PurePath
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..fixtures.canonical import fixture_metadata
from ..models import *
from .week45 import row, stable_hash
from .week7 import create_routed_finding, resolve_finding_code
from .week8 import ensure_lineage_edge


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _rule(db: Session, scenario_id: str, category_code: str) -> AttachmentCategoryRule | None:
    return db.scalar(select(AttachmentCategoryRule).where(AttachmentCategoryRule.scenario_id == scenario_id, AttachmentCategoryRule.category_code == category_code, AttachmentCategoryRule.status == "ACTIVE"))


def _rules(db: Session, revision: PreparationRevision) -> list[AttachmentCategoryRule]:
    scenario = db.scalar(select(ScenarioConfig).where(ScenarioConfig.version == revision.scenario_version))
    if not scenario:
        scenario = db.scalar(select(ScenarioConfig).where(ScenarioConfig.scenario_code == "DEMO_BUILDING_PERMIT_V1"))
    return db.scalars(select(AttachmentCategoryRule).where(AttachmentCategoryRule.scenario_id == scenario.id, AttachmentCategoryRule.status == "ACTIVE").order_by(AttachmentCategoryRule.portal_order)).all() if scenario else []


def _is_current_revision(db: Session, revision: PreparationRevision) -> None:
    package = db.get(Package, revision.package_id) if revision.package_id else None
    if revision.status in {"STALE", "SUPERSEDED", "NEEDS_REVALIDATION"} or (package and package.status in {"STALE", "SUPERSEDED"}):
        raise ValueError("STALE_PREPARATION_REVISION_REVALIDATION_REQUIRED")


def _category_for_document(document_type: str) -> str | None:
    return {
        "TITLE_DEED": "TITLE_DEED_PROPERTY_PLAN",
        "SURVEY_PLAN": "TITLE_DEED_PROPERTY_PLAN",
        "OWNER_QID": "OWNER_REPRESENTATIVE_ID",
        "AUTHORIZATION": "OWNER_AUTHORIZATION",
        "COMMERCIAL_REGISTRATION": "COMMERCIAL_REGISTRATION",
        "COORDINATE_REPORT": "COORDINATE_REPORT",
        "DRAWING_SET": "PRELIMINARY_ARCHITECTURAL_DRAWINGS",
        "NOC": "THIRD_PARTY_NOC",
    }.get(document_type)


def _language_ok(rule: AttachmentCategoryRule, version: DocumentVersion) -> bool:
    allowed = set(rule.allowed_languages or [])
    language = (version.language or "").upper()
    if not allowed or "ANY" in allowed or "ANY_ALLOWED" in allowed:
        return True
    if rule.required_language_combination == "AR_AND_EN":
        return language in {"AR/EN", "EN/AR", "BILINGUAL"}
    if language in allowed:
        return True
    if language in {"AR/EN", "EN/AR", "BILINGUAL"} and ({"AR", "EN"} & allowed):
        return True
    return False


def _format_ok(rule: AttachmentCategoryRule, version: DocumentVersion) -> bool:
    mime = (version.mime_type or "").lower()
    extension = PurePath(version.source_filename or "").suffix.lower()
    return (not rule.allowed_mime_types or mime in {x.lower() for x in rule.allowed_mime_types}) and (not rule.allowed_extensions or extension in {x.lower() for x in rule.allowed_extensions})


def _item_status(db: Session, rule: AttachmentCategoryRule, version: DocumentVersion | None) -> tuple[str, str]:
    if not version:
        return ("BLOCKED", "No exact approved DocumentVersion is associated with this required category.") if rule.requirement_state == "REQUIRED" and rule.min_files else ("NOT_APPLICABLE", "No applicable source is selected for this category.")
    validity = db.scalar(select(DocumentValidity).where(DocumentValidity.document_version_id == version.id))
    valid_state = validity.validity_status if validity else "UNKNOWN_REVIEW_REQUIRED"
    if version.approval_state != DocumentApprovalState.APPROVED or version.superseded_by:
        return "BLOCKED", "DocumentVersion is not the current approved version."
    if validity and validity.validity_status != DocumentValidityStatus.VALID:
        return "BLOCKED", f"DocumentValidity is {validity.validity_status}."
    if not _language_ok(rule, version):
        return "BLOCKED", "Language rule is not satisfied."
    if not _format_ok(rule, version):
        return "BLOCKED", "Format or extension rule is not satisfied."
    if rule.max_file_size_bytes is not None and version.file_size > rule.max_file_size_bytes:
        return "BLOCKED", "File exceeds the configured maximum size."
    return "READY", "Exact approved, current, valid DocumentVersion satisfies category rules."


def refresh_manifest(db: Session, revision_id: str, *, actor: str = "operator", correlation_id: str = "week9-manifest") -> AttachmentManifest:
    revision = db.get(PreparationRevision, revision_id)
    if not revision:
        raise ValueError("PREPARATION_REVISION_NOT_FOUND")
    _is_current_revision(db, revision)
    package = db.get(Package, revision.package_id) if revision.package_id else None
    if not package or package.status not in {"APPROVED", "DRAFT", "READY_FOR_INTERNAL_REVIEW"}:
        raise ValueError("CURRENT_APPROVED_PACKAGE_REQUIRED")
    rules = _rules(db, revision)
    if not rules:
        raise ValueError("ATTACHMENT_CATEGORY_RULES_REQUIRED")
    manifest = db.scalar(select(AttachmentManifest).where(AttachmentManifest.package_id == package.id))
    if not manifest:
        manifest = AttachmentManifest(package_id=package.id, scenario_version=revision.scenario_version, items=[], manifest_hash="", preparation_revision_id=revision.id, manifest_version="W9-MANIFEST-1.0", generated_by=actor, status="DRAFT")
        db.add(manifest); db.flush()
    existing_v9 = db.scalars(select(AttachmentManifestItem).where(AttachmentManifestItem.attachment_manifest_id == manifest.id)).all()
    package_items = db.scalars(select(PackageItem).where(PackageItem.package_id == package.id).order_by(PackageItem.order)).all()
    by_category: dict[str, list[PackageItem]] = {}
    for item in package_items:
        category = _category_for_document(item.document_type)
        if category:
            by_category.setdefault(category, []).append(item)
    payload_items: list[dict[str, Any]] = []
    rows: list[AttachmentManifestItem] = []
    for rule in rules:
        selected = by_category.get(rule.category_code, [])
        if len(selected) < rule.min_files:
            selected = selected
        if rule.max_files is not None and len(selected) > rule.max_files:
            selected = selected
        if not selected:
            status = "BLOCKED" if rule.requirement_state == "REQUIRED" and rule.min_files else "NOT_APPLICABLE"
            payload_items.append({"category_code": rule.category_code, "category_rule_version": rule.rule_version, "requirement_state": rule.requirement_state, "document_version_id": None, "status": status})
            if not existing_v9:
                rows.append(AttachmentManifestItem(attachment_manifest_id=manifest.id, category_code=rule.category_code, category_rule_version=rule.rule_version, requirement_state=rule.requirement_state, source_reason="No applicable exact package item.", validity_state="NOT_APPLICABLE", approval_state="NOT_APPLICABLE", status=status))
            continue
        language_pair_valid = True
        if rule.required_language_combination == "AR_AND_EN":
            languages = {(x.language or "").upper() for x in (db.get(DocumentVersion, item.document_version_id) for item in selected)}
            language_pair_valid = bool({"AR", "EN"} <= languages or {"AR/EN", "EN/AR", "BILINGUAL"} & languages)
        for sequence, package_item in enumerate(selected, 1):
            version = db.get(DocumentVersion, package_item.document_version_id)
            status, reason = _item_status(db, rule, version)
            if not language_pair_valid:
                status, reason = "BLOCKED", "AR_AND_EN requires both configured language variants."
            if rule.max_files is not None and len(selected) > rule.max_files:
                status, reason = "BLOCKED", "Category maximum file count exceeded."
            logical_name = version.document.logical_name if version and version.document else None
            filename = version.source_filename if version else None
            payload_items.append({"category_code": rule.category_code, "category_rule_version": rule.rule_version, "requirement_state": rule.requirement_state, "document_id": version.document_id if version else None, "document_version_id": version.id if version else None, "file_sha256": version.sha256 if version else None, "logical_name": logical_name, "revision_label": version.revision_label if version else None, "language": version.language if version else None, "mime_type": version.mime_type if version else None, "file_size_bytes": version.file_size if version else None, "intended_portal_filename": filename, "sequence_in_category": sequence, "validity_state": "VALID" if status == "READY" else "BLOCKED", "approval_state": version.approval_state.value if version else "MISSING", "status": status})
            if not existing_v9:
                rows.append(AttachmentManifestItem(attachment_manifest_id=manifest.id, category_code=rule.category_code, category_rule_version=rule.rule_version, requirement_state=rule.requirement_state, document_id=version.document_id if version else None, document_version_id=version.id if version else None, file_sha256=version.sha256 if version else None, logical_name=logical_name, revision_label=version.revision_label if version else None, language=version.language if version else None, mime_type=version.mime_type if version else None, file_size_bytes=version.file_size if version else None, intended_portal_filename=filename, sequence_in_category=sequence, source_reason=reason, validity_state="VALID" if status == "READY" else "BLOCKED", approval_state=version.approval_state.value if version else "MISSING", status=status))
    manifest_hash = stable_hash(payload_items)
    if manifest.status == "LOCKED" and manifest.manifest_hash != manifest_hash:
        raise ValueError("LOCKED_MANIFEST_IMMUTABLE")
    if not existing_v9:
        db.add_all(rows)
    manifest.items = payload_items
    manifest.manifest_hash = manifest_hash
    manifest.preparation_revision_id = revision.id
    manifest.scenario_id = next((r.scenario_id for r in rules), None)
    manifest.scenario_version = revision.scenario_version
    manifest.manifest_version = "W9-MANIFEST-1.0"
    manifest.generated_by = actor
    manifest.status = "LOCKED" if not any(x["status"] == "BLOCKED" for x in payload_items) else "DRAFT"
    db.flush()
    ensure_lineage_edge(db, project_id=revision.project_id, upstream_type="Package", upstream_id=package.id, upstream_version_or_hash=package.manifest_hash, downstream_type="AttachmentManifest", downstream_id=manifest.id, downstream_version_or_hash=manifest.manifest_hash, dependency_kind="MANIFEST_FOR", correlation_id=correlation_id)
    for item in db.scalars(select(AttachmentManifestItem).where(AttachmentManifestItem.attachment_manifest_id == manifest.id)).all():
        if item.document_version_id:
            ensure_lineage_edge(db, project_id=revision.project_id, upstream_type="DocumentVersion", upstream_id=item.document_version_id, upstream_version_or_hash=item.file_sha256, downstream_type="AttachmentManifestItem", downstream_id=item.id, downstream_version_or_hash=item.category_rule_version, dependency_kind="INCLUDED_IN_MANIFEST", correlation_id=correlation_id)
    audit(db, correlation_id=correlation_id, event_type="ATTACHMENT_MANIFEST_REFRESHED", entity_type="AttachmentManifest", entity_id=manifest.id, after={"status": manifest.status, "manifest_hash": manifest.manifest_hash, "item_count": len(payload_items)}, metadata=fixture_metadata())
    return manifest


def manifest_items(db: Session, manifest_id: str) -> list[AttachmentManifestItem]:
    return db.scalars(select(AttachmentManifestItem).where(AttachmentManifestItem.attachment_manifest_id == manifest_id).order_by(AttachmentManifestItem.category_code, AttachmentManifestItem.sequence_in_category)).all()


def attachment_intent(db: Session, revision_id: str, payload: dict[str, Any], *, actor: str, correlation_id: str) -> AttachmentAssociationIntent:
    revision = db.get(PreparationRevision, revision_id)
    if not revision: raise ValueError("PREPARATION_REVISION_NOT_FOUND")
    _is_current_revision(db, revision)
    manifest = db.scalar(select(AttachmentManifest).where(AttachmentManifest.preparation_revision_id == revision.id)) or refresh_manifest(db, revision_id, actor=actor, correlation_id=correlation_id)
    if manifest.status != "LOCKED": raise ValueError("ATTACHMENT_MANIFEST_BLOCKED")
    version = db.get(DocumentVersion, payload.get("document_version_id"))
    if not version: raise ValueError("DOCUMENT_VERSION_NOT_FOUND")
    category = payload.get("category_code")
    item = db.scalar(select(AttachmentManifestItem).where(AttachmentManifestItem.attachment_manifest_id == manifest.id, AttachmentManifestItem.category_code == category, AttachmentManifestItem.document_version_id == version.id, AttachmentManifestItem.status == "READY"))
    if not item: raise ValueError("EXACT_MANIFEST_ITEM_REQUIRED")
    key = payload.get("idempotency_key") or f"{revision.application_id}:{revision.id}:{category}:{version.id}"
    existing = db.scalar(select(AttachmentAssociationIntent).where(AttachmentAssociationIntent.idempotency_key == key))
    if existing:
        audit(db, correlation_id=correlation_id, event_type="ATTACHMENT_ASSOCIATION_RETRY_LINKED", entity_type="AttachmentAssociationIntent", entity_id=existing.id, after={"idempotency_key": key}, metadata=fixture_metadata())
        return existing
    same_source = db.scalars(select(AttachmentAssociationIntent).where(AttachmentAssociationIntent.preparation_revision_id == revision.id, AttachmentAssociationIntent.document_version_id == version.id, AttachmentAssociationIntent.category_code != category, AttachmentAssociationIntent.status == "INTENDED")).all()
    rule = _rule(db, item.attachment_manifest_id and manifest.scenario_id, category) if manifest.scenario_id else None
    if same_source and rule and rule.reuse_policy == "SINGLE_CATEGORY_ONLY": raise ValueError("ATTACHMENT_REUSE_NOT_PERMITTED")
    intent = AttachmentAssociationIntent(application_id=revision.application_id, preparation_revision_id=revision.id, attachment_manifest_item_id=item.id, category_code=category, document_version_id=version.id, operation_type=payload.get("operation_type", "ASSOCIATE"), replaces_association_id=payload.get("replaces_association_id"), idempotency_key=key, intended_portal_filename=payload.get("intended_portal_filename") or version.source_filename, status="INTENDED", created_by=actor)
    db.add(intent); db.flush()
    ensure_lineage_edge(db, project_id=revision.project_id, upstream_type="AttachmentManifestItem", upstream_id=item.id, upstream_version_or_hash=item.file_sha256, downstream_type="AttachmentAssociationIntent", downstream_id=intent.id, downstream_version_or_hash=key, dependency_kind="ASSOCIATED_FOR_PORTAL", correlation_id=correlation_id)
    audit(db, correlation_id=correlation_id, event_type="ATTACHMENT_ASSOCIATION_INTENDED", entity_type="AttachmentAssociationIntent", entity_id=intent.id, after={"category_code": category, "document_version_id": version.id, "operation_type": intent.operation_type}, metadata=fixture_metadata())
    return intent


def _attachment_observed(snapshot: PortalSnapshot) -> list[dict[str, Any]]:
    state = snapshot.attachment_state or []
    return state if isinstance(state, list) else [{"category_code": key, "files": value if isinstance(value, list) else [value]} for key, value in state.items()]


def reconcile_attachments(db: Session, revision_id: str, snapshot: PortalSnapshot, *, actor: str, correlation_id: str) -> list[AttachmentReconciliationResult]:
    revision = db.get(PreparationRevision, revision_id)
    manifest = db.scalar(select(AttachmentManifest).where(AttachmentManifest.preparation_revision_id == revision_id))
    if not revision or not manifest: raise ValueError("ATTACHMENT_MANIFEST_AND_REVISION_REQUIRED")
    intents = db.scalars(select(AttachmentAssociationIntent).where(AttachmentAssociationIntent.preparation_revision_id == revision_id, AttachmentAssociationIntent.status == "INTENDED")).all()
    observed = _attachment_observed(snapshot)
    by_category = {x.get("category_code"): x.get("files", []) for x in observed}
    results: list[AttachmentReconciliationResult] = []
    matched_observed_ids: set[str] = set()
    for intent in intents:
        version = db.get(DocumentVersion, intent.document_version_id)
        expected = {"category_code": intent.category_code, "document_version_id": intent.document_version_id, "filename": intent.intended_portal_filename, "size": version.file_size if version else None, "sha256": version.sha256 if version else None}
        files = by_category.get(intent.category_code, [])
        matches = [f for f in files if f.get("filename") == intent.intended_portal_filename or f.get("document_version_id") == intent.document_version_id]
        wrong_category = [(category, file) for category, values in by_category.items() for file in values if category != intent.category_code and (file.get("filename") == intent.intended_portal_filename or file.get("document_version_id") == intent.document_version_id)]
        if wrong_category:
            status, reason = "WRONG_CATEGORY", "Exact file was observed under a different portal category."
        elif not matches:
            status, reason = "MISSING", "Association was intended but no matching file was observed after reopen."
        elif len(matches) > 1:
            status, reason = "DUPLICATE", "More than one matching file was observed in the category."
        elif matches[0].get("filename") != intent.intended_portal_filename:
            status, reason = "WRONG_FILE", "Observed filename does not match intended file."
        elif version and matches[0].get("size") is not None and matches[0].get("size") != version.file_size:
            status, reason = "WRONG_SIZE", "Observed file size does not match the approved source version."
        else:
            matched_observed_ids.add(matches[0].get("id") or "")
            status, reason = "MATCH", "Persisted category, file identity, and size match the intended association."
        result = AttachmentReconciliationResult(preparation_revision_id=revision_id, manifest_item_id=intent.attachment_manifest_item_id, category_code=intent.category_code, document_version_id=intent.document_version_id, expected=expected, observed=matches[0] if matches else wrong_category[0][1] if wrong_category else None, status=status, severity="BLOCKING" if status != "MATCH" else "NONE", reason=reason, evidence_id=snapshot.id)
        db.add(result); db.flush(); results.append(result)
        evidence = AttachmentPersistenceEvidence(application_id=revision.application_id, preparation_revision_id=revision_id, category_code=intent.category_code, document_version_id=intent.document_version_id, expected_filename=intent.intended_portal_filename, expected_size=version.file_size if version else None, observed_filename=(matches[0].get("filename") if matches else None), observed_size=(matches[0].get("size") if matches else None), observed_category_code=(wrong_category[0][0] if wrong_category else intent.category_code if matches else None), capture_method=snapshot.capture_method, post_save_state_hash=snapshot.snapshot_hash, reopened_state_hash=snapshot.snapshot_hash, result="PERSISTED_MATCH" if status == "MATCH" else "MISSING_AFTER_SAVE" if status == "MISSING" else status, evidence_artifact_id=snapshot.id, verified_by=actor, verified_at=now_utc())
        db.add(evidence); db.flush()
        ensure_lineage_edge(db, project_id=revision.project_id, upstream_type="AttachmentAssociationIntent", upstream_id=intent.id, upstream_version_or_hash=intent.idempotency_key, downstream_type="AttachmentPersistenceEvidence", downstream_id=evidence.id, downstream_version_or_hash=snapshot.snapshot_hash, dependency_kind="PERSISTENCE_EVIDENCE", correlation_id=correlation_id)
        if status != "MATCH":
            _exception(db, revision, f"ATTACHMENT_{'WRONG_CATEGORY' if status == 'WRONG_CATEGORY' else 'MISSING_AFTER_SAVE' if status == 'MISSING' else status}", result.expected, result.observed, snapshot.id, correlation_id)
    expected_categories = {x.category_code for x in intents}
    for category, files in by_category.items():
        for file in files:
            if category not in expected_categories or not any(file.get("filename") == intent.intended_portal_filename and category == intent.category_code for intent in intents):
                extra = AttachmentReconciliationResult(preparation_revision_id=revision_id, manifest_item_id=None, category_code=category or "UNKNOWN", document_version_id=file.get("document_version_id"), expected=None, observed=file, status="EXTRA" if category in expected_categories else "CATEGORY_UNEXPECTED", severity="BLOCKING", reason="Observed portal attachment has no exact intended association.", evidence_id=snapshot.id)
                db.add(extra); db.flush(); _exception(db, revision, "ATTACHMENT_EXTRA", None, file, snapshot.id, correlation_id)
    if any(x.status != "MATCH" for x in results):
        revision.status = "IN_PREPARATION"
    audit(db, correlation_id=correlation_id, event_type="ATTACHMENT_PERSISTENCE_VERIFIED" if all(x.status == "MATCH" for x in results) else "ATTACHMENT_PERSISTENCE_FAILED", entity_type="PreparationRevision", entity_id=revision_id, after={"result_count": len(results), "mismatch_count": sum(x.status != "MATCH" for x in results)}, metadata=fixture_metadata())
    return results


def _exception(db: Session, revision: PreparationRevision, exception_type: str, expected: Any, observed: Any, evidence: str, correlation_id: str) -> MunicipalityPreparationException:
    exception = MunicipalityPreparationException(application_id=revision.application_id, preparation_revision_id=revision.id, exception_type=exception_type, severity="BLOCKING", expected=expected, observed=observed, evidence=[evidence], owner="Permit Preparer", status="OPEN")
    db.add(exception); db.flush()
    application = db.get(PermitApplication, revision.application_id); project = db.get(Project, revision.project_id)
    if application and project and resolve_finding_code(db, exception_type, FindingSourceType.PORTAL_VALIDATION):
        try:
            create_routed_finding(db, project=project, application=application, source_type=FindingSourceType.PORTAL_VALIDATION, source_channel="SYNTHETIC_PORTAL", source_reference=f"week9://{exception.id}", raw_text=exception_type, title=exception_type.replace("_", " "), severity="BLOCKING", blocking=True, finding_code=exception_type, preparation_revision_id=revision.id, evidence_artifact_id=evidence, correlation_id=correlation_id)
        except (ValueError, KeyError):
            pass
    audit(db, correlation_id=correlation_id, event_type="ATTACHMENT_CATEGORY_MISMATCH" if "WRONG_CATEGORY" in exception_type else "PORTAL_VALIDATION_EXCEPTION_CREATED", entity_type="MunicipalityPreparationException", entity_id=exception.id, after={"exception_type": exception_type, "evidence": evidence}, metadata=fixture_metadata())
    return exception


def canonical_row(row_data: dict[str, Any], sequence: int) -> dict[str, Any]:
    row_type = row_data.get("row_type", "BUILDING")
    row_type = {"BUILDINGS": "BUILDING", "FLOORS": "FLOOR", "UNITS": "UNIT"}.get(str(row_type).upper(), str(row_type).upper())
    canonical_id = row_data.get("canonical_row_id") or row_data.get("canonical_id") or row_data.get("building_ref") or row_data.get("floor_ref") or row_data.get("unit_ref")
    parent = row_data.get("parent_canonical_row_id") or row_data.get("building_ref") if row_type.upper() != "BUILDING" else None
    if row_type.upper() == "FLOOR":
        business_key = f"{row_data.get('building_ref')}::{row_data.get('floor_ref') or canonical_id}"
    elif row_type.upper() == "UNIT":
        business_key = f"{row_data.get('building_ref')}::{row_data.get('floor_ref')}::{row_data.get('unit_ref') or canonical_id}"
    else:
        business_key = str(row_data.get("business_key") or row_data.get("building_ref") or canonical_id)
    target = row_data.get("target_values", row_data)
    return {"row_type": row_type, "canonical_row_id": str(canonical_id), "parent_canonical_row_id": parent, "business_key": business_key, "target_values": target, "source_entity_version": row_data.get("source_entity_version") or row_data.get("source_hash"), "intended_sequence": sequence, "row_hash": stable_hash({"row_type": row_type, "canonical_row_id": canonical_id, "parent": parent, "business_key": business_key, "target_values": target})}


def ensure_grid_intents(db: Session, revision_id: str, *, grid_code: str = "BUILDING_FLOOR_UNIT", correlation_id: str = "week9-grid") -> list[PortalGridRowIntent]:
    revision = db.get(PreparationRevision, revision_id)
    if not revision: raise ValueError("PREPARATION_REVISION_NOT_FOUND")
    _is_current_revision(db, revision)
    existing = db.scalars(select(PortalGridRowIntent).where(PortalGridRowIntent.preparation_revision_id == revision_id, PortalGridRowIntent.grid_code == grid_code).order_by(PortalGridRowIntent.intended_sequence)).all()
    if existing: return existing
    intended = db.scalar(select(PortalIntendedState).where(PortalIntendedState.preparation_revision_id == revision_id))
    snapshot = db.scalar(select(PreparationSnapshot).where(PreparationSnapshot.preparation_revision_id == revision_id))
    rows_data = intended.repeating_rows if intended and intended.repeating_rows else snapshot.repeating_rows if snapshot else []
    rows = []
    for sequence, data in enumerate(rows_data or [], 1):
        normalized = canonical_row(data, sequence)
        rows.append(PortalGridRowIntent(preparation_revision_id=revision_id, row_type=normalized["row_type"], canonical_row_id=normalized["canonical_row_id"], parent_canonical_row_id=normalized["parent_canonical_row_id"], business_key=normalized["business_key"], target_values=normalized["target_values"], rendering_rule_versions=[revision.rendering_config_version], source_entity_version=normalized["source_entity_version"], intended_sequence=sequence, row_hash=normalized["row_hash"], status="INTENDED", grid_code=grid_code))
    db.add_all(rows); db.flush()
    for item in rows:
        ensure_lineage_edge(db, project_id=revision.project_id, upstream_type="PreparationRevision", upstream_id=revision.id, upstream_version_or_hash=revision.package_manifest_hash, downstream_type="PortalGridRowIntent", downstream_id=item.id, downstream_version_or_hash=item.row_hash, dependency_kind="GRID_INTENT", correlation_id=correlation_id)
        audit(db, correlation_id=correlation_id, event_type="GRID_INTENT_CREATED", entity_type="PortalGridRowIntent", entity_id=item.id, after={"canonical_row_id": item.canonical_row_id, "business_key": item.business_key}, metadata=fixture_metadata())
    return rows


def observe_grid(db: Session, revision_id: str, snapshot: PortalSnapshot, observed_rows: list[dict[str, Any]], *, grid_code: str, correlation_id: str) -> list[PortalGridRowObservation]:
    observations = []
    for sequence, data in enumerate(observed_rows, 1):
        normalized = canonical_row(data, sequence)
        item = PortalGridRowObservation(portal_snapshot_id=snapshot.id, grid_code=grid_code, portal_row_id=data.get("portal_row_id"), observed_sequence=sequence, observed_values=data.get("observed_values", data), observed_business_key=data.get("business_key") or normalized["business_key"], row_hash=stable_hash(data.get("observed_values", data)))
        db.add(item); observations.append(item)
    db.flush()
    audit(db, correlation_id=correlation_id, event_type="GRID_STATE_CAPTURED", entity_type="PortalSnapshot", entity_id=snapshot.id, after={"grid_code": grid_code, "row_count": len(observations)}, metadata=fixture_metadata())
    return observations


def reconcile_grid(db: Session, revision_id: str, snapshot: PortalSnapshot, *, grid_code: str, correlation_id: str) -> GridReconciliationRun:
    revision = db.get(PreparationRevision, revision_id)
    intents = ensure_grid_intents(db, revision_id, grid_code=grid_code, correlation_id=correlation_id)
    observations = db.scalars(select(PortalGridRowObservation).where(PortalGridRowObservation.portal_snapshot_id == snapshot.id, PortalGridRowObservation.grid_code == grid_code).order_by(PortalGridRowObservation.observed_sequence)).all()
    if not observations:
        observations = observe_grid(db, revision_id, snapshot, snapshot.grid_state if isinstance(snapshot.grid_state, list) else [], grid_code=grid_code, correlation_id=correlation_id)
    by_key: dict[str, list[PortalGridRowObservation]] = {}
    for item in observations:
        if item.observed_business_key: by_key.setdefault(item.observed_business_key, []).append(item)
    used: set[str] = set(); results: list[GridRowReconciliationResult] = []
    for intent in intents:
        matches = by_key.get(intent.business_key or "", [])
        if len(matches) > 1:
            status, observation, diffs = "DUPLICATE_KEY", None, []
        elif len(matches) == 0:
            keyless = [x for x in observations if not x.observed_business_key and x.id not in used]
            status, observation, diffs = ("AMBIGUOUS_IDENTITY", keyless[0], []) if keyless else ("MISSING", None, [])
            if observation: used.add(observation.id)
        else:
            observation = matches[0]; used.add(observation.id); diffs = []
            observed_values = observation.observed_values or {}; expected_values = intent.target_values or {}
            for field in sorted(set(expected_values) | set(observed_values)):
                expected, observed = expected_values.get(field), observed_values.get(field)
                if expected != observed:
                    diffs.append({"field_code": field, "expected": expected, "observed": observed, "normalized_expected": expected, "normalized_observed": observed, "status": "MISMATCH"})
            expected_parent = intent.parent_canonical_row_id or (intent.target_values or {}).get("building_ref") if intent.row_type.upper() != "BUILDING" else None
            observed_parent = (observed_values.get("parent_canonical_row_id") or observed_values.get("building_ref")) if intent.row_type.upper() != "BUILDING" else None
            if observed_parent and expected_parent and str(observed_parent) != str(expected_parent): status = "PARENT_MISMATCH"
            else: status = "FIELD_MISMATCH" if diffs else "MATCH"
        results.append(GridRowReconciliationResult(run_id="pending", canonical_row_id=intent.canonical_row_id, portal_row_id=observation.portal_row_id if observation else None, business_key=intent.business_key, status=status, field_diffs=diffs, severity="BLOCKING" if status != "MATCH" else "NONE", evidence=[snapshot.id]))
    for observation in observations:
        if observation.id not in used:
            results.append(GridRowReconciliationResult(run_id="pending", canonical_row_id=None, portal_row_id=observation.portal_row_id, business_key=observation.observed_business_key, status="EXTRA", field_diffs=[], severity="BLOCKING", evidence=[snapshot.id]))
    run = GridReconciliationRun(preparation_revision_id=revision_id, portal_snapshot_id=snapshot.id, grid_code=grid_code, intended_row_count=len(intents), observed_row_count=len(observations), matched_count=sum(x.status == "MATCH" for x in results), missing_count=sum(x.status == "MISSING" for x in results), extra_count=sum(x.status == "EXTRA" for x in results), mismatch_count=sum(x.status in {"FIELD_MISMATCH", "PARENT_MISMATCH"} for x in results), ambiguous_count=sum(x.status in {"DUPLICATE_KEY", "AMBIGUOUS_IDENTITY"} for x in results), result="MATCH" if all(x.status == "MATCH" for x in results) else "FINDINGS")
    db.add(run); db.flush()
    for result in results:
        result.run_id = run.id; db.add(result); db.flush()
        for diff in result.field_diffs:
            db.add(GridFieldDiff(row_result_id=result.id, field_code=diff["field_code"], expected=diff["expected"], observed=diff["observed"], normalized_expected=diff["normalized_expected"], normalized_observed=diff["normalized_observed"], tolerance_rule_version=None, status=diff["status"]))
        if result.status != "MATCH":
            _exception(db, revision, f"GRID_{result.status}", {"canonical_row_id": result.canonical_row_id, "business_key": result.business_key}, result.field_diffs, snapshot.id, correlation_id)
    db.flush(); audit(db, correlation_id=correlation_id, event_type="GRID_RECONCILIATION_COMPLETED", entity_type="GridReconciliationRun", entity_id=run.id, after={"result": run.result, "missing": run.missing_count, "extra": run.extra_count, "mismatch": run.mismatch_count, "ambiguous": run.ambiguous_count}, metadata=fixture_metadata())
    ensure_lineage_edge(db, project_id=revision.project_id, upstream_type="PortalGridRowIntent", upstream_id=intents[0].id if intents else revision.id, upstream_version_or_hash=None, downstream_type="GridReconciliationRun", downstream_id=run.id, downstream_version_or_hash=None, dependency_kind="GRID_RECONCILIATION", correlation_id=correlation_id)
    return run


def reconcile_portal_derived(db: Session, revision_id: str, payload: dict[str, Any], *, correlation_id: str) -> PortalDerivedFieldReconciliation:
    revision = db.get(PreparationRevision, revision_id)
    if not revision: raise ValueError("PREPARATION_REVISION_NOT_FOUND")
    expected, observed = payload.get("expected_office_value"), payload.get("observed_portal_value")
    source_mode = payload.get("source_mode", "PORTAL_DERIVED")
    if source_mode not in {"PORTAL_DERIVED", "AUTHORITY_OWNED"}: raise ValueError("PORTAL_SOURCE_MODE_REQUIRED")
    if observed == expected:
        result, action = "MATCH", "ACCEPT_AS_PORTAL_FACT" if source_mode == "PORTAL_DERIVED" else "KEEP_OFFICE_FACT"
    elif source_mode == "PORTAL_DERIVED":
        result, action = "LEGITIMATE_SOURCE_DIFFERENCE", "KEEP_OFFICE_FACT"
    else:
        result, action = "CONFLICT_NEEDS_REVIEW", "CREATE_CONFLICT"
    item = PortalDerivedFieldReconciliation(preparation_revision_id=revision_id, portal_field_code=payload["portal_field_code"], semantic_field_code=payload["semantic_field_code"], purpose=payload.get("purpose", "RECONCILIATION"), expected_office_value=expected, observed_portal_value=observed, source_mode=source_mode, field_authority_rule_version=payload.get("field_authority_rule_version", revision.field_authority_version), target_rendering_rule_version=payload.get("target_rendering_rule_version", revision.rendering_config_version), result=result, action=action, evidence=payload.get("evidence", []))
    db.add(item); db.flush(); audit(db, correlation_id=correlation_id, event_type="PORTAL_DERIVED_FIELD_RECONCILED", entity_type="PortalDerivedFieldReconciliation", entity_id=item.id, after={"result": result, "action": action, "canonical_overwrite": False}, metadata=fixture_metadata())
    if result == "CONFLICT_NEEDS_REVIEW": audit(db, correlation_id=correlation_id, event_type="PORTAL_DERIVED_CONFLICT_CREATED", entity_type="PortalDerivedFieldReconciliation", entity_id=item.id, after={"portal_field_code": item.portal_field_code}, metadata=fixture_metadata())
    return item
