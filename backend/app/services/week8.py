"""Week 8 deterministic lineage, validity, impact, and corpus services.

The service records dependency and review consequences; it never approves a
replacement package, closes a finding, or submits to a municipality.
"""

from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..fixtures.canonical import fixture_metadata
from ..models import *
from .week45 import build_package, evaluate_readiness, row, stable_hash


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _dt(value: Any) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time(), tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _date(value: Any) -> date | None:
    parsed = _dt(value)
    return parsed.date() if parsed else None


def ensure_lineage_edge(
    db: Session, *, project_id: str, upstream_type: str, upstream_id: str,
    upstream_version_or_hash: str | None, downstream_type: str, downstream_id: str,
    downstream_version_or_hash: str | None, dependency_kind: str,
    correlation_id: str,
) -> LineageEdge:
    edge = db.scalar(select(LineageEdge).where(
        LineageEdge.project_id == project_id,
        LineageEdge.upstream_type == upstream_type,
        LineageEdge.upstream_id == upstream_id,
        LineageEdge.downstream_type == downstream_type,
        LineageEdge.downstream_id == downstream_id,
        LineageEdge.dependency_kind == dependency_kind,
    ))
    if edge:
        return edge
    edge = LineageEdge(
        project_id=project_id, upstream_type=upstream_type, upstream_id=upstream_id,
        upstream_version_or_hash=upstream_version_or_hash,
        downstream_type=downstream_type, downstream_id=downstream_id,
        downstream_version_or_hash=downstream_version_or_hash,
        dependency_kind=dependency_kind, correlation_id=correlation_id,
    )
    db.add(edge)
    db.flush()
    return edge


