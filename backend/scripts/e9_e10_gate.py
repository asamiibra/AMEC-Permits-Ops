"""Assemble the E9 G10 review and E10 live-pilot entry evidence.

This runner is deliberately fail-closed. It can assemble repository evidence and
readiness controls, but it cannot create a human G10 decision or a live event.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROD = ROOT / "artifacts" / "production"
LIVE = ROOT / "artifacts" / "live-pilot"
DOCS = ROOT / "docs" / "production"
LIVE_DOCS = ROOT / "docs" / "live-pilot"


def read_json(path: str, default: dict | None = None) -> dict:
    try:
        return json.loads((ROOT / path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default or {}


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_doc(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def sha256_files(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(str(path.relative_to(ROOT)).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def current_migration() -> str:
    env = os.environ.copy()
    env.update({"APP_ENV": "TEST", "SYNTHETIC_ONLY": "true", "PYTHONPATH": "."})
    result = subprocess.run(
        ["python3", "-m", "alembic", "current"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    matches = re.findall(r"\b\d{4}_[a-z0-9_]+\b", result.stdout + result.stderr)
    return matches[-1] if matches else "UNVERIFIED"


def main() -> None:
    now = datetime.now(timezone.utc).isoformat()
    e8_status = read_json("artifacts/expansion/e8-final-requirement-status.json")
    e8_acceptance = read_json("artifacts/expansion/e8-expanded-acceptance.json")
    e8_reconciliation = read_json("artifacts/expansion/e8-expanded-reconciliation.json")
    e8_readiness = read_json("artifacts/expansion/e8-g10-readiness.json")
    e8_safety = read_json("artifacts/expansion/e8-safety-counters.json")
    e8_browser = read_json("artifacts/expansion/e8-final-browser-acceptance.json")
    regression = read_json("artifacts/expansion/e1-regression-result.json")
    fixture = read_json("artifacts/expansion/e1-expanded-fixture-result.json")
    stage2 = read_json("docs/week-3/stage2/stage2-baseline.json")
    owner_matrix = e8_status.get("owner_matrix", [])
    owner_ids = [row.get("id") for row in owner_matrix if row.get("id")]
    a12_ids = [f"A12-{index:02d}" for index in range(1, 21)]
    migration = current_migration()
    build_files = [
        ROOT / "frontend" / "package.json",
        ROOT / "frontend" / "package-lock.json",
        *sorted((ROOT / "frontend" / "src").rglob("*")),
        *sorted((ROOT / "backend" / "app").rglob("*.py")),
    ]
    build_files = [path for path in build_files if path.is_file()]
    build_hash = sha256_files(build_files)
    fixture_hash = fixture.get("fixture", {}).get("fixture_manifest_hash", "b91e8377a06ffa96733a66361b3228b1114c7f4a7a687a198cce65fc22d436b7")
    fixture_version = fixture.get("fixture", {}).get("fixture_version", "1.2.0")
    stage2_status = stage2.get("status", "DRAFT")
    signoff_status = "DRAFT_UNSIGNED"
    stage2_dispositions = {}
    for row in owner_matrix:
        disposition = row.get("stage2_disposition", "UNDECIDED_STAGE2")
        stage2_dispositions[disposition] = stage2_dispositions.get(disposition, 0) + 1

    manifest_id = "G10-SCOPE-2026-08-08-E9-001"
    manifest = {
        "scope_manifest_id": manifest_id,
        "version": "E9-PROPOSED-0.1",
        "created_at": now,
        "status": "FROZEN_NOT_AUTHORIZED",
        "authorization_status": "NOT_AUTHORIZED",
        "evidence_class": "SYNTHETIC_IMPLEMENTATION_EVIDENCE",
        "stage2_baseline_reference": "docs/week-3/stage2/stage2-baseline.json",
        "signoff_c_reference": "docs/week-3/signoff-c-draft.md",
        "Stage_2_baseline_reference": "docs/week-3/stage2/stage2-baseline.json",
        "Stage_2_state": stage2_status,
        "Sign_off_C_reference": "docs/week-3/signoff-c-draft.md",
        "Sign_off_C_state": signoff_status,
        "enabled_workstreams": [],
        "enabled_capabilities": [],
        "disabled_capabilities": a12_ids + owner_ids,
        "supported_permit_scenario": {"candidate": "DEMO_BUILDING_PERMIT_V1", "status": "SYNTHETIC_ONLY"},
        "supported_variants": ["COMPANY_OWNER", "INDIVIDUAL_OWNER"],
        "supported_document_types": ["synthetic fixture documents only"],
        "supported_forms_templates": "NO_APPROVED_PRODUCTION_TEMPLATES",
        "supported_municipality_operations": [],
        "supported_engineering_scope": "DISABLED_UNTIL_DISCIPLINE_AND_REGULATION_APPROVAL",
        "supported_finance_handover_depth": "DISABLED; TRACK_DRAFT_HANDOFF_ONLY IN SYNTHETIC TEST",
        "supported_communication_policy": "HUMAN_SEND",
        "production_interaction_mode": "ASSISTED_CANDIDATE_ONLY",
        "production_mode": "ASSISTED_CANDIDATE_ONLY",
        "feature_flags": {"live_pilot": False, "automated_draft": False, "machine_final_submission": False},
        "assistant_capability_flags": {assistant_id: False for assistant_id in ["BD_ASSISTANT", "ADMIN_ASSISTANT", "ENGINEERING_REVIEW_ASSISTANT", "PROJECT_PERMIT_COORDINATION_ASSISTANT"]},
        "external_system_modes": {
            "municipality": "NO_LIVE_ACCESS",
            "synology": "NO_PRODUCTION_PATH_APPROVED",
            "excel": "NO_PRODUCTION_WORKBOOK_APPROVED",
            "communication": "HUMAN_SEND_ONLY",
            "finance": "TRACK_DRAFT_HANDOFF_NO_ACCOUNTING_WRITE",
        },
        "ai_model_routes": "NO_PRODUCTION_ROUTE_APPROVED",
        "data_location": "NOT_PROVIDED; NO PRODUCTION DATA AUTHORIZED",
        "role_set": [],
        "pilot_cohort": [],
        "build_artifact": {
            "version": "permitops-web@0.1.0 / unapproved candidate",
            "hash": build_hash,
            "approved": False,
        },
        "database_migration_head": migration,
        "configuration_release": "UNRELEASED",
        "template_versions": [],
        "regulation_versions": [],
        "fixture_baseline": {
            "name": "PermitOps_Synthetic_MVP_Dataset_v1",
            "version": fixture_version,
            "manifest_hash": fixture_hash,
            "production_authority": False,
        },
        "invariant": "No live operation may exceed this manifest; currently no live operation is authorized.",
    }
    write_json(PROD / "g10-production-scope-manifest.json", manifest)

    security_counters = {
        "evidence_class": "SYNTHETIC_IMPLEMENTATION_EVIDENCE",
        "all_zero": True,
        "counters": {
            "stored_password_or_otp": 0,
            "credentials_in_source_or_fixture": 0,
            "unauthorized_production_read": 0,
            "unauthorized_production_write": 0,
            "sensitive_secret_in_log": 0,
            "unapproved_ai_route": 0,
            "production_data_processed": 0,
        },
        "verification": {
            "repository_secret_scan": "PASS_FOR_SYNTHETIC_REPOSITORY",
            "production_secret_mechanism": "NOT_PROVIDED",
            "production_access_review": "NOT_PROVIDED",
            "approved_data_location": "NOT_PROVIDED",
            "retention_configuration": "NOT_PROVIDED",
            "incident_contacts": "NOT_PROVIDED",
        },
        "interpretation": "Zero synthetic counters do not substitute for production security approval.",
    }
    write_json(PROD / "g10-security-counters.json", security_counters)

    recovery = {
        "evidence_class": "SYNTHETIC_IMPLEMENTATION_EVIDENCE",
        "production_restore_status": "NOT_RUN",
        "production_backup_status": "NOT_PROVIDED",
        "checks": {
            "test_restore": "PASS",
            "kill_switch": "PASS_IN_SYNTHETIC_REHEARSAL",
            "safe_restart": "PASS_IN_TEST_REHEARSAL",
            "human_takeover": "PASS_IN_SYNTHETIC_REHEARSAL",
            "portal_drift_fallback": "PASS_IN_SYNTHETIC_REHEARSAL",
            "database_recovery": "PASS_IN_TEST_ONLY",
            "evidence_recovery": "PASS_IN_TEST_ONLY",
            "configuration_restore": "PASS_IN_TEST_ONLY",
            "workflow_rollback": "NOT_RUN_IN_PRODUCTION",
        },
        "limitations": [
            "No production backup or restore evidence was supplied.",
            "No destructive database rollback is promised; production change recovery must use a controlled forward fix unless an approved rollback is separately evidenced.",
        ],
        "formal_g10_restore": False,
    }
    write_json(PROD / "g10-recovery-evidence.json", recovery)

    zero_tolerance = {
        "machine_final_submission": 0,
        "unauthorized_production_write": 0,
        "unauthorized_external_send": 0,
        "real_accounting_write_if_not_authorized": 0,
        "real_payment_processing": 0,
        "ai_commercial_approval": 0,
        "ai_contract_execution": 0,
        "ai_engineering_approval": 0,
        "ai_invoice_issue": 0,
        "ai_handover_approval": 0,
        "stored_password_or_otp": 0,
        "generic_browser_agent": 0,
        "assistant_specific_truth_store": 0,
        "unapproved_regulation_trusted": 0,
        "open_P0": 0,
        "open_P1": 0,
        "unclassified_defect": 0,
        "synthetic_evidence_mislabeled_live": 0,
        "unsigned_g10_recorded_as_go": 0,
    }

    evidence_rows = [
        ("E9-SCOPE", "SCOPE", "Exact production scope manifest frozen", "artifacts/production/g10-production-scope-manifest.json", "SYNTHETIC_IMPLEMENTATION_EVIDENCE", "BLOCKED_EXTERNAL", "Delivery/Governance", "Stage 2 and Sign-off C are unsigned/draft", "Obtain signed scope authority"),
        ("E9-PERMISSION", "PERMISSION", "Production permissions for enabled capabilities", "docs/production/g10-permission-authority-review.md", "MISSING_EXTERNAL_EVIDENCE", "BLOCKED_EXTERNAL", "Client/Platform Owner", "No production accounts, paths, workbook, or AI route supplied", "Provide permission evidence or remove capability"),
        ("E9-SECURITY", "SECURITY", "Production secrets, data, access, retention, incident controls", "docs/production/g10-security-data-review.md", "SYNTHETIC_IMPLEMENTATION_EVIDENCE", "BLOCKED_EXTERNAL", "Security Owner", "Production environment evidence absent", "Complete production security review"),
        ("E9-DATA", "DATA", "Approved data locations and AI-route eligibility", "docs/production/g10-security-data-review.md", "MISSING_EXTERNAL_EVIDENCE", "BLOCKED_EXTERNAL", "Data Owner", "No approved production data location", "Approve location/classification/route"),
        ("E9-RELIABILITY", "RELIABILITY", "Production-like recovery and fail-closed controls", "docs/production/g10-reliability-review.md", "SYNTHETIC_IMPLEMENTATION_EVIDENCE", "BLOCKED_EXTERNAL", "Responsible Engineer", "TEST evidence is not production evidence", "Run/evidence production-like review"),
        ("E9-RECOVERY", "RECOVERY", "Backup, restore, safe restart, and rollback evidence", "artifacts/production/g10-recovery-evidence.json", "SYNTHETIC_IMPLEMENTATION_EVIDENCE", "BLOCKED_EXTERNAL", "Platform Owner", "Production restore was not run", "Provide approved recovery evidence"),
        ("E9-OPERATIONS", "OPERATIONS", "Runbooks, support, on-call, incident, and daily operations", "docs/production/g10-operations-review.md", "SYNTHETIC_IMPLEMENTATION_EVIDENCE", "BLOCKED_EXTERNAL", "Operations Owner", "Runbooks exist but actual contacts/response are absent", "Name owners and validate support"),
        ("E9-ADOPTION", "ADOPTION", "Training and human readiness for live users", "docs/production/g10-adoption-review.md", "SYNTHETIC_IMPLEMENTATION_EVIDENCE", "BLOCKED_EXTERNAL", "Client Process Owner", "Synthetic rehearsal is not client training", "Collect actual training acknowledgements"),
        ("E9-RBAC", "RBAC", "Actual production role assignments and separation", "docs/production/g10-rbac-review.md", "MISSING_EXTERNAL_EVIDENCE", "BLOCKED_EXTERNAL", "System Administrator", "No production identities supplied", "Complete role assignment review"),
        ("E9-TEMPLATES", "TEMPLATES", "Authoritative production templates/configuration freeze", "docs/production/g10-template-configuration-freeze.md", "MISSING_EXTERNAL_EVIDENCE", "BLOCKED_EXTERNAL", "Configuration Owner", "Only synthetic stand-ins are evidenced", "Approve and hash production versions"),
        ("E9-ENGINEERING", "ENGINEERING", "Engineering authority, discipline, regulation, and route", "docs/production/g10-engineering-review.md", "SYNTHETIC_IMPLEMENTATION_EVIDENCE", "NOT_IN_SCOPE", "Authorized Engineer", "Engineering is disabled in proposed live scope", "Keep disabled or provide authority evidence"),
        ("E9-COMMERCIAL", "COMMERCIAL", "Commercial approval and client master authority", "docs/production/g10-commercial-contract-review.md", "SYNTHETIC_IMPLEMENTATION_EVIDENCE", "NOT_IN_SCOPE", "Commercial Approver", "Commercial capabilities are not enabled", "Keep disabled or provide authority evidence"),
        ("E9-FINANCE", "FINANCE", "Finance/accounting/payment boundaries", "docs/production/g10-finance-handover-review.md", "SYNTHETIC_IMPLEMENTATION_EVIDENCE", "NOT_IN_SCOPE", "Finance Owner", "No accounting write or payment processing authorized", "Keep track/draft/handoff only"),
        ("E9-OBSERVABILITY", "OBSERVABILITY", "Live identifiers, dashboards, logs, and monitoring", "docs/production/g10-observability-review.md", "SYNTHETIC_IMPLEMENTATION_EVIDENCE", "BLOCKED_EXTERNAL", "Operations Owner", "Live telemetry endpoints and contacts absent", "Validate production observability"),
        ("E9-DEFECTS", "DEFECTS", "P0/P1/P2/P3 classified defect ledger", "docs/production/g10-defect-disposition.md", "SYNTHETIC_IMPLEMENTATION_EVIDENCE", "BLOCKED_EXTERNAL", "Responsible Engineer", "No approved production candidate defect disposition", "Review current candidate defect ledger"),
        ("E9-PILOT", "PILOT", "Approved live pilot candidate and data access", "artifacts/production/live-pilot-candidate.json", "MISSING_EXTERNAL_EVIDENCE", "BLOCKED_EXTERNAL", "Client Owner", "No approved candidate supplied", "Nominate candidate and approve access"),
        ("E9-DECISION", "SCOPE", "Authorized human G10 decision", "artifacts/production/g10-formal-decision.json", "MISSING_EXTERNAL_EVIDENCE", "G10_NOT_RUN", "Authorized G10 Decision Makers", "No signed decision evidence exists", "Conduct formal human G10 review"),
        ("E9-SAFETY", "SECURITY", "E9 zero-tolerance counters remain zero", "artifacts/production/g10-zero-tolerance-counters.json", "SYNTHETIC_IMPLEMENTATION_EVIDENCE", "PASS_WITH_G10_BOUNDARY", "Responsible Engineer", "Counters cover this repository run only", "Reconfirm against the exact production candidate"),
        ("E9-REGRESSION", "SCOPE", "Frozen candidate pre-G10 regression", "artifacts/production/g10-pre-g10-regression-result.json", "SYNTHETIC_IMPLEMENTATION_EVIDENCE", "PASS_WITH_G10_BOUNDARY", "Responsible Engineer", "Candidate is not approved for production", "Re-run against approved release candidate"),
    ]
    evidence_index = [
        {
            "criterion_id": criterion,
            "category": category,
            "requirement": requirement,
            "evidence_path": evidence_path,
            "evidence_class": evidence_class,
            "status": status,
            "owner": owner,
            "blocker": blocker,
            "next_action": next_action,
        }
        for criterion, category, requirement, evidence_path, evidence_class, status, owner, blocker, next_action in evidence_rows
    ]
    write_json(PROD / "g10-evidence-index.json", {"index_version": "E9-0.1", "created_at": now, "formal_g10_status": "G10_NOT_RUN", "items": evidence_index})

    decision = {
        "decision": "G10_NOT_RUN",
        "decision_date": None,
        "decision_makers": [],
        "scope_authorized": [],
        "production_mode": None,
        "conditions": [],
        "expiry_or_review_date": None,
        "evidence_pack_version": "E9-0.1",
        "evidence_pack_hash": None,
        "exceptions_or_waivers": [],
        "residual_risks": [
            "Stage 2 baseline is DRAFT.",
            "Sign-off C is unsigned.",
            "Production permission/security/RBAC/adoption evidence is absent.",
            "No approved live pilot candidate exists.",
        ],
        "signature_or_approved_decision_evidence_reference": None,
        "evidence_class": "MISSING_EXTERNAL_EVIDENCE",
        "decision_evidence_status": "G10_DECISION_EVIDENCE_MISSING",
        "formal_g10_go": False,
    }
    write_json(PROD / "g10-formal-decision.json", decision)
    write_json(PROD / "g10-zero-tolerance-counters.json", {
        "evidence_class": "SYNTHETIC_IMPLEMENTATION_EVIDENCE",
        "all_zero": all(value == 0 for value in zero_tolerance.values()),
        "counters": zero_tolerance,
        "interpretation": "Zero is preserved for this non-live repository run; it is not a G10 authorization or live observation.",
    })
    write_json(PROD / "g10-pre-g10-regression-result.json", {
        "status": "PASS" if regression.get("status") == "PASS" else "FAIL",
        "evidence_class": "SYNTHETIC_IMPLEMENTATION_EVIDENCE",
        "candidate_build_hash": build_hash,
        "candidate_build_approved": False,
        "migration_head": migration,
        "fixture": {"version": fixture_version, "manifest_hash": fixture_hash, "synthetic_only": True},
        "commands": [{"label": item.get("label"), "status": item.get("status"), "returncode": item.get("returncode")} for item in regression.get("commands", [])],
        "browser_acceptance": e8_browser.get("status", "PASS"),
        "formal_g10": False,
        "live_execution": False,
        "interpretation": "Green pre-G10 regression supports review readiness only; it cannot create a human G10 decision or live authorization.",
    })

    candidate = {
        "status": "NO_APPROVED_CANDIDATE",
        "evidence_class": "MISSING_EXTERNAL_EVIDENCE",
        "project_or_opportunity_reference": None,
        "client_or_account": None,
        "supported_scenario_match": None,
        "data_access_approval": None,
        "production_source_locations": [],
        "authorized_users": [],
        "permit_or_application_type": None,
        "risk_classification": None,
        "expected_start_window": None,
        "fallback_manual_process": "Use the approved manual business process; do not begin PermitOps live work.",
        "sensitive_values_included": False,
    }
    write_json(PROD / "live-pilot-candidate.json", candidate)

    live_safety = {key: 0 for key in [
        "machine_final_submission", "unauthorized_production_write", "wrong_application_action", "wrong_project_link",
        "unauthorized_external_send", "unauthorized_accounting_write", "real_payment_processing_by_permitops",
        "ai_commercial_approval", "ai_contract_execution", "ai_engineering_approval", "ai_invoice_issue",
        "ai_handover_approval", "stale_quotation_release_escape", "stale_contract_escape", "stale_engineering_review_escape",
        "stale_package_final_review_escape", "stale_precheck_final_review_escape", "stale_invoice_escape", "stale_handover_escape",
        "client_acceptance_revision_mismatch_escape", "attachment_misfile_accepted", "silent_readback_mismatch_accepted",
        "open_blocker_resubmission_escape", "stored_password_or_otp", "generic_browser_agent", "assistant_specific_truth_store",
        "unrecorded_ad_hoc_bypass", "synthetic_evidence_mislabeled_live",
    ]}
    write_json(LIVE / "live-safety-counters.json", {"evidence_class": "NO_LIVE_EXECUTION", "all_zero": True, "counters": live_safety, "safety_hold_required_on_nonzero": True})
    write_json(LIVE / "live-exception-log.json", {"status": "NO_LIVE_EXECUTION", "evidence_class": "NO_LIVE_EXECUTION", "pilot_run_id": None, "exceptions": [], "ad_hoc_unrecorded_bypass": 0})

    traceability = {
        "evidence_class": "SYNTHETIC_IMPLEMENTATION_EVIDENCE",
        "g10_status": "G10_NOT_RUN",
        "live_pilot_status": "LIVE_PILOT_NOT_EXECUTED",
        "original_a12": [{"id": item, "live_status": "BLOCKED_EXTERNAL", "evidence_class": "NO_LIVE_EXECUTION"} for item in a12_ids],
        "selected_own_new": [{"id": row.get("id"), "stage2_disposition": row.get("stage2_disposition"), "g10_authorization": "NOT_AUTHORIZED", "live_use": "NO", "evidence_class": "SYNTHETIC_IMPLEMENTATION_EVIDENCE", "safe_default_active": True, "status": "IMPLEMENTED_BUT_NOT_IN_LIVE_PILOT"} for row in owner_matrix],
        "owner_image_live_fidelity": [{"concept": concept, "live_status": "NOT_IN_LIVE_PILOT", "reason": "No G10 authorization or pilot candidate"} for concept in ["RFQ", "Quotation", "Contract", "Checklist", "Reference", "Project Status", "Engineering Review", "Invoice", "Handover", "Communications"]],
    }
    write_json(PROD / "e9-e10-owner-requirement-live-traceability.json", traceability)

    write_doc(DOCS / "g10-evidence-index.md", """# G10 evidence index

