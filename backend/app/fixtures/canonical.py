"""The single recording-derived synthetic fixture authority for end-to-end work."""

import hashlib
import json
from typing import Any


CANONICAL_FIXTURE_ID = "PermitOps_Synthetic_MVP_Dataset_v1"
CANONICAL_FIXTURE_VERSION = "1.1.1"
CANONICAL_PROJECT_IDS = ["GHCE-2026-0142", "GHCE-2026-0187", "GHCE-2026-0210", "GHCE-2026-0244"]
CANONICAL_APPLICATION_IDS = ["GHCE-APP-0142", "GHCE-APP-0187", "GHCE-APP-0210", "GHCE-APP-0244"]
LEGACY_FIXTURE_ALIASES = {
    "PRJ-2026-001": "GHCE-2026-0142",
    "PRJ-2026-002": "GHCE-2026-0187",
    "PRJ-2026-003": "GHCE-2026-0210",
    "PRJ-2026-004": "GHCE-2026-0244",
    "REQ-DEMO-1001": "GHCE-APP-0142",
    "REQ-DEMO-1002": "GHCE-APP-0187",
    "REQ-DEMO-1003": "GHCE-APP-0210",
    "REQ-DEMO-1004": "GHCE-APP-0244",
}
CANONICAL_WORKBOOK = "mock-systems/excel/permit_tracker.xlsx"
CANONICAL_SYNOLOGY_ROOT = "mock-systems/synology"
CANONICAL_PROJECT_SUBFOLDERS = ["01_Client", "02_Property", "03_Design", "04_Permits", "05_Correspondence"]
CANONICAL_WORKBOOK_SHEETS = ["GENERAL FOLLOW UP", "DESIGN", "Suppervission", "Services Provider"]
CANONICAL_PROJECTION_SHEET = "PERMITOPS SYSTEM PROJECTION"
CANONICAL_ATTACHMENT_CATEGORIES = [
    "OWNER_ID", "TITLE_DEED", "AUTHORIZATION", "COMMERCIAL_REGISTRATION", "SURVEY_PLAN",
    "COORDINATES", "ARCHITECTURAL_DRAWING", "STRUCTURAL_DRAWING", "NOC_CIVIL_DEFENCE",
    "NOC_KAHRAMAA", "CONSULTANT_REGISTRATION", "ENGINEER_REGISTRATION", "OWNER_UNDERTAKING",
    "CONSULTANT_UNDERTAKING", "ENGINEER_UNDERTAKING", "PROFESSIONAL_DECLARATION", "AUTHORITY_DECLARATION",
]
CANONICAL_FORMS = [
    "AUTHORIZATION", "OWNER_UNDERTAKING", "CONSULTANT_UNDERTAKING",
    "ENGINEER_UNDERTAKING", "PROFESSIONAL_DECLARATION", "AUTHORITY_DECLARATION",
]


def _manifest() -> dict[str, Any]:
    return {
        "fixture_set_id": CANONICAL_FIXTURE_ID,
        "name": CANONICAL_FIXTURE_ID,
        "semantic_version": CANONICAL_FIXTURE_VERSION,
        "source": "RECORDING_DERIVED_SYNTHETIC",
        "office": {"office_code": "QEC-DOHA", "name": "AMEC Engineering"},
        "users": [
            "owner@amec.synthetic", "champion@amec.synthetic", "steward@amec.synthetic",
            "engineer@amec.synthetic", "preparer@amec.synthetic", "submitter@amec.synthetic",
            "admin@amec.synthetic",
        ],
        "projects": CANONICAL_PROJECT_IDS,
        "applications": CANONICAL_APPLICATION_IDS,
        "legacy_aliases": LEGACY_FIXTURE_ALIASES,
        "synology": {"root": CANONICAL_SYNOLOGY_ROOT, "subfolders": CANONICAL_PROJECT_SUBFOLDERS},
        "excel": {"workbook": CANONICAL_WORKBOOK, "human_sheets": CANONICAL_WORKBOOK_SHEETS, "projection_sheet": CANONICAL_PROJECTION_SHEET},
        "municipality": {"system": "Permit Authority Simulator", "fixtures": ["applications", "comments", "findings", "precheck", "drafts", "submission_confirmation"]},
        "document_inventory": [
            "title_deed_clean.pdf", "title_deed_scan_arabic.pdf", "owner_id_bilingual.pdf", "authorization_bilingual.pdf",
            "survey_plan.pdf", "coordinate_report.pdf", "drawing_package_R01.pdf", "drawing_package_R02.pdf",
            "title_deed_west_bay.pdf", "owner_id_west_bay.pdf", "drawing_west_bay_R02.pdf", "noc_expired.pdf",
            "renamed_duplicate.pdf", "wrong_project_document.pdf", "lusail_title_deed.pdf", "lusail_cr.pdf", "lusail_drawing.pdf", "missing_data.pdf",
        ],
        "portal_attachment_categories": CANONICAL_ATTACHMENT_CATEGORIES,
        "undertaking_authorization_forms": CANONICAL_FORMS,
        "title_deed_property_evidence": ["title_deed_clean.pdf", "title_deed_west_bay.pdf"],
        "drawings_revisions": ["drawing_package_R01.pdf", "drawing_package_R02.pdf", "drawing_west_bay_R02.pdf", "lusail_drawing.pdf"],
        "extraction_spike_corpus": "SYNTHETIC_WORST_CASE_V1",
        "fixture_authority": "ONE_ACTIVE_FIXTURE_AUTHORITY",
        "notes": "Controlled canonical successor for the recording-derived synthetic universe. Legacy identifiers are unit/deprecated only.",
    }


CANONICAL_FIXTURE_MANIFEST = _manifest()
CANONICAL_FIXTURE_MANIFEST_HASH = hashlib.sha256(
    json.dumps(CANONICAL_FIXTURE_MANIFEST, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()


def fixture_metadata() -> dict[str, Any]:
    return {
        "fixture_set": CANONICAL_FIXTURE_ID,
        "fixture_version": CANONICAL_FIXTURE_VERSION,
        "fixture_manifest_hash": CANONICAL_FIXTURE_MANIFEST_HASH,
    }