def ensure_project_lineage(db: Session, project_id: str, correlation_id: str = "week8-lineage") -> list[LineageEdge]:
    """Materialize the relational dependency graph from existing Week 2–7 rows."""
    edges: list[LineageEdge] = []
    versions = db.scalars(select(DocumentVersion).join(Document).where(Document.project_id == project_id)).all()
    for version in versions:
        observations = db.scalars(select(FieldObservation).where(FieldObservation.document_version_id == version.id)).all()
        for observation in observations:
            edges.append(ensure_lineage_edge(db, project_id=project_id, upstream_type="DocumentVersion", upstream_id=version.id, upstream_version_or_hash=version.sha256, downstream_type="FieldObservation", downstream_id=observation.id, downstream_version_or_hash=None, dependency_kind="DERIVED_FROM", correlation_id=correlation_id))
            assertions = db.scalars(select(VerifiedAssertion).where(VerifiedAssertion.source_observation_id == observation.id)).all()
            for assertion in assertions:
                edges.append(ensure_lineage_edge(db, project_id=project_id, upstream_type="FieldObservation", upstream_id=observation.id, upstream_version_or_hash=None, downstream_type="VerifiedAssertion", downstream_id=assertion.id, downstream_version_or_hash=None, dependency_kind="VERIFIED_FROM", correlation_id=correlation_id))
    packages = db.scalars(select(Package).where(Package.project_id == project_id)).all()
    for package in packages:
        if package.configuration_bundle_id:
            bundle = db.get(ConfigurationBundle, package.configuration_bundle_id)
            edges.append(ensure_lineage_edge(db, project_id=project_id, upstream_type="ConfigurationBundle", upstream_id=package.configuration_bundle_id, upstream_version_or_hash=bundle.checksum if bundle else None, downstream_type="Package", downstream_id=package.id, downstream_version_or_hash=package.manifest_hash, dependency_kind="CONFIGURATION_CONTEXT", correlation_id=correlation_id))
        for item in db.scalars(select(PackageItem).where(PackageItem.package_id == package.id)).all():
            version = db.get(DocumentVersion, item.document_version_id)
            edges.append(ensure_lineage_edge(db, project_id=project_id, upstream_type="DocumentVersion", upstream_id=item.document_version_id, upstream_version_or_hash=version.sha256 if version else item.file_sha256, downstream_type="Package", downstream_id=package.id, downstream_version_or_hash=package.manifest_hash, dependency_kind="INCLUDED_IN_PACKAGE", correlation_id=correlation_id))
        for assertion in db.scalars(select(VerifiedAssertion).where(VerifiedAssertion.project_id == project_id)).all():
            edges.append(ensure_lineage_edge(db, project_id=project_id, upstream_type="VerifiedAssertion", upstream_id=assertion.id, upstream_version_or_hash=None, downstream_type="Package", downstream_id=package.id, downstream_version_or_hash=package.source_truth_hash, dependency_kind="DERIVED_FROM", correlation_id=correlation_id))
        for dependency in db.scalars(select(ApprovalDependency).where(ApprovalDependency.project_id == project_id)).all():
            edges.append(ensure_lineage_edge(db, project_id=project_id, upstream_type="ApprovalDependency", upstream_id=dependency.id, upstream_version_or_hash=dependency.status, downstream_type="Package", downstream_id=package.id, downstream_version_or_hash=package.source_truth_hash, dependency_kind="VALIDITY_DEPENDS_ON", correlation_id=correlation_id))
        for credential in db.scalars(select(ProfessionalCredential).where(ProfessionalCredential.project_id == project_id)).all():
            edges.append(ensure_lineage_edge(db, project_id=project_id, upstream_type="ProfessionalCredential", upstream_id=credential.id, upstream_version_or_hash=credential.status, downstream_type="Package", downstream_id=package.id, downstream_version_or_hash=package.source_truth_hash, dependency_kind="VALIDITY_DEPENDS_ON", correlation_id=correlation_id))
    revisions = db.scalars(select(PreparationRevision).where(PreparationRevision.project_id == project_id)).all()
    for revision in revisions:
        if revision.package_id:
            package = db.get(Package, revision.package_id)
            edges.append(ensure_lineage_edge(db, project_id=project_id, upstream_type="Package", upstream_id=revision.package_id, upstream_version_or_hash=package.manifest_hash if package else None, downstream_type="PreparationRevision", downstream_id=revision.id, downstream_version_or_hash=revision.package_manifest_hash, dependency_kind="PREPARED_FROM", correlation_id=correlation_id))
        for config_type, config_id, config_version in (("RequirementConfig", revision.requirement_config_version, revision.requirement_config_version), ("FieldAuthorityRule", revision.field_authority_version, revision.field_authority_version), ("TargetRenderingRule", revision.rendering_config_version, revision.rendering_config_version), ("ScenarioConfig", revision.scenario_version, revision.scenario_version)):
            edges.append(ensure_lineage_edge(db, project_id=project_id, upstream_type=config_type, upstream_id=config_id, upstream_version_or_hash=config_version, downstream_type="PreparationRevision", downstream_id=revision.id, downstream_version_or_hash=revision.package_manifest_hash, dependency_kind="PINNED_CONFIGURATION", correlation_id=correlation_id))
        scenario_config = db.scalar(select(ScenarioConfig).where(ScenarioConfig.version == revision.scenario_version))
        if scenario_config:
            edges.append(ensure_lineage_edge(db, project_id=project_id, upstream_type="ScenarioConfig", upstream_id=scenario_config.id, upstream_version_or_hash=scenario_config.version, downstream_type="PreparationRevision", downstream_id=revision.id, downstream_version_or_hash=revision.package_manifest_hash, dependency_kind="PINNED_CONFIGURATION", correlation_id=correlation_id))
            for config in db.scalars(select(RequirementConfig).where(RequirementConfig.scenario_id == scenario_config.id)).all():
                edges.append(ensure_lineage_edge(db, project_id=project_id, upstream_type="RequirementConfig", upstream_id=config.id, upstream_version_or_hash=revision.requirement_config_version, downstream_type="PreparationRevision", downstream_id=revision.id, downstream_version_or_hash=revision.package_manifest_hash, dependency_kind="PINNED_CONFIGURATION", correlation_id=correlation_id))
            for config in db.scalars(select(FieldAuthorityRule).where(FieldAuthorityRule.scenario_id == scenario_config.id)).all():
                edges.append(ensure_lineage_edge(db, project_id=project_id, upstream_type="FieldAuthorityRule", upstream_id=config.id, upstream_version_or_hash=revision.field_authority_version, downstream_type="PreparationRevision", downstream_id=revision.id, downstream_version_or_hash=revision.package_manifest_hash, dependency_kind="PINNED_CONFIGURATION", correlation_id=correlation_id))
            for config in db.scalars(select(TargetRenderingRule).where(TargetRenderingRule.scenario_id == scenario_config.id)).all():
                edges.append(ensure_lineage_edge(db, project_id=project_id, upstream_type="TargetRenderingRule", upstream_id=config.id, upstream_version_or_hash=config.version, downstream_type="PreparationRevision", downstream_id=revision.id, downstream_version_or_hash=revision.package_manifest_hash, dependency_kind="PINNED_CONFIGURATION", correlation_id=correlation_id))
        runs = db.scalars(select(AuthorityPrecheckRun).where(AuthorityPrecheckRun.preparation_revision_id == revision.id)).all()
        for run in runs:
            edges.append(ensure_lineage_edge(db, project_id=project_id, upstream_type="PreparationRevision", upstream_id=revision.id, upstream_version_or_hash=revision.package_manifest_hash, downstream_type="AuthorityPrecheckRun", downstream_id=run.id, downstream_version_or_hash=run.result_hash, dependency_kind="PRECHECKED_AGAINST", correlation_id=correlation_id))
    for rendered in db.scalars(select(RenderedForm).where(RenderedForm.project_id == project_id)).all():
        if rendered.configuration_bundle_id:
            bundle = db.get(ConfigurationBundle, rendered.configuration_bundle_id)
            edges.append(ensure_lineage_edge(db, project_id=project_id, upstream_type="ConfigurationBundle", upstream_id=rendered.configuration_bundle_id, upstream_version_or_hash=bundle.checksum if bundle else None, downstream_type="RenderedForm", downstream_id=rendered.id, downstream_version_or_hash=rendered.output_file_hash, dependency_kind="CONFIGURATION_CONTEXT", correlation_id=correlation_id))
        if rendered.package_id:
            edges.append(ensure_lineage_edge(db, project_id=project_id, upstream_type="Package", upstream_id=rendered.package_id, upstream_version_or_hash=None, downstream_type="RenderedForm", downstream_id=rendered.id, downstream_version_or_hash=rendered.output_file_hash, dependency_kind="RENDERED_FROM", correlation_id=correlation_id))
    for evaluation in db.scalars(select(PackageReadinessEvaluation).where(PackageReadinessEvaluation.project_id == project_id)).all():
        if evaluation.configuration_bundle_id:
            bundle = db.get(ConfigurationBundle, evaluation.configuration_bundle_id)
            edges.append(ensure_lineage_edge(db, project_id=project_id, upstream_type="ConfigurationBundle", upstream_id=evaluation.configuration_bundle_id, upstream_version_or_hash=bundle.checksum if bundle else None, downstream_type="PackageReadinessEvaluation", downstream_id=evaluation.id, downstream_version_or_hash=evaluation.result_hash, dependency_kind="CONFIGURATION_CONTEXT", correlation_id=correlation_id))
    for state in db.scalars(select(PortalIntendedState).join(PreparationRevision).where(PreparationRevision.project_id == project_id)).all():
        if state.configuration_bundle_id:
            bundle = db.get(ConfigurationBundle, state.configuration_bundle_id)
            edges.append(ensure_lineage_edge(db, project_id=project_id, upstream_type="ConfigurationBundle", upstream_id=state.configuration_bundle_id, upstream_version_or_hash=bundle.checksum if bundle else None, downstream_type="PortalIntendedState", downstream_id=state.id, downstream_version_or_hash=state.state_hash, dependency_kind="CONFIGURATION_CONTEXT", correlation_id=correlation_id))
    for finding in db.scalars(select(Finding).where(Finding.project_id == project_id)).all():
        if finding.finding_code_id:
            code = db.get(FindingCode, finding.finding_code_id)
            edges.append(ensure_lineage_edge(db, project_id=project_id, upstream_type="FindingCode", upstream_id=code.id, upstream_version_or_hash=finding.finding_code_checksum or code.checksum or code.version, downstream_type="Finding", downstream_id=finding.id, downstream_version_or_hash=finding.finding_code_version, dependency_kind="CLASSIFIED_BY", correlation_id=correlation_id))
    return edges


