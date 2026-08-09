"""Deterministic Week 4–5 package and assisted-preparation workflows."""

from datetime import date, datetime, timezone
import hashlib
import json
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from fastapi.encoders import jsonable_encoder

from ..adapters.excel.adapter import MockExcelAdapter, WorkbookLockedError
from ..audit.service import audit
from ..config.settings import repo_root
from ..fixtures.canonical import CANONICAL_PROJECTION_SHEET, CANONICAL_WORKBOOK, fixture_metadata
from ..models import *
from .configuration import evaluate_drawing_controls, scenario
from .rendering import render_target_value
from .configuration_lineage import ensure_configuration_bundle


def stable_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def row(item: Any) -> dict[str, Any] | None:
    if item is None:
        return None
    result = {}
    for column in item.__table__.columns:
        value = getattr(item, column.name)
        result[column.name] = value.value if hasattr(value, "value") else value
    return jsonable_encoder(result)


def current_assertions(db: Session, project_id: str) -> dict[str, VerifiedAssertion]:
    result = {}
    for assertion in db.scalars(select(VerifiedAssertion).where(VerifiedAssertion.project_id == project_id, VerifiedAssertion.status == AssertionStatus.CURRENT)).all():
        field = db.get(FieldDefinition, assertion.field_definition_id)
        if field:
            result[field.field_code] = assertion
    return result


def package_definition(db: Session) -> MinimumPackageDefinition:
    definition = db.scalar(select(MinimumPackageDefinition).where(MinimumPackageDefinition.status == "ACTIVE").order_by(MinimumPackageDefinition.version.desc()))
    if not definition:
        raise ValueError("MINIMUM_PACKAGE_DEFINITION_REQUIRED")
    return definition