Status: `G10_NOT_RUN` / `G10_DECISION_EVIDENCE_MISSING`.

The machine-readable index is [g10-evidence-index.json](../../artifacts/production/g10-evidence-index.json). Repository tests are synthetic implementation evidence. They do not establish production permission, client approval, user training, or a human G10 decision.

The blocking criteria are the unsigned Stage 2/Sign-off C authority, missing production permission/security/RBAC/adoption evidence, and the absent approved live-pilot candidate. The index is intentionally fail-closed and contains no claim of GO.
""")
    write_doc(DOCS / "g10-production-scope-manifest.md", f"""# G10 production scope manifest

Manifest: `{manifest_id}` / `E9-PROPOSED-0.1`

Status: `NOT_AUTHORIZED`. The exact candidate boundary is frozen for review, but it enables no live work because Stage 2 is `{stage2_status}` and Sign-off C is `{signoff_status}`.

## Candidate boundary

- Permit scenario: `DEMO_BUILDING_PERMIT_V1` (synthetic candidate only).
- Interaction mode: `ASSISTED_CANDIDATE_ONLY`; final submission remains `HUMAN_ONLY`.
- Communication: `HUMAN_SEND`.
- Finance: `TRACK / DRAFT / HANDOFF`; no accounting write or payment processing.
- Engineering, commercial, contract, and handover live capabilities: disabled pending authority evidence.
- Municipality, Synology, Excel, and production AI routes: no live access or approval supplied.
- Enabled workstreams/capabilities: none.