def _reason(source_type: str, change_type: str) -> tuple[str, str]:
    if source_type in {"VerifiedAssertion", "FieldObservation"}:
        return "VERIFIED_FACT_CHANGED", "A verified fact or its source observation changed."
    if source_type in {"ApprovalDependency", "AuthorityApprovalValidity"}:
        return ("DEPENDENCY_EXPIRED" if "EXPIR" in change_type else "DEPENDENCY_REVOKED" if "REVOK" in change_type else "DEPENDENCY_CHANGED", "An authority approval dependency is no longer safely current.")
    if source_type == "OfficeCredential":
        return "OFFICE_CREDENTIAL_EXPIRED", "A consultancy-office credential requires validity review."
    if source_type == "ProfessionalCredential":
        return "PROFESSIONAL_CREDENTIAL_EXPIRED", "A professional credential requires validity review."
    if source_type in {"RequirementConfig", "FieldAuthorityRule", "TargetRenderingRule", "ScenarioConfig"}:
        return ("REQUIREMENT_CONFIG_CHANGED" if source_type in {"RequirementConfig", "ScenarioConfig"} else "RENDERING_CONFIG_CHANGED" if source_type == "TargetRenderingRule" else "FIELD_AUTHORITY_CONFIG_CHANGED", "A pinned configuration version changed.")
    if "EXPIRE" in change_type:
        return "DOCUMENT_EXPIRED", "A document validity window expired."
    if "REVOK" in change_type:
        return "DOCUMENT_REVOKED", "A document or approval was revoked."
    if "SUPERSEDE" in change_type:
        return "DOCUMENT_SUPERSEDED", "A pinned document version was superseded."
    return "UPSTREAM_DOCUMENT_CHANGED", "An upstream document version or source hash changed."


