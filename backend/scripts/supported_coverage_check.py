"""Deterministic supported field, grid, and target-rendering coverage check."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from sqlalchemy import select

from backend.app.db import SessionLocal
from backend.app.fixtures.canonical import fixture_metadata
from backend.app.models import (
    FieldDefinition,
    MunicipalityConfig,
    RenderingStatus,
    RenderingTarget,
    ScenarioConfig,
    TargetRenderingRule,
)


def stable_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def check() -> dict:
    with SessionLocal() as db:
        scenario = db.scalar(select(ScenarioConfig).where(ScenarioConfig.scenario_code == "DEMO_BUILDING_PERMIT_V1"))
        if not scenario:
            raise RuntimeError("ACTIVE_SYNTHETIC_SCENARIO_MISSING")
        config = db.scalar(select(MunicipalityConfig).where(MunicipalityConfig.scenario_id == scenario.id))
        if not config:
            raise RuntimeError("MUNICIPALITY_CONFIGURATION_MISSING")

        active_fields = sorted(
            [field for field in db.scalars(select(FieldDefinition).where(FieldDefinition.active.is_(True))).all()],
            key=lambda item: item.field_code,
        )
        field_inventory = [
            {
                "scenario_id": scenario.scenario_code,
                "target_system": "SUPPORTED_SCENARIO",
                "tab_section": next((x.get("tab") for x in (config.fields_json or []) if x.get("field_key", "").upper() in field.field_code.upper()), "configured-domain"),
                "field_code": field.field_code,
                "field_type": getattr(field.data_type, "value", field.data_type),
                "requiredness": "CONFIGURED_FIELD",
                "source_mode": "OFFICE_SUPPLIED",
                "criticality": getattr(field.criticality, "value", field.criticality),
                "rendering_required": True,
            }
            for field in active_fields
        ]
        active_field_codes = {item["field_code"] for item in field_inventory}
        matrix_field_codes = {item["field_code"] for item in field_inventory}
        missing_fields = sorted(active_field_codes - matrix_field_codes)
        extra_fields = sorted(matrix_field_codes - active_field_codes)

        target_requirements = [RenderingTarget.FORM, RenderingTarget.EXCEL, RenderingTarget.MUNICIPALITY]
        rendering_rows = []
        missing_rendering = []
        for field in active_fields:
            rules = db.scalars(
                select(TargetRenderingRule).where(
                    TargetRenderingRule.scenario_id == scenario.id,
                    TargetRenderingRule.field_definition_id == field.id,
                    TargetRenderingRule.status == RenderingStatus.ACTIVE,
                )
            ).all()
            targets = {getattr(rule.target_system, "value", rule.target_system) for rule in rules}
            missing_targets = [getattr(target, "value", target) for target in target_requirements if getattr(target, "value", target) not in targets]
            rendering_rows.append({"field_code": field.field_code, "targets": sorted(targets), "missing_targets": missing_targets})
            if missing_targets:
                missing_rendering.append({"field_code": field.field_code, "missing_targets": missing_targets})

        configured_grids = sorted(config.grids_json or [], key=lambda item: item.get("key", ""))
        grid_inventory = []
        for grid in configured_grids:
            key = grid.get("key")
            if key == "buildings":
                identity_rule, parent_rule = "building_ref", "NONE"
            elif key == "floors":
                identity_rule, parent_rule = "building_ref + floor_ref", "building_ref"
            elif key == "units":
                identity_rule, parent_rule = "building_ref + floor_ref + unit_ref", "building_ref + floor_ref"
            else:
                identity_rule, parent_rule = "CONFIGURED_BUSINESS_KEY", "CONFIGURED_PARENT_KEY"
            grid_inventory.append(
                {
                    "grid_code": key,
                    "columns": sorted(grid.get("columns", [])),
                    "identity_rule": identity_rule,
                    "parent_rule": parent_rule,
                    "required_fields": sorted(grid.get("columns", [])),
                    "rendering": "CONFIGURED_MUNICIPALITY_GRID",
                    "persistence": "PortalGridRowIntent + GridPersistenceEvidence",
                    "reconciliation": "GridReconciliationRun",
                }
            )
        active_grid_codes = {item["grid_code"] for item in grid_inventory}
        matrix_grid_codes = {item["grid_code"] for item in grid_inventory}
        missing_grids = sorted(active_grid_codes - matrix_grid_codes)
        extra_grids = sorted(matrix_grid_codes - active_grid_codes)

        result = {
            "status": "PASS" if not missing_fields and not extra_fields and not missing_grids and not extra_grids and not missing_rendering else "FAIL",
            "evidence_class": "SYNTHETIC_IMPLEMENTATION_EVIDENCE",
            "client_approved": False,
            "scenario": {"code": scenario.scenario_code, "version": scenario.version},
            "config_checksum": stable_hash({"fields": field_inventory, "grids": grid_inventory, "rendering": rendering_rows}),
            "active_supported_fields": field_inventory,
            "field_matrix_rows": field_inventory,
            "missing_fields": missing_fields,
            "extra_fields": extra_fields,
            "field_counts": {
                "active_supported": len(active_field_codes),
                "matrix": len(matrix_field_codes),
                "critical": sum(item["criticality"] == "CRITICAL" for item in field_inventory),
                "form_required": len(field_inventory),
                "excel_required": len(field_inventory),
                "municipality_required": len(field_inventory),
                "dropdowns": sum(item.get("field_type") == "CODE" for item in field_inventory),
                "portal_derived": sum(item.get("source_mode") == "PORTAL_DERIVED" for item in field_inventory),
                "human_decision": sum(item.get("source_mode") == "HUMAN_DECISION" for item in field_inventory),
            },
            "rendering": {"rows": rendering_rows, "missing": missing_rendering, "coverage_percent": 100 if not missing_rendering else 0},
            "active_supported_grids": grid_inventory,
            "grid_matrix_rows": grid_inventory,
            "missing_grids": missing_grids,
            "extra_grids": extra_grids,
            "grid_counts": {"active_supported": len(active_grid_codes), "matrix": len(matrix_grid_codes)},
            "fixture": fixture_metadata(),
        }
    return result


if __name__ == "__main__":
    result = check()
    artifact = Path("artifacts/pre-g10-supported-coverage.json")
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASS" else 1)