def evaluate_readiness(db: Session, project_id: str, *, preparation_revision_id: str | None = None, actor: str = "permitops-system") -> tuple[PackageReadinessEvaluation, list[ReadinessResultItem]]:
    project = db.get(Project, project_id)
    if not project:
        raise ValueError("PROJECT_NOT_FOUND")
    definition = package_definition(db)
    cfg = scenario(db)
    config_bundle = ensure_configuration_bundle(db, cfg.id)
    assertions = current_assertions(db, project_id)
    items: list[dict[str, Any]] = []

    for code in definition.required_field_codes:
        assertion = assertions.get(code)
        items.append({"requirement_code": f"FIELD_{code}", "category": "FIELD", "status": "PASS" if assertion else "BLOCKED", "severity": "BLOCKING", "reason": "Current VerifiedAssertion is present." if assertion else "No current VerifiedAssertion exists for this required field.", "evidence_refs": [assertion.id] if assertion else [], "related_entity_refs": [project_id]})

    document_rules = definition.required_document_rules
    for rule in document_rules:
        docs = db.scalars(select(Document).where(Document.project_id == project_id, Document.document_type == rule["document_type"])).all()
        version = None
        if docs:
            current_ids = [d.current_version_id for d in docs if d.current_version_id]
            if current_ids:
                version = db.get(DocumentVersion, current_ids[0])
        validity = db.scalar(select(DocumentValidity).where(DocumentValidity.document_version_id == version.id)) if version else None
        valid = bool(version and version.approval_state == DocumentApprovalState.APPROVED and (not version.valid_until or version.valid_until >= date.today()) and version.approval_state not in {DocumentApprovalState.SUPERSEDED, DocumentApprovalState.WORKING} and (not validity or validity.validity_status == DocumentValidityStatus.VALID))
        reason = "Current approved, non-expired document version selected." if valid else "Required document is missing, not APPROVED, superseded, or expired."
        items.append({"requirement_code": rule["requirement_code"], "category": "DOCUMENT", "status": "PASS" if valid else "BLOCKED", "severity": "BLOCKING" if rule.get("blocking", True) else "WARNING", "reason": reason, "evidence_refs": [version.id] if version else [], "related_entity_refs": [project_id]})

    for rule in definition.required_dependency_rules:
        dependency = db.scalar(select(ApprovalDependency).where(ApprovalDependency.project_id == project_id, ApprovalDependency.dependency_type == rule["dependency_type"]).order_by(ApprovalDependency.valid_until.desc().nullslast()))
        dependency_validity = db.scalar(select(AuthorityApprovalValidity).where(AuthorityApprovalValidity.approval_dependency_id == dependency.id)) if dependency else None
        valid = bool(dependency and dependency.status == "CURRENT" and (not dependency.valid_until or dependency.valid_until >= date.today()) and (not dependency_validity or dependency_validity.status == "VALID"))
        items.append({"requirement_code": rule["dependency_type"], "category": "DEPENDENCY", "status": "PASS" if valid else "BLOCKED", "severity": "BLOCKING" if rule.get("blocking", True) else "WARNING", "reason": "Dependency is current and valid." if valid else "Dependency is absent, expired, revoked, superseded, or needs review.", "evidence_refs": [dependency.id] if dependency else [], "related_entity_refs": [project_id]})

    credential = db.scalar(select(ProfessionalCredential).where(ProfessionalCredential.project_id == project_id).order_by(ProfessionalCredential.valid_until.desc().nullslast()))
    credential_valid = bool(credential and credential.status == "CURRENT" and (not credential.valid_from or credential.valid_from.date() <= date.today()) and (not credential.valid_until or credential.valid_until.date() >= date.today()))
    items.append({"requirement_code": "PROFESSIONAL_VALIDITY", "category": "PROFESSIONAL", "status": "PASS" if credential_valid else "BLOCKED", "severity": "BLOCKING", "reason": "Responsible Engineer credential is current." if credential_valid else "Responsible Engineer credential is missing or invalid.", "evidence_refs": [credential.id] if credential else [], "related_entity_refs": [project_id]})
    office = db.get(ConsultancyOffice, project.office_id)
    office_credential = db.scalar(select(OfficeCredential).where(OfficeCredential.office_id == project.office_id, OfficeCredential.status == "CURRENT").order_by(OfficeCredential.valid_until.desc().nullslast()))
    office_valid = bool(office_credential and (not office_credential.valid_from or office_credential.valid_from.date() <= date.today()) and (not office_credential.valid_until or office_credential.valid_until.date() >= date.today()))
    items.append({"requirement_code": "OFFICE_CREDENTIAL_VALIDITY", "category": "PROFESSIONAL", "status": "PASS" if office_valid else "BLOCKED", "severity": "BLOCKING", "reason": "Consultancy office credential is current." if office_valid else "Consultancy office credential is missing or invalid.", "evidence_refs": [office_credential.id] if office_credential else [], "related_entity_refs": [office.id] if office else [project_id]})

    property_record = db.scalar(select(Property).where(Property.project_id == project_id))
    ownerships = db.scalars(select(PropertyOwnership).where(PropertyOwnership.property_id == property_record.id)).all() if property_record else []
    ownership_valid = bool(property_record and len(ownerships) >= 2 and abs(sum(x.normalized_share for x in ownerships) - 1.0) < 1e-9)
    items.append({"requirement_code": "MULTI_OWNER_PROPERTY", "category": "FIELD", "status": "PASS" if ownership_valid else "BLOCKED", "severity": "BLOCKING", "reason": "Property, multiple owners, and ownership shares are preserved." if ownership_valid else "Property ownership/share semantics are incomplete.", "evidence_refs": [property_record.id] if property_record else [], "related_entity_refs": [x.id for x in ownerships]})
    representations = db.scalars(select(Representation).where(Representation.principal_party_id.in_([x.party_id for x in ownerships]))).all() if ownerships else []
    representation_valid = bool(representations and all(r.status == AuthorizationStatus4.VALID and (not r.valid_until or r.valid_until >= date.today()) and r.evidence_document_version_id for r in representations))
    items.append({"requirement_code": "REPRESENTATION_VALIDITY", "category": "VALIDITY", "status": "PASS" if representation_valid else "BLOCKED", "severity": "BLOCKING", "reason": "Representative authorization is separate, evidenced, and current." if representation_valid else "Required representative authorization is missing, expired, revoked, or lacks evidence.", "evidence_refs": [r.evidence_document_version_id for r in representations if r.evidence_document_version_id], "related_entity_refs": [r.id for r in representations]})

    for control in evaluate_drawing_controls(db, project_id):
        status = "PASS" if control["result"] == "PASS" else ("BLOCKED" if control["result"] == "FAIL" else "WARNING")
        items.append({"requirement_code": control["control_code"], "category": "DRAWING_METADATA", "status": status, "severity": "BLOCKING" if control["blocking"] and status == "BLOCKED" else "WARNING", "reason": f"Drawing control result: {control['result']}", "evidence_refs": [], "related_entity_refs": [project_id]})

    for conflict in db.scalars(select(Conflict).where(Conflict.project_id == project_id, Conflict.severity == ConflictSeverity.CRITICAL, Conflict.status.in_([ConflictStatus.OPEN, ConflictStatus.BLOCKED]))).all():
        items.append({"requirement_code": "CRITICAL_CONFLICT", "category": "CONFLICT", "status": "BLOCKED", "severity": "BLOCKING", "reason": conflict.reason, "evidence_refs": conflict.observation_ids_json, "related_entity_refs": [conflict.id]})

    blockers = sum(1 for item in items if item["status"] == "BLOCKED" and item["severity"] == "BLOCKING")
    warnings = sum(1 for item in items if item["status"] == "WARNING")
    status = "BLOCKED" if blockers else ("READY_WITH_NONBLOCKING_WARNINGS" if warnings else "READY")
    input_hash = stable_hash({"project": project_id, "assertions": {k: v.id for k, v in assertions.items()}, "documents": [(d.id, d.current_version_id) for d in db.scalars(select(Document).where(Document.project_id == project_id)).all()], "definition": definition.version})
    normalized_items = [{k: value for k, value in item.items()} for item in items]
    result_hash = stable_hash(normalized_items)
    rules = ApplicableRuleSet(project_id=project_id, preparation_revision_id=preparation_revision_id, scenario_version=cfg.version, requirement_config_version=definition.version, evaluated_by_system_version="WEEK45-READINESS-1.0", input_snapshot_hash=input_hash, result_hash=result_hash, status=status, configuration_bundle_id=config_bundle.id, configuration_checksum=config_bundle.checksum)
    db.add(rules); db.flush()
    evaluation = PackageReadinessEvaluation(project_id=project_id, preparation_revision_id=preparation_revision_id, minimum_package_definition_version=definition.version, applicable_rule_set_id=rules.id, overall_status=status, blocker_count=blockers, warning_count=warnings, result_hash=result_hash, configuration_bundle_id=config_bundle.id)
    db.add(evaluation); db.flush()
    result_items = [ReadinessResultItem(evaluation_id=evaluation.id, **item) for item in normalized_items]
    db.add_all(result_items); db.flush()
    audit(db, correlation_id=f"readiness-{evaluation.id}", event_type="READINESS_EVALUATED", entity_type="PackageReadinessEvaluation", entity_id=evaluation.id, after={"status": status, "blockers": blockers, "warnings": warnings, "result_hash": result_hash}, metadata=fixture_metadata())
    audit(db, correlation_id=f"readiness-{evaluation.id}", event_type="READINESS_BLOCKED" if blockers else "READINESS_READY", entity_type="Project", entity_id=project_id, after={"status": status}, metadata=fixture_metadata())
    return evaluation, result_items