def _affected(db: Session, source_type: str, source_id: str) -> list[tuple[str, str]]:
    queue = [(source_type, source_id)]
    visited: set[tuple[str, str]] = set()
    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        for edge in db.scalars(select(LineageEdge).where(LineageEdge.upstream_type == current[0], LineageEdge.upstream_id == current[1])).all():
            queue.append((edge.downstream_type, edge.downstream_id))
    return list(visited)


def _stale(db: Session, project_id: str, target_type: str, target_id: str, event: MaterialChangeEvent, code: str, reason: str) -> StaleReason:
    existing = db.scalar(select(StaleReason).where(StaleReason.material_change_event_id == event.id, StaleReason.target_type == target_type, StaleReason.target_id == target_id, StaleReason.cleared_at.is_(None)))
    if existing:
        return existing
    item = StaleReason(project_id=project_id, target_type=target_type, target_id=target_id, material_change_event_id=event.id, reason_code=code, reason=reason)
    db.add(item)
    db.flush()
    return item


def record_material_change(
    db: Session, *, project_id: str, source_type: str, source_id: str,
    previous_version_or_hash: str | None, new_version_or_hash: str | None,
    change_type: str, material: bool | None = None, actor_or_system: str = "permitops-system",
    correlation_id: str = "week8-material-change", metadata: dict[str, Any] | None = None,
) -> MaterialChangeEvent:
    metadata = metadata or {}
    if material is None:
        material = bool(metadata.get("semantic_change", True))
        if source_type in {"RequirementConfig", "FieldAuthorityRule", "TargetRenderingRule", "ScenarioConfig"} and "semantic_change" not in metadata:
            policy_type = {"RequirementConfig": "REQUIREMENT_SET", "TargetRenderingRule": "TARGET_RENDERING_RULE", "FieldAuthorityRule": "FIELD_AUTHORITY_RULE", "ScenarioConfig": "SCENARIO_CONFIG"}[source_type]
            policy = db.scalar(select(ConfigurationChangeImpactPolicy).where(ConfigurationChangeImpactPolicy.config_type == policy_type, ConfigurationChangeImpactPolicy.active.is_(True), ConfigurationChangeImpactPolicy.change_severity == "MATERIAL"))
            material = bool(policy.requires_re_evaluation) if policy else material
    if "material" in metadata:
        material = bool(metadata["material"])
    event = MaterialChangeEvent(project_id=project_id, source_type=source_type, source_id=source_id, previous_version_or_hash=previous_version_or_hash, new_version_or_hash=new_version_or_hash, change_type=change_type, occurred_at=now_utc(), actor_or_system=actor_or_system, correlation_id=correlation_id, status=MaterialChangeStatus.DETECTED if material else MaterialChangeStatus.NO_MATERIAL_CHANGE, material=material, metadata_json=metadata)
    db.add(event)
    db.flush()
    if source_type in {"RequirementConfig", "FieldAuthorityRule", "TargetRenderingRule", "ScenarioConfig"}:
        audit(db, correlation_id=correlation_id, event_type="CONFIGURATION_CHANGE_IMPACT_EVALUATED", entity_type=source_type, entity_id=source_id, after={"material": material, "change_type": change_type}, metadata=fixture_metadata())
    audit(db, correlation_id=correlation_id, event_type="MATERIAL_CHANGE_DETECTED" if material else "NO_MATERIAL_CHANGE", entity_type=source_type, entity_id=source_id, after={"event_id": event.id, "change_type": change_type, "material": material}, metadata=fixture_metadata())
    if not material:
        return event
    event.status = MaterialChangeStatus.APPLIED
    code, reason = _reason(source_type, change_type)
    ids = _affected(db, source_type, source_id)
    for additional in metadata.get("additional_source_ids", []):
        ids.extend(_affected(db, source_type, additional))
    for target_type, target_id in set(ids):
        target = db.get(Package, target_id) if target_type == "Package" else db.get(PreparationRevision, target_id) if target_type == "PreparationRevision" else db.get(AuthorityPrecheckRun, target_id) if target_type == "AuthorityPrecheckRun" else db.get(PackageReadinessEvaluation, target_id) if target_type == "PackageReadinessEvaluation" else db.get(RenderedForm, target_id) if target_type == "RenderedForm" else None
        if target_type == "Package" and target and target.status not in {"SUPERSEDED", "STALE"}:
            target.status = "STALE"; audit(db, correlation_id=correlation_id, event_type="PACKAGE_MARKED_STALE", entity_type=target_type, entity_id=target_id, after={"reason_code": code}, metadata=fixture_metadata())
        elif target_type == "PreparationRevision" and target and target.status not in {"SUPERSEDED", "STALE"}:
            target.status = "STALE"; audit(db, correlation_id=correlation_id, event_type="PREPARATION_REVISION_MARKED_STALE", entity_type=target_type, entity_id=target_id, after={"reason_code": code}, metadata=fixture_metadata())
        elif target_type == "AuthorityPrecheckRun" and target and target.status not in {"STALE", "SUPERSEDED"}:
            target.status = "STALE"; audit(db, correlation_id=correlation_id, event_type="PRECHECK_CLEARANCE_INVALIDATED", entity_type=target_type, entity_id=target_id, after={"reason_code": code}, metadata=fixture_metadata())
        elif target_type == "PackageReadinessEvaluation" and target:
            target.overall_status = "STALE"
        elif target_type == "RenderedForm" and target and target.review_state not in {"SUPERSEDED", "STALE"}:
            target.review_state = "STALE"
        if target is not None:
            _stale(db, project_id, target_type, target_id, event, code, reason)
    # Configuration changes are bounded by explicit lineage. A missing edge is
    # evidence debt, not permission to invalidate every historical evaluation.
    if source_type not in {"RequirementConfig", "FieldAuthorityRule", "TargetRenderingRule", "ScenarioConfig"}:
        for evaluation in db.scalars(select(PackageReadinessEvaluation).where(PackageReadinessEvaluation.project_id == project_id, PackageReadinessEvaluation.overall_status != "STALE")).all():
            evaluation.overall_status = "STALE"
            _stale(db, project_id, "PackageReadinessEvaluation", evaluation.id, event, code, reason)
    audit(db, correlation_id=correlation_id, event_type="LINEAGE_IMPACT_EVALUATED", entity_type="MaterialChangeEvent", entity_id=event.id, after={"affected_count": len(set(ids)), "reason_code": code}, metadata=fixture_metadata())
    return event


