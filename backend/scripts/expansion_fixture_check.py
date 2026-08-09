"""Validate the E1 successor fixture and expansion governance invariants."""
import json
from pathlib import Path

import yaml
from sqlalchemy import func, select

from backend.app.db import SessionLocal
from backend.app.expansion.fixture import EXPANDED_FIXTURE_MANIFEST, EXPANDED_FIXTURE_MANIFEST_HASH, expanded_fixture_metadata
from backend.app.expansion.governance import ASSISTANT_IDS, validate_governance
from backend.app.models import *


def main():
    governance = validate_governance()
    a12 = yaml.safe_load(Path("config/recording_fidelity_requirements_v2_5.yaml").read_text(encoding="utf-8"))["requirements"]
    resource_path = Path("synthetic-data/fixtures/expansion/stage1_v2_6_fixture.json")
    prohibited = ["password", "otp", "client qid", "real credential", "qatar regulation text"]
    content = resource_path.read_text(encoding="utf-8").lower()
    checks = {
        "a12_count": len(a12) == 20,
        "a12b_count": governance["a12b_count"] == 40,
        "a15_count": governance["a15_count"] == 18,
        "assistant_ids": governance["assistant_ids"] == ASSISTANT_IDS,
        "predecessor": EXPANDED_FIXTURE_MANIFEST["predecessor"]["version"] == "1.1.1",
        "manifest_hash": EXPANDED_FIXTURE_MANIFEST_HASH == expanded_fixture_metadata()["fixture_manifest_hash"],
        "resource_exists": resource_path.exists(),
        "required_source_families": set(EXPANDED_FIXTURE_MANIFEST["source_families"]) == {"BD_COMMERCIAL", "CONTRACT_ADMIN", "PROJECT_REFERENCE", "ENGINEERING", "FINANCE", "HANDOVER", "COMMUNICATION", "PERMIT_CORE"},
        "three_scenarios": len(EXPANDED_FIXTURE_MANIFEST["scenarios"]) == 3,
        "synthetic_only": EXPANDED_FIXTURE_MANIFEST["synthetic_only"] and EXPANDED_FIXTURE_MANIFEST["owner_session_expansion"],
        "no_prohibited_content": not any(token in content for token in prohibited),
    }
    with SessionLocal() as db:
        checks.update({
            "seeded_opportunity": (db.scalar(select(func.count(Opportunity.id))) or 0) >= 1,
            "seeded_capabilities": (db.scalar(select(func.count(AssistantCapabilityDefinition.id))) or 0) >= 30,
            "seeded_resources": (db.scalar(select(func.count(ExpansionFixtureResource.id))) or 0) >= 30,
            "safe_regulation": (db.scalar(select(func.count(RegulationVersion.id)).where(RegulationVersion.content_status == "SYNTHETIC_PLACEHOLDER")) or 0) >= 1,
        })
    result = {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "fixture": expanded_fixture_metadata(), "source_families": EXPANDED_FIXTURE_MANIFEST["source_families"], "scenarios": EXPANDED_FIXTURE_MANIFEST["scenarios"], "synthetic_only": True}
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