def latest_evaluation(db: Session, project_id: str) -> PackageReadinessEvaluation | None:
    return db.scalar(select(PackageReadinessEvaluation).where(PackageReadinessEvaluation.project_id == project_id).order_by(PackageReadinessEvaluation.evaluated_at.desc()))


def build_package(db: Session, project_id: str, created_by: str = "synthetic-preparer") -> Package:
    evaluation = latest_evaluation(db, project_id)
    if not evaluation or evaluation.overall_status not in {"READY", "READY_WITH_NONBLOCKING_WARNINGS"}:
        raise ValueError("PACKAGE_READINESS_REQUIRED")
    definition = package_definition(db)
    versions: list[tuple[DocumentVersion, str]] = []
    for doc_type, category in [(DocumentType.TITLE_DEED, "TITLE_DEED"), (DocumentType.OWNER_QID, "OWNER_ID"), (DocumentType.DRAWING_SET, "ARCHITECTURAL_DRAWING")]:
        document = db.scalar(select(Document).where(Document.project_id == project_id, Document.document_type == doc_type))
        version = db.get(DocumentVersion, document.current_version_id) if document and document.current_version_id else None
        if not version or version.approval_state != DocumentApprovalState.APPROVED:
            raise ValueError("APPROVED_CURRENT_DOCUMENT_REQUIRED")
        versions.append((version, category))
    truth = {"assertions": {k: v.semantic_value_json for k, v in current_assertions(db, project_id).items()}, "versions": [(v.id, v.sha256) for v, _ in versions]}
    package = Package(project_id=project_id, package_definition_version=definition.version, status="DRAFT", created_by=created_by, source_truth_hash=stable_hash(truth), configuration_bundle_id=evaluation.configuration_bundle_id)
    db.add(package); db.flush()
    items = []
    for order, (version, category) in enumerate(versions, 1):
        item = PackageItem(package_id=package.id, document_version_id=version.id, document_type=version.document.document_type.value, attachment_category_code=category, file_sha256=version.sha256, revision=version.revision_label, approval_state=version.approval_state.value, validity_state="CURRENT", source_reason="Selected by configured category/document-type rule from current approved version.", order=order)
        db.add(item); db.flush(); items.append(item)
    manifest_items = [{"document_version_id": i.document_version_id, "document_type": i.document_type, "category": i.attachment_category_code, "sha256": i.file_sha256, "revision": i.revision, "approval_state": i.approval_state, "validity_state": i.validity_state, "order": i.order} for i in items]
    manifest_hash = stable_hash(manifest_items)
    db.add(AttachmentManifest(package_id=package.id, scenario_version=scenario(db).version, items=manifest_items, manifest_hash=manifest_hash))
    package.manifest_hash = manifest_hash
    audit(db, correlation_id=f"package-{package.id}", event_type="PACKAGE_CREATED", entity_type="Package", entity_id=package.id, after={"status": package.status, "source_truth_hash": package.source_truth_hash}, metadata=fixture_metadata())
    audit(db, correlation_id=f"package-{package.id}", event_type="PACKAGE_MANIFEST_GENERATED", entity_type="Package", entity_id=package.id, after={"manifest_hash": manifest_hash, "item_count": len(items)}, metadata=fixture_metadata())
    db.flush()
    return package


