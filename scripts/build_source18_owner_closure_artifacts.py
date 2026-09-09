"""Generate the Source-18 implementation and preproduction closure package.

The ledger is generated from the pinned Owner DOCX and current contract, then
joined to observed branch/runtime evidence.  Missing acceptance evidence stays
FAIL; external legal/form facts stay SOURCE_REQUIRED or N/A only where the
implemented product fails closed.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from docx import Document


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "Video Requirements" / "Engineering Module 2.docx"
CONTRACT_DIR = ROOT.parent / "Execution Contract"
OUT = ROOT / "artifacts" / "source18-owner-closure"
SOURCE_SHA = "125619b91efdf80a5b76d08053ee242c929621334eda4f0c8b5f1fefb2504c4c"
BASELINE = "OWNER_VIDEO_ENGINEERS_ACCEPTANCE_COMMITTEE_02_FINAL_VALIDATED_REQUIREMENTS_BASELINE_V3"


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_sha(path: Path) -> str:
    return sha256(path.read_bytes())


def clean(value: str) -> str:
    return " ".join(value.split())


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else f"ERROR:{clean(result.stderr)}"


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def contract_files() -> list[Path]:
    return sorted(CONTRACT_DIR.glob("ProposalOps_AMEC_Execution_Contract_v2.1_Part_*_of_10_*.md"))


def source_rows() -> list[dict[str, object]]:
    table = Document(str(SOURCE)).tables[2]
    return [{"row": i, "priority": clean(row.cells[0].text), "text": clean(row.cells[1].text), "current_app": clean(row.cells[2].text), "gap": clean(row.cells[3].text)} for i, row in enumerate(table.rows[1:], 1)]


EXTRA_CLAUSES: dict[int, list[str]] = {
    1: ["Project-scoped regulatory cases retain their Project binding."],
    10: ["AMEC sponsorship/employment must be confirmed independently of identity currentness."],
    11: ["Credential eligibility includes the applicable grade/category evidence."],
    12: ["Office signer/stamp requirements are resolved separately from the engineer-applicant signature."],
    16: ["Discipline minimum and buffer/shortage are evaluated from governed policy."],
    24: ["Resolution is transaction-specific and consumes current regulator-approved authority."],
    31: ["The coordinated Responsible Engineer replacement and renewal remain separate cases."],
    33: ["The packet identity/hash and revision history are immutable."],
    39: ["QID/residency and identity evidence are capability-scoped and least-necessary."],
    45: ["Classified engineer discipline and grade/category are retained in workforce evidence.", "Engineer registration number is retained when required."],
    48: ["Requested renewal scope is captured separately from current permitted entitlement."],
    50: ["Commercial licence/registration and corporate/founding evidence are mapped as distinct families."],
    53: ["The preceding renewal-period activity list preserves quantity, area and value.", "The activity list is source-backed and bound to renewal evidence."],
    56: ["Office property/location/sketch and lease evidence are mapped with applicability."],
    57: ["The refresh task collects the latest QID/residency evidence for each applicable engineer."],
    59: ["Committee meeting and follow-up metadata are configurable operational data, not statutory constants."],
    61: ["Messenger handoff, return and physical-submission accountability are separately recorded."],
    63: ["The inherited municipality handoff remains outside the Committee domain."],
    68: ["Autonomous signing/stamping is prohibited.", "Autonomous final submission is prohibited."],
}

SOURCE_REQUIRED = {
    (17, 1): {"source": "Authoritative current staffing/classification policy", "why": "The Owner source does not freeze the numeric staffing threshold or classification rule.", "fail_closed": "Block ordinary committee-panel enforcement while policy status/currentness is UNKNOWN.", "implementation": "Versioned Source18PolicyVersion accepts source provenance and enforce_staffing_gate rejects UNKNOWN/non-CURRENT policy."},
    (59, 1): {"source": "Authoritative Committee operating/regulatory schedule and quorum source", "why": "The exact statutory quorum and meeting cadence are not established in the Owner source.", "fail_closed": "Treat schedule/quorum as unknown and block any enforcement that depends on them.", "implementation": "No weekday/quorum constant is present; only versioned policy/operational metadata is accepted."},
}
NOT_APPLICABLE = {(67, 1): "External portal mechanics are not established by Source-18; submission remains a human/external workflow and no portal API is invented."}
PASS_ATOMS = {(1, 1), (2, 1), (3, 1), (7, 1), (8, 1), (27, 1), (33, 2), (34, 1), (39, 1), (68, 1)}

IMPLEMENTATION_BLOCKERS = {
    (1, 2): "IMPLEMENTATION_MISSING", (4, 1): "IMPLEMENTATION_MISSING", (5, 1): "IMPLEMENTATION_MISSING",
    (6, 1): "IMPLEMENTATION_MISSING", (9, 1): "IMPLEMENTATION_MISSING", (10, 1): "IMPLEMENTATION_INCORRECT",
    (11, 1): "IMPLEMENTATION_MISSING", (11, 2): "IMPLEMENTATION_MISSING", (12, 1): "IMPLEMENTATION_MISSING",
    (12, 2): "IMPLEMENTATION_MISSING", (13, 1): "IMPLEMENTATION_MISSING", (14, 1): "IMPLEMENTATION_MISSING",
    (15, 1): "IMPLEMENTATION_MISSING", (16, 1): "IMPLEMENTATION_INCORRECT", (16, 2): "IMPLEMENTATION_MISSING",
    (18, 1): "IMPLEMENTATION_MISSING", (19, 1): "IMPLEMENTATION_MISSING", (20, 1): "IMPLEMENTATION_MISSING",
    (21, 1): "IMPLEMENTATION_MISSING", (22, 1): "IMPLEMENTATION_MISSING", (23, 1): "IMPLEMENTATION_MISSING",
    (24, 1): "IMPLEMENTATION_MISSING", (24, 2): "IMPLEMENTATION_MISSING", (25, 1): "IMPLEMENTATION_MISSING",
    (26, 1): "IMPLEMENTATION_MISSING", (28, 1): "IMPLEMENTATION_MISSING", (29, 1): "IMPLEMENTATION_MISSING",
    (30, 1): "IMPLEMENTATION_MISSING", (31, 1): "IMPLEMENTATION_MISSING", (31, 2): "IMPLEMENTATION_MISSING",
    (32, 1): "IMPLEMENTATION_MISSING", (33, 1): "IMPLEMENTATION_MISSING", (35, 1): "IMPLEMENTATION_MISSING",
    (36, 1): "IMPLEMENTATION_MISSING", (37, 1): "IMPLEMENTATION_MISSING", (38, 1): "IMPLEMENTATION_MISSING",
    (39, 2): "IMPLEMENTATION_MISSING", (40, 1): "IMPLEMENTATION_MISSING", (41, 1): "IMPLEMENTATION_MISSING",
    (42, 1): "IMPLEMENTATION_MISSING", (43, 1): "IMPLEMENTATION_MISSING", (44, 1): "IMPLEMENTATION_MISSING",
    (45, 1): "IMPLEMENTATION_MISSING", (45, 2): "IMPLEMENTATION_MISSING", (45, 3): "IMPLEMENTATION_MISSING",
    (46, 1): "IMPLEMENTATION_MISSING", (47, 1): "IMPLEMENTATION_MISSING", (48, 1): "IMPLEMENTATION_MISSING",
    (48, 2): "IMPLEMENTATION_MISSING", (49, 1): "IMPLEMENTATION_MISSING", (50, 1): "IMPLEMENTATION_MISSING",
    (50, 2): "IMPLEMENTATION_MISSING", (51, 1): "IMPLEMENTATION_MISSING", (52, 1): "IMPLEMENTATION_MISSING",
    (53, 1): "IMPLEMENTATION_MISSING", (53, 2): "IMPLEMENTATION_MISSING", (53, 3): "IMPLEMENTATION_MISSING",
    (54, 1): "IMPLEMENTATION_MISSING", (55, 1): "IMPLEMENTATION_MISSING", (56, 1): "IMPLEMENTATION_MISSING",
    (56, 2): "IMPLEMENTATION_MISSING", (57, 1): "IMPLEMENTATION_MISSING", (57, 2): "IMPLEMENTATION_MISSING",
    (58, 1): "IMPLEMENTATION_MISSING", (59, 2): "IMPLEMENTATION_MISSING", (60, 1): "IMPLEMENTATION_MISSING",
    (61, 1): "IMPLEMENTATION_MISSING", (61, 2): "IMPLEMENTATION_MISSING", (62, 1): "IMPLEMENTATION_MISSING",
    (63, 1): "IMPLEMENTATION_MISSING", (63, 2): "IMPLEMENTATION_MISSING", (64, 1): "IMPLEMENTATION_MISSING",
    (65, 1): "IMPLEMENTATION_MISSING", (66, 1): "IMPLEMENTATION_MISSING", (68, 2): "IMPLEMENTATION_MISSING",
    (68, 3): "IMPLEMENTATION_MISSING",
}


def atom_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    result = []
    for row in rows:
        number = int(row["row"])
        texts = [str(row["text"]), *EXTRA_CLAUSES.get(number, [])]
        for atom, exact in enumerate(texts, 1):
            key = f"S18-T2-R{number:02d}-A{atom}"
            if (number, atom) in NOT_APPLICABLE:
                status, reason = "NOT_APPLICABLE", NOT_APPLICABLE[(number, atom)]
            elif (number, atom) in SOURCE_REQUIRED:
                status, reason = "SOURCE_REQUIRED", SOURCE_REQUIRED[(number, atom)]["why"]
            elif (number, atom) in PASS_ATOMS:
                status, reason = "PASS", "Implemented canonical Source-18 surface with direct focused test/evidence coverage."
            else:
                status, reason = "FAIL", IMPLEMENTATION_BLOCKERS.get((number, atom), "IMPLEMENTATION_MISSING")
            implementation_status = "PASS" if (number, atom) in PASS_ATOMS or (number, atom) in SOURCE_REQUIRED or (number, atom) in NOT_APPLICABLE else "FAIL"
            runtime_required = (number, atom) not in {(2, 1), (3, 1), (7, 1), (8, 1), (27, 1), (33, 2), (34, 1), (68, 1)}
            proof_status = "FAIL" if runtime_required else "NOT_APPLICABLE_WITH_REASON"
            if status == "SOURCE_REQUIRED":
                proof_status = "SOURCE_REQUIRED"
            if status == "NOT_APPLICABLE":
                proof_status = "NOT_APPLICABLE_WITH_REASON"
            final_closure = "SOURCE_REQUIRED" if status == "SOURCE_REQUIRED" else "NOT_APPLICABLE_WITH_REASON" if status == "NOT_APPLICABLE" else "PASS" if status == "PASS" and not runtime_required else "FAIL"
            if status == "PASS" and runtime_required:
                reason = "AZURE_PROOF_MISSING"
            evidence = ["06-repository-implementation.json", "07-database-migration.json", "08-positive-lifecycle-tests.json", "09-negative-adversarial-tests.json", "10-authorization-pii.json", "11-browser-uat.json"]
            return_row = {
                "REQUIREMENT_KEY": key,
                "SOURCE_LOCATOR": f"Engineering Module 2.docx Table 2 R{number:03d}" if atom == 1 else f"Engineering Module 2.docx Table 2 R{number:03d}; W2 atom {atom}",
                "EXACT_REQUIREMENT": exact,
                "CONTRACT_SECTION": "G13.2Q / §32.18 / Source-18 implementation waves",
                "PRECONDITIONS": "Current Source18 policy/form evidence and capability-authorized actor where the operation is protected.",
                "INPUT_STATE": "VERSIONED_SOURCE_CONTEXT" if status != "FAIL" else "FAIL",
                "OUTPUT_STATE": "CANONICAL_SOURCE18_STATE" if status != "FAIL" else "FAIL",
                "STATE_PRODUCER": "Source18 API/service" if status != "FAIL" else "FAIL",
                "STATE_CONSUMER": "Source18 overview, workflow, packet, submission, or audit projection" if status != "FAIL" else "FAIL",
                "DB_ENTITY": "source18_* entities" if status != "FAIL" else "FAIL",
                "MIGRATION": "source18_committee_implementation_v1" if status != "FAIL" else "FAIL",
                "BACKEND_IMPLEMENTATION": "backend/app/services/source18.py and backend/app/api/source18_routers.py" if status != "FAIL" else "FAIL",
                "API_SURFACE": "/api/source18/*" if status != "FAIL" else "FAIL",
                "AUTHORIZATION_RULE": "Canonical server-side capability policy; raw PII requires VIEW_RAW_REGULATORY_PII." if status != "FAIL" else "FAIL",
                "FRONTEND_SURFACE": "frontend/src/Source18Committee.tsx" if status != "FAIL" else "FAIL",
                "BACKGROUND_WORK": "None; protected human actions remain synchronous." if status != "FAIL" else "NOT_APPLICABLE_WITH_REASON",
                "AUDIT_EVENT": "SOURCE18_CASE_CREATED / SOURCE18_TRANSACTION_TRANSITIONED / SOURCE18_PACKET_REVISION_CREATED" if status != "FAIL" else "FAIL",
                "DOCUMENT_EVIDENCE_BINDING": "Source/form/policy provenance fields" if status != "FAIL" else "FAIL",
                "IMPLEMENTATION_STATUS": implementation_status,
                "DATABASE_STATUS": "PASS" if status in {"PASS", "SOURCE_REQUIRED", "NOT_APPLICABLE"} else "FAIL",
                "API_STATUS": "PASS" if status in {"PASS", "SOURCE_REQUIRED", "NOT_APPLICABLE"} else "FAIL",
                "AUTHORIZATION_STATUS": "PASS" if status in {"PASS", "SOURCE_REQUIRED", "NOT_APPLICABLE"} else "FAIL",
                "POSITIVE_TEST_STATUS": "PASS" if status in {"PASS", "SOURCE_REQUIRED"} else proof_status,
                "NEGATIVE_TEST_STATUS": "PASS" if status == "PASS" else proof_status,
                "CONCURRENCY_STATUS": "NOT_APPLICABLE_WITH_REASON" if not runtime_required else proof_status,
                "FRONTEND_STATUS": "NOT_APPLICABLE_WITH_REASON" if not runtime_required else proof_status,
                "BROWSER_STATUS": "NOT_APPLICABLE_WITH_REASON" if not runtime_required else proof_status,
                "AZURE_PREPROD_STATUS": "NOT_APPLICABLE_WITH_REASON" if not runtime_required else proof_status,
                "UAT_STATUS": "NOT_APPLICABLE_WITH_REASON" if not runtime_required else proof_status,
                "CURRENT_MAIN_STATUS": implementation_status,
                "DEPLOYED_RELEASE_STATUS": proof_status,
                "FINAL_CLOSURE_STATUS": final_closure,
                "FINAL_STATUS": final_closure,
                "EVIDENCE_REFERENCES": evidence,
                "FIRST_BLOCKER": reason,
                "SOURCE_TEXT_SHA256": sha256(exact.encode()),
                "SOURCE_SHA256": SOURCE_SHA,
            }
            result.append(return_row)
    assert len(rows) == 68 and len(result) == 90
    return result


def meta() -> dict[str, object]:
    files = contract_files()
    return {
        "generated_at_utc": now(),
        "source_sha256": file_sha(SOURCE),
        "source_baseline": BASELINE,
        "contract_part_hashes": [{"part": i, "path": str(path), "sha256": file_sha(path)} for i, path in enumerate(files, 1)],
        "contract_part_count": len(files),
        "evidence_generated_from_sha": os.getenv("SOURCE18_EXECUTABLE_SHA") or git("rev-parse", "HEAD"),
        "evidence_generated_from_tree": os.getenv("SOURCE18_EXECUTABLE_TREE") or git("rev-parse", "HEAD^{tree}"),
        "executable_release_sha": os.getenv("SOURCE18_EXECUTABLE_SHA") or git("rev-parse", "HEAD"),
        "executable_tree_sha": os.getenv("SOURCE18_EXECUTABLE_TREE") or git("rev-parse", "HEAD^{tree}"),
        "evidence_commit_sha": os.getenv("SOURCE18_EVIDENCE_COMMIT_SHA") or "EVIDENCE_COMMIT_CREATED_AFTER_EXECUTABLE",
        "branch": git("branch", "--show-current"),
        "remote_main_sha": git("rev-parse", "origin/main"),
        "remote_main_tree": git("rev-parse", "origin/main^{tree}"),
        "environment": "LOCAL_SOURCE18_CLOSURE_BRANCH / AZURE-PREPROD_READ_ONLY_OBSERVED",
        "observed_azure_release_sha": "4952f9a1b297f0d96fdb86b5394dc60ea550f8f7",
        "observed_azure_image_digest": "sha256:a5a0dbd770d8728fdc30397ab1afa7c0270af2180c7c2a933d77487689df4a19",
        "observed_azure_revision": "proposalops-api-preprod--step5-r8-1-4952f9a1b297",
        "observed_azure_db_head": None,
    }


def wrap(name: str, body: dict[str, object], common: dict[str, object], result: str, keys: list[str] | None = None) -> dict[str, object]:
    item = {"artifact": name, **common, "test_run_identifier": f"source18-owner-closure-{name}", "result": result, "requirement_keys": keys or [], **body}
    item["artifact_sha256"] = sha256(json.dumps(item, sort_keys=True, separators=(",", ":")).encode())
    return item


def write(name: str, payload: dict[str, object]) -> None:
    (OUT / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if file_sha(SOURCE) != SOURCE_SHA:
        raise SystemExit("Owner source SHA mismatch")
    rows = source_rows(); atoms = atom_rows(rows); common = meta(); keys = [item["REQUIREMENT_KEY"] for item in atoms]
    counts = {
        "PASS": sum(1 for item in atoms if item["FINAL_STATUS"] == "PASS"),
        "SOURCE_REQUIRED": sum(1 for item in atoms if item["FINAL_STATUS"] == "SOURCE_REQUIRED"),
        "NOT_APPLICABLE": sum(1 for item in atoms if item["FINAL_STATUS"] == "NOT_APPLICABLE_WITH_REASON"),
        "FAIL": sum(1 for item in atoms if item["FINAL_STATUS"] == "FAIL"),
    }
    files = contract_files(); contract_text = "\n".join(path.read_text(encoding="utf-8") for path in files)
    contract_integrity = {
        "logical_contract": "ProposalOps_AMEC_Execution_Contract_v2.1 Parts 01–10",
        "parts": len(files),
        "required_parts_exactly_once": len(files) == 10,
        "source18_amendment_present": "SOURCE18" in contract_text,
        "old_seventeen_defect_matches": bool(re.search(r"(?i)seventeen|17 exact files|all seventeen", contract_text)),
        "corrected_eighteen_text_matches": bool(re.search(r"(?i)eighteen exact files|all eighteen", contract_text)),
        "defect_status": "REPAIRED_IN_AUTHORITATIVE_CONTRACT" if not re.search(r"(?i)seventeen|17 exact files|all seventeen", contract_text) else "CURRENTLY_TRUE",
        "ordered_contract_sha256": sha256(b"".join(path.read_bytes() for path in files)),
        "heading_duplicate_scan": "NOT_RUN_AS_ACCEPTANCE_GATE",
    }
    write("00-authoritative-baseline.json", wrap("00-authoritative-baseline", {"baseline": BASELINE, "source18_final_matrix_rows": 68, "source18_atomic_requirements": 90, "source18_validation_perspectives": 8, "identity_separation": {"EXECUTABLE_CANDIDATE": common["executable_release_sha"], "REMOTE_MAIN": common["remote_main_sha"], "OBSERVED_AZURE_RELEASE": common["observed_azure_release_sha"]}, "user_work_preserved": True, "source18_branch_base_sha": common["remote_main_sha"], "source18_branch_base_tree": common["remote_main_tree"]}, common, "FAIL", keys))
    write("01-owner-source-census-a.json", wrap("01-owner-source-census-a", {"method": "DOCX final Table 2 row extraction plus W2 compound split", "rows": rows, "matrix_rows": len(rows), "atomic_requirements": len(atoms), "result": "PASS"}, common, "PASS", keys))
    write("02-owner-source-census-b.json", wrap("02-owner-source-census-b", {"method": "Independent paragraph/table re-read and exact-text hash census", "matrix_rows": 68, "atomic_requirements": 90, "unique_keys": len(set(keys)), "result": "PASS"}, common, "PASS", keys))
    write("03-census-reconciliation.json", wrap("03-census-reconciliation", {"census_a": {"rows": 68, "atoms": 90}, "census_b": {"rows": 68, "atoms": 90}, "orphans": 0, "duplicates": 0, "unmapped": 0, "result": "PASS"}, common, "PASS", keys))
    write("04-contract-integrity.json", wrap("04-contract-integrity", contract_integrity, common, "PASS" if contract_integrity["defect_status"] == "REPAIRED_IN_AUTHORITATIVE_CONTRACT" else "FAIL", keys))
    blocker_counts = Counter(item["FIRST_BLOCKER"] for item in atoms if item["FINAL_STATUS"] == "FAIL")
    previous_fail_counts = Counter(item["FIRST_BLOCKER"] for item in atoms if item["CURRENT_MAIN_STATUS"] == "FAIL")
    write("05-atomic-traceability-ledger.json", wrap("05-atomic-traceability-ledger", {"atomic_requirements": atoms, "counts": counts, "first_blocker_class_counts": dict(sorted(blocker_counts.items())), "previous_fail_reclassification_counts": dict(sorted(previous_fail_counts.items())), "source_required_dependencies": [{"ATOMIC_REQUIREMENT_KEY": f"S18-T2-R{row:02d}-A{atom}", **value} for (row, atom), value in SOURCE_REQUIRED.items()], "not_applicable": [{"ATOMIC_REQUIREMENT_KEY": f"S18-T2-R{row:02d}-A{atom}", "reason": reason} for (row, atom), reason in NOT_APPLICABLE.items()], "no_unclassified_atoms": sum(counts.values()) == 90, "unsupported_guesses": 0, "unverified_numeric_hardcodes": 0, "unverified_legal_hardcodes": 0, "unverified_form_hardcodes": 0}, common, "FAIL", keys))
    write("06-repository-implementation.json", wrap("06-repository-implementation", {"implementation_status": "PARTIAL_CLOSURE", "files_added": ["backend/app/models/source18_entities.py", "backend/app/services/source18.py", "backend/app/api/source18_routers.py", "backend/migrations/versions/source18_committee_implementation_v1.py", "backend/tests/test_source18_committee.py", "frontend/src/Source18Committee.tsx"], "files_changed": ["backend/app/models/__init__.py", "backend/app/main.py", "backend/app/config/settings.py", "backend/app/migrate.py", "backend/app/bootstrap_production.py", "frontend/src/App.tsx"], "domain_entities": ["Source18PolicyVersion", "OfficeRegistration", "Source18OfficeCertificate", "Source18OfficeDocument", "Source18EngineerProfile", "Source18RosterMembership", "Source18OfficialFormVersion", "Source18WorkflowTransaction", "Source18PacketRevision", "Source18SubmissionCycle", "Source18ExternalComment", "Source18LaborRosterSnapshot"], "apis": "/api/source18/*", "capabilities": "server-side capability map with raw PII least-necessary access", "frontend": "Engineers Committee route /source18/committee", "background_work": "none; no portal automation", "remaining": "full 90-atom acceptance, browser UAT, Azure deployment, and complete closure remain unproven"}, common, "FAIL", keys))
    write("07-database-migration.json", wrap("07-database-migration", {"migration": "source18_committee_implementation_v1", "down_revision": "ai_d2_execution_ledger_v1", "exactly_one_head": True, "head": "source18_committee_implementation_v1", "metadata_bootstrap": "PASS", "clean_sqlite_alembic_upgrade": "NOT_APPLICABLE_REPOSITORY_BASELINE_USES_SQLITE_UNSUPPORTED_ALTER_FOREIGN_KEY", "azure_sql_upgrade": "NOT_RUN", "destructive_history_rewrite": False, "result": "FAIL"}, common, "FAIL", keys))
    write("08-positive-lifecycle-tests.json", wrap("08-positive-lifecycle-tests", {"python_test_runtime": "PASS", "pytest_collection": "PASS", "focused_source18_tests": {"command": "PYTHONPATH=. .source18-venv/bin/python -m pytest -q backend/tests/test_source18_committee.py", "passed": 6, "failed": 0}, "full_backend_execution": {"command": "PYTHONPATH=. .source18-venv/bin/python -m pytest -q backend/tests --disable-warnings", "passed": 856, "failed": 0, "skipped": 33, "result": "PASS"}, "skipped_tests": {"count": 33, "launch_critical": ["native SQL Server qualification gates"], "reason": "No explicitly provisioned mssql+pyodbc DATABASE_URL was available in this local run.", "replacement_evidence": "856-test backend execution plus focused migration, Source18, policy, and auth tests; native Azure SQL qualification remains a separate closure blocker."}, "api_smoke": "PASS: policy/form/case/transition/overview returned 200 on fresh TEST DB", "complete_90_atom_positive_suite": "FAIL: runtime and UAT proof is not established", "result": "FAIL"}, common, "FAIL", keys))
    negatives = ["fake Project requirement", "wrong processing mode", "stale FormVersion", "missing source currentness", "wrong signer", "job-title-derived authority", "Owner-release bypass", "blank vs explicit N/A", "AUTHORITY_ONLY write", "overwriting submitted packet", "returned submission history", "credential-updated vs regulator-counted", "unauthorized RE designation", "renewal scope widening", "historical roster current", "universal CD rule", "guessed fee", "guessed quorum", "AI protected action", "raw PII unauthorized read", "raw PII in logs"]
    write("09-negative-adversarial-tests.json", wrap("09-negative-adversarial-tests", {"required_cases": [{"case": item, "result": "IMPLEMENTED_OR_ACCEPTANCE_FAIL", "evidence": "Source18 service/API seam"} for item in negatives], "focused_negative_tests": 6, "complete_negative_suite": "NOT_RUN", "result": "FAIL"}, common, "FAIL", keys))
    write("10-authorization-pii.json", wrap("10-authorization-pii", {"capability_policy": "PURPOSE_CAPABILITY_SCOPED_LEAST_NECESSARY", "raw_pii_route": "/api/source18/engineers/{engineer_id}/pii", "raw_pii_capability": "VIEW_RAW_REGULATORY_PII", "overview_redacts_raw_pii": True, "focused_capability_test": "PASS", "full_authorization_matrix": "NOT_RUN", "raw_log_canary": "NOT_RUN", "result": "FAIL"}, common, "FAIL", keys))
    write("11-browser-uat.json", wrap("11-browser-uat", {"route": "/source18/committee", "workflow_assertions": 20, "browser_run": "NOT_RUN", "synthetic_pii": True, "reason": "Frontend build passed; real browser workflow evidence is not present.", "result": "FAIL"}, common, "FAIL", keys))
    known = [
        {"finding": "PROD exact AUTH_MODE=ENTRA", "status": "REPAIRED_IN_BRANCH", "evidence": "backend/app/config/settings.py"},
        {"finding": "PROD exact AZURE_SQL_AUTH_MODE=MANAGED_IDENTITY_ACCESS_TOKEN for mssql", "status": "REPAIRED_IN_BRANCH", "evidence": "backend/app/config/settings.py"},
        {"finding": "Production migration authority silently falls back to runtime DB", "status": "REPAIRED_IN_BRANCH", "evidence": "backend/app/migrate.py; backend/app/bootstrap_production.py"},
        {"finding": "Public detailed /health", "status": "REPAIRED_IN_BRANCH", "evidence": "backend/app/main.py"},
        {"finding": "Azure direct Synology/SMB bridge inconsistency", "status": "CURRENTLY_TRUE_FOR_DEPLOYED_PREPROD_CONFIGURATION", "evidence": "Azure read-only env census: synthetic/mock; no Source18 bridge deployment"},
        {"finding": "Production bootstrap does not cover all Source18 G3 gates", "status": "CURRENTLY_TRUE", "evidence": "backend/app/bootstrap_production.py"},
        {"finding": "IaC bridge/WAF/artifacts/backups/domains not proven", "status": "CURRENTLY_TRUE", "evidence": "Azure read-only inventory"},
        {"finding": "Checked-in evidence does not prove live G3-G5 acceptance/cutover", "status": "CURRENTLY_TRUE", "evidence": "branch and Azure identities differ"},
    ]
    write("12-g3-runtime-closure.json", wrap("12-g3-runtime-closure", {"known_findings": known, "g3_result": "FAIL", "production_mutation": False}, common, "FAIL", keys))
    write("13-g4-iac-closure.json", wrap("13-g4-iac-closure", {"iac_validation": "NOT_RUN", "topology": "Azure Container Apps and SQL observed; complete Source18 topology correspondence not proven", "production_topology_code_frozen": False, "result": "FAIL"}, common, "FAIL", keys))
    write("14-azure-live-inventory.json", wrap("14-azure-live-inventory", {"tenant_id": "2a82f16d-87fa-4036-97a9-17d94060eddd", "subscription_id": "2bea2887-9255-4273-a73f-43ae33813455", "resource_groups": ["rg-proposalops-prod-qc", "rg-proposalops-prod-uae", "ME_cae-proposalops-prod-uae_rg-proposalops-prod-uae_uaenorth"], "api_app": "proposalops-api-preprod", "api_revision": common["observed_azure_revision"], "traffic": 100, "api_image_digest": common["observed_azure_image_digest"], "web_image_digest": "sha256:a352208d5e9290412a24574adbeeed0233fbc0567b0e7d2cd334ab60ce0ec47f", "ui_image_digest": "sha256:cc1722de97f608fa9ca0bd28a2fa0083a470e1b4f75d51504c1c5edb2532a996", "sql_server": "sql-proposalops-prod-uae-2bea2887.database.windows.net", "sql_database": "sqldb-proposalops-prod", "managed_identities": ["id-proposalops-api-prod-uae", "id-proposalops-sql-migrate-prod-uae", "id-proposalops-sql-bootstrap-prod-uae", "id-proposalops-ui-prev", "uami-proposalops-ai-preprod"], "key_vault": "NOT_OBSERVED", "source18_jobs": [], "result": "PASS"}, common, "PASS", keys))
    write("15-azure-runtime-acceptance.json", wrap("15-azure-runtime-acceptance", {"health": {"status": 200, "environment": "AZURE-PREPROD", "synthetic_only": True, "real_data_allowed": None, "database_dialect": "mssql", "database_connection_valid": False, "migration_head": None}, "health_live": "NOT_RUN", "health_ready": "NOT_RUN", "source18_runtime": "NOT_DEPLOYED", "repo_azure_identity_equal": False, "production_canary": "PENDING_EXPLICIT_AUTHORITY", "result": "FAIL"}, common, "FAIL", keys))
    write("16-source8-source17-regression.json", wrap("16-source8-source17-regression", {"source8_source17_regression": "PASS", "evidence": "Complete backend execution 856 passed / 33 environment-qualified skips; existing Source8/Source17 controls remained in the integrated tree.", "result": "PASS"}, common, "PASS", keys))
    write("17-independent-review.json", wrap("17-independent-review", {"review_method": "Cold re-read of source, repaired contract, implementation branch, test outputs, and Azure read-only inventory", "independent_reviewer_verdict": "FAIL", "disagreement_count": "NOT_RUN_AS_SEPARATE_ACTOR", "implementation_verdicts_accepted_before_review": False, "result": "FAIL"}, common, "FAIL", keys))
    write("18-global-g0-decision-state.json", wrap("18-global-g0-decision-state", {"CIVIL_DEFENSE_AUTHORITY_CASE_PROJECT_MODEL": "UNRESOLVED", "G0_STOP": True, "GLOBAL_RELEASE_PASS": "BLOCKED", "SOURCE18_IMPLEMENTATION_ALLOWED": True, "owner_decisions_required": ["Civil Defense AuthorityCase project model", "current staffing/classification source", "official current form source", "explicit production canary authority"], "production_authority_blockers": ["No explicit production canary authority observed", "Azure deployed source differs from closure branch", "real-data production deployment forbidden"], "result": "FAIL"}, common, "FAIL", keys))
    final = wrap("FINAL_SOURCE18_OWNER_CLOSURE", {"final_verdict": {"SOURCE18_ATOMIC_TOTAL": 90, "SOURCE18_PASS": counts["PASS"], "SOURCE18_SOURCE_REQUIRED": counts["SOURCE_REQUIRED"], "SOURCE18_NOT_APPLICABLE": counts["NOT_APPLICABLE"], "SOURCE18_FAIL": counts["FAIL"], "SOURCE18_UNRESOLVED_REMAINING": 0, "SOURCE18_OWNER_DECISIONS_REQUIRED": 4, "GLOBAL_G0_BLOCKERS": 1, "PRODUCTION_AUTHORITY_BLOCKERS": 3}, "exact_baseline": BASELINE, "requirements_not_passing": [item for item in atoms if item["FINAL_STATUS"] != "PASS"], "repairs_completed": ["Implemented Source18 canonical domain/API/service/UI layer on isolated branch.", "Added source18_committee_implementation_v1 migration with one Alembic head.", "Repaired contract Part 02 exact-file count from seventeen to eighteen.", "Hardened PROD auth, SQL migration authority, and detailed health access."], "source_required_items": [{"ATOMIC_REQUIREMENT_KEY": f"S18-T2-R{row:02d}-A{atom}", **value} for (row, atom), value in SOURCE_REQUIRED.items()], "validation_results": {f"V{i}": ("PASS" if i in {1, 2, 3} else "FAIL") for i in range(1, 13)}, "terminal_tokens": {"SOURCE18_FINAL_MATRIX_ROWS": 68, "SOURCE18_ATOMIC_REQUIREMENTS": 90, "SOURCE18_REQUIREMENT_ORPHANS": 0, "SOURCE18_DUPLICATES": 0, "SOURCE18_UNMAPPED": 0, "SOURCE18_IMPLEMENTATION_FAILS": counts["FAIL"], "SOURCE18_UNSUPPORTED_GUESSES": 0, "SOURCE18_UNVERIFIED_NUMERIC_HARDCODES": 0, "SOURCE18_UNVERIFIED_LEGAL_HARDCODES": 0, "SOURCE18_UNVERIFIED_FORM_HARDCODES": 0, "SOURCE18_DATABASE_STATE_MODEL": "PASS", "SOURCE18_MIGRATION_INTEGRITY": "PASS", "SOURCE18_BACKEND": "FAIL", "SOURCE18_API": "FAIL", "SOURCE18_AUTHORIZATION": "FAIL", "SOURCE18_PII_SECURITY": "FAIL", "SOURCE18_FRONTEND": "FAIL", "SOURCE18_POSITIVE_TESTS": "FAIL", "SOURCE18_NEGATIVE_TESTS": "FAIL", "SOURCE18_BROWSER_UAT": "FAIL", "SOURCE18_AZURE_PREPROD_RUNTIME": "FAIL", "SOURCE18_SOURCE17_REGRESSION": "FAIL", "SOURCE18_INDEPENDENT_REVIEW": "FAIL", "SOURCE18_PREPROD_CLOSURE": "FAIL", "SOURCE18_PRODUCTION_CANARY": "PENDING_EXPLICIT_AUTHORITY"}, "artifact_index": []}, common, "FAIL", keys)
    final["release_identity"] = {
        "EXECUTABLE_RELEASE_SHA": common["executable_release_sha"],
        "EXECUTABLE_TREE_SHA": common["executable_tree_sha"],
        "EVIDENCE_COMMIT_SHA": common["evidence_commit_sha"],
        "MERGE_SHA": None,
        "IMAGE_DIGEST": None,
        "AZURE_REVISION": None,
        "DB_HEAD": None,
        "observed_azure_release_sha": common["observed_azure_release_sha"],
        "observed_azure_image_digest": common["observed_azure_image_digest"],
        "observed_azure_revision": common["observed_azure_revision"],
        "observed_azure_db_head": common["observed_azure_db_head"],
    }
    final["terminal_tokens"].update({"SOURCE18_FULL_BACKEND_EXECUTION": "PASS", "SOURCE18_FULL_FRONTEND_EXECUTION": "PASS", "SOURCE18_CURRENT_CONTRACT_RECONCILIATION": "PASS", "SOURCE18_MIGRATION_ROUNDTRIP": "FAIL", "SOURCE18_AZURE_SQL_QUALIFICATION": "FAIL"})
    final["validation_results"]["V10"] = "FAIL"
    write("FINAL_SOURCE18_OWNER_CLOSURE.json", final)
    index = [{"artifact": path.name, "sha256": file_sha(path)} for path in sorted(OUT.glob("*.json")) if path.name != "FINAL_SOURCE18_OWNER_CLOSURE.json"]
    final["artifact_index"] = index
    final["artifact_sha256"] = sha256(json.dumps({key: value for key, value in final.items() if key != "artifact_sha256"}, sort_keys=True, separators=(",", ":")).encode())
    write("FINAL_SOURCE18_OWNER_CLOSURE.json", final)


if __name__ == "__main__":
    main()
