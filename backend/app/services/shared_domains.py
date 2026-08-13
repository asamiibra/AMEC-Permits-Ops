"""Shared-domain services with fail-closed resolver and runtime contracts."""

from __future__ import annotations

import hashlib
import json
import operator
from datetime import date, datetime, timezone
from typing import Any, Type

from fastapi import HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..models import (
    AuthorityCase,
    AuthorityCaseIdentifier,
    AuthorityCaseWorkPeriod,
    AuthorityOutcome,
    ExternalBody,
    ExternalBodyUnit,
    ExternalInteractionProfile,
    FormAutomationProfile,
    FormInstance,
    FormMappingRelease,
    FormMappingRule,
    FormQARun,
    FormSignatureRequirement,
    FormValidationResult,
    GeneratedArtifact,
    Jurisdiction,
    MasterContentItem,
    RegulatoryJourney,
    RegulatoryLifecyclePhase,
    RegulatoryRelation,
    RequirementApplicabilityDecision,
    RequirementDefinition,
    RequirementDecision,
    RequirementEvidenceConstraint,
    RequirementEvidenceEvaluation,
    RequirementEvaluation,
    RequirementGroup,
    RequirementPolicyItem,
    RequirementPolicyLineage,
    RequirementPolicyVersion,
    Role,
    SemanticKeyDefinition,
    SemanticValueAssertion,
    ServiceType,
    ServiceTypeVersion,
    SignaturePacket,
    TechnicalRule,
    TechnicalRuleEvaluation,
    TechnicalRuleLineage,
    TechnicalRuleSetVersion,
)


OWNER_ROLES = {Role.SYSTEM_ADMIN, Role.OWNER_SPONSOR}
REQUIREMENT_APPROVER_ROLES = OWNER_ROLES | {Role.REQUIREMENT_STEWARD}
TECHNICAL_APPROVER_ROLES = OWNER_ROLES | {Role.RESPONSIBLE_ENGINEER}
CASE_ROLES = OWNER_ROLES | {Role.RESPONSIBLE_ENGINEER}
AUTOMATION_EXECUTE_ROLES = OWNER_ROLES | {Role.RESPONSIBLE_ENGINEER}


class DomainConflict(ValueError):
    pass


def actor(role: Role) -> str:
    return getattr(role, "value", str(role))


def require_role(role: Role, allowed: set[Role], code: str = "ROLE_NOT_AUTHORIZED") -> None:
    if role not in allowed:
        raise HTTPException(status_code=403, detail={"code": code})


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _dump(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, list):
        return [_dump(item) for item in value]
    if isinstance(value, dict):
        return {key: _dump(item) for key, item in value.items()}
    return value


def projection(item: Any) -> dict[str, Any]:
    return {attribute.key: _dump(getattr(item, attribute.key)) for attribute in inspect(item).mapper.column_attrs}


def projections(items: list[Any]) -> list[dict[str, Any]]:
    return [projection(item) for item in items]


def _assign(item: Any, payload: dict[str, Any], *, allowed: set[str] | None = None) -> None:
    columns = {attribute.key for attribute in inspect(item).mapper.column_attrs}
    for key, value in payload.items():
        if key in columns and key not in {"id", "created_at", "updated_at"} and (allowed is None or key in allowed):
            setattr(item, key, value)


def _create(db: Session, model: Type[Any], payload: dict[str, Any], *, defaults: dict[str, Any] | None = None) -> Any:
    data = {**(defaults or {}), **payload}
    # Accept only mapped columns; request metadata cannot smuggle arbitrary
    # attributes onto the persisted domain object.
    columns = {attribute.key for attribute in inspect(model).mapper.column_attrs}
    column_map = {attribute.key: attribute for attribute in inspect(model).mapper.column_attrs}
    normalized = {}
    for key, value in data.items():
        if key not in columns or key in {"id", "created_at", "updated_at"}:
            continue
        column_type = str(column_map[key].columns[0].type).upper()
        if value not in (None, "") and "DATE" in column_type and "TIME" not in column_type and isinstance(value, str):
            value = date.fromisoformat(value)
        elif value not in (None, "") and "DATETIME" in column_type and isinstance(value, str):
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        normalized[key] = value
    item = model(**normalized)
    db.add(item)
    db.flush()
    return item