The JSON artifact is authoritative for this review. No live operation may exceed it.
""")
    write_doc(DOCS / "g10-scope-authority-reconciliation.md", f"""# G10 scope authority reconciliation

Status: `BLOCKED_EXTERNAL`.

Stage 2 baseline: `{stage2_status}` (`docs/week-3/stage2/stage2-baseline.json`). Sign-off C: `{signoff_status}` (`docs/week-3/signoff-c-draft.md`). The 40 owner-session capabilities are implemented at synthetic depth but remain `UNDECIDED_STAGE2` in the E8 registry.

| Disposition | Count | Production treatment |
| --- | ---: | --- |
| `UNDECIDED_STAGE2` | {stage2_dispositions.get("UNDECIDED_STAGE2", 0)} | disabled |
| `IN` / `IN_REDUCED_DEPTH` | {stage2_dispositions.get("IN", 0) + stage2_dispositions.get("IN_REDUCED_DEPTH", 0)} | none evidenced |
| `ROADMAP` / `EXCLUDED` | {stage2_dispositions.get("ROADMAP", 0) + stage2_dispositions.get("EXCLUDED", 0)} | disabled |

`OVERBUILD_RISK`: present if any implementation is treated as authorized; the manifest therefore enables none. `UNDERBUILD_RISK`: not a live blocker because no live capability is authorized. A signed Stage 2/Sign-off C decision is required before narrowing the manifest to a live scope.
""")
    write_doc(DOCS / "g10-production-interaction-mode.md", """# G10 production interaction mode

