"""Server-owned editing model for Proposal V1 Editor Option B.

The browser receives a small rich-text model, never a DOCX.  Each editable
node carries the immutable anchor and XML precondition from the imported
package.  Export callers convert changed nodes to :class:`TextMutation` and
apply them to the original bytes with ``apply_text_mutations``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .proposal_document_package import DocumentBlock, TextMutation, document_map


READ_ONLY_BLOCK_TYPES = frozenset({
    "DRAWING", "EMBEDDED_MEDIA", "VML_TEXTBOX", "SECTION_PROPERTIES",
    "COMPLEX_PARAGRAPH",
})


@dataclass(frozen=True)
class EditorNode:
    node_id: str
    anchor: str
    part: str
    text: str
    xml_hash: str
    editable: bool
    block_type: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.node_id,
            "anchor": self.anchor,
            "part": self.part,
            "text": self.text,
            "xml_hash": self.xml_hash,
            "editable": self.editable,
            "block_type": self.block_type,
        }


def _block_type(content: bytes, block: DocumentBlock) -> str:
    xml = content[block.start:block.end]
    if b"w:pict" in xml or b"w:txbxContent" in xml:
        return "VML_TEXTBOX"
    if b"w:drawing" in xml or b"wp:inline" in xml or b"wp:anchor" in xml:
        return "DRAWING"
    if block.has_nested_paragraphs:
        return "COMPLEX_PARAGRAPH"
    return "TEXT_PARAGRAPH"


def import_editor_model(content: bytes) -> dict[str, Any]:
    """Build a licence-free browser model from a validated DOCX package.

    Only plain paragraph/table-cell text is editable.  Header/footer chrome,
    drawings, media and complex textboxes remain visible read-only nodes.
    """
    blocks = document_map(content)
    nodes: list[EditorNode] = []
    for block in blocks:
        kind = _block_type(content, block)
        editable = kind == "TEXT_PARAGRAPH" and bool(block.text_spans)
        nodes.append(EditorNode(
            node_id=block.anchor,
            anchor=block.anchor,
            part=block.part,
            text=block.text,
            xml_hash=block.xml_hash,
            editable=editable,
            block_type=kind,
        ))
    editable_count = sum(node.editable for node in nodes)
    return {
        "version": "PROPOSAL-EDITOR-MODEL-1.0",
        "docx_import_owned_by": "server",
        "editor_parses_docx": False,
        "nodes": [node.as_dict() for node in nodes],
        "editable_node_count": editable_count,
        "read_only_node_count": len(nodes) - editable_count,
        "read_only_block_types": sorted({node.block_type for node in nodes if not node.editable}),
        "export_path": "ORIGINAL_PACKAGE_TARGETED_MUTATIONS",
    }


def _node_map(model: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    nodes = model.get("nodes")
    if not isinstance(nodes, Sequence) or isinstance(nodes, (str, bytes, bytearray)):
        raise ValueError("EDITOR_MODEL_NODES_REQUIRED")
    result: dict[str, Mapping[str, Any]] = {}
    for node in nodes:
        if not isinstance(node, Mapping) or not isinstance(node.get("id"), str):
            raise ValueError("INVALID_EDITOR_NODE")
        if node["id"] in result:
            raise ValueError("DUPLICATE_EDITOR_NODE")
        result[node["id"]] = node
    return result


def editor_diff_to_mutations(imported: Mapping[str, Any], current: Mapping[str, Any]) -> list[TextMutation]:
    """Convert browser edits into anchored mutations, failing closed on drift."""
    before, after = _node_map(imported), _node_map(current)
    if before.keys() != after.keys():
        raise ValueError("EDITOR_MODEL_TOPOLOGY_CHANGED")
    mutations: list[TextMutation] = []
    for node_id, original in before.items():
        edited = after[node_id]
        if bool(original.get("editable")) is not bool(edited.get("editable")):
            raise ValueError("EDITOR_NODE_EDITABILITY_CHANGED")
        if not original.get("editable"):
            if edited.get("text") != original.get("text"):
                raise ValueError("READ_ONLY_NODE_EDIT")
            continue
        if edited.get("text") == original.get("text"):
            continue
        expected = str(original.get("xml_hash") or "")
        if len(expected) != 64:
            raise ValueError("EDITOR_NODE_PRECONDITION_REQUIRED")
        mutations.append(TextMutation(node_id, expected, str(edited.get("text") or "")))
    return mutations


def tracked_changes(imported: Mapping[str, Any], current: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return Word-style review rows without changing the source package."""
    before, after = _node_map(imported), _node_map(current)
    rows: list[dict[str, Any]] = []
    for node_id, original in before.items():
        edited = after.get(node_id)
        if not edited or not original.get("editable") or edited.get("text") == original.get("text"):
            continue
        rows.append({
            "anchor": node_id,
            "before": original.get("text", ""),
            "after": edited.get("text", ""),
            "state": "PROPOSED",
            "review_actions": ["ACCEPT", "EDIT", "REJECT", "SHOW_SOURCE"],
        })
    return rows
