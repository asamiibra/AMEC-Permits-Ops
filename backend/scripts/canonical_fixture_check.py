"""Repository-native canonical fixture invariant check."""

import hashlib
import json
from pathlib import Path
import sys

from sqlalchemy import func, select

from backend.app.db import SessionLocal
from backend.app.fixtures.canonical import CANONICAL_APPLICATION_IDS, CANONICAL_FIXTURE_MANIFEST, CANONICAL_FIXTURE_MANIFEST_HASH, CANONICAL_FIXTURE_ID, CANONICAL_PROJECT_IDS, CANONICAL_WORKBOOK
from backend.app.models import ExcelProjectRow, ExternalSystemLink, Project, PermitApplication, Property, PropertyOwnership, SyntheticFixtureSet, SystemType
from backend.app.services.canonical_workbook import canonical_workbook_contract


def check() -> dict:
    expected_hash = hashlib.sha256(json.dumps(CANONICAL_FIXTURE_MANIFEST, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert expected_hash == CANONICAL_FIXTURE_MANIFEST_HASH, "MANIFEST_HASH_MISMATCH"
    with SessionLocal() as db:
        fixture = db.scalar(select(SyntheticFixtureSet).where(SyntheticFixtureSet.fixture_set_id == CANONICAL_FIXTURE_ID))
        assert fixture and fixture.golden_path_authority and fixture.manifest_sha256 == expected_hash, "ACTIVE_FIXTURE_AUTHORITY_MISSING_OR_HASH_MISMATCH"
        assert db.scalar(select(func.count(SyntheticFixtureSet.id)).where(SyntheticFixtureSet.golden_path_authority.is_(True))) == 1, "ACTIVE_FIXTURE_AUTHORITY_COUNT_NOT_ONE"
        projects = {item.project_number: item for item in db.scalars(select(Project)).all()}
        applications = {item.external_request_number: item for item in db.scalars(select(PermitApplication)).all()}
        assert all(item in projects for item in CANONICAL_PROJECT_IDS), "CANONICAL_PROJECT_MISSING"
        assert all(item in applications for item in CANONICAL_APPLICATION_IDS), "CANONICAL_APPLICATION_MISSING"
        for index, app_id in enumerate(CANONICAL_APPLICATION_IDS):
            assert applications[app_id].project_id == projects[CANONICAL_PROJECT_IDS[index]].id, "APPLICATION_PROJECT_LINK_MISMATCH"
        project = projects[CANONICAL_PROJECT_IDS[0]]
        assert len(db.scalars(select(PropertyOwnership).join(Property).where(Property.project_id == project.id)).all()) == 2, "MULTI_OWNER_CANONICAL_CASE_MISSING"
        links = db.scalars(select(ExternalSystemLink).where(ExternalSystemLink.project_id == project.id)).all()
        assert any(link.system_type == SystemType.SYNOLOGY and link.external_reference.startswith("2026/GHCE-") for link in links), "SYNOLOGY_LINK_MISSING"
        excel_row = db.scalar(select(ExcelProjectRow).where(ExcelProjectRow.project_id == project.id))
        assert excel_row and excel_row.workbook_identity == CANONICAL_WORKBOOK, "WORKBOOK_LINK_MISSING"
    workbook = canonical_workbook_contract(Path(CANONICAL_WORKBOOK))
    assert workbook["sheets"] == workbook["required_sheets"] + ["PERMITOPS SYSTEM PROJECTION"], "CANONICAL_WORKBOOK_CONTRACT_MISMATCH"
    return {"status": "PASS", "fixture_set": CANONICAL_FIXTURE_ID, "fixture_version": CANONICAL_FIXTURE_MANIFEST["semantic_version"], "manifest_hash": expected_hash, "canonical_projects": CANONICAL_PROJECT_IDS, "canonical_applications": CANONICAL_APPLICATION_IDS, "workbook": CANONICAL_WORKBOOK, "synology_root": CANONICAL_FIXTURE_MANIFEST["synology"]["root"]}


if __name__ == "__main__":
    try:
        print(json.dumps(check(), sort_keys=True))
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error": str(error)}))
        sys.exit(1)
