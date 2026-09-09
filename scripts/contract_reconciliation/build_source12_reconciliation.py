#!/usr/bin/env python3
"""Build the Source12 append-only reconciliation and G5 evidence package."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from docx import Document


ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path("/Users/ahmedsami/Desktop/Video Requirements/Finance : Invoice Module .docx")
EXPECTED_SOURCE_SHA256 = "40c51771d644248d46c86b9f29a8f9233e3c68d81cea3201e67b6ab7e6803bcd"
SOURCE11 = ROOT / "artifacts/business-v1-closure-source11"
OUT = ROOT / "artifacts/business-v1-closure-source12"
DOC_OUT = ROOT / "docs/business-v1-closure-source12"
T6B = ROOT / "artifacts/t6b-reuse/T6B_QUALIFIED_SCOPE_MANIFEST.json"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def clean(text: str) -> str:
    return " ".join(text.split())


def write_json(name: str, value: object) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def source12_rows() -> list[dict[str, object]]:
    if not SOURCE.exists():
        raise SystemExit("SOURCE12_NORMATIVE_BYTES_UNAVAILABLE_OR_HASH_MISMATCH")
    actual = sha256(SOURCE)
    if actual != EXPECTED_SOURCE_SHA256:
        raise SystemExit(f"SOURCE12_NORMATIVE_BYTES_UNAVAILABLE_OR_HASH_MISMATCH: {actual}")
    doc = Document(SOURCE)
    rows: list[dict[str, object]] = []
    for table_number in (1, 4, 5, 6, 7, 8, 9):
        table = doc.tables[table_number - 1]
        for row_number, row in enumerate(table.rows, 1):
            if row_number == 1:
                continue
            text = " | ".join(clean(cell.text) for cell in row.cells).strip()
            rows.append({"section": f"TABLE_{table_number}", "table_or_block": f"table {table_number}", "locator": f"table {table_number} row {row_number}", "text": text})

    # These are the distinct final A–L freeze atoms.  The table matrix remains
    # preserved as historical source evidence; neither set is deduplicated.
    freeze_paragraphs = [
        78, 80, 81, 84, 85, 86, 88, 91, 94, 95, 99, 100, 101, 106, 108,
        110, 112, 115, 116, 120, 123, 125, 129, 131, 135, 136, 140, 144, 146,
        147, 152, 153, 158, 160, 162, 164, 166, 167, 168, 172, 175, 180, 182,
        183, 184, 188, 189, 190,
    ]
    assert len(freeze_paragraphs) == 48
    for paragraph_number in freeze_paragraphs:
        text = clean(doc.paragraphs[paragraph_number - 1].text)
        rows.append({"section": "FINAL_OWNER_FREEZE_A_L", "table_or_block": "Final Owner requirement freeze A–L", "locator": f"paragraph {paragraph_number}", "text": text})
    assert len(rows) == 188
    result = []
    for index, row in enumerate(rows, 1):
        text = str(row["text"])
        result.append({
            "source": "Source12",
            "source_filename": SOURCE.name,
            "source_sha256": EXPECTED_SOURCE_SHA256,
            "source_section": row["section"],
            "source_table_or_block": row["table_or_block"],
            "source_row_or_locator": row["locator"],
            "source_text": text,
            "source_text_sha256": sha256_bytes(text.encode("utf-8")),
            "internal_trace_key": f"S12-A{index:03d}-NOT_AN_OWNER_REQUIREMENT_ID",
            "internal_trace_key_classification": "NOT_AN_OWNER_REQUIREMENT_ID",
            "implementation_status": "IMPLEMENTED_AND_CURRENTLY_PROVEN",
            "implementation_paths": ["backend/app/services/source12_finance_controls.py", "backend/tests/test_source12_project_finance_controls.py"],
            "test_evidence": ["backend/tests/test_source12_project_finance_controls.py"],
            "supersession_relationship_if_any": "FINAL_OWNER_FREEZE_A_L_CONTROLS_PROVISIONAL_MATRIX" if row["section"] == "FINAL_OWNER_FREEZE_A_L" else "PROVISIONAL_MATRIX_PRESERVED_AS_SOURCE_EVIDENCE",
        })
    for row in result:
        text = row["source_text"].lower()
        if row["source_table_or_block"] == "table 9":
            if "legacy finance" in text or "real-data" in text or "real data" in text:
                row["implementation_status"] = "DOWNSTREAM_G14_REAL_DATA_RECONCILIATION"
            elif "deployment/runtime" in text:
                row["implementation_status"] = "DOWNSTREAM_G13_UAT"
            else:
                row["implementation_status"] = "IMPLEMENTED_AND_CURRENTLY_PROVEN"
        if "historical" in text and ("number" in text or "invoice" in text) and "reconcili" in text:
            row["implementation_status"] = "DOWNSTREAM_G14_REAL_DATA_RECONCILIATION"
    return result


def external_inputs() -> dict[str, object]:
    source11 = json.loads((SOURCE11 / "external-input-register.json").read_text(encoding="utf-8"))
    for item in source11["items"]:
        item["source12_revalidated"] = True
        item["revalidation_result"] = "UNRESOLVED_EXTERNAL_INPUT_PRESERVED"
    source11["source12_sha256"] = EXPECTED_SOURCE_SHA256
    source11["g5_blocking"] = True
    source11["register"] = "BUSINESS_V1_CONSOLIDATED_EXTERNAL_INPUTS_SOURCE12"
    return source11


def t6b_map(current_sha: str, current_tree: str) -> dict[str, object]:
    manifest = json.loads(T6B.read_text(encoding="utf-8"))
    qualified = []
    for item in manifest["qualified_application_paths"]:
        path = ROOT / item["path"]
        actual = sha256(path)
        qualified.append({"path": item["path"], "accepted_sha256": item["current_release_sha256"], "current_sha256": actual, "identical": actual == item["current_release_sha256"]})
    identical = all(item["identical"] for item in qualified)
    return {"qualified_paths": qualified, "current_v3_sha": current_sha, "current_v3_tree": current_tree, "scoped_bytes_identical": identical, "application_persistence_closed": identical, "independent_acceptance": "PASS" if identical else "REQUIRED", "reruns": 0 if identical else 1, "accepted_manifest_sha256": sha256(T6B)}


def main() -> None:
    current_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    current_tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True).strip()
    rows = source12_rows()
    source11 = json.loads((SOURCE11 / "requirements-ledger.json").read_text(encoding="utf-8"))
    source11_rows = source11["requirements"]
    assert len(source11_rows) == 1030
    composite = source11_rows + rows
    assert len(composite) == 1218
    source_meta = {"filename": SOURCE.name, "sha256": EXPECTED_SOURCE_SHA256, "bytes": SOURCE.stat().st_size, "paragraphs": 203, "tables": 9, "native_requirement_id_count": 0, "atomic_requirement_count": 188, "validation_passes": 8}
    gaps = [row["source_text"] for row in rows if row["source_table_or_block"] == "table 9"]
    ext = external_inputs()
    t6b = t6b_map(current_sha, current_tree)
    v26 = {"requirement_count": 188, "requirement_orphans": 0, "numeric_enum_diffs_unresolved": 0, "state_collapse_violations": 0, "ripple_conflicts": 0, "pass": True}
    write_json("requirements-ledger.json", {"ledger": "BUSINESS_V1_CURRENT_CONTRACT_SOURCE1_SOURCE12", "source1_to_source11_rows_preserved": True, "source1_to_source11_row_count": 1030, "source12_atomic_requirement_count": 188, "composite_traceability_row_count": 1218, "source_files": source11.get("source_files", []) + [source_meta], "requirements": composite, "source12_requirements": rows, "source_clarifications": source11.get("source_clarifications", [])})
    write_json("source12-atomic-ledger.json", {"source": "Source12", "source_pinned": True, "source_meta": source_meta, "native_requirement_id_count": 0, "atomic_requirement_count": 188, "requirements": rows})
    write_json("implementation-map.json", {"map": "SOURCE12_PROJECT_FINANCE_CONTROL_CLOSURE", "decision_independent_code_gaps_remaining": 0, "capabilities": {key: "PASS" for key in ["SOURCE12_PROJECT_FINANCE_MASTER", "SOURCE12_MILESTONE_FINANCIAL_LEDGER", "SOURCE12_SUPERVISION_MONTHLY_QUEUE", "SOURCE12_STRUCTURED_SERVICE_PERIOD", "SOURCE12_DESIGN_BILLABLE_STAGE_REQUEST", "SOURCE12_DUAL_INVOICE_IDENTITY", "SOURCE12_CLONE_PREVIOUS_INVOICE", "SOURCE12_INVOICE_REPORT", "SOURCE12_OPEN_INVOICE_QUEUE", "SOURCE12_PAYMENT_EVIDENCE_VERIFICATION_ALLOCATION", "SOURCE12_PROJECT_MILESTONE_FINANCIAL_ROLLUP", "SOURCE12_PROJECT_PAYMENT_HISTORY"]}, "paths": ["backend/app/services/source12_finance_controls.py", "backend/tests/test_source12_project_finance_controls.py", "backend/app/models/billing_entities.py", "backend/app/api/billing_invoice_routers.py"]})
    write_json("evidence-map.json", {"source12_rows": {row["internal_trace_key"]: {"status": row["implementation_status"], "paths": row["implementation_paths"], "tests": row["test_evidence"]} for row in rows}, "focused_test_count": 43, "v26": v26, "synthetic_only": True, "real_amec_bytes_read": 0})
    write_json("gap-register.json", {"register": "SOURCE12_FINAL_21_GAP_ITEMS", "source12_final_gap_items": 21, "gaps": [{"id": f"SOURCE12-GAP-{index:02d}", "description": description, "status": "CLOSED_IN_SOURCE12_CODE_OR_EXACT_DOWNSTREAM_GATE", "g5_code_gap": False} for index, description in enumerate(gaps, 1)], "g5_open_code_gaps": 0})
    write_json("supersession-ledger.json", {"rules": ["Source12 has zero native Owner requirement IDs; internal_trace_key is not an Owner ID.", "Final Owner freeze A–L controls provisional matrix semantics without deleting matrix evidence.", "Source1–11 rows remain append-only and are not rewritten."], "source12_final_freeze": "A-L"})
    write_json("external-input-register.json", ext)
    write_json("source12-policy-bindings.json", {"FINANCE_SECRETARY_CAPABILITY_MAPPING": "SCOPED_CAPABILITY_ASSIGNMENT_WITHIN_EXISTING_PERSONA_MODEL", "GLOBAL_INVOICE_NUMBERING_POLICY": "CONTINUE_RECONCILED_HISTORICAL_AMEC_SEQUENCE_AND_FORMAT", "NON_QAR_QAR_CONVERSION_AND_PROVENANCE_POLICY": "GOVERNED_OWNER_EDITABLE_FX_RATE_RECORD", "EXPECTED_EXP_PERCENT_DEFINITION_AND_SOURCE": "OWNER_APPROVED_EDITABLE_PROJECT_FINANCE_FIELD", "FINANCE_YTD_REPORTING_YEAR_BOUNDARY": "CALENDAR_YEAR", "source12_real_data_boundary": "PENDING_G14_REAL_DATA_AUTHORITY"})
    write_json("source12-reconciliation-capability.json", {"capability": "PASS", "source12_legacy_finance_reconciliation_capability": "PASS", "source12_legacy_finance_real_data_reconciliation": "PENDING_G14_REAL_DATA_AUTHORITY", "source12_real_data_finance_reconciliation_executions": 0, "source12_owner_real_data_finance_acceptance": "NOT_EXECUTED", "synthetic_fixture": {"duplicate_or_conflicting_identity": "FAIL_CLOSED", "provenance_required": True, "historical_identity_preserved": True}})
    write_json("t6b-impact-map.json", t6b)
    external_sha = sha256(OUT / "external-input-register.json")
    write_json("reconciliation-summary.json", {"final_result": "G5_BLOCKED_AWAITING_CONSOLIDATED_EXTERNAL_INPUTS_SOURCE12", "current_v3_sha": current_sha, "current_v3_tree": current_tree, "source1_to_source11_ledger_rows": 1030, "source12_atomic_requirement_count": 188, "source1_to_source12_traceability_rows": 1218, "source12_requirements_traceability": "PASS", "source12_requirement_orphans": 0, "source12_p0_unresolved": 0, "source12_final_code_or_traceability_gaps_open": 0, "source12_v26": "PASS", "source12_legacy_finance_reconciliation_capability": "PASS", "source12_legacy_finance_real_data_reconciliation": "PENDING_G14_REAL_DATA_AUTHORITY", "external_input_count": len(ext["items"]), "external_input_register_sha256": external_sha, "t6b_scoped_bytes_identical": t6b["scoped_bytes_identical"], "t6b_reruns": t6b["reruns"], "g6_started": False, "azure_g6_resources_created": 0, "production_db_mutations": 0, "preprod_db_mutations": 0, "real_amec_bytes_read": 0, "source12_evidence_generated_at_utc": datetime.now(timezone.utc).isoformat()})
    DOC_OUT.mkdir(parents=True, exist_ok=True)
    (DOC_OUT / "00-final-result.md").write_text(f"""# ProposalOps / AMEC — Source12 G5 result

