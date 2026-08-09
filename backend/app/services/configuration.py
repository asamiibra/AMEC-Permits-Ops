from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import *


def scenario(db: Session) -> ScenarioConfig:
    item = db.scalar(select(ScenarioConfig).where(ScenarioConfig.scenario_code == "DEMO_BUILDING_PERMIT_V1"))
    if not item: raise ValueError("Synthetic scenario configuration is not seeded")
    return item


def evaluate_requirements(db: Session, project_id: str) -> list[dict]:
    cfg = scenario(db)
    assertions = {db.get(FieldDefinition, a.field_definition_id).field_code: a for a in db.scalars(select(VerifiedAssertion).where(VerifiedAssertion.project_id == project_id, VerifiedAssertion.status == AssertionStatus.CURRENT)).all() if db.get(FieldDefinition, a.field_definition_id)}
    documents = db.scalars(select(Document).where(Document.project_id == project_id)).all()
    dependencies = db.scalars(select(ApprovalDependency).where(ApprovalDependency.project_id == project_id)).all()
    results = []
    for req in db.scalars(select(RequirementConfig).where(RequirementConfig.scenario_id == cfg.id)).all():
        expression = req.applicability_expression_json or {}
        applicable = True
        if expression.get("owner_type"):
            current = assertions.get("OWNER.TYPE")
            applicable = bool(current and current.semantic_value_json.get("value") == expression["owner_type"])
        if expression.get("representative") is True:
            current = assertions.get("REPRESENTATIVE.FLAG")
            applicable = bool(current and current.semantic_value_json.get("value") is True)
        evidence = False
        if req.required_document_type:
            for document in documents:
                if document.document_type.value != req.required_document_type or not document.current_version_id:
                    continue
                version = db.get(DocumentVersion, document.current_version_id)
                if version and version.approval_state == DocumentApprovalState.APPROVED and (not version.valid_until or version.valid_until >= date.today()):
                    evidence = True
                    break
        elif req.required_dependency_type:
            evidence = any(d.dependency_type == req.required_dependency_type and d.status == "CURRENT" and (not d.valid_until or d.valid_until >= date.today()) for d in dependencies)
        elif req.requirement_type == RequirementType.FIELD:
            evidence = bool(assertions.get(expression.get("field_code", "")))
        results.append({"id": req.id, "requirement_code": req.requirement_code, "description": req.description, "applicable": applicable, "blocking": req.blocking, "status": "REQUIRED" if applicable and not evidence else ("NOT_APPLICABLE" if not applicable else "SATISFIED"), "evidence": evidence, "human_decision_required": req.human_decision_required})
    return results


def evaluate_drawing_controls(db: Session, project_id: str) -> list[dict]:
    cfg = scenario(db)
    assertions = {db.get(FieldDefinition, a.field_definition_id).field_code: a.semantic_value_json.get("value") for a in db.scalars(select(VerifiedAssertion).where(VerifiedAssertion.project_id == project_id, VerifiedAssertion.status == AssertionStatus.CURRENT)).all() if db.get(FieldDefinition, a.field_definition_id)}
    results = []
    for control in db.scalars(select(DrawingMetadataControl).where(DrawingMetadataControl.scenario_id == cfg.id)).all():
        drawing_value = None
        observations = db.scalars(
            select(FieldObservation)
            .join(DocumentVersion)
            .join(Document)
            .where(
                Document.project_id == project_id,
                Document.current_version_id == DocumentVersion.id,
                FieldObservation.field_definition_id == control.field_definition_id,
            )
            .order_by(DocumentVersion.ingested_at.desc())
        ).all()
        if observations:
            obs = observations[0]
            drawing_value = obs.normalized_candidate_value or obs.raw_value
        canonical = assertions.get(control.canonical_field_code)
        result = "NEEDS_REVIEW" if drawing_value is None or canonical is None else ("PASS" if drawing_value == canonical else "FAIL")
        results.append({"control_code": control.control_code, "field_code": control.canonical_field_code, "drawing_value": drawing_value, "canonical_value": canonical, "result": result, "blocking": control.blocking, "notes": control.notes})
    return results