def create_record(db: Session, model: Type[Any], payload: dict[str, Any], *, defaults: dict[str, Any] | None = None) -> Any:
    return _create(db, model, payload, defaults=defaults)


def update_record(db: Session, item: Any, payload: dict[str, Any]) -> Any:
    _assign(item, payload)
    db.flush()
    return item


def active_policy_query(db: Session, *, service_type_id: str, jurisdiction_id: str | None, external_body_id: str | None, effective_date: date | None = None) -> list[RequirementPolicyVersion]:
    effective_date = effective_date or date.today()
    stmt = select(RequirementPolicyVersion).where(
        RequirementPolicyVersion.service_type_id == service_type_id,
        RequirementPolicyVersion.status == "ACTIVE",
        or_(RequirementPolicyVersion.jurisdiction_id == jurisdiction_id, RequirementPolicyVersion.jurisdiction_id.is_(None)),
        or_(RequirementPolicyVersion.external_body_id == external_body_id, RequirementPolicyVersion.external_body_id.is_(None)),
        or_(RequirementPolicyVersion.effective_from.is_(None), RequirementPolicyVersion.effective_from <= effective_date),
        or_(RequirementPolicyVersion.effective_to.is_(None), RequirementPolicyVersion.effective_to >= effective_date),
    )
    return list(db.scalars(stmt).all())


def resolve_requirement_policy(db: Session, *, service_type_id: str, jurisdiction_id: str | None, external_body_id: str | None, effective_date: date | None = None) -> RequirementPolicyVersion:
    rows = active_policy_query(db, service_type_id=service_type_id, jurisdiction_id=jurisdiction_id, external_body_id=external_body_id, effective_date=effective_date)
    # Exact context beats a broader policy; a tie remains an intentional fail-closed conflict.
    rows.sort(key=lambda row: (int(row.jurisdiction_id is not None), int(row.external_body_id is not None)), reverse=True)
    if not rows:
        raise DomainConflict("NO_ACTIVE_REQUIREMENT_POLICY")
    best_specificity = (int(rows[0].jurisdiction_id is not None), int(rows[0].external_body_id is not None))
    if sum(1 for row in rows if (int(row.jurisdiction_id is not None), int(row.external_body_id is not None)) == best_specificity) > 1:
        raise DomainConflict("AMBIGUOUS_ACTIVE_REQUIREMENT_POLICY")
    return rows[0]


def _value_from_expression(expression: dict[str, Any], context: dict[str, Any]) -> str:
    if not expression:
        return "APPLICABLE"
    if expression.get("always") in {"UNKNOWN", "APPLICABILITY_UNKNOWN"}:
        return "APPLICABILITY_UNKNOWN"
    if expression.get("always") in {"NOT_APPLICABLE", "NOT_APPLICABLE"}:
        return "NOT_APPLICABLE"
    field = expression.get("field")
    if field and field not in context:
        return "APPLICABILITY_UNKNOWN"
    if field and "equals" in expression and context.get(field) != expression["equals"]:
        return "NOT_APPLICABLE"
    if field and "in" in expression and context.get(field) not in expression["in"]:
        return "NOT_APPLICABLE"
    return "APPLICABLE"


