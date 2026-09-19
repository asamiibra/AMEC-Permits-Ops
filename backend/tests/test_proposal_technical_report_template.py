"""Regression contract for the Owner-approved Proposal V1 report template."""

import io
import json
import zipfile
from pathlib import Path

from backend.app.services.proposal_document_package import document_map, package_parts
from backend.app.api.proposal_source_routers import _apply_dynamic_building_structure
from backend.app.services.proposal_technical_report_template import (
    FIELD_KEYS,
    PROTECTED_FIELDS,
    SECTION_KEYS,
    TEMPLATE_ID,
    TEMPLATE_VERSION,
    canonical_docx_bytes,
    load_embedded_contract,
    template_contract,
    template_metadata,
)


def test_canonical_technical_report_contract_and_package_are_complete():
    metadata = template_metadata()
    content = canonical_docx_bytes()
    assert metadata["template_id"] == TEMPLATE_ID
    assert metadata["template_version"] == TEMPLATE_VERSION
    assert metadata["body_language"] == "ar"
    assert metadata["direction"] == "rtl"
    assert set(SECTION_KEYS).issubset(metadata["semantic_sections"])
    assert set(FIELD_KEYS).issubset(metadata["field_keys"])
    assert set(PROTECTED_FIELDS).issubset(metadata["protected_fields"])
    assert metadata["source_pdf_sha256"]
    assert metadata["template_sha256"]
    assert metadata["source_docx_sha256"] == "20e120b3ecb1c8a53bfb530ec256949faa0e264fdc7a8662c97231df34dcbb73"
    assert metadata["template_reconstructed_from_pdf"] is False
    assert metadata["page_images_used_for_generation"] is False
    assert metadata["page_images_used_only_for_qa"] is True
    assert len(package_parts(content)) >= 20
    blocks = document_map(content)
    assert len(blocks) >= 24
    visible_text = "\n".join(block.text for block in blocks)
    assert "تقرير فني لموقع" in visible_text
    assert "ART MARK ENGINEERING CONSULTANT" in visible_text
    # The actual Owner master keeps the approval area visibly blank; the
    # protected-field decision is carried by the non-visible contract rather
    # than inserted into the supplied Word template.
    assert "الختم والتوقيع" in visible_text
    embedded = load_embedded_contract()
    assert embedded and embedded["template_id"] == TEMPLATE_ID
    assert embedded["template_version"] == TEMPLATE_VERSION
    assert embedded["field_keys"] == list(FIELD_KEYS)
    assert template_contract()["protected_fields"]["protected.approval"]["ai_allowed"] is False


def test_template_reference_pdf_is_not_proposal_evidence():
    metadata = template_metadata()
    assert metadata["template_pdf_filename"].endswith(".pdf")
    # The reference identity is retained in the contract; no PDF bytes are
    # embedded in the editable DOCX package or exposed as a source document.
    names = set(zipfile.ZipFile(io.BytesIO(canonical_docx_bytes())).namelist())
    assert not any(name.lower().endswith(".pdf") for name in names)


def test_actual_word_template_building_sections_expand_and_trim_in_place():
    for count, expected in ((0, ""), (2, "AB"), (5, "ABCDE"), (8, "ABCDEFGH")):
        content = _apply_dynamic_building_structure(
            canonical_docx_bytes(), building_count=count, building_count_known=True
        )
        text = "\n".join(block.text for block in document_map(content))
        for symbol in "ABCDEFGH":
            assert text.count(f"المبني {symbol}") == (1 if symbol in expected else 0)