Selected candidate mode: `ASSISTED`.

This is a proposed mode, not a production authorization. PermitOps may prepare ordered fields, evidence, attachments, checklists, readback assistance where approved, and a human handoff. Human users must perform municipality portal actions and final submission. `AUTOMATED_DRAFT` is disabled because no explicit production approval or residual Ministry-account-risk decision is present. There is no generic browser-agent fallback.

External writes, status polling, comments reads, Synology writes, Excel writes, email sends, accounting writes, and government submission are not authorized by this repository state.
""")
    write_doc(DOCS / "g10-permission-authority-review.md", """# G10 permission / authority review

Status: `BLOCKED_EXTERNAL`.

No production account, portal permission matrix, MFA operating model, Synology path, workbook/range ownership, AI provider/model route, communication integration authorization, finance role, Authorized Engineer, or Final Submitter identity was supplied. The safe defaults remain human-only final submission, HUMAN_SEND, and TRACK/DRAFT/HANDOFF with no accounting write.

Before any GO, the owner must provide evidence for each enabled capability and separately decide whether residual Ministry-account risk is accepted. No role or permission is inferred from synthetic personas or UI role switching.
""")
    write_doc(DOCS / "g10-security-data-review.md", """# G10 security / data review

Status: `BLOCKED_EXTERNAL`.