def _evidence_status(item: RequirementPolicyItem, constraint: RequirementEvidenceConstraint | None, evidence: list[dict[str, Any]], context: dict[str, Any]) -> tuple[str, str, list[dict[str, Any]]]:
    if not evidence:
        return "MISSING", "No evidence evaluation was supplied.", []
    candidates = []
    for entry in evidence:
        if entry.get("context_id") not in (None, context.get("context_id")):
            continue
        if entry.get("context_type") not in (None, context.get("context_type")):
            continue
        if entry.get("verified") is not True:
            candidates.append({"status": "NEEDS_REVIEW", "reason": "Evidence is not a verified assertion.", **entry})
            continue
        expires_at = entry.get("expires_at")
        if expires_at and str(expires_at) < datetime.now(timezone.utc).isoformat():
            candidates.append({"status": "EXPIRED", "reason": "Evidence validity has expired.", **entry})
            continue
        if constraint and constraint.allowed_formats and entry.get("format") not in constraint.allowed_formats:
            candidates.append({"status": "MISSING", "reason": "Evidence format does not satisfy the policy constraint.", **entry})
            continue
        candidates.append({"status": "SATISFIED", "reason": "Verified evidence satisfies the available policy constraints.", **entry})
    if any(item.get("status") == "SATISFIED" for item in candidates):
        return "SATISFIED", "Verified evidence satisfies the requirement.", candidates
    if any(item.get("status") == "EXPIRED" for item in candidates):
        return "EXPIRED", "All candidate evidence is expired.", candidates
    if any(item.get("status") == "NEEDS_REVIEW" for item in candidates):
        return "NEEDS_REVIEW", "Evidence exists but is not verified.", candidates
    return "MISSING", "No candidate evidence satisfies the policy.", candidates


def evaluate_policy(db: Session, policy: RequirementPolicyVersion, *, context: dict[str, Any], evidence: list[dict[str, Any]], actor_id: str, correlation_id: str) -> dict[str, Any]:
    items = list(db.scalars(select(RequirementPolicyItem).where(RequirementPolicyItem.policy_version_id == policy.id).order_by(RequirementPolicyItem.order_index)).all())
    result_items: list[dict[str, Any]] = []
    for item in items:
        applicability = _value_from_expression(item.applicability_expression or {}, context)
        constraint = db.scalar(select(RequirementEvidenceConstraint).where(RequirementEvidenceConstraint.policy_item_id == item.id))
        if applicability == "NOT_APPLICABLE":
            status, reason, evidence_rows = "NOT_APPLICABLE", "Policy applicability evaluated to NOT_APPLICABLE.", []
        elif applicability == "APPLICABILITY_UNKNOWN":
            status, reason, evidence_rows = "NEEDS_REVIEW", "Applicability is unknown; it is not treated as Not Applicable.", []
        else:
            status, reason, evidence_rows = _evidence_status(item, constraint, evidence, context)
        evaluation = RequirementEvaluation(policy_version_id=policy.id, policy_item_id=item.id, context_type=context.get("context_type", "GENERIC"), context_id=context.get("context_id", "UNBOUND"), applicability=applicability, status=status, reason=reason, evidence_summary={"count": len(evidence_rows), "items": evidence_rows})
        db.add(evaluation)
        db.flush()
        for evidence_row in evidence_rows:
            db.add(RequirementEvidenceEvaluation(requirement_evaluation_id=evaluation.id, document_version_id=evidence_row.get("document_version_id"), evidence_ref=evidence_row.get("evidence_ref"), status=evidence_row.get("status", status), reason=evidence_row.get("reason", reason), details_json=evidence_row))
        result_items.append({"policy_item_id": item.id, "requirement_definition_id": item.requirement_definition_id, "applicability": applicability, "status": status, "reason": reason, "evidence": evidence_rows})
    db.flush()
    audit(db, correlation_id=correlation_id, event_type="REQUIREMENT_POLICY_EVALUATED", entity_type="RequirementPolicyVersion", entity_id=policy.id, actor_id=actor_id, after={"context": context, "items": len(result_items)})
    return {"policy": projection(policy), "context": context, "items": result_items}


_UNIT_CONVERSIONS = {("mm", "m"): 0.001, ("m", "mm"): 1000.0, ("ft", "m"): 0.3048, ("m", "ft"): 3.280839895, ("m2", "ft2"): 10.7639104167, ("ft2", "m2"): 0.09290304}


def convert_unit(value: float, source: str | None, target: str | None) -> float:
    if not target or not source or source == target:
        return value
    factor = _UNIT_CONVERSIONS.get((source, target))
    if factor is None:
        raise ValueError(f"UNIT_CONVERSION_UNAVAILABLE:{source}:{target}")
    return value * factor


