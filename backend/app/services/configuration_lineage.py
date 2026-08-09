"""Deterministic configuration identity and bundle context for Week 8 evidence."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    AttachmentCategoryConfig, ConfigurationArtifact, ConfigurationBundle,
    FieldAuthorityRule, FindingCode, MunicipalityConfig, RequirementConfig,
    ScenarioConfig, TargetRenderingRule,
)


def stable_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _payload(item: Any) -> dict[str, Any]:
    return {column.name: getattr(item, column.name) for column in item.__table__.columns if column.name not in {"id", "created_at", "updated_at", "effective_from", "effective_to"} and not column.name.endswith("_id")}


def _artifact(db: Session, *, artifact_type: str, stable_id: str, version: str, payload: Any, source_basis: str) -> ConfigurationArtifact:
    if isinstance(payload, (dict, list)):
        semantic = payload
    else:
        semantic = _payload(payload)
    checksum = stable_hash(semantic)
    item = db.scalar(select(ConfigurationArtifact).where(ConfigurationArtifact.stable_id == stable_id))
    if item:
        if item.checksum != checksum or item.version != version:
            raise ValueError(f"IMMUTABLE_CONFIGURATION_ARTIFACT_CHANGED:{stable_id}")
        return item
    item = ConfigurationArtifact(stable_id=stable_id, artifact_type=artifact_type, version=version, checksum=checksum, effective_from=datetime.now(timezone.utc), status="ACTIVE", source_basis=source_basis, semantic_payload_json=semantic)
    db.add(item)
    db.flush()
    return item


def ensure_configuration_bundle(db: Session, scenario_id: str | None = None) -> ConfigurationBundle:
    scenario = db.get(ScenarioConfig, scenario_id) if scenario_id else db.scalar(select(ScenarioConfig).order_by(ScenarioConfig.scenario_code))
    if not scenario:
        raise ValueError("SCENARIO_CONFIGURATION_NOT_FOUND")
    artifacts: list[ConfigurationArtifact] = []
    configs = [
        ("SCENARIO_CONFIG", f"SCENARIO_CONFIG:{scenario.scenario_code}", scenario.version, scenario, "ScenarioConfig"),
    ]
    for model, artifact_type, version_field in [
        (RequirementConfig, "REQUIREMENT_CONFIGURATION", "scenario_id"),
        (FieldAuthorityRule, "FIELD_AUTHORITY_RULE_SET", "scenario_id"),
        (TargetRenderingRule, "TARGET_RENDERING_RULE_SET", "scenario_id"),
        (AttachmentCategoryConfig, "ATTACHMENT_TAXONOMY", "scenario_id"),
        (MunicipalityConfig, "MUNICIPALITY_CONTROL_CONFIGURATION", "scenario_id"),
    ]:
        rows = db.scalars(select(model).where(getattr(model, version_field) == scenario.id).order_by(model.id)).all()
        payload = [_payload(row) for row in rows]
        version = f"{scenario.version}:{artifact_type}:1.0"
        configs.append((artifact_type, f"{artifact_type}:{scenario.scenario_code}", version, payload, model.__tablename__))
    finding_codes = db.scalars(select(FindingCode).order_by(FindingCode.code)).all()
    configs.append(("FINDING_CODE_TAXONOMY", f"FINDING_CODE_TAXONOMY:{scenario.scenario_code}", "1.0", [_payload(row) for row in finding_codes], "FindingCode"))
    for artifact_type, stable_id, version, payload, basis in configs:
        artifacts.append(_artifact(db, artifact_type=artifact_type, stable_id=stable_id, version=version, payload=payload, source_basis=basis))
    artifact_ids = [item.stable_id for item in artifacts]
    bundle_checksum = stable_hash({"scenario": scenario.scenario_code, "version": scenario.version, "artifacts": [(item.stable_id, item.version, item.checksum) for item in artifacts]})
    bundle_id = f"CONFIG-BUNDLE:{scenario.scenario_code}:{bundle_checksum[:16]}"
    bundle = db.scalar(select(ConfigurationBundle).where(ConfigurationBundle.bundle_id == bundle_id))
    if not bundle:
        bundle = ConfigurationBundle(bundle_id=bundle_id, scenario_id=scenario.id, bundle_version=f"{scenario.version}:1.0", artifact_ids_json=artifact_ids, checksum=bundle_checksum, effective_from=datetime.now(timezone.utc), status="ACTIVE", source_basis="Week 1–8 configuration registry")
        db.add(bundle)
        db.flush()
    return bundle


def configuration_context(db: Session, scenario_id: str | None = None) -> dict[str, str]:
    bundle = ensure_configuration_bundle(db, scenario_id)
    return {"configuration_bundle_id": bundle.id, "bundle_id": bundle.bundle_id, "bundle_version": bundle.bundle_version, "configuration_checksum": bundle.checksum}