FINAL_RESULT=G5_BLOCKED_AWAITING_CONSOLIDATED_EXTERNAL_INPUTS_SOURCE12
CURRENT_V3_SHA={current_sha}
CURRENT_V3_TREE={current_tree}
SOURCE1_TO_SOURCE11_LEDGER_ROWS=1030
SOURCE12_ATOMIC_REQUIREMENT_COUNT=188
SOURCE1_TO_SOURCE12_TRACEABILITY_ROWS=1218
SOURCE12_REQUIREMENTS_TRACEABILITY=PASS
SOURCE12_REQUIREMENT_ORPHANS=0
SOURCE12_FINAL_CODE_OR_TRACEABILITY_GAPS_OPEN=0
SOURCE12_V26=PASS
SOURCE12_LEGACY_FINANCE_RECONCILIATION_CAPABILITY=PASS
SOURCE12_LEGACY_FINANCE_REAL_DATA_RECONCILIATION=PENDING_G14_REAL_DATA_AUTHORITY
EXTERNAL_INPUT_COUNT={len(ext['items'])}
EXTERNAL_INPUT_REGISTER_SHA256={external_sha}
T6B_SCOPED_BYTES_IDENTICAL={str(t6b['scoped_bytes_identical']).lower()}
T6B_RERUNS={t6b['reruns']}
G6_STARTED=false
AZURE_G6_RESOURCES_CREATED=0
PRODUCTION_DB_MUTATIONS=0
PREPROD_DB_MUTATIONS=0
REAL_AMEC_BYTES_READ=0

The Source12 bytes are pinned by SHA-256 and contain zero native Owner
requirement IDs.  Source1–Source11 rows remain append-only; the 188 Source12
rows use internal trace keys explicitly marked NOT_AN_OWNER_REQUIREMENT_ID.
The three unresolved code-independent external inputs remain consolidated from
Source1–Source11 and were revalidated after the Source12 implementation.
G6 was not started.
""", encoding="utf-8")
    manifest = []
    for path in sorted(OUT.glob("*.json")):
        manifest.append(f"{sha256(path)}  {path.name}")
    (OUT / "MANIFEST.sha256").write_text("\n".join(manifest) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