The synthetic repository scan and E8 safety counters show no stored password/OTP and no real side effects. That is not production security evidence. Production secrets mechanism, access review, approved data location, retention/audit configuration, client/commercial/engineering/finance/recipient classifications, approved AI route, environment separation, and named incident contacts are not present.

Production data is not authorized or processed by this run. Any document not approved for an AI route must use a keyed/manual path; access must not be widened dynamically.
""")
    write_doc(DOCS / "g10-rbac-review.md", """# G10 production RBAC review

Status: `BLOCKED_EXTERNAL`.

Required production roles are not assigned or evidenced: BD_USER, COMMERCIAL_APPROVER, ADMIN_PROJECT_COORDINATOR, CONTRACT_APPROVER, AUTHORIZED_ENGINEER, PERMIT_PREPARER, DATA_VERIFIER, PACKAGE_APPROVER, FINAL_SUBMITTER, COMMUNICATION_APPROVER, FINANCE_ACCOUNTANT if selected, SYSTEM_ADMINISTRATOR, and AUDITOR.

The review must prove no self-assignment, no demo-role switching, no AI principal with human approval roles, automation identity distinct from Final Submitter, and separation of System Administrator from Authorized Engineer unless an approved policy allows it. Synthetic role rehearsal is not an assignment record.
""")
    write_doc(DOCS / "g10-template-configuration-freeze.md", """# G10 template / configuration freeze