def document_validity_status(version: DocumentVersion) -> str:
    today = date.today()
    if version.approval_state == DocumentApprovalState.SUPERSEDED or version.superseded_by:
        return DocumentValidityStatus.SUPERSEDED
    if version.metadata_json.get("revoked_at"):
        return DocumentValidityStatus.REVOKED
    if version.valid_from and version.valid_from > today:
        return DocumentValidityStatus.NOT_YET_EFFECTIVE
    if version.valid_until and version.valid_until < today:
        return DocumentValidityStatus.EXPIRED
    return DocumentValidityStatus.VALID


def evaluate_document_validity(db: Session, version_id: str, *, actor: str = "permitops-system", correlation_id: str = "week8-validity", overrides: dict[str, Any] | None = None) -> DocumentValidity:
    version = db.get(DocumentVersion, version_id)
    if not version:
        raise ValueError("DOCUMENT_VERSION_NOT_FOUND")
    overrides = overrides or {}
    before = document_validity_status(version)
    for key in ("valid_from", "valid_until"):
        if key in overrides:
            setattr(version, key, _date(overrides[key]))
    if "approval_state" in overrides:
        version.approval_state = DocumentApprovalState(overrides["approval_state"])
    validity = db.scalar(select(DocumentValidity).where(DocumentValidity.document_version_id == version_id))
    status = document_validity_status(version)
    if not validity:
        validity = DocumentValidity(document_version_id=version_id, issued_at=None, effective_from=_dt(version.valid_from), expires_at=_dt(version.valid_until), revoked_at=_dt(version.metadata_json.get("revoked_at")), superseded_at=now_utc() if status == DocumentValidityStatus.SUPERSEDED else None, validity_status=status, rule_version="W8-DOCUMENT-VALIDITY-1.0")
        db.add(validity)
    else:
        validity.effective_from = _dt(version.valid_from); validity.expires_at = _dt(version.valid_until); validity.validity_status = status; validity.evaluated_at = now_utc()
    db.flush()
    if before != status and status != DocumentValidityStatus.VALID:
        audit(db, correlation_id=correlation_id, event_type="DOCUMENT_VALIDITY_CHANGED", entity_type="DocumentValidity", entity_id=validity.id, after={"status": status, "previous_status": before}, metadata=fixture_metadata())
        record_material_change(db, project_id=version.document.project_id, source_type="DocumentVersion", source_id=version.id, previous_version_or_hash=before, new_version_or_hash=status, change_type=f"DOCUMENT_{status}", material=True, actor_or_system=actor, correlation_id=correlation_id, metadata={"validity_status": status})
    return validity


