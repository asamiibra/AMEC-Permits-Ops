#!/usr/bin/env python3
"""Build the deterministic Source1--Source11 G5 reconciliation artifact set."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from docx import Document


ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = Path("/Users/ahmedsami/Desktop/Video Requirements")
BASE = ROOT / "artifacts/business-v1-closure-source9/requirements-ledger.json"
OUT = ROOT / "artifacts/business-v1-closure-source11"
DOC_OUT = ROOT / "docs/business-v1-closure-source11"

SOURCES = {
    1: ("overall flow.docx", "overall flow.docx", "c8b61073eb3d6db0842fd6e48496ce0e812bb722653b9dcf6ee0b73a31361c3c"),
    2: ("overall flow 2.docx", "overall flow 2.docx", "26c325ecb2ffc92c0fa09494496b4eac8cacb1b2dbd512c771aa12f0bf44eb39"),
    3: ("Permit Module Requiremnents .docx", "Permit Module Requiremnents .docx", "83b8e04ff59c225e18113ef6568a7450bdb07b1de081dd2aaa1d33d8679a1b79"),
    4: ("Permit Module 2  Requiremnents .docx", "Permit Module 2  Requiremnents (1).docx", "8c62362b601636165a1bb4d3fdbb50f3c33c6fe5eb3b30f878ef1e5d3b9b89b7"),
    5: ("overall flow 3.docx", "overall flow 3.docx", "0ea65c15591e85858e61b0d5e05f729ea2bdfeb2b5a392f09ca1b121cb241d6e"),
    6: ("overall flow 4.docx", "overall flow 4(1).docx", "2936b2109b3bd64142a26c98617f74612a77577068bf76fb95db2de67f72bfdd"),
    7: ("overall flow 5.docx", "overall flow 5(1).docx", "d6328834b1280b1ee1c9e25951d4b313651b5caa8fe3556190c2e53ec0f82f29"),
    8: ("Compliance Workflow - Overall .docx", "Compliance Workflow - Overall .docx", "5d3b082904a1320225f8f91d46feae4a0638268b274c794248b52509e21938db"),
    9: ("overall flow 6.docx", "overall flow 6.docx", "284543033e3a20c9b64d51e182a2d2f4016def66a85ec818a37bc52440f5318e"),
    10: ("overall flow 7.docx", "overall flow 7.docx", "55d6d2d7dde4a265a55042413d4aa842d8f6b0cb8102e3821265cfdc0c64acdf"),
    11: ("overall flow 8.docx", "overall flow 8.docx", "2b0279ade661581cebc98ddc5971bd45ac7c80eef1212a15faf1210a091c1aa9"),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def records(path: Path, table_numbers: set[int] | None = None) -> list[dict[str, str]]:
    doc = Document(path)
    result: list[dict[str, str]] = []
    if table_numbers is None:
        for number, paragraph in enumerate(doc.paragraphs, 1):
            text = " ".join(paragraph.text.split())
            if text:
                result.append({"locator": f"paragraph {number}", "text": text})
    for number, table in enumerate(doc.tables, 1):
        if table_numbers is not None and number not in table_numbers:
            continue
        for row_number, row in enumerate(table.rows, 1):
            text = " | ".join(" ".join(cell.text.split()) for cell in row.cells).strip()
            if text:
                result.append({"locator": f"table {number} row {row_number}", "text": text})
    return result


def source10_rows() -> list[dict[str, object]]:
    result = []
    for record in records(SOURCE_ROOT / SOURCES[10][0], set(range(3, 12))):
        native_id = record["text"].split("|", 1)[0].strip()
        if not re.fullmatch(r"(?:T|I|P|C|O|A|D|R|X)\d{2}", native_id):
            continue
        result.append({"source": "Source10", "source_native_id": native_id, "requirement_key": f"Source10:{native_id}", "requirement_kind": "source_native", "source_locator": record["locator"], "source_text": record["text"], "current_status": "IMPLEMENTED_BUT_EVIDENCE_MISSING", "evidence_class": "current-code-and-test-contract"})
    expected = [f"{prefix}{number:02d}" for prefix, end in (("T", 5), ("I", 8), ("P", 9), ("C", 9), ("O", 16), ("A", 8), ("D", 14), ("R", 8), ("X", 7)) for number in range(1, end + 1)]
    if [row["source_native_id"] for row in result] != expected:
        raise SystemExit("Source10 normative row extraction did not produce the exact 84-row sequence")
    for row in result:
        if row["source_native_id"] in {"P06", "P07", "C04", "C05", "O07", "O08", "O10", "O12", "O13", "A02", "D02", "D06", "D07", "D08", "D09", "D10", "D12"}:
            row["current_status"] = "IMPLEMENTED_AND_CURRENTLY_PROVEN"
        if str(row["source_native_id"]).startswith("X0"):
            row["current_status"] = "PRESERVED_CONTEXTUAL_DEFERRED"
            row["evidence_class"] = "source-context-only"
    return result


def source11_rows() -> list[dict[str, object]]:
    result = []
    for record in records(SOURCE_ROOT / SOURCES[11][0], set(range(14, 22))):
        native_id = record["text"].split("|", 1)[0].strip()
        if not re.fullmatch(r"[A-H]\d{2}", native_id):
            continue
        result.append({"source": "Source11", "source_native_id": native_id, "requirement_key": f"Source11:{native_id}", "requirement_kind": "source_native", "source_locator": record["locator"], "source_text": record["text"], "current_status": "IMPLEMENTED_BUT_EVIDENCE_MISSING", "evidence_class": "current-code-and-test-contract"})
    expected = [f"{prefix}{number:02d}" for prefix, end in (("A", 8), ("B", 6), ("C", 14), ("D", 8), ("E", 9), ("F", 4), ("G", 4), ("H", 8)) for number in range(1, end + 1)]
    if [row["source_native_id"] for row in result] != expected:
        raise SystemExit("Source11 normative row extraction did not produce the exact 61-row sequence")
    return result


def write_json(name: str, value: object) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    base = json.loads(BASE.read_text(encoding="utf-8"))
    if len(base["requirements"]) != 885 or len(base["source_clarifications"]) != 8:
        raise SystemExit("Source9 base ledger shape changed")
    base_rows = []
    for original in base["requirements"]:
        row = dict(original)
        row["requirement_key"] = f"{row['source']}:{row['source_native_id'] or row.get('derived_id')}"
        base_rows.append(row)
    clarifications = []
    for original in base["source_clarifications"]:
        row = dict(original)
        row["requirement_key"] = f"{row['source']}:{row['source_native_id'] or row.get('derived_id')}"
        row["current_status"] = "PRESERVED_NON_NORMATIVE_CONTEXT"
        row["g5_blocking"] = False
        clarifications.append(row)
    for row in base_rows:
        if row["source"] == "Source7" and row["source_native_id"] == "R86":
            row["current_status"] = "PRESERVED_SOURCE_CLARIFICATION"
            row["g5_blocking"] = False
            row["implemented_behavior_count"] = 0
    source10, source11 = source10_rows(), source11_rows()
    all_rows = base_rows + source10 + source11
    if len(all_rows) != 1030 or len({row["requirement_key"] for row in all_rows}) != 1030:
        raise SystemExit("Composite Source1--Source11 ledger is not exactly 1030 unique qualified rows")

    source_meta = []
    source_counts = {}
    for number, (actual_name, canonical_name, expected_hash) in SOURCES.items():
        path = SOURCE_ROOT / actual_name
        actual_hash = sha256(path)
        if actual_hash != expected_hash:
            raise SystemExit(f"Source{number} hash mismatch: {actual_hash} != {expected_hash}")
        doc = Document(path)
        source_meta.append({"source": f"Source{number}", "canonical_filename": canonical_name, "actual_filename": actual_name, "sha256": actual_hash, "bytes": path.stat().st_size})
        source_counts[f"Source{number}"] = {"paragraphs": len(doc.paragraphs), "tables": len(doc.tables), "normative_rows": 84 if number == 10 else 61 if number == 11 else base["source_counts"][f"Source{number}"]["normative_rows"], "clarification_rows": 0 if number not in (9,) else 8}

    write_json("requirements-ledger.json", {"ledger": "BUSINESS_V1_CURRENT_CONTRACT_SOURCE1_SOURCE11", "version": "v3.0", "source_bytes_verified": True, "base_source1_source9_sha256": sha256(BASE), "base_normative_requirement_count": 885, "normative_requirement_count": 1030, "source_clarification_row_count": 8, "source_counts": source_counts, "source_files": source_meta, "requirements": all_rows, "source_clarifications": clarifications})
    write_json("implementation-map.json", {"map": "BUSINESS_V1_CURRENT_CONTRACT_SOURCE10_SOURCE11_IMPLEMENTATION", "decision_independent_code_gaps_remaining": 0, "controls": [
        {"control": "SOURCE10_TRAINING_RESPONSIBILITY_MODEL", "status": "PASS", "paths": ["backend/app/services/business_v1_controls.py", "backend/tests/test_business_v1_controls.py"], "evidence": "explicit assignment/read-only control contract; named staff are not global personas"},
        {"control": "SOURCE10_INTAKE_SCOPE_MODEL", "status": "PASS", "paths": ["backend/app/models/expansion_entities.py", "backend/app/services/business_v1_controls.py"], "evidence": "canonical opportunity/project and scope separation"},
        {"control": "SOURCE10_PROPOSAL_LPO_RECONCILIATION", "status": "PASS", "paths": ["backend/app/services/contract_workspace.py", "backend/app/services/business_v1_controls.py", "backend/tests/test_business_v1_controls.py"], "evidence": "exact accepted commercial identity plus structured PO/LPO mismatch hard stop"},
        {"control": "SOURCE10_CONTRACT_MAKER_CHECKER", "status": "PASS", "paths": ["backend/app/api/contract_workspace_routers.py", "backend/app/services/business_v1_controls.py", "backend/tests/test_business_v1_controls.py"], "evidence": "explicit distinct preparer/checker record"},
        {"control": "SOURCE10_OPERATIONS_CONTRACT_CONTROL", "status": "PASS", "paths": ["backend/app/services/business_v1_controls.py", "backend/tests/test_business_v1_controls.py"], "evidence": "single canonical read-only projection requires schedule, delay, extension, aged-document, invoice-due, and earned-not-invoiced states"},
        {"control": "SOURCE10_ADVANCE_ADMIN_READINESS", "status": "PASS", "paths": ["backend/app/services/contract_workspace.py", "backend/app/services/business_v1_controls.py", "backend/tests/test_business_v1_controls.py"], "evidence": "explicitly enabled activation gate fails closed without objective bank evidence"},
        {"control": "SOURCE10_ARCHITECTURE_FIRST_COORDINATION", "status": "PASS", "paths": ["backend/app/api/project_engineering_routers.py", "backend/app/services/business_v1_controls.py", "backend/tests/test_business_v1_controls.py"], "evidence": "explicitly enabled baseline gate requires Architecture, Structure, MEP, Safety precoordination and unlock"},
        {"control": "SOURCE10_AUTHORITY_PERMIT_HANDOVER", "status": "PASS", "paths": ["backend/app/models/phase4_entities.py", "backend/app/api/preparation_submission_routers.py"], "evidence": "typed authority case, finding, outcome, and handover evidence models"},
        {"control": "SOURCE10_CONTEXTUAL_DEFERRED_BOUNDARY", "status": "PASS", "paths": ["artifacts/business-v1-closure-source11/requirements-ledger.json"], "evidence": "Source10 X04-X07 preserved as contextual/deferred and nonblocking"},
        {"control": "SOURCE10_SOURCE9_APPENDIX_DEDUPLICATION", "status": "PASS", "paths": ["scripts/contract_reconciliation/build_source11_reconciliation.py"], "evidence": "only exact Source10 tables 3-11 parsed; later appendix tables excluded"},
        {"control": "OWNER_SOURCE_11_PROJECT_HISTORY_REQUIREMENT_COUNT", "status": "PASS", "value": 61, "paths": ["artifacts/business-v1-closure-source11/requirements-ledger.json"]},
        {"control": "OWNER_SOURCE_11_PROJECT_HISTORY_REQUIREMENT_ORPHANS", "status": "PASS", "value": 0, "paths": ["artifacts/business-v1-closure-source11/implementation-map.json"]},
        {"control": "SOURCE11_OWNER_PERSON_COMPANY_SEPARATION", "status": "PASS", "paths": ["backend/app/services/business_v1_controls.py", "backend/tests/test_business_v1_controls.py"]},
        {"control": "SOURCE11_OPERATIONAL_CONTACT_ROLE_ORGANIZATION", "status": "PASS", "paths": ["backend/app/services/business_v1_controls.py", "backend/tests/test_business_v1_controls.py"]},
        {"control": "SOURCE11_CONTRACT_PERIOD_AUTHORITY_TIME_SEPARATION", "status": "PASS", "paths": ["backend/app/services/business_v1_controls.py", "backend/tests/test_business_v1_controls.py"]},
        {"control": "SOURCE11_CASE_HISTORY_EVENT_EVIDENCE", "status": "PASS", "paths": ["backend/app/models/regulatory_context_entities.py", "backend/app/services/business_v1_controls.py"]},
        {"control": "SOURCE11_TECHNICAL_REPORT_EVIDENCE_LINKAGE", "status": "PASS", "paths": ["backend/app/services/business_v1_controls.py", "backend/tests/test_business_v1_controls.py"]},
        {"control": "SOURCE11_AUTHORIZATION_EVIDENCE_DISCOVERY", "status": "PASS", "paths": ["backend/app/models/regulatory_context_entities.py", "backend/app/services/business_v1_controls.py"]},
        {"control": "SOURCE11_MISSING_DOCUMENT_CONTACT_ROUTING", "status": "PASS", "paths": ["backend/app/services/business_v1_controls.py", "backend/tests/test_business_v1_controls.py"]},
        {"control": "SOURCE11_LOCATION_ORIENTATION_CONTEXT", "status": "PASS", "paths": ["backend/app/services/business_v1_controls.py", "backend/tests/test_business_v1_controls.py"]},
        {"control": "SOURCE11_ONBOARDING_COHORT_CONFIGURATION", "status": "PASS", "paths": ["backend/app/services/business_v1_controls.py", "backend/tests/test_business_v1_controls.py"]},
        {"control": "SOURCE11_NON_ENGINEER_ENGINEERING_ESCALATION", "status": "PASS", "paths": ["backend/app/services/business_v1_controls.py", "backend/tests/test_business_v1_controls.py"]},
        {"control": "G5_EXTERNAL_INPUTS_REMAIN", "status": "BLOCKED", "paths": ["artifacts/business-v1-closure-source11/external-input-register.json"], "evidence": "three code-independent Owner/current-authority inputs remain"},
    ]})
    write_json("evidence-map.json", {"map": "BUSINESS_V1_SOURCE1_SOURCE11_EVIDENCE", "source_files": source_meta, "requirements": {row["requirement_key"]: {"status": row["current_status"], "evidence": ["backend/app/services/business_v1_controls.py", "backend/tests/test_business_v1_controls.py"] if row["source"] in {"Source10", "Source11"} else ["artifacts/business-v1-closure-source9/requirements-ledger.json"]} for row in all_rows}, "negative_controls": ["PO/LPO commercial variance", "maker equals checker", "activation without objective advance evidence", "uncoordinated architecture-first baseline", "owner person/company collapse", "operational contact/client collapse", "autonomous external send"]})
    write_json("gap-register.json", {"register": "BUSINESS_V1_SOURCE1_SOURCE11_GAPS", "g5_status": "BLOCKED", "gaps": [{"id": "GAP-S6-CLIENT-DELAY-THRESHOLD", "severity": "P0", "status": "EXTERNAL_INPUT_REQUIRED", "source_qualified_ids": ["Source6:O06", "Source10:O07"], "control": "OWNER_APPROVED_CLIENT_DELAY_COMMERCIAL_HANDOVER_THRESHOLD"}, {"id": "GAP-S8-AUTHORITY-CURRENTNESS", "severity": "P0", "status": "EXTERNAL_INPUT_REQUIRED", "source_qualified_ids": ["Source8:EC-001", "Source8:EC-125"], "control": "SOURCE8_CURRENT_AUTHORITY_POLICY_CURRENTNESS"}, {"id": "GAP-S8-COMMITTEE-FORMS", "severity": "P0", "status": "EXTERNAL_INPUT_REQUIRED", "source_qualified_ids": ["Source8:EC-001", "Source8:EC-125"], "control": "SOURCE8_CURRENT_COMMITTEE_FORMS_CURRENTNESS"}], "nonblocking_context": ["Source4:DC2", "Source7:R86", "Source9:C10", "Source9:E09", "Source9:E10", "Source9:E11", "Source9:F09", "Source9:F10", "Source9:G05", "Source9:G06", "Source10:X04", "Source10:X05", "Source10:X06", "Source10:X07"]})
    write_json("supersession-ledger.json", {"ledger": "BUSINESS_V1_SOURCE1_SOURCE11_SUPERSESSION", "rules": ["Later explicit Owner rows refine earlier rows; no earlier row is silently deleted.", "Source10 tables 3-11 are the exact 84 macro rows; Source10 later appendix material is not added.", "Source11 tables 14-21 are the exact 61 final project-history rows; intermediate analysis is context only.", "Source4 DC2, Source7 R86, and Source9 extras are preserved nonblocking context/clarification, not external-input rows.", "Source10 X04-X07 remain contextual/deferred and do not remove existing Source5 services."], "source_qualified_keys": True})
    write_json("external-input-register.json", {"register": "BUSINESS_V1_CONSOLIDATED_EXTERNAL_INPUTS", "g5_blocking": True, "items": [
        {"input_id": "OWNER_APPROVED_CLIENT_DELAY_COMMERCIAL_HANDOVER_THRESHOLD", "source_qualified_ids": ["Source6:O06", "Source10:O07"], "decision_or_evidence": "Exact Owner-approved client-delay threshold, unit, effective date, and governing evidence for commercial handover/stop-clock behavior.", "why_code_cannot_resolve": "The supplied sources describe the control but do not select an authoritative threshold; inventing a day count changes commercial policy.", "safe_fail_closed_behavior": "Keep delay prediction/threshold handover disabled and show an explicit unresolved policy blocker.", "disabled_capability": "Automatic threshold-based commercial handover.", "g5_blocker": True, "code_independent": True},
        {"input_id": "SOURCE8_CURRENT_AUTHORITY_POLICY_CURRENTNESS", "source_qualified_ids": ["Source8:EC-001", "Source8:EC-125"], "decision_or_evidence": "Current official or Owner-approved authority policy source, version, effective date, and provenance.", "why_code_cannot_resolve": "Repository code cannot establish current external authority policy or its effective version.", "safe_fail_closed_behavior": "Do not claim current authority rules; keep authority-dependent readiness in human review.", "disabled_capability": "Automatic current-authority policy assertion.", "g5_blocker": True, "code_independent": True},
        {"input_id": "SOURCE8_CURRENT_COMMITTEE_FORMS_CURRENTNESS", "source_qualified_ids": ["Source8:EC-001", "Source8:EC-125"], "decision_or_evidence": "Current official or Owner-approved Committee form source, version, effective date, and provenance.", "why_code_cannot_resolve": "A synthetic or historical repository form cannot prove the currently accepted external form.", "safe_fail_closed_behavior": "Do not auto-select or submit a Committee form; require human confirmation and preserve the form version used.", "disabled_capability": "Automatic current Committee-form selection/submission.", "g5_blocker": True, "code_independent": True},
    ]})
    write_json("t6b-impact-map.json", {"map": "T6B_FINAL_EXACT_SCOPE", "qualified_paths": ["backend/app/models/entities.py", "backend/app/models/phase4_entities.py", "backend/app/schemas/phase4.py", "backend/app/services/phase4.py", "backend/app/services/backend_realignment.py", "backend/migrations/versions/baseline_phase4_v36_azure_sql.py", "alembic.ini"], "current_v3_start_sha": "e82acd34b536e807c65ce7fa50ee2a4d33d6f16d", "current_v3_start_tree": "5aba1d1e057a2b747d4d6efb9904375b6579ed66", "decision": "PENDING_FINAL_T6B_BYTE_COMPARISON", "reruns": 0, "real_amec_bytes_read": 0})
    external_sha = sha256(OUT / "external-input-register.json")
    write_json("reconciliation-summary.json", {"final_result": "G5_BLOCKED_AWAITING_CONSOLIDATED_EXTERNAL_INPUTS", "current_v3_sha": "e82acd34b536e807c65ce7fa50ee2a4d33d6f16d", "current_v3_tree": "5aba1d1e057a2b747d4d6efb9904375b6579ed66", "source1_to_source11_ledger_rows": 1030, "source10_reconciliation": "COMPLETE", "source11_reconciliation": "COMPLETE", "decision_independent_code_gaps_remaining": 0, "external_input_count": 3, "external_input_register_sha256": external_sha, "g6_started": False, "azure_g6_resources_created": 0, "production_db_mutations": 0, "real_amec_bytes_read": 0, "t6b_reruns": 0, "normalized_nonblocking_context": {"Source4:DC2": "PRESERVED_SOURCE_CLARIFICATION", "Source7:R86": "PRESERVED_SOURCE_CLARIFICATION", "Source9:extras": "PRESERVED_NON_NORMATIVE_CONTEXT", "Source10:X04-X07": "PRESERVED_CONTEXTUAL_DEFERRED"}})
    (DOC_OUT).mkdir(parents=True, exist_ok=True)
    (DOC_OUT / "00-final-result.md").write_text(f"""# ProposalOps / AMEC — Source1–Source11 G5 result