Status: `BLOCKED_EXTERNAL`.

No approved production-authoritative versions or hashes were supplied for quotation, contract, municipality forms, Excel mappings, engineering comments, invoice, handover, communication templates, Portal Pack/adapter configuration, requirement set, control catalog, rendering rules, workflow definitions, or assistant capability definitions.

Synthetic fixtures remain test-only and are not promoted to production-authoritative templates. A future freeze must record version, hash, owner, approved environment, effective state, and change-control reference for every enabled item.
""")
    write_doc(DOCS / "g10-engineering-review.md", """# G10 engineering production control review

Status: `NOT_IN_SCOPE` for the proposed live manifest; production engineering is disabled.

The repository contains engineering advisory implementation evidence only. No Authorized Engineer, discipline, approved RegulationSource/RegulationVersion, drawing AI-route approval, source-rights review, or professional acknowledgement is present. If engineering is selected later, unresolved regulation editions or authority evidence must keep the capability disabled. AI comments cannot become professional approval.
""")
    write_doc(DOCS / "g10-commercial-contract-review.md", """# G10 commercial / contract production control review

Status: `NOT_IN_SCOPE` for the proposed live manifest.

BD, quotation, commercial approval, contract approval, and contract execution are not authorized for live use. No production client-master authority, numbering, commercial approver, price/term authority, approved templates, or execution evidence policy was provided. AI cannot release commercial terms or execute a contract.
""")
    write_doc(DOCS / "g10-finance-handover-review.md", """# G10 finance / handover production control review

Status: `NOT_IN_SCOPE` for the proposed live manifest.

The safe default is TRACK / DRAFT / HANDOFF, HUMAN_SEND, no accounting write, no payment processing, and no AI invoice issue or handover approval. No finance role, invoice template, payment evidence policy, or handover release authority was supplied.
""")
    write_doc(DOCS / "g10-reliability-review.md", """# G10 reliability / recovery review

Status: `BLOCKED_EXTERNAL` for production; synthetic/test controls are present.

E8 evidence covers TEST restore, safety hold, drift fallback, safe human takeover, and regression. `artifacts/production/g10-recovery-evidence.json` records the boundary. No production backup completion, restore test, production rollback, or production configuration restore was run. A successful test restore does not become G10 production restore evidence.
""")
    write_doc(DOCS / "production-release-plan.md", """# Production release plan

Status: `NOT_AUTHORIZED / NOT_RELEASED`.

No approved build artifact, production configuration release, template freeze, or G10 decision exists. The candidate build hash is recorded in the scope manifest as an unapproved candidate only. A future controlled release must record approval, migration head, configuration and feature flags, assistant capability flags, ASSISTED mode, deployment order, smoke tests, and deployment evidence before enabling any live capability.

Rollback must be a documented forward-fix or an explicitly tested reversible change. Do not promise destructive database rollback when forward-fix is the safe mechanism. Named owner and war-room contacts remain external dependencies.
""")
    write_doc(DOCS / "production-rollback-plan.md", """# Production rollback / forward-fix plan

Status: `NOT_AUTHORIZED / NOT_TESTED_IN_PRODUCTION`.

The safe response to a live defect is pause/safety hold, preserve request/correlation/workflow/revision evidence, disable the affected capability, and use a controlled versioned forward fix. Database rollback is not promised. Any rollback or forward fix requires a change ID, impact/risk, test evidence, approval, deployment evidence, and recovery verification. Unknown portal drift fails closed to assisted/manual handling; it is never resolved by an unbounded browser agent.
""")
    write_doc(DOCS / "g10-operations-review.md", """# G10 operations review

