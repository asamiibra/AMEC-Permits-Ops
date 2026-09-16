from __future__ import annotations

import io
import zipfile

import pytest

from backend.app.services.proposal_template_fidelity import (
    PROPOSAL_TEMPLATE_REGION_MAP,
    evaluate_proposal_semantic_consistency,
    inspect_template_bytes,
    proposal_source_1_18_traceability,
    proposal_template_contract,
    render_deterministic_proposal_docx,
)


def _docx(*paragraphs: str) -> bytes:
    body = "".join(f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>" for text in paragraphs)
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body></w:document>"
    ).encode()
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", "<Types/>")
        package.writestr("word/document.xml", document)
    return output.getvalue()


def test_region_map_is_complete_and_highlighting_is_not_the_variable_map():
    assert PROPOSAL_TEMPLATE_REGION_MAP
    assert all(item.classification for item in PROPOSAL_TEMPLATE_REGION_MAP)
    inspection = inspect_template_bytes(_docx('<w:highlight w:val="yellow"/>', "{{proposal_reference}}"))
    assert inspection["yellow_highlight_count"] == 1
    assert inspection["yellow_highlight_is_variable_map"] is False
    contract = proposal_template_contract({})
    assert contract["PROPOSAL_TEMPLATE_REGION_MAP"] == "PASS"
    assert contract["UNCLASSIFIED_TEMPLATE_REGIONS"] == 0


def test_source_1_18_traceability_has_exactly_eighteen_rows():
    result = proposal_source_1_18_traceability({"source_1_18": {"7": {"disposition": "NOT_APPLICABLE", "rationale": "No downstream Contract effect in this Proposal."}}})
    assert result["status"] == "PASS"
    assert result["source_count"] == 18
    assert result["orphan_count"] == 0
    assert next(row for row in result["rows"] if row["source_id"] == "7")["disposition"] == "NOT_APPLICABLE"


def test_sample_proposal_conflict_is_material_and_scope_expansion_is_rejected():
    sample = {
        "page_6": "Fire Fighting DC2 comment review. Formal Authority submissions remain with VGC Arplan.",
        "page_9": "Fire Fighting selected scope.",
        "page_11": "Full Architecture Structure MEP design and new building licence.",
    }
    result = evaluate_proposal_semantic_consistency(sample)
    assert result["MATERIAL_SCOPE_CONFLICT_DETECTED"] is True
    assert result["scope_expansion_violation"] is True
    assert {item["code"] for item in result["conflicts"]} >= {"FIRE_SCOPE_VS_FULL_DESIGN_BOILERPLATE"}


def test_deterministic_docx_renderer_preserves_package_and_pins_values():
    template = _docx("AMEC Proposal", "Reference {{proposal_reference}}", "Revision {{revision}}", "Scope {{amec_scope}}")
    snapshot = {
        "proposal_reference": "AMEC-SYN-001",
        "revision_number": 1,
        "accepted_at": "2026-09-16",
        "title": "Synthetic Fire Review",
        "client_name": "Synthetic Client",
        "fields": {"scope_of_work": "Fire Fighting DC2 comment review"},
    }
    first, lineage = render_deterministic_proposal_docx(template, snapshot)
    second, second_lineage = render_deterministic_proposal_docx(template, snapshot)
    assert first == second
    assert lineage["deterministic_artifact_sha256"] == second_lineage["deterministic_artifact_sha256"]
    assert lineage["fixed_template_region_mutations"] == 0
    assert lineage["unresolved_placeholders"] == []
    assert lineage["format"] == "DOCX"
    with zipfile.ZipFile(io.BytesIO(first)) as package:
        rendered_xml = package.read("word/document.xml").decode()
    assert "AMEC-SYN-001" in rendered_xml
    assert "{{proposal_reference}}" not in rendered_xml


def test_deterministic_docx_renderer_blocks_material_scope_conflict():
    template = _docx("{{proposal_reference}}")
    snapshot = {
        "proposal_reference": "AMEC-SYN-002",
        "title": "Fire Fighting DC2 review",
        "fields": {"scope_of_work": "Fire Fighting comment review with Architecture Structure MEP full design and new building licence"},
    }
    with pytest.raises(ValueError, match="MATERIAL_SCOPE_CONFLICT"):
        render_deterministic_proposal_docx(template, snapshot)