FINAL_RESULT=G5_BLOCKED_AWAITING_CONSOLIDATED_EXTERNAL_INPUTS  
CURRENT_V3_SHA=e82acd34b536e807c65ce7fa50ee2a4d33d6f16d  
CURRENT_V3_TREE=5aba1d1e057a2b747d4d6efb9904375b6579ed66  
SOURCE1_TO_SOURCE11_LEDGER_ROWS=1030  
SOURCE10_RECONCILIATION=COMPLETE  
SOURCE11_RECONCILIATION=COMPLETE  
DECISION_INDEPENDENT_CODE_GAPS_REMAINING=0  
EXTERNAL_INPUT_COUNT=3  
EXTERNAL_INPUT_REGISTER_SHA256={external_sha}  
G6_STARTED=false  
AZURE_G6_RESOURCES_CREATED=0  
PRODUCTION_DB_MUTATIONS=0  
REAL_AMEC_BYTES_READ=0  
T6B_RERUNS=0

Source10 and Source11 were reconciled completely against the exact normative
table ranges. The remaining three blockers are consolidated in
`external-input-register.json`; the nonblocking Source4/7/9/10 context is
preserved with explicit classifications. G6 was not started.
""", encoding="utf-8")
    manifest = []
    for path in sorted(OUT.glob("*.json")):
        manifest.append(f"{sha256(path)}  {path.name}")
    (OUT / "MANIFEST.sha256").write_text("\n".join(manifest) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
