import pytest

from backend.app.services.proposal_document_package import apply_text_mutations, package_parts
from backend.app.services.proposal_editor_model import (
    editor_diff_to_mutations,
    import_editor_model,
    tracked_changes,
)
from backend.tests.test_proposal_document_package import package


def test_import_is_server_owned_and_marks_complex_blocks_read_only():
    content = package('<w:p><w:r><w:t>Editable</w:t></w:r></w:p><w:p><w:r><w:t>Logo</w:t><w:pict><w:txbxContent><w:p><w:r><w:t>Branding</w:t></w:r></w:p></w:txbxContent></w:pict></w:r></w:p>')
    model = import_editor_model(content)
    assert model["docx_import_owned_by"] == "server"
    assert model["editor_parses_docx"] is False
    nodes = {node["text"]: node for node in model["nodes"]}
    assert nodes["Editable"]["editable"] is True
    assert nodes["Logo"]["editable"] is False
    assert "COMPLEX_PARAGRAPH" in model["read_only_block_types"]


def test_sections_use_native_heading_styles_and_no_heading_falls_back_to_body():
    heading_content = package(
        '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Project Description</w:t></w:r></w:p>'
        '<w:p><w:r><w:t>Body text</w:t></w:r></w:p>'
        '<w:p><w:pPr><w:outlineLvl w:val="1"/></w:pPr><w:r><w:t>Details</w:t></w:r></w:p>'
    )
    model = import_editor_model(heading_content)
    assert [section["title"] for section in model["sections"]] == ["Project Description", "Details"]
    assert all(section["node_ids"] for section in model["sections"])

    body = import_editor_model(package())
    assert body["sections"] == [{
        "section_id": "document-body",
        "title": "Document body",
        "level": 0,
        "heading_anchor": None,
        "node_ids": [node["id"] for node in body["nodes"] if node["part"] == "word/document.xml"],
    }]


def test_browser_diff_roundtrips_through_original_package_only():
    content = package()
    imported = import_editor_model(content)
    current = {**imported, "nodes": [
        {**node, "text": "Duration: 4 months" if node["text"] == "Duration: 3 months" else node["text"]}
        for node in imported["nodes"]
    ]}
    changes = tracked_changes(imported, current)
    assert changes[0]["review_actions"] == ["ACCEPT", "EDIT", "REJECT", "SHOW_SOURCE"]
    mutations = editor_diff_to_mutations(imported, current)
    result = apply_text_mutations(content, mutations)
    before, after = package_parts(content), package_parts(result)
    assert sum(before[name] != after[name] for name in before) == 1
    assert after["word/document.xml"] == before["word/document.xml"].replace(b"3 months", b"4 months")


def test_read_only_nodes_cannot_be_changed_and_topology_cannot_drift():
    content = package('<w:p><w:r><w:t>Editable</w:t><w:pict><w:txbxContent><w:p><w:r><w:t>Branding</w:t></w:r></w:p></w:txbxContent></w:pict></w:r></w:p>')
    imported = import_editor_model(content)
    readonly = next(node for node in imported["nodes"] if not node["editable"])
    changed = {**imported, "nodes": [
        {**node, "text": "tampered"} if node["id"] == readonly["id"] else node
        for node in imported["nodes"]
    ]}
    with pytest.raises(ValueError, match="READ_ONLY_NODE_EDIT"):
        editor_diff_to_mutations(imported, changed)
    with pytest.raises(ValueError, match="TOPOLOGY_CHANGED"):
        editor_diff_to_mutations(imported, {**imported, "nodes": imported["nodes"][:-1]})
