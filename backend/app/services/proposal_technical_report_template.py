"""Canonical Arabic technical-report template contract for Proposal V1.

The supplied ``التقرير الفني.pdf`` is the visual authority.  The checked-in
DOCX is the editable master used by the server; the PDF is retained only as
its reference identity and is never treated as project evidence.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ..config.settings import repo_root

TEMPLATE_ID = "AMEC-PROPOSAL-V1-TECHNICAL-REPORT"
TEMPLATE_VERSION = "1.0.0"
TEMPLATE_PURPOSE = "PROPOSAL_V1_TECHNICAL_REPORT"
DOCX_FILENAME = "AMEC-P-D-2026-Q-TECHNICAL-REPORT.docx"
ORIGINAL_DOCX_FILENAME = "نموذج التقرير الفني.docx"
PDF_FILENAME = "AMEC-PROPOSAL-V1-TECHNICAL-REPORT.pdf"
CONTRACT_VERSION = "AMEC-TECHNICAL-REPORT-CONTRACT-1.0"
# SHA-256 of the Owner-supplied editable Word master before the non-visible
# contract part is added to the governed package.  Keeping this identity lets
# reviewers prove that the generation baseline came from the actual DOCX.
SOURCE_DOCX_SHA256 = "20e120b3ecb1c8a53bfb530ec256949faa0e264fdc7a8662c97231df34dcbb73"

SECTION_KEYS = (
    "report_identity", "owner_data", "site_data", "existing_license", "purpose",
    "site_description", "site_map", "site_layout", "building_inventory",
    "building_detail", "modifications", "overall_condition", "conclusion",
    "protected_approval",
)

FIXED_CONTENT = (
    "amec_branding", "corporate_identity", "grade_a_designation",
    "discipline_header", "arabic_company_name", "office_contact_footer",
    "page_numbering", "standard_report_purpose", "condition_definitions",
    "section_headings", "action_checkbox_labels", "approval_area",
)

PROTECTED_FIELDS = (
    "consultant_approval", "stamp", "signature", "protected.approval",
)

FIELD_KEYS = (
    "report.recipient", "report.project_name_or_site", "report.number", "report.date",
    "owner.name", "owner.qid_or_cr", "owner.contact_number",
    "site.name_or_description", "site.municipality", "site.zone", "site.street",
    "site.plot_number", "site.pin", "site.plot_area", "site.coordinates",
    "site.current_use", "site.proposed_use", "site.inspection_date",
    "site.actual_building_count", "site.general_description", "site.map_image",
    "site.layout_plan_image", "license.previous_building_permit_number", "license.date",
    "license.completion_certificate_number", "license.licensed_use",
    "license.approved_building_count", "license.actual_building_count", "license.status",
    "license.last_approved_amendment", "overall_building_condition", "report.conclusion",
    "modifications.rows",
)


def _fixture(name: str) -> Path:
    return repo_root() / "backend" / "app" / "fixtures" / name


def canonical_docx_path() -> Path:
    return _fixture(DOCX_FILENAME)


def reference_pdf_path() -> Path:
    return _fixture(PDF_FILENAME)


def canonical_docx_bytes() -> bytes:
    return canonical_docx_path().read_bytes()


def reference_pdf_sha256() -> str:
    return hashlib.sha256(reference_pdf_path().read_bytes()).hexdigest()


def canonical_docx_sha256() -> str:
    return hashlib.sha256(canonical_docx_bytes()).hexdigest()


def template_metadata() -> dict[str, Any]:
    return {
        "template_id": TEMPLATE_ID,
        "template_version": TEMPLATE_VERSION,
        "template_purpose": TEMPLATE_PURPOSE,
        "template_contract_version": CONTRACT_VERSION,
        "template_document_filename": DOCX_FILENAME,
        "source_docx_filename": ORIGINAL_DOCX_FILENAME,
        "source_docx_sha256": SOURCE_DOCX_SHA256,
        "template_pdf_filename": PDF_FILENAME,
        "source_pdf_sha256": reference_pdf_sha256(),
        "template_sha256": canonical_docx_sha256(),
        "effective_status": "CURRENT",
        "body_language": "ar",
        "direction": "rtl",
        "revision_default": "Rev. 00",
        "fixed_content": list(FIXED_CONTENT),
        "protected_fields": list(PROTECTED_FIELDS),
        "semantic_sections": list(SECTION_KEYS),
        "repeatable_structures": ["buildings", "building.photos", "modifications.rows"],
        "field_keys": list(FIELD_KEYS),
        "visual_reference": "PDF_PAGE_BY_PAGE_BUSINESS_EQUIVALENCE",
        "template_reconstructed_from_pdf": False,
        "page_images_used_for_generation": False,
        "page_images_used_only_for_qa": True,
    }


def template_contract() -> dict[str, Any]:
    """Return the server-owned semantic contract stored with each revision."""
    metadata = template_metadata()
    return {
        **metadata,
        "semantic_fields": {
            key: {
                "field_id": key,
                "classification": "PROTECTED_HUMAN" if key in PROTECTED_FIELDS else "PROJECT_GENERATED",
                "source_required": key not in PROTECTED_FIELDS,
                "unresolved_state": "NEEDS_OWNER_REVIEW",
                "anchor_pattern": f"[[{key}]]",
            }
            for key in FIELD_KEYS
        },
        "protected_fields": {
            key: {"field_id": key, "ai_allowed": False, "owner": "AUTHORIZED_HUMAN"}
            for key in PROTECTED_FIELDS
        },
    }


def load_embedded_contract() -> dict[str, Any] | None:
    """Read the DOCX's non-visible contract part when present."""
    import zipfile
    try:
        with zipfile.ZipFile(canonical_docx_path()) as package:
            contract = json.loads(package.read("customXml/amec-technical-report-contract.json"))
            if isinstance(contract, dict):
                contract["field_keys"] = list(FIELD_KEYS)
                contract["semantic_sections"] = list(SECTION_KEYS)
            return contract
    except (OSError, KeyError, ValueError, json.JSONDecodeError):
        return None