def evaluate_dependency_validity(db: Session, dependency_id: str, *, actor: str = "permitops-system", correlation_id: str = "week8-validity", overrides: dict[str, Any] | None = None) -> AuthorityApprovalValidity:
    dependency = db.get(ApprovalDependency, dependency_id)
    if not dependency:
        raise ValueError("APPROVAL_DEPENDENCY_NOT_FOUND")
    overrides = overrides or {}
    if "valid_until" in overrides: dependency.valid_until = _date(overrides["valid_until"])
    if "valid_from" in overrides: dependency.valid_from = _date(overrides["valid_from"])
    if "status" in overrides: dependency.status = overrides["status"]
    today = date.today()
    status = "VALID" if dependency.status == "CURRENT" and (not dependency.valid_from or dependency.valid_from <= today) and (not dependency.valid_until or dependency.valid_until >= today) else ("EXPIRED" if dependency.valid_until and dependency.valid_until < today else "REVOKED" if dependency.status in {"REVOKED", "SUPERSEDED"} else "UNKNOWN_REVIEW_REQUIRED")
    validity = db.scalar(select(AuthorityApprovalValidity).where(AuthorityApprovalValidity.approval_dependency_id == dependency_id))
    before = validity.status if validity else "UNKNOWN_REVIEW_REQUIRED"
    if not validity:
        validity = AuthorityApprovalValidity(approval_dependency_id=dependency_id, valid_from=_dt(dependency.valid_from), valid_until=_dt(dependency.valid_until), status=status, evaluated_at=now_utc())
        db.add(validity)
    else:
        validity.valid_from = _dt(dependency.valid_from); validity.valid_until = _dt(dependency.valid_until); validity.status = status; validity.evaluated_at = now_utc()
    db.flush()
    if before != status and status != "VALID":
        audit(db, correlation_id=correlation_id, event_type="DEPENDENCY_VALIDITY_CHANGED", entity_type="AuthorityApprovalValidity", entity_id=validity.id, after={"status": status, "previous_status": before}, metadata=fixture_metadata())
        record_material_change(db, project_id=dependency.project_id, source_type="ApprovalDependency", source_id=dependency.id, previous_version_or_hash=before, new_version_or_hash=status, change_type=f"DEPENDENCY_{status}", material=True, actor_or_system=actor, correlation_id=correlation_id, metadata={"validity_status": status})
    return validity


