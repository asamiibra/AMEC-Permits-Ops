"""Inventory supplied Contract DOCX sources without promoting any as canonical.

The command is intentionally read-only unless ``--output`` is supplied.  It
ignores Word temporary files, hashes raw originals, records duplicate groups,
and flags transaction-specific content for Owner sanitization review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree


W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
PLACEHOLDER = re.compile(r"(?:\{\{[^}]+\}\}|<<[^>]+>>|\[[A-Z][A-Z0-9_ .-]{2,}\])")
TRANSACTION_MARKERS = re.compile(
    r"\b(?:client|customer|project|site|address|quotation|proposal|invoice|amount|fee|aed|qar|usd|bank|iban|account|effective date|dated)\b",
    re.IGNORECASE,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _docx_structure(path: Path) -> dict[str, object]:
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml")
        root = ElementTree.fromstring(xml)
        paragraphs = ["".join(node.text or "" for node in paragraph.iter(W + "t")) for paragraph in root.iter(W + "p")]
        tables = []
        for table in root.iter(W + "tbl"):
            rows = list(table.iter(W + "tr"))
            tables.append({"rows": len(rows), "columns": max((len(list(row.iter(W + "tc"))) for row in rows), default=0)})
        languages = sorted({node.attrib.get(W + "val") for node in root.iter(W + "lang") if node.attrib.get(W + "val")})
        highlighted_runs = sum(1 for node in root.iter(W + "highlight") if node.attrib.get(W + "val"))
        text = "\n".join(paragraphs)
        placeholders = sorted(set(PLACEHOLDER.findall(text)))
        return {
            "paragraph_count": len(paragraphs),
            "non_empty_paragraph_count": sum(bool(value.strip()) for value in paragraphs),
            "table_count": len(tables),
            "tables": tables,
            "languages": languages,
            "highlighted_run_count": highlighted_runs,
            "placeholders": placeholders,
            "embedded_parts": sorted(name for name in archive.namelist() if name.startswith("word/media/")),
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "transaction_specific_marker_count": len(TRANSACTION_MARKERS.findall(text)),
        }


def inventory(paths: list[str]) -> dict[str, object]:
    records: list[dict[str, object]] = []
    skipped: list[str] = []
    for raw in paths:
        path = Path(raw).expanduser()
        if path.name.startswith("~$") or path.suffix.lower() != ".docx":
            skipped.append(str(path))
            continue
        if not path.is_file():
            skipped.append(str(path))
            continue
        digest = _sha256(path)
        structure = _docx_structure(path)
        reasons = []
        if structure["transaction_specific_marker_count"]:
            reasons.append("TRANSACTION_SPECIFIC_CONTENT_REQUIRES_SANITIZATION")
        if not structure["placeholders"]:
            reasons.append("NO_EXPLICIT_VARIABLE_PLACEHOLDERS")
        records.append({
            "original_path": str(path.resolve()),
            "sha256": digest,
            "raw_source_status": "IMMUTABLE_SOURCE_ONLY",
            "promotion_status": "QUARANTINED_PENDING_OWNER_SANITIZATION",
            "quarantine_reasons": reasons,
            "structure": structure,
        })
    by_hash: dict[str, list[str]] = defaultdict(list)
    for record in records:
        by_hash[str(record["sha256"])].append(str(record["original_path"]))
    duplicate_groups = [paths for paths in by_hash.values() if len(paths) > 1]
    for record in records:
        record["duplicate_group"] = next((group for group in duplicate_groups if record["original_path"] in group), None)
    return {
        "evidence_scope": "RAW_OWNER_DOCX_INVENTORY_ONLY",
        "canonical_template_promotion": "FORBIDDEN_BY_INVENTORY",
        "records": records,
        "skipped_paths": skipped,
        "document_count": len(records),
        "duplicate_group_count": len(duplicate_groups),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", help="Supplied DOCX paths")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.dumps(inventory(args.paths), indent=2) + "\n"
    if args.output:
        args.output.write_text(payload)
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