def snapshot_for_revision(db: Session, revision: PreparationRevision) -> PreparationSnapshot:
    assertions = current_assertions(db, revision.project_id)
    app = db.get(PermitApplication, revision.application_id)
    cfg = db.scalar(select(MunicipalityConfig).limit(1))
    fields: dict[str, Any] = {}
    rendered: dict[str, Any] = {}
    for spec in (cfg.fields_json if cfg else []):
        key = spec.get("field_key")
        code = {"plot_number": "PROPERTY.PLOT_NUMBER", "owner_name": "OWNER.NAME_EN"}.get(key)
        canonical = assertions.get(code).semantic_value_json.get("value") if code and assertions.get(code) else (app.permit_type if key == "permit_type" else app.municipality if key == "municipality" else None)
        fields[key] = {"portal_tab": spec.get("tab"), "label": spec.get("label"), "canonical_value": canonical, "source_assertion_id": assertions.get(code).id if code and assertions.get(code) else None, "source_mode": spec.get("source_mode"), "required": spec.get("required", False), "editable": spec.get("editable", True), "portal_order": spec.get("portal_order")}
        rendered[key] = canonical
    rows = [{"row_type": "buildings", "canonical_row_id": "building-1", "target_values": {"building_ref": "building-1", "building_type": "VILLA", "floors": 2, "use": "RESIDENTIAL"}}, {"row_type": "floors", "canonical_row_id": "building-1-floor-1", "target_values": {"building_ref": "building-1", "floor_ref": "floor-1", "floor_type": "GROUND", "area": 250}}]
    package_items = db.scalars(select(PackageItem).where(PackageItem.package_id == revision.package_id).order_by(PackageItem.order)).all() if revision.package_id else []
    attachments = [{"category": i.attachment_category_code, "document_version_id": i.document_version_id, "sha256": i.file_sha256, "revision": i.revision, "approval_state": i.approval_state, "validity_state": i.validity_state, "status": "NOT_ENTERED"} for i in package_items]
    payload = {"fields": fields, "rendered": rendered, "rows": rows, "attachments": attachments, "dependencies": [row(d) for d in db.scalars(select(ApprovalDependency).where(ApprovalDependency.project_id == revision.project_id)).all()]}
    snapshot = PreparationSnapshot(preparation_revision_id=revision.id, verified_field_values=fields, rendered_target_values=rendered, repeating_rows=rows, attachment_manifest=attachments, dependency_state=payload["dependencies"], human_gate_state={"data_verification": "PENDING", "technical_review": "PENDING", "package_approval": "PASS"}, snapshot_hash=stable_hash(payload))
    db.add(snapshot); db.flush()
    audit(db, correlation_id=f"revision-{revision.id}", event_type="PREPARATION_SNAPSHOT_CREATED", entity_type="PreparationSnapshot", entity_id=snapshot.id, after={"snapshot_hash": snapshot.snapshot_hash}, metadata=fixture_metadata())
    return snapshot


def revision_view(db: Session, revision_id: str) -> dict[str, Any]:
    revision = db.get(PreparationRevision, revision_id)
    if not revision:
        raise ValueError("PREPARATION_REVISION_NOT_FOUND")
    snapshot = db.scalar(select(PreparationSnapshot).where(PreparationSnapshot.preparation_revision_id == revision.id))
    return {"revision": row(revision), "snapshot": row(snapshot), "fixture": fixture_metadata()}