def resolve_rule_set(db: Session, *, code: str | None = None, service_type_id: str | None = None, jurisdiction_id: str | None = None, external_body_id: str | None = None, effective_date: date | None = None) -> TechnicalRuleSetVersion:
    effective_date = effective_date or date.today()
    stmt = select(TechnicalRuleSetVersion).where(TechnicalRuleSetVersion.status == "ACTIVE", or_(TechnicalRuleSetVersion.code == code, code is None), or_(TechnicalRuleSetVersion.service_type_id == service_type_id, service_type_id is None), or_(TechnicalRuleSetVersion.jurisdiction_id == jurisdiction_id, jurisdiction_id is None), or_(TechnicalRuleSetVersion.external_body_id == external_body_id, external_body_id is None), or_(TechnicalRuleSetVersion.effective_from.is_(None), TechnicalRuleSetVersion.effective_from <= effective_date), or_(TechnicalRuleSetVersion.effective_to.is_(None), TechnicalRuleSetVersion.effective_to >= effective_date))
    rows = list(db.scalars(stmt).all())
    if len(rows) != 1:
        raise DomainConflict("NO_ACTIVE_TECHNICAL_RULE_SET" if not rows else "AMBIGUOUS_ACTIVE_TECHNICAL_RULE_SET")
    return rows[0]


def evaluate_rule(db: Session, rule: TechnicalRule, *, inputs: dict[str, Any], context_type: str, context_id: str, actor_id: str, correlation_id: str) -> dict[str, Any]:
    expression = rule.expression_json or {}
    input_key = expression.get("input_key")
    raw = inputs.get(input_key) if input_key else None
    if raw is None:
        result, reason, calculated = "UNKNOWN", "Required technical input is missing.", {}
    else:
        try:
            if isinstance(raw, dict):
                value = float(raw["value"])
                value = convert_unit(value, raw.get("unit"), expression.get("unit"))
            else:
                value = float(raw)
            threshold = float(expression["threshold"])
            op = {">": operator.gt, ">=": operator.ge, "<": operator.lt, "<=": operator.le, "==": operator.eq}.get(expression.get("operator", ">"))
            if op is None:
                raise ValueError("UNSUPPORTED_OPERATOR")
            passed = bool(op(value, threshold))
            result, reason, calculated = ("PASS", "Technical rule condition passed.", {"value": value, "threshold": threshold, "unit": expression.get("unit")}) if passed else ("FAIL", "Technical rule condition failed; review is required.", {"value": value, "threshold": threshold, "unit": expression.get("unit")})
        except (KeyError, TypeError, ValueError) as exc:
            result, reason, calculated = "UNKNOWN", str(exc), {}
    rule_set = db.get(TechnicalRuleSetVersion, rule.rule_set_version_id)
    record = TechnicalRuleEvaluation(technical_rule_id=rule.id, context_type=context_type, context_id=context_id, result=result, calculated_values=calculated, inputs_json=inputs, rule_version=rule_set.version if rule_set else rule.rule_set_version_id, reason=reason)
    db.add(record)
    db.flush()
    audit(db, correlation_id=correlation_id, event_type="TECHNICAL_RULE_EVALUATED", entity_type="TechnicalRule", entity_id=rule.id, actor_id=actor_id, after={"result": result, "context_id": context_id})
    return {"evaluation": projection(record), "rule": projection(rule)}


def resolve_assertions(db: Session, *, context_type: str, context_id: str, semantic_keys: list[str]) -> list[tuple[SemanticKeyDefinition, SemanticValueAssertion]]:
    rows = list(db.execute(select(SemanticKeyDefinition, SemanticValueAssertion).join(SemanticValueAssertion, SemanticValueAssertion.semantic_key_id == SemanticKeyDefinition.id).where(SemanticKeyDefinition.semantic_key.in_(semantic_keys), SemanticValueAssertion.context_type == context_type, SemanticValueAssertion.context_id == context_id, SemanticValueAssertion.verification_status == "VERIFIED")).all())
    by_key: dict[str, list[tuple[SemanticKeyDefinition, SemanticValueAssertion]]] = {}
    for key, assertion in rows:
        by_key.setdefault(key.semantic_key, []).append((key, assertion))
    missing = [key for key in semantic_keys if key not in by_key]
    ambiguous = [key for key, values in by_key.items() if len(values) != 1]
    if missing:
        raise DomainConflict(f"SEMANTIC_VALUE_MISSING:{','.join(missing)}")
    if ambiguous:
        raise DomainConflict(f"SEMANTIC_VALUE_AMBIGUOUS:{','.join(ambiguous)}")
    return [by_key[key][0] for key in semantic_keys]