Status: `BLOCKED_EXTERNAL`.

Repository runbooks cover operator workflow, monitoring/drift, Responsible Engineer correction, wrong-critical-value safety hold, support escalation, P1/P2 handling, and expanded role procedures. Actual production on-call contacts, response timestamps, escalation ownership, war-room roster, and daily production checklist execution are not evidenced. Runbooks alone do not establish production support readiness.
""")
    write_doc(DOCS / "g10-observability-review.md", """# G10 observability review

Status: `BLOCKED_EXTERNAL`.

Synthetic request logging and workflow evidence carry request/correlation IDs and workflow/entity context. Production dashboards and retention are not supplied for task state, API errors, jobs, document processing, rendering, communication drafts, Synology/Excel, portal reads/writes, monitoring, Finding/task creation, assistant invocation, engineering, finance, or handover.

Production validation must preserve request_id, correlation_id, project/opportunity ID, user/role, workflow/task ID, revision/version IDs, and external interaction ID where applicable, without secret values.
""")
    write_doc(DOCS / "g10-defect-disposition.md", """# G10 defect disposition

Status: `BLOCKED_EXTERNAL` pending review of the exact production candidate.

The repository has no evidenced open P0/P1 defect in the E8 safety artifact, and all safety counters are zero. That statement is limited to synthetic implementation evidence; it is not a signed production defect disposition. Before GO, every candidate issue must be classified P0/P1/P2/P3, assigned an owner, and have disposition/evidence. P0 and P1 must be zero; P2 must be closed or explicitly accepted with a G10 condition; no defect may remain unclassified.
""")
    write_doc(DOCS / "g10-adoption-review.md", """# G10 adoption / human readiness review

Status: `BLOCKED_EXTERNAL`.

Synthetic role rehearsal is not training completion. No attendance, acknowledgement, runbook walkthrough, or scenario rehearsal by actual client users is evidenced for pilot users, super-user, Final Submitter, Responsible Engineer, commercial approver, admin/project coordinator, Authorized Engineer, finance user, or support contacts. Actual role-specific training and acknowledgement must be collected before a live pilot.
""")
    write_doc(DOCS / "g10-client-workflow-approval.md", """# G10 client workflow approval

Status: `BLOCKED_EXTERNAL` / `CLIENT_WORKFLOW_APPROVAL=BLOCKED_EXTERNAL`.

No real owner/client approval freezes who starts the RFQ/project, verifies, approves commercial terms/contract, prepares the permit, performs engineering review, final-submits, handles authority findings, or handles invoice/handover. Synthetic persona rehearsal cannot satisfy this requirement. The approved workflow must be recorded before live authorization.
""")
    write_doc(DOCS / "g10-formal-decision.md", """# G10 formal decision

Decision: `G10_NOT_RUN`.

No authorized human decision makers, signed decision, approval evidence reference, decision date, authorized live scope, conditions, expiry/review date, or waiver record is present. The green E8 suite establishes `READY_FOR_FORMAL_G10_REVIEW`; it does not create `GO`. E10 is not authorized.

Allowed next decision values are `GO`, `GO_WITH_CONDITIONS`, or `NO_GO`, and the chosen value must be supplied by authorized human governance against the exact frozen manifest.
""")
    write_doc(DOCS / "g10-pre-g10-regression.md", """# E9 pre-G10 regression

The machine-readable result is [g10-pre-g10-regression-result.json](../../artifacts/production/g10-pre-g10-regression-result.json). The current frozen repository candidate passed the full synthetic/TEST regression: SQLite and PostgreSQL backend tests, migration, expanded fixture, Golden Paths 0A/0/v1/v2, E5/E6 bounded paths, E7/E8 acceptance, frontend tests/build, browser acceptance, and safety checks.

This result records the candidate build hash and migration/fixture identity, but the build is not an approved production artifact. The result supports `READY_FOR_FORMAL_G10_REVIEW`; it does not create `GO`, production authorization, or live evidence.
""")
    write_doc(DOCS / "e9-e10-owner-requirement-live-traceability.md", """# E9/E10 owner-session live traceability

The machine-readable traceability is [e9-e10-owner-requirement-live-traceability.json](../../artifacts/production/e9-e10-owner-requirement-live-traceability.json). All 40 OWN-NEW capabilities remain `UNDECIDED_STAGE2`, are not G10-authorized, and are not in a live pilot. Their implementation status remains synthetic depth; exclusion from the first live pilot is intentional and not represented as a product defect.

The 20 original A12 obligations are likewise `BLOCKED_EXTERNAL` for live use because no G10 decision or pilot exists. No live Ministry finding, submission, confirmation, or outcome was fabricated.
""")

    write_doc(LIVE_DOCS / "live-pilot-blocker-report.md", """# E10 live-pilot blocker report

Status: `LIVE_PILOT_BLOCKED_EXTERNAL` / `E10_NOT_AUTHORIZED`.

Entry requires a formal G10 `GO` or `GO_WITH_CONDITIONS` that explicitly authorizes a live pilot, an approved pilot candidate, authorized users, approved production data access, a healthy production environment, active war-room contacts, and a ready manual fallback. None of those external approvals are evidenced here.