def evaluate_project_validity(db: Session, project_id: str, *, actor: str = "permitops-system", correlation_id: str = "week8-validity", overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    overrides = overrides or {}
    documents = [evaluate_document_validity(db, v.id, actor=actor, correlation_id=correlation_id) for v in db.scalars(select(DocumentVersion).join(Document).where(Document.project_id == project_id)).all()]
    dependencies = [evaluate_dependency_validity(db, d.id, actor=actor, correlation_id=correlation_id) for d in db.scalars(select(ApprovalDependency).where(ApprovalDependency.project_id == project_id)).all()]
    credentials = []
    for credential in db.scalars(select(ProfessionalCredential).where(ProfessionalCredential.project_id == project_id)).all():
        if credential.id in overrides:
            credential.valid_until = _dt(overrides[credential.id])
        if credential.status == "CURRENT" and credential.valid_until and credential.valid_until.date() < date.today():
            credential.status = "EXPIRED"
            audit(db, correlation_id=correlation_id, event_type="PROFESSIONAL_CREDENTIAL_VALIDITY_CHANGED", entity_type="ProfessionalCredential", entity_id=credential.id, after={"status": credential.status}, metadata=fixture_metadata())
            record_material_change(db, project_id=project_id, source_type="ProfessionalCredential", source_id=credential.id, previous_version_or_hash="CURRENT", new_version_or_hash="EXPIRED", change_type="PROFESSIONAL_CREDENTIAL_EXPIRED", material=True, actor_or_system=actor, correlation_id=correlation_id)
        credentials.append(row(credential))
    project = db.get(Project, project_id)
    office_credentials = db.scalars(select(OfficeCredential).where(OfficeCredential.office_id == project.office_id)).all() if project else []
    for credential in office_credentials:
        if credential.status == "CURRENT" and credential.valid_until and credential.valid_until.date() < date.today():
            credential.status = "EXPIRED"
            audit(db, correlation_id=correlation_id, event_type="OFFICE_CREDENTIAL_VALIDITY_CHANGED", entity_type="OfficeCredential", entity_id=credential.id, after={"status": credential.status}, metadata=fixture_metadata())
            record_material_change(db, project_id=project_id, source_type="OfficeCredential", source_id=credential.id, previous_version_or_hash="CURRENT", new_version_or_hash="EXPIRED", change_type="OFFICE_CREDENTIAL_EXPIRED", material=True, actor_or_system=actor, correlation_id=correlation_id)
    return {"documents": [row(x) for x in documents], "dependencies": [row(x) for x in dependencies], "professional_credentials": credentials, "office_credentials": [row(x) for x in office_credentials]}


def impact_summary(db: Session, event_id: str) -> dict[str, Any]:
    event = db.get(MaterialChangeEvent, event_id)
    if not event:
        raise ValueError("MATERIAL_CHANGE_NOT_FOUND")
    reasons = db.scalars(select(StaleReason).where(StaleReason.material_change_event_id == event_id)).all()
    return {"event": row(event), "affected_entities": [{"type": x.target_type, "id": x.target_id, "reason_code": x.reason_code, "reason": x.reason} for x in reasons], "approval_required": bool(reasons), "auto_approved": False, "revalidation_required": bool(reasons)}


def precheck_validity(db: Session, run_id: str) -> dict[str, Any]:
    run = db.get(AuthorityPrecheckRun, run_id)
    if not run:
        raise ValueError("PRECHECK_RUN_NOT_FOUND")
    reasons = db.scalars(select(StaleReason).where(StaleReason.target_type == "AuthorityPrecheckRun", StaleReason.target_id == run_id, StaleReason.cleared_at.is_(None))).all()
    status = "STALE" if reasons or run.status == "STALE" else ("NEEDS_REVALIDATION" if run.status == "NEEDS_REVALIDATION" else "CURRENT")
    return {"run": row(run), "validity_status": status, "reasons": [row(x) for x in reasons], "revision_id": run.preparation_revision_id}


def revalidate_project(db: Session, project_id: str, action: str, actor: str, correlation_id: str) -> dict[str, Any]:
    if action == "RE_EVALUATE_READINESS":
        evaluation, _ = evaluate_readiness(db, project_id, actor=actor)
        audit(db, correlation_id=correlation_id, event_type="READINESS_REVALIDATED", entity_type="Project", entity_id=project_id, after={"evaluation_id": evaluation.id, "status": evaluation.overall_status}, metadata=fixture_metadata())
        return {"action": action, "evaluation": row(evaluation), "auto_approved": False}
    if action == "MARK_PRECHECK_RECHECK_REQUIRED":
        runs = db.scalars(select(AuthorityPrecheckRun).join(PreparationRevision).where(PreparationRevision.project_id == project_id)).all()
        for run in runs: run.status = "NEEDS_REVALIDATION"
        return {"action": action, "runs_marked": len(runs), "auto_approved": False}
    audit(db, correlation_id=correlation_id, event_type="REVALIDATION_ACTION_REQUESTED", entity_type="Project", entity_id=project_id, after={"action": action, "human_gate_required": True}, metadata=fixture_metadata())
    return {"action": action, "status": "REQUIRES_HUMAN_REVIEW", "auto_approved": False}


def run_corpus(db: Session, *, project_id: str | None, fixture_set: str, fixture_version: str, corpus_version: str, label: str, correlation_id: str) -> CorpusRun:
    run = CorpusRun(fixture_set=fixture_set, fixture_version=fixture_version, corpus_version=corpus_version, status="RUNNING", label=label, metrics_json={})
    db.add(run); db.flush()
    audit(db, correlation_id=correlation_id, event_type="CORPUS_RUN_STARTED", entity_type="CorpusRun", entity_id=run.id, after={"fixture_set": fixture_set, "corpus_version": corpus_version}, metadata=fixture_metadata())
    query = select(DocumentVersion).join(Document)
    if project_id: query = query.where(Document.project_id == project_id)
    versions = db.scalars(query.order_by(DocumentVersion.id)).all()
    results = []
    for version in versions:
        document = version.document
        classification = db.scalar(select(DocumentClassification).where(DocumentClassification.document_version_id == version.id).order_by(DocumentClassification.created_at.desc()))
        observations = db.scalars(select(FieldObservation).where(FieldObservation.document_version_id == version.id)).all()
        assertion = db.scalar(select(VerifiedAssertion).where(VerifiedAssertion.source_observation_id.in_([x.id for x in observations]), VerifiedAssertion.status == AssertionStatus.CURRENT)) if observations else None
        case = CorpusCase(corpus_run_id=run.id, case_key=f"{document.logical_name}:{version.version_number}", document_version_id=version.id, expected_class=document.document_type.value, expected_fields={}, status="COMPLETED")
        db.add(case); db.flush()
        expected = document.document_type.value
        predicted = classification.final_type if classification and classification.final_type else classification.predicted_type if classification else None
        result = CorpusCaseResult(corpus_run_id=run.id, corpus_case_id=case.id, document_classification_agreement=predicted == expected, critical_candidate_agreement=bool(observations), verified_final_agreement=bool(assertion), false_accept=False, degraded_keyed_entry=False, human_correction=any(x.extraction_method == ExtractionMethod.MANUAL_KEYED for x in observations), evidence_quality="GOOD" if observations else "MISSING", timing_seconds=None)
        db.add(result); results.append(result)
    total = len(results)
    run.status = "COMPLETED"; run.completed_at = now_utc(); run.metrics_json = {"case_count": total, "document_classification_agreement_rate": sum(x.document_classification_agreement for x in results) / total if total else 1.0, "critical_candidate_agreement_rate": sum(x.critical_candidate_agreement for x in results) / total if total else 1.0, "verified_final_agreement_rate": sum(x.verified_final_agreement for x in results) / total if total else 1.0, "false_accept_count": sum(x.false_accept for x in results), "degraded_keyed_entry_rate": sum(x.degraded_keyed_entry for x in results) / total if total else 0.0, "human_correction_rate": sum(x.human_correction for x in results) / total if total else 0.0, "evidence_quality": {quality: sum(x.evidence_quality == quality for x in results) for quality in {x.evidence_quality for x in results}}}
    db.flush(); audit(db, correlation_id=correlation_id, event_type="CORPUS_RUN_COMPLETED", entity_type="CorpusRun", entity_id=run.id, after=run.metrics_json, metadata=fixture_metadata())
    return run


def record_shadow_correction(db: Session, project_id: str, payload: dict[str, Any], correlation_id: str) -> ShadowCorrection:
    item = ShadowCorrection(project_id=project_id, application_id=payload.get("application_id"), preparation_revision_id=payload.get("preparation_revision_id"), entity_type=payload.get("entity_type", "FIELD"), field_or_category=payload.get("field_or_category", "UNSPECIFIED"), proposed_value=payload.get("proposed_value"), approved_human_value=payload.get("approved_human_value"), correction_type=payload.get("correction_type", "VALUE_CORRECTION"), root_cause_category=payload.get("root_cause_category", "OTHER"), evidence_artifact_id=payload.get("evidence_artifact_id"))
    db.add(item); db.flush(); audit(db, correlation_id=correlation_id, event_type="SHADOW_CORRECTION_RECORDED", entity_type="ShadowCorrection", entity_id=item.id, after={"root_cause_category": item.root_cause_category, "field_or_category": item.field_or_category}, metadata=fixture_metadata())
    return item