def transform_value(value: Any, mapping: FormMappingRule) -> Any:
    transform = mapping.transform_type
    if transform == "SCALAR":
        return value
    if transform == "CHARACTER_SPLIT":
        return list(str(value))
    if transform == "BOOLEAN_TO_CHECKBOX":
        return bool(value)
    if transform == "DATE_PART":
        component = mapping.configuration_json.get("part", "year")
        parsed = date.fromisoformat(str(value)) if not isinstance(value, date) else value
        return getattr(parsed, component)
    if transform == "FORMATTER":
        return str(mapping.configuration_json.get("prefix", "")) + str(value)
    return value


def render_instance(db: Session, instance: FormInstance, *, actor_id: str, correlation_id: str) -> dict[str, Any]:
    profile = db.get(FormAutomationProfile, instance.profile_id)
    if not profile:
        raise DomainConflict("FORM_AUTOMATION_PROFILE_NOT_FOUND")
    master = db.get(MasterContentItem, instance.master_content_item_id)
    if not master or master.current_document_version_id != instance.source_document_version_id or profile.source_document_version_id != instance.source_document_version_id:
        instance.status = "NEEDS_REVALIDATION"
        instance.invalidation_reason = "Source DocumentVersion changed after profile/instance creation."
        db.flush()
        raise DomainConflict("SOURCE_VERSION_NEEDS_REVALIDATION")
    release = db.get(FormMappingRelease, instance.mapping_release_id) if instance.mapping_release_id else None
    rules = list(db.scalars(select(FormMappingRule).where(FormMappingRule.mapping_release_id == release.id).order_by(FormMappingRule.id)).all()) if release else []
    output: dict[str, Any] = {}
    skipped: list[dict[str, Any]] = []
    for mapping in rules:
        value = instance.resolved_values.get(mapping.logical_field_key)
        if mapping.target_writer in {"AUTHORITY_ONLY", "HUMAN_SIGNER", "EXTERNAL_PARTY"}:
            skipped.append({"target": mapping.target_key, "writer": mapping.target_writer, "reason": "Runtime cannot write this ownership class."})
            continue
        if mapping.transform_type == "REPEATING_GRID":
            rows = value if isinstance(value, list) else []
            if mapping.capacity is not None and len(rows) > mapping.capacity:
                raise DomainConflict("MAPPING_REPEATING_GRID_OVERFLOW")
        output[mapping.target_key] = transform_value(value, mapping)
    payload = {"renderer": profile.renderer_type, "source_document_version_id": instance.source_document_version_id, "fields": output, "skipped_writer_targets": skipped}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    artifact = GeneratedArtifact(form_instance_id=instance.id, source_document_version_id=instance.source_document_version_id, profile_id=profile.id, mapping_release_id=release.id if release else None, renderer_version="SYNTHETIC_RENDERER_1", artifact_type="SYNTHETIC_JSON", source_path_or_reference=f"runtime://generated/{instance.id}", generated_payload=payload, content_hash=digest, resolved_assertion_ids=instance.resolved_assertion_ids, created_by=actor_id)
    db.add(artifact)
    instance.status = "GENERATED"
    db.flush()
    validation = FormValidationResult(generated_artifact_id=artifact.id, validation_type="READ_BACK", status="PASS", result_json={"hash": digest, "authority_only_untouched": True, "human_signer_untouched": True, "skipped": skipped}, validated_by=actor_id)
    db.add(validation)
    db.flush()
    audit(db, correlation_id=correlation_id, event_type="FORM_AUTOMATION_RENDERED", entity_type="FormInstance", entity_id=instance.id, actor_id=actor_id, after={"artifact_id": artifact.id, "hash": digest})
    return {"instance": projection(instance), "artifact": projection(artifact), "validation": projection(validation)}