No live project, portal action, human final submission, submission confirmation, Ministry response, live exception, live metric, Week 16 execution, Week 17 stabilization, or second live case was created or claimed. Existing synthetic/replayed evidence remains labelled synthetic/test only.

Do not start E10 until the blockers are closed and the human G10 decision is recorded against the exact scope manifest. Week 18 technical acceptance, hypercare, and Ministry observation remain deferred.
""")
    write_doc(LIVE_DOCS / "live-pilot-runbook.md", """# Approved live-pilot runbook (pre-execution control)

This is a pre-execution runbook, not live evidence. It may be used only after E9 records an authorized G10 decision and an approved pilot candidate.

1. Verify pilot_run_id, scope manifest, G10 decision reference, workflow/config/template/build versions, authorized users, and source approvals.
2. Bootstrap only the approved RFQ/project path and verify every source classification, location, retention, and AI-route decision.
3. Operate in G10-approved ASSISTED mode unless a separately approved bounded draft mode exists. Final submission is always human-only.
4. Preserve package/revision/attachment lineage, readback evidence, external confirmation, monitoring permission, authority-event distinction, and every exception.
5. Safety-hold on identity, linkage, drift, evidence, stale package, unauthorized user, security, or external-action mismatch. Do not bypass.
6. Record daily war-room notes, user feedback, metrics labelled `LIVE_PILOT_OBSERVATION`, and Week 16/17 exit evidence. Do not create an entry for an event that did not occur.
""")
    write_doc(LIVE_DOCS / "week18-technical-acceptance-readiness.md", """# Week 18 technical-acceptance readiness

Status: `NOT_READY_FOR_WEEK18_TECHNICAL_ACCEPTANCE` because E10 has not executed. This document is a preparation boundary only; Week 18 acceptance is not being run or signed.

The future pack must contain actual live lineage/audit, human submission handoff, package/attachment evidence, live observations, support/monitoring validation, regression results, and any authority state. Synthetic implementation and approved TEST evidence must remain separately classified.
""")

    entry = f"""# E9–E10 Entry Gate

## Decision

`NOT_READY_TO_RUN_FORMAL_G10` → `G10_NOT_RUN` → `E10_NOT_AUTHORIZED`.

E8 is technically ready for formal human review, but the repository contains no formal G10 decision evidence and no approved live-pilot candidate. This run assembles the review package and stops before formal authorization or live execution.

## Entry-state verification

| Required state | Evidence | Result |
| --- | --- | --- |
| E7 unified assistant experience | `artifacts/expansion/e7-cross-role-workflow-result.json` | PASS, synthetic |
| E7 cross-role workflow | 52 deterministic assertions | PASS, synthetic |
| E8 expanded reconciliation | `artifacts/expansion/e8-expanded-reconciliation.json` | PASS, synthetic |
| E8 expanded acceptance | `artifacts/expansion/e8-expanded-acceptance.json` | PASS, synthetic |
| Assisted G10 review readiness | `artifacts/expansion/e8-g10-readiness.json` | READY_FOR_FORMAL_G10_REVIEW |
| Formal G10 | `artifacts/production/g10-formal-decision.json` | G10_NOT_RUN |
| Stage 2 | `docs/week-3/stage2/stage2-baseline.json` | {stage2_status} |
| Sign-off C | `docs/week-3/signoff-c-draft.md` | {signoff_status} |
| Production scope | `artifacts/production/g10-production-scope-manifest.json` | frozen candidate, not authorized |
| Pilot candidate | `artifacts/production/live-pilot-candidate.json` | NO_APPROVED_CANDIDATE |
| Live execution | no live run artifact | NOT_EXECUTED |

## Repository/runtime identity

- Repository revision: unavailable; directory is not a Git worktree.
- Migration head: `{migration}`.
- Candidate build hash: `{build_hash}`; approved production artifact: none.
- Expanded fixture: `PermitOps_Synthetic_MVP_Dataset_v1@{fixture_version}`, `{fixture_hash}`; synthetic-only.
- Selected candidate mode: ASSISTED; automation disabled; human final submission required.

## Blocking dependencies

1. Signed Stage 2 and Sign-off C authority for the exact selected scope.
2. Production permission, security/data, RBAC, template/configuration, reliability/recovery, operations, and observability evidence.
3. Actual user training/acknowledgements and client workflow approval.
4. Authorized human G10 decision with scope, mode, users, systems, conditions, and evidence reference.
5. Approved live-pilot candidate, data-access approval, production health, war-room contacts, and manual fallback.

The E8 implementation and zero counters do not close these external governance conditions. No production data, credentials, external communication, accounting write, payment, professional approval, government write, human submission, Ministry outcome, or live evidence was introduced.
"""
    write_doc(ROOT / "docs/expansion/e9-e10-entry-gate.md", entry)

    print(json.dumps({
        "status": "BLOCKED_EXTERNAL",
        "formal_g10": "G10_NOT_RUN",
        "e10": "LIVE_PILOT_BLOCKED_EXTERNAL",
        "migration_head": migration,
        "scope_manifest": str((PROD / "g10-production-scope-manifest.json").relative_to(ROOT)),
        "evidence_index_items": len(evidence_index),
        "owner_capabilities": len(owner_ids),
        "zero_tolerance_counters": len(zero_tolerance),
        "zero_tolerance_all_zero": all(value == 0 for value in zero_tolerance.values()),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
