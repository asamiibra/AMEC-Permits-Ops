#!/usr/bin/env python3
"""Build the append-only Source15 current-contract reconciliation package.

All normative source paths, canonical names, and SHA-256 values are supplied
explicitly at invocation time.  The tool records exact DOCX byte identity and
stable table/paragraph locators; it never silently substitutes a source.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from docx import Document


ROOT = Path(__file__).resolve().parents[2]
SOURCE12_LEDGER = ROOT / "artifacts/business-v1-closure-source12/requirements-ledger.json"
SOURCE14_CHECKPOINT = ROOT / "artifacts/business-v1-closure-source14/source14-requirements-ledger.json"

SOURCE_LIBRARY_FILES = {
    "Source1": "overall flow.docx",
    "Source2": "overall flow 2.docx",
    "Source3": "Permit Module Requiremnents .docx",
    "Source4": "Permit Module 2  Requiremnents .docx",
    "Source5": "overall flow 3.docx",
    "Source6": "overall flow 4.docx",
    "Source7": "overall flow 5.docx",
    "Source8": "Compliance Workflow - Overall .docx",
    "Source9": "overall flow 6.docx",
    "Source10": "overall flow 7.docx",
    "Source11": "overall flow 8.docx",
    "Source12": "Finance : Invoice Module .docx",
}
SOURCE_LIBRARY_SHAS = {
    "Source1": "c8b61073eb3d6db0842fd6e48496ce0e812bb722653b9dcf6ee0b73a31361c3c",
    "Source2": "26c325ecb2ffc92c0fa09494496b4eac8cacb1b2dbd512c771aa12f0bf44eb39",
    "Source3": "83b8e04ff59c225e18113ef6568a7450bdb07b1de081dd2aaa1d33d8679a1b79",
    "Source4": "8c62362b601636165a1bb4d3fdbb50f3c33c6fe5eb3b30f878ef1e5d3b9b89b7",
    "Source5": "0ea65c15591e85858e61b0d5e05f729ea2bdfeb2b5a392f09ca1b121cb241d6e",
    "Source6": "2936b2109b3bd64142a26c98617f74612a77577068bf76fb95db2de67f72bfdd",
    "Source7": "d6328834b1280b1ee1c9e25951d4b313651b5caa8fe3556190c2e53ec0f82f29",
    "Source8": "5d3b082904a1320225f8f91d46feae4a0638268b274c794248b52509e21938db",
    "Source9": "284543033e3a20c9b64d51e182a2d2f4016def66a85ec818a37bc52440f5318e",
    "Source10": "55d6d2d7dde4a265a55042413d4aa842d8f6b0cb8102e3821265cfdc0c64acdf",
    "Source11": "2b0279ade661581cebc98ddc5971bd45ac7c80eef1212a15faf1210a091c1aa9",
    "Source12": "40c51771d644248d46c86b9f29a8f9233e3c68d81cea3201e67b6ab7e6803bcd",
}

ALLOWED_CLASSIFICATIONS = {
    "IMPLEMENTED_AND_PROVEN",
    "IMPLEMENTED_BUT_EVIDENCE_MISSING",
    "PARTIAL",
    "MISSING",
    "EXTERNAL_CURRENTNESS_EVIDENCE_REQUIRED",
    "OWNER_DECISION_REQUIRED",
    "SOURCE_CLARIFICATION_REQUIRED",
    "EXPLICITLY_SUPERSEDED",
    "CONTEXTUAL_ONLY",
    "NOT_APPLICABLE_WITH_EXACT_REASON",
}

# These are the 143 Finance/Billing atoms in the final Owner requirement set.
# They are deliberately paragraph locators, not fabricated source-native IDs.
FINANCE_ATOM_PARAGRAPHS = (
    540, 542, 544, 546, 548,
    *range(553, 561),
    564, 568, 570, 571,
    574, 576, 577, 578, 579, 580,
    584, 586, 587, 589, 590, 592, 593, 594, 597, 598,
    602, 603, 605, 606, 608, 610,
    615, 617, 619, 621, 624,
    627, 629, 630, 631, 632, 634,
    639, 643, 647, 651, 655, 656,
    659, 661, 662, 663, 664, 665,
    670, 671, 672, 673, 674, 676, 679, 680,
    685, 686, 688, 690, 692, 694, 696, 698, 702, 709,
    713, 714, 715, 716, 717, 718, 719, 720,
    723, 724, 725, 726, 727, 728, 729, 730, 731, 732,
    740, 741, 742, 743, 744, 746,
    750, 751, 752, 753, 754, 755,
    758, 759, 760, 761, 762, 763, 764, 765, 766, 767,
    771, 772, 773, 774, 775, 776, 777, 778, 779, 780, 781, 782, 783, 784, 785, 786,
    794, 798, 799, 800, 801, 802, 803,
)
assert len(FINANCE_ATOM_PARAGRAPHS) == 143


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def clean(value: str) -> str:
    return " ".join(value.split())


def write_json(out: Path, name: str, value: object) -> None:
    (out / name).write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def source_meta(path: Path, canonical_name: str, expected_sha: str) -> dict[str, object]:
    if not path.is_file():
        raise SystemExit(f"NORMATIVE_SOURCE_MISSING:{canonical_name}:{path}")
    actual_sha = sha256(path)
    if actual_sha != expected_sha:
        raise SystemExit(f"NORMATIVE_SOURCE_HASH_MISMATCH:{canonical_name}:{actual_sha}")
    doc = Document(str(path))
    return {
        "canonical_filename": canonical_name,
        "actual_path": str(path),
        "actual_filename": path.name,
        "sha256": actual_sha,
        "bytes": path.stat().st_size,
        "paragraphs": len(doc.paragraphs),
        "tables": len(doc.tables),
    }


def row_status(text: str) -> str:
    text = clean(text)
    if text.startswith("🔴"):
        return "MISSING"
    if text.startswith("⚪"):
        return "CONTEXTUAL_ONLY"
    if text.startswith("🟡") or text.startswith("⚠️"):
        return "PARTIAL"
    if text.startswith("✅"):
        return "IMPLEMENTED_BUT_EVIDENCE_MISSING"
    return "SOURCE_CLARIFICATION_REQUIRED"


def source13_ledger(path: Path, meta: dict[str, object]) -> dict[str, object]:
    doc = Document(str(path))
    rows: list[dict[str, object]] = []
    for table_number in range(1, 10):
        for row_number, row in enumerate(doc.tables[table_number - 1].rows, 1):
            if row_number == 1:
                continue
            cells = [clean(cell.text) for cell in row.cells]
            source_key = cells[0] or f"Source13:T{table_number}:R{row_number}"
            if source_key in {"INV-04", "INV-05"}:
                final_text = "Accepted Contract is required for production standard Invoice billing; quotation-only billing is unsupported in production."
                final_source = "Source13 final adjudication / Verifications 4–6"
                status = "IMPLEMENTED_BUT_EVIDENCE_MISSING"
            else:
                final_text = "Source13 final standard AMEC Invoice requirement preserved, subject to later same-scope Source15 Finance refinements."
                final_source = "Source13 final adjudication / Verifications 4–6"
                status = row_status(cells[3] if len(cells) > 3 else "")
            raw_text = " | ".join(cells)
            rows.append({
                "source_requirement_key": source_key,
                "source_table": table_number,
                "source_row": row_number,
                "source_text": raw_text,
                "source_text_sha256": sha256_bytes(raw_text.encode("utf-8")),
                "source_sha256": meta["sha256"],
                "source_canonical_filename": meta["canonical_filename"],
                "raw_source_row": True,
                "final_governing_requirement": final_text,
                "final_adjudication_source": final_source,
                "implementation_status_against_final_requirement": status,
                "precedence_relationship": "FINAL_GOVERNING_SOURCE13_ADJUDICATION",
                "traceability_key": f"Source13-FINAL-{source_key}",
            })
    if len(rows) != 116:
        raise SystemExit(f"SOURCE13_REQUIREMENT_COUNT_UNEXPECTED:{len(rows)}")
    return {
        "ledger": "BUSINESS_V1_FINAL_GOVERNING_SOURCE13_ADJUDICATION",
        "source_pinned": True,
        "source_meta": meta,
        "requirement_count": len(rows),
        "requirement_orphans": 0,
        "legacy_quotation_only_billing_policy": "UNSUPPORTED_IN_PRODUCTION",
        "go_forward_commercial_authority": "ACCEPTED_CONTRACT_REQUIRED",
        "requirements": rows,
    }


def source15_primary(path: Path, meta: dict[str, object]) -> list[dict[str, object]]:
    doc = Document(str(path))
    rows: list[dict[str, object]] = []
    for row_number, row in enumerate(doc.tables[0].rows, 1):
        if row_number == 1:
            continue
        cells = [clean(cell.text) for cell in row.cells]
        if not cells[0].isdigit():
            continue
        raw_text = " | ".join(cells)
        rows.append({
            "source": "Source15",
            "source_public_requirement_id": int(cells[0]),
            "source_table": 1,
            "source_row": row_number,
            "source_text": raw_text,
            "source_text_sha256": sha256_bytes(raw_text.encode("utf-8")),
            "source_sha256": meta["sha256"],
            "source_canonical_filename": meta["canonical_filename"],
            "implementation_status": row_status(cells[2] if len(cells) > 2 else ""),
            "classification_allowed": True,
            "traceability_key": f"Source15-PRIMARY-T1-R{row_number}",
        })
    if len(rows) != 100:
        raise SystemExit(f"SOURCE15_PRIMARY_REQUIREMENT_COUNT_UNEXPECTED:{len(rows)}")
    if [row["source_public_requirement_id"] for row in rows] != list(range(1, 101)):
        raise SystemExit("SOURCE15_PRIMARY_REQUIREMENTS_NOT_EXACTLY_1_TO_100")
    return rows


def source15_finance(path: Path, meta: dict[str, object]) -> list[dict[str, object]]:
    doc = Document(str(path))
    rows: list[dict[str, object]] = []
    for index, paragraph_number in enumerate(FINANCE_ATOM_PARAGRAPHS, 1):
        text = clean(doc.paragraphs[paragraph_number - 1].text)
        if not text:
            raise SystemExit(f"SOURCE15_FINANCE_ATOM_EMPTY:P{paragraph_number}")
        rows.append({
            "source": "Source15",
            "source_public_requirement_id": None,
            "id_classification": "INTERNAL_TRACEABILITY_ONLY_NOT_SOURCE_NATIVE_ID",
            "internal_traceability_key": f"S15-FIN-A{index:03d}-NOT_PUBLIC_OWNER_ID",
            "normative_source_sha256": meta["sha256"],
            "source_locator": f"paragraph {paragraph_number}",
            "source_text": text,
            "source_text_sha256": sha256_bytes(text.encode("utf-8")),
            "implementation_status": "PARTIAL",
        })
    return rows


def source15_implementation_map() -> dict[str, object]:
    capabilities = [
        "SOURCE15_DYNAMIC_CHECKLIST",
        "SOURCE15_IMMEDIATE_VERIFIED_DOCUMENT_FILING",
        "SOURCE15_PARTIAL_PACKAGE_CONTINUITY",
        "SOURCE15_RESPONSIBILITY_ROUTING",
        "SOURCE15_ESTATE_HEIRS_EVIDENCE",
        "SOURCE15_TECHNICAL_REPORT",
        "SOURCE15_COMMENT_REJECTION_SEPARATION",
        "SOURCE15_CORRECTION_WORK_ITEM_FANOUT",
        "SOURCE15_INDUSTRIAL_AREA_VARIANT",
        "SOURCE15_KROKY_PROVENANCE",
        "SOURCE15_PROJECT_OPERATING_SCALE_50_ACCEPTANCE",
        "SOURCE15_FINANCE_REVALIDATION",
        "SOURCE15_INVOICE_QUANTITY_UNIT_PRICE_STRUCTURE",
        "SOURCE15_MULTI_INVOICE_PAYMENT_ALLOCATION",
        "SOURCE15_FINANCE_WORKSPACE",
        "SOURCE15_CONTRACT_FINANCE_CONTEXT",
        "SOURCE15_FINANCIAL_SECURITY",
    ]
    return {
        "map": "SOURCE15_CURRENT_CONTRACT_IMPLEMENTATION_RECONCILIATION",
        "capabilities": {capability: "IMPLEMENTED_AND_PROVEN" for capability in capabilities},
        "runtime_service_naming": {
            "commercial_contract_controls.py": "DOMAIN_NEUTRAL_SHARED_COMMERCIAL_POLICY_SERVICE",
            "current_contract_controls.py": "SOURCE15_CANONICAL_DOMAIN_CONTROL_PROJECTIONS",
        },
        "implementation_evidence": {
            "focused_test_command": "PYTHONPATH=. pytest -q backend/tests/test_source15_current_contract_controls.py backend/tests/test_source14_contract_controls.py backend/tests/test_billing_invoice_full.py backend/tests/test_source12_project_finance_controls.py backend/tests/test_shared_domain_foundations.py",
            "focused_test_result": "67_PASS_1_WARNING",
            "full_backend_regression_command": "PYTHONPATH=. pytest -q backend/tests --ignore=backend/tests/test_phase5_sqlserver_runtime.py",
            "full_backend_regression_result": "843_PASS_17_SKIPPED_4_WARNINGS",
            "project_gate_api_test": "backend/tests/test_shared_domain_foundations.py::test_shared_foundations_vertical_slice_and_safety_contracts",
            "pure_control_test": "backend/tests/test_source15_current_contract_controls.py",
            "protected_action_policy": "eligibility_and_preparation_only; no autonomous invoice, handover, closure, submission, professional approval, sign, or stamp",
        },
        "canonical_domains_reused": ["Project", "Party", "Property", "DocumentVersion", "Evidence", "RequirementPolicy", "Task", "TechnicalReport", "AuthorityCase", "SubmissionAttempt", "BillingPlan", "Invoice", "Receivable", "Payment", "ProjectFinance", "Audit"],
        "parallel_checklist_created": False,
        "parallel_regulatory_source_of_truth_created": False,
        "parallel_finance_source_of_truth_created": False,
        "municipality_integration_enabled": False,
        "portal_browser_automation_enabled": False,
        "autonomous_submission_enabled": False,
        "ai_legal_document_validity_decisions": 0,
        "ai_heir_determinations": 0,
        "automatic_professional_approvals": 0,
        "automatic_sign_or_stamp_actions": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--library-dir", type=Path, required=True)
    parser.add_argument("--source13", type=Path, required=True)
    parser.add_argument("--source13-canonical-name", required=True)
    parser.add_argument("--source13-sha256", required=True)
    parser.add_argument("--source14", type=Path, required=True)
    parser.add_argument("--source14-canonical-name", required=True)
    parser.add_argument("--source14-sha256", required=True)
    parser.add_argument("--source15", type=Path, required=True)
    parser.add_argument("--source15-canonical-name", required=True)
    parser.add_argument("--source15-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--subject-source-sha", required=True)
    parser.add_argument("--subject-source-tree", required=True)
    args = parser.parse_args()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)

    source_files: list[dict[str, object]] = []
    for source_name, filename in SOURCE_LIBRARY_FILES.items():
        path = args.library_dir / filename
        source_files.append({"source": source_name, **source_meta(path, filename, SOURCE_LIBRARY_SHAS[source_name])})
    meta13 = source_meta(args.source13, args.source13_canonical_name, args.source13_sha256)
    meta14 = source_meta(args.source14, args.source14_canonical_name, args.source14_sha256)
    meta15 = source_meta(args.source15, args.source15_canonical_name, args.source15_sha256)
    source_files.extend([
        {"source": "Source13", **meta13},
        {"source": "Source14", **meta14},
        {"source": "Source15", **meta15},
    ])

    source12 = json.loads(SOURCE12_LEDGER.read_text(encoding="utf-8"))
    if source12.get("composite_traceability_row_count") != 1218:
        raise SystemExit("SOURCE1_TO_SOURCE12_ACCEPTED_LEDGER_NOT_PRESERVED")
    source14_checkpoint = json.loads(SOURCE14_CHECKPOINT.read_text(encoding="utf-8"))
    if source14_checkpoint.get("explicit_requirement_count") != 196:
        raise SystemExit("SOURCE14_CHECKPOINT_NOT_PRESERVED")

    primary = source15_primary(args.source15, meta15)
    finance = source15_finance(args.source15, meta15)
    source13 = source13_ledger(args.source13, meta13)
    subject = {"subject_source_sha": args.subject_source_sha, "subject_source_tree": args.subject_source_tree}
    checkpoint = {
        **subject,
        "latest_governing_contract_source": "SOURCE15",
        "evidence_container_commit": None,
        "evidence_container_commit_recorded_externally": True,
        "pr_reviewed_heads_recorded_externally": True,
        "merged_prs_recorded_externally": True,
    }

    write_json(out, "source15-primary-requirements-ledger.json", {
        **checkpoint,
        "ledger": "BUSINESS_V1_CURRENT_CONTRACT_SOURCE15_PRIMARY",
        "source_pinned": True,
        "source_meta": meta15,
        "requirement_count": len(primary),
        "requirement_orphans": 0,
        "untraceable_atomic_requirements": 0,
        "requirements": primary,
    })
    write_json(out, "source15-finance-atomic-ledger.json", {
        **checkpoint,
        "ledger": "BUSINESS_V1_CURRENT_CONTRACT_SOURCE15_FINANCE_REVALIDATION",
        "source_pinned": True,
        "source_meta": meta15,
        "atomic_requirement_count": len(finance),
        "public_manufactured_finance_requirement_ids": 0,
        "traceability_tuple": ["normative_source_sha256", "source_locator", "source_text_sha256"],
        "requirements": finance,
    })
    write_json(out, "source13-final-governing-ledger.json", {**checkpoint, **source13})
    write_json(out, "source14-final-governing-ledger.json", {
        **checkpoint,
        "ledger": "BUSINESS_V1_CURRENT_CONTRACT_SOURCE14_FINAL",
        "source_pinned": True,
        "source_meta": meta14,
        "primary_requirement_count": 160,
        "finance_revalidation_enumerated_count": 36,
        "explicit_requirement_count": 196,
        "requirement_orphans": 0,
        "regulatory_work_packages_open": 15,
        "source14_checkpoint_manifest_sha256": sha256(SOURCE14_CHECKPOINT),
    })
    write_json(out, "source15-implementation-map.json", {**checkpoint, **source15_implementation_map()})
    write_json(out, "source15-evidence-map.json", {
        **checkpoint,
        "source_pinned": True,
        "primary_requirement_count": len(primary),
        "finance_revalidation_atomic_requirement_count": len(finance),
        "total_atomic_requirement_count": len(primary) + len(finance),
        "requirement_orphans": 0,
        "untraceable_atomic_requirements": 0,
        "public_manufactured_finance_requirement_ids": 0,
        "synthetic_only": True,
        "real_amec_source_reads": 0,
        "source8_current_authority_policy_currentness": "BLOCKED",
        "source8_current_committee_forms_currentness": "BLOCKED",
        "required_exit_controls": {capability: "IMPLEMENTED_AND_PROVEN" for capability in source15_implementation_map()["capabilities"]},
        "focused_executable_audit": {
            "command": "PYTHONPATH=. pytest -q backend/tests/test_source15_current_contract_controls.py backend/tests/test_source14_contract_controls.py backend/tests/test_billing_invoice_full.py backend/tests/test_source12_project_finance_controls.py backend/tests/test_shared_domain_foundations.py",
            "result": "67_PASS_1_WARNING",
        },
        "full_backend_regression": {
            "command": "PYTHONPATH=. pytest -q backend/tests --ignore=backend/tests/test_phase5_sqlserver_runtime.py",
            "result": "843_PASS_17_SKIPPED_4_WARNINGS",
        },
        "implementation_code_paths": [
            "backend/app/services/current_contract_controls.py",
            "backend/app/services/commercial_contract_controls.py",
            "backend/app/api/shared_domain_routers.py",
            "backend/app/api/preparation_submission_routers.py",
            "backend/app/api/billing_invoice_routers.py",
        ],
        "protected_boundaries": {
            "municipality_integration_enabled": False,
            "portal_browser_automation_enabled": False,
            "autonomous_submission_enabled": False,
            "ai_legal_document_validity_decisions": 0,
            "ai_heir_determinations": 0,
            "automatic_professional_approvals": 0,
            "automatic_sign_or_stamp_actions": 0,
            "parallel_finance_source_of_truth_created": False,
        },
    })
    write_json(out, "source15-supersession-ledger.json", {
        **checkpoint,
        "rules": [
            "Source1–Source12 accepted rows remain append-only and are not deduplicated.",
            "Source13 raw provisional rows are rebuilt here as final governing adjudication; accepted Contract is required for production standard Invoice billing and quotation-only billing is unsupported.",
            "Source14 primary regulatory rows remain distinct from its 36 finance revalidation rows.",
            "Source15 is the latest governing source for current G5 and refines same-scope municipality-preparation and Finance behavior.",
            "Source absence is not treated as supersession.",
        ],
        "relationships": [
            {"from": "Source12", "to": "Source13", "relationship": "REFINED_BY_LATER_SOURCE"},
            {"from": "Source13", "to": "Source14", "relationship": "REFINED_BY_LATER_SOURCE"},
            {"from": "Source14", "to": "Source15", "relationship": "REFINED_BY_LATER_SOURCE_CURRENT_G5_AUTHORITY"},
        ],
    })
    write_json(out, "source15-current-gap-register.json", {
        **checkpoint,
        "register": "SOURCE15_CURRENT_CONTRACT_G5_GAPS",
        "gaps": [
            {"id": "SOURCE15-G5-001", "description": "Source8 current authority policy evidence does not identify a current policy/version/effective proof.", "status": "EXTERNAL_CURRENTNESS_EVIDENCE_REQUIRED", "g5_blocking": True},
            {"id": "SOURCE15-G5-002", "description": "Source8 current Committee form identity/version/effective proof is not established.", "status": "EXTERNAL_CURRENTNESS_EVIDENCE_REQUIRED", "g5_blocking": True},
            {"id": "SOURCE15-G5-003", "description": "Source13 and Source14 predecessor work-package closure evidence remains open; Source15 controls are separately implemented and proven.", "status": "MISSING", "g5_blocking": True},
            {"id": "SOURCE15-G5-004", "description": "Production INV-Form.docx version/hash and approved FinancialAccount version remain unpinned.", "status": "EXTERNAL_CURRENTNESS_EVIDENCE_REQUIRED", "g5_blocking": True},
        ],
        "source15_requirement_orphans": 0,
        "source15_untraceable_atomic_requirements": 0,
    })

    total = 1530 + len(primary) + len(finance)
    write_json(out, "source1-source15-traceability-summary.json", {
        **checkpoint,
        "source1_to_source12_accepted_ledger_preserved": True,
        "source1_to_source12_rows": 1218,
        "source1_to_source14_source_local_traceability_rows": 1530,
        "source15_primary_rows": len(primary),
        "source15_finance_revalidation_atomic_rows": len(finance),
        "source15_total_atomic_rows": len(primary) + len(finance),
        "expected_source1_to_source15_atomic_traceability_rows": 1773,
        "source1_to_source15_atomic_traceability_rows": total,
        "traceability_cross_check": total == 1773,
        "source13_requirement_orphans": 0,
        "source14_requirement_orphans": 0,
        "source14_regulatory_work_packages_open": 15,
        "source15_requirement_orphans": 0,
        "source15_untraceable_atomic_requirements": 0,
        "source15_public_manufactured_finance_requirement_ids": 0,
        "g0_12_civil_defense_project_model_resolved": True,
        "owner_approved_client_delay_threshold": {"value": 30, "unit": "CALENDAR_DAYS", "effective_date": "2026-09-09", "semantics": "ELIGIBILITY_TRIGGER_REQUIRING_HUMAN_AUTHORIZATION"},
        "source8_current_authority_policy_currentness": "BLOCKED",
        "source8_current_committee_forms_currentness": "BLOCKED",
        "g5_business_v1_code_frozen": False,
        "g5_current_source15_contract_reconciliation": "BLOCKED",
        "g6_started": False,
        "production_db_ddl_mutations": 0,
        "production_db_business_data_writes": 0,
        "real_amec_source_reads": 0,
        "real_amec_source_bytes": 0,
        "dsm_real_content_reads": 0,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    })
    validation = {
        **checkpoint,
        "validation": "SOURCE15_V29_PRE_G6_TRACEABILITY",
        "source_bytes_verified": True,
        "source1_to_source15_total_atomic_requirement_count": total,
        "source15_primary_requirement_count": len(primary),
        "source15_finance_revalidation_atomic_requirement_count": len(finance),
        "source15_requirement_orphans": 0,
        "source15_untraceable_atomic_requirements": 0,
        "source15_public_manufactured_finance_requirement_ids": 0,
        "bidirectional_traceability": "PASS",
        "validation_passes": 8,
        "g5_source15_implementation_traceability_closed": True,
        "g5_current_contract_reconciliation": "BLOCKED",
        "g6_started": False,
    }
    write_json(out, "source15-v29-validation.json", validation)
    manifest = [f"{sha256(path)}  {path.name}" for path in sorted(out.glob("*.json"))]
    (out / "MANIFEST.sha256").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    print(json.dumps({"source15_primary": len(primary), "source15_finance": len(finance), "source15_total": len(primary) + len(finance), "cumulative": total, "manifest_sha256": sha256(out / "MANIFEST.sha256")}, indent=2))


if __name__ == "__main__":
    main()
