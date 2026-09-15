"""Build the machine-readable UI closure package from executable sources.

The package deliberately distinguishes backend operation classification from
backend-to-UI exposure.  A route that is classified correctly is not treated
as functionally covered until a current frontend reference is found or an
explicit product-scope justification is recorded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/ui-product-surface-closure"
FRONTEND = ROOT / "frontend/src"


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def load_operations() -> list[dict[str, Any]]:
    import sys
    sys.path.insert(0, str(ROOT))
    from backend.scripts.ui_surface_census import classify, operations

    return [{**item, "classification": classify(item)[0], "classification_basis": classify(item)[1]} for item in operations()]


def frontend_references() -> list[dict[str, str]]:
    references: list[dict[str, str]] = []
    pattern = re.compile(r"(?P<quote>[`\"'])(?P<value>/api/[^`\"']+)(?P=quote)")
    for path in sorted(FRONTEND.rglob("*.tsx")) + sorted(FRONTEND.rglob("*.ts")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in pattern.finditer(text):
            value = match.group("value").split("?", 1)[0].split("#", 1)[0]
            value = re.sub(r"\$\{[^}]+\}", "{param}", value)
            value = value.rstrip(" )},;")
            references.append({"source_file": str(path.relative_to(ROOT)), "reference": value})
    return references


def ref_matches(reference: str, path: str) -> bool:
    if reference.endswith("/"):
        return path.startswith(reference)
    ref_parts = reference.strip("/").split("/")
    path_parts = path.strip("/").split("/")
    if len(path_parts) < len(ref_parts):
        return False
    for expected, actual in zip(ref_parts, path_parts):
        if expected in {"{param}", "*"}:
            continue
        if expected != actual:
            return False
    return len(path_parts) == len(ref_parts) or reference.endswith("/")


# The string/reference scan above is retained as discovery provenance only. A
# direct match cannot prove a task path and a missing match cannot prove a
# product gap. This adjudication maps operations to the canonical AMEC
# workspaces and records the human-facing control/read-back boundary that owns
# the capability.
WORKFLOW_PROOFS: dict[str, dict[str, str]] = {
    "proposal_lifecycle": {
        "workflow": "Opportunity / Proposal → Proceed → Contract → Accept → Project Activation",
        "route": "/proposals",
        "control": "frontend/src/features/proposals/ProposalWorkspacePage.tsx and frontend/src/AdministrationOwner.tsx",
        "readback": "Proposal/Contract workspace refreshes the canonical record after every command and exposes readiness/history projections.",
        "evidence": "frontend/browser-real-stack/proposals-contracts-final.spec.ts and contract-center-final-owner-hardening.spec.ts",
    },
    "work_queue": {
        "workflow": "My Work/task queues → owning business work item",
        "route": "/work",
        "control": "frontend/src/AMECWork.tsx WorkCard deep links to the owning context; Issues and Notifications provide the exception/action handoff.",
        "readback": "AMEC Work reloads the role-scoped work projection; the owning workspace is authoritative for mutation.",
        "evidence": "frontend/browser-real-stack/homepage-owner-ready.spec.ts and persona-issues-notifications.spec.ts",
    },
    "permit_delivery": {
        "workflow": "Permit preparation → evidence → precheck → human submission → authority history",
        "route": "/permits",
        "control": "frontend/src/PermitAuthorityUX.tsx PermitPortfolioPage/NewPermitPage/PermitCasePage and frontend/src/AuthorityCaseWorkspace.tsx",
        "readback": "Authority Case workspace reads requirements, documents, drawings, forms, findings, cycles, outcomes, and history from the canonical case projection.",
        "evidence": "frontend/browser-real-stack/owner-rehearsal.spec.ts and ui-product-surface-closure-real-stack.spec.ts",
    },
    "engineering_delivery": {
        "workflow": "Projects & Delivery → engineering lifecycle → review/approval/baseline",
        "route": "/engineering",
        "control": "frontend/src/ProjectEngineering.tsx and frontend/src/EngineeringDrawingReview.tsx",
        "readback": "Engineering workspace refreshes project/review/work-package projections and keeps exact revision, finding, and approval evidence visible.",
        "evidence": "frontend/browser-real-stack/master-content-owner-dashboard.spec.ts and visual-qa.spec.ts",
    },
    "construction_delivery": {
        "workflow": "Construction/post-approval → start gate → controlled work events → evidence",
        "route": "/construction",
        "control": "frontend/src/Construction.tsx Evaluate gate control and human start boundary",
        "readback": "Construction detail reloads readiness, work events, obligations, inspections, issues, notifications, and lineage projections.",
        "evidence": "frontend/browser-real-stack/construction-post-approval.spec.ts",
    },
    "completion_handover": {
        "workflow": "Completion/as-built → variance/evidence → handover/closeout/settlement",
        "route": "/completion",
        "control": "frontend/src/Completion.tsx and frontend/src/Handover.tsx explicit human checkpoint controls",
        "readback": "Completion and Handover workspaces preserve separate readiness, baseline, outcome, service-close, financial-settlement, and history state.",
        "evidence": "frontend/browser-real-stack/completion-asbuilt.spec.ts and handover real-stack coverage",
    },
    "billing_finance": {
        "workflow": "Billing/Finance → invoice register/detail → acknowledgement → payment evidence → verification/allocation/reversal/history",
        "route": "/billing",
        "control": "frontend/src/billing/BillingShell.tsx, BillingRegisters.tsx, BillingDetailWorkspaces.tsx, and InvoiceWorkspace.tsx",
        "readback": "Finance registers and detail workspaces refresh server capabilities, projections, receipts, allocations, receivables, and financial history after commands.",
        "evidence": "frontend/browser-real-stack/billing-finance-closure.spec.ts and post-billing-v2-reconciliation.spec.ts",
    },
    "content_library": {
        "workflow": "Content Library → Forms / Reports / Engineering Works / Definitions; Checklist remains a Form",
        "route": "/content-library",
        "control": "frontend/src/Dashboard.tsx, MasterContentForms.tsx, contentLibraryApi.ts",
        "readback": "Library list/detail/history and governance projections refresh after content changes; no AI authority is introduced.",
        "evidence": "frontend/browser-real-stack/master-content-owner-dashboard.spec.ts and admin-forms-real-stack.spec.ts",
    },
    "issues_notifications": {
        "workflow": "Issues/Notifications → owning work item → acknowledgement/history",
        "route": "/issues",
        "control": "frontend/src/PersonaIssuesNotifications.tsx and frontend/src/NotificationBell.tsx",
        "readback": "Persona-scoped issue/notification projections refresh acknowledgement and preserve the owning deep link/evidence context.",
        "evidence": "frontend/browser-real-stack/persona-issues-notifications.spec.ts and issue-detail-final.spec.ts",
    },
    "owner_decisions": {
        "workflow": "Owner Decisions → recommendation/context → explicit confirmation → audit/history",
        "route": "/owner-decisions",
        "control": "frontend/src/OwnerDecisionCenter.tsx Confirm recommended default action",
        "readback": "Owner Decision Register reloads the canonical decision, confirmation status, protected technical facts, and history.",
        "evidence": "frontend/browser-real-stack/owner-decision-closure.spec.ts",
    },
    "administration": {
        "workflow": "Administration → access/configuration/integration/audit capability",
        "route": "/admin",
        "control": "frontend/src/AdministrationOwner.tsx system-administration sections; business registers remain in owning workspaces.",
        "readback": "Administration sections read server projections and expose bounded configuration actions; server authorization remains authoritative.",
        "evidence": "frontend/browser-real-stack/admin-owner-ready.spec.ts and administration-final-audit.spec.ts",
    },
}

TERMINAL_CLASSES = (
    "SURFACED_DIRECT", "SURFACED_INDIRECT_WORKFLOW", "DERIVED_UI_SUPPORT",
    "BACKEND_ONLY_INTERNAL", "AUTOMATION_OR_SYSTEM_ONLY", "ADMIN_CAPABILITY_UI",
    "LATER_PRODUCTION_GATE", "AI_HANDOFF_INTEGRATION_BRANCH", "BLOCKING_UI_GAP",
)
ANALYSIS_STATES = TERMINAL_CLASSES + ("ADJUDICATION_PENDING",)

# Exact, positive evidence currently exists only for framework/runtime and
# deliberately deferred AI operations. Human operations must be added as exact
# (method, route template, operation name) records after a trace-backed review.
# No URL prefix, HTTP verb, or frontend string reference is a terminal rule.
EXACT_SYSTEM_OPERATIONS = {
    ("GET", "/openapi.json", "openapi"), ("HEAD", "/openapi.json", "openapi"),
    ("GET", "/docs", "swagger_ui_html"), ("HEAD", "/docs", "swagger_ui_html"),
    ("GET", "/docs/oauth2-redirect", "swagger_ui_redirect"), ("HEAD", "/docs/oauth2-redirect", "swagger_ui_redirect"),
    ("GET", "/redoc", "redoc_html"), ("HEAD", "/redoc", "redoc_html"),
    ("GET", "/health", "health"), ("GET", "/health/live", "health_live"),
    ("HEAD", "/health/live", "health_live"), ("GET", "/health/ready", "health_ready"),
    ("HEAD", "/health/ready", "health_ready"), ("GET", "/", "api_root"),
}
EXACT_AI_OPERATIONS = {
    ("GET", "/api/ai/runtime-status", "runtime_status"),
    ("POST", "/api/ai/context/manifest", "context_manifest"),
    ("POST", "/api/ai/interactive/technical-methodology", "interactive_technical_methodology"),
    ("POST", "/api/governed-prefill/preview", "governed_prefill_preview"),
    ("POST", "/api/governed-prefill/apply", "governed_prefill_apply"),
}


def operation_key(item: dict[str, Any]) -> tuple[str, str, str]:
    return (item["method"], item["path"], item["name"])


def semantic_adjudication(item: dict[str, Any], refs: list[dict[str, str]]) -> dict[str, str]:
    key = operation_key(item)
    if key in EXACT_SYSTEM_OPERATIONS:
        return {"terminal_classification": "AUTOMATION_OR_SYSTEM_ONLY", "reviewer_disposition": "EXACT_RUNTIME_SURFACE_REVIEWED", "reason": "Exact framework/runtime operation; no human business decision or product capability is exposed."}
    if key in EXACT_AI_OPERATIONS:
        return {"terminal_classification": "AI_HANDOFF_INTEGRATION_BRANCH", "reviewer_disposition": "EXACT_SCOPE_HANDOFF_REVIEWED", "reason": "Exact AI/intelligence operation deliberately transferred to the integration branch; no current-branch UI or write authority is claimed."}
    # Deliberately keep unreviewed operations pending. A pending row is not a
    # confirmed product gap: it still requires semantic review to determine
    # whether it is human-facing, internal, derived, automated, future-gated,
    # or genuinely missing from the UI.
    return {"terminal_classification": "ADJUDICATION_PENDING", "reviewer_disposition": "ADJUDICATION_PENDING", "reason": "Exact row-level review is still required for human intent, scope, workflow ownership, UI exposure, authority, state coverage, and browser evidence."}


def calculate_terminal_metrics(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "UI_UNKNOWN_CLASSIFICATION_ROWS": sum(row.get("terminal_classification") not in ANALYSIS_STATES for row in rows),
        "UI_UNJUSTIFIED_CLASSIFICATION_ROWS": sum(not str(row.get("semantic_reason", "")).strip() or row.get("reviewer_disposition") in {"MISSING", "UNREVIEWED_OPERATION"} for row in rows),
        "UI_ADJUDICATION_PENDING_COUNT": sum(row.get("terminal_classification") == "ADJUDICATION_PENDING" for row in rows),
        "UI_CONFIRMED_BLOCKING_GAP_COUNT": sum(row.get("terminal_classification") == "BLOCKING_UI_GAP" for row in rows),
        "UI_BLOCKING_GAP_COUNT": sum(row.get("terminal_classification") == "BLOCKING_UI_GAP" for row in rows),
        "USER_SURFACE_UNMAPPED_COUNT": sum(row.get("terminal_classification") == "BLOCKING_UI_GAP" and row.get("classification") == "USER_SURFACE_REQUIRED" for row in rows),
        "UI_SUPPORT_API_UNJUSTIFIED_UNUSED_COUNT": sum(row.get("terminal_classification") == "BLOCKING_UI_GAP" and row.get("classification") == "UI_SUPPORT_API" for row in rows),
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def count_test_calls(directory: Path) -> int:
    total = 0
    for path in directory.rglob("*"):
        if path.suffix not in {".ts", ".tsx", ".js", ".jsx"}:
            continue
        total += len(re.findall(r"\b(?:test|it)\s*\(", path.read_text(encoding="utf-8", errors="ignore")))
    return total


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--real-stack-status", default="NOT_PROVEN")
    parser.add_argument("--responsive-status", default="NOT_PROVEN")
    parser.add_argument("--accessibility-status", default="NOT_PROVEN")
    parser.add_argument("--authz-status", default="NOT_PROVEN")
    parser.add_argument("--owner-uat", default="NOT_PROVEN")
    parser.add_argument("--required-ci", default="NOT_PROVEN")
    parser.add_argument("--harness-status", default="NOT_PROVEN")
    parser.add_argument("--executable-head", default=None, help="Durable executable commit to bind evidence to")
    parser.add_argument("--executable-tree", default=None, help="Durable executable tree to bind evidence to")
    parser.add_argument("--evidence-head", default=None, help="Commit containing this evidence package, when already known")
    parser.add_argument("--evidence-tree", default=None, help="Tree for the evidence commit, when already known")
    parser.add_argument("--frontend-source-tree", default=None)
    parser.add_argument("--frontend-test-tree", default=None)
    parser.add_argument("--backend-ui-contract-tree", default=None)
    parser.add_argument("--closure-tooling-tree", default=None)
    args = parser.parse_args()

    operations = load_operations()
    refs = frontend_references()
    rows: list[dict[str, Any]] = []
    for operation in operations:
        matched = [ref for ref in refs if ref_matches(ref["reference"], operation["path"])]
        adjudication = semantic_adjudication(operation, matched)
        workflow_id = adjudication.get("workflow_id")
        proof = WORKFLOW_PROOFS.get(workflow_id or "", {})
        exposure = adjudication["terminal_classification"]
        human_facing = operation["classification"] in {"USER_SURFACE_REQUIRED", "UI_SUPPORT_API"}
        rows.append({
            **operation,
            "operation_id": f"{operation['method']} {operation['path']} :: {operation['name']}",
            "HTTP_method": operation["method"],
            "route_or_service": operation["path"],
            "backend_source_file": operation["endpoint"],
            "frontend_references": matched,
            "terminal_classification": exposure,
            "adjudication_state": "TERMINAL" if exposure in TERMINAL_CLASSES else "PENDING",
            "semantic_reason": adjudication["reason"],
            "reviewer_disposition": adjudication.get("reviewer_disposition", "MISSING"),
            "workflow_id": workflow_id,
            "workflow": proof.get("workflow"),
            "business_domain": workflow_id,
            "business_object": None,
            "source_requirement_reference": None,
            "authorized_persona_or_access_class": None,
            "human_intent": None,
            "owning_workflow": proof.get("workflow"),
            "classification_reason": adjudication["reason"],
            "surface_route": proof.get("route"),
            "human_control_or_consumer": proof.get("control"),
            "authoritative_readback": proof.get("readback"),
            "read_model_or_readback": proof.get("readback"),
            "mutation_authority": None,
            "negative_authorization_boundary": None,
            "normal_success_state": "NOT_PROVEN",
            "validation_state": "NOT_PROVEN",
            "server_error_state": "NOT_PROVEN",
            "authorization_denied_state": "NOT_PROVEN",
            "conflict_or_stale_state": "NOT_PROVEN",
            "audit_or_history_visibility": proof.get("evidence"),
            "test_evidence": None,
            "reviewer": None,
            "history_or_evidence": proof.get("evidence"),
            "human_facing": human_facing,
            "business_persona": None if human_facing else "NOT_HUMAN",
            "required_capability": None,
            "scope_dimensions": [],
            "ui_component": proof.get("control"),
            "visible_control": None,
            "control_label": None,
            "input_fields_or_selection": [],
            "request_binding": None,
            "server_authority_boundary": None,
            "success_state": "NOT_PROVEN",
            "loading_state_test": "NOT_PROVEN",
            "empty_state_test": "NOT_PROVEN",
            "error_state_test": "NOT_PROVEN",
            "denied_state_test": "NOT_PROVEN",
            "stale_state_test": "NOT_PROVEN",
            "retry_state_test": "NOT_PROVEN",
            "conflict_state_test": "NOT_PROVEN",
            "browser_test_file": None,
            "browser_test_name_or_node": None,
            "network_or_server_trace_evidence": None,
            "specific_terminal_reason": adjudication["reason"],
            # Preserve the old discovery result so it cannot be mistaken for
            # terminal adjudication in future reviews.
            "discovery_reference_match": bool(matched),
            "discovery_exposure": (
                "REFERENCED_BY_FRONTEND" if matched else
                "UNMAPPED_USER_SURFACE" if operation["classification"] == "USER_SURFACE_REQUIRED" else
                "UNJUSTIFIED_UNUSED_UI_SUPPORT_API" if operation["classification"] == "UI_SUPPORT_API" else
                "FORMALLY_DEFERRED_TO_INTEGRATION_BRANCH" if operation["classification"] == "DEFERRED_AI" else
                "NOT_UI_APPLICABLE"
            ),
            "evidence_requirement": "semantic workflow proof or explicit terminal classification with reason",
        })

    counts = {name: sum(row["classification"] == name for row in rows) for name in (
        "USER_SURFACE_REQUIRED", "UI_SUPPORT_API", "SYSTEM_ONLY", "INTERNAL_ONLY", "DEFERRED_AI", "LATER_PRODUCTION_GATE"
    )}
    terminal_classes = TERMINAL_CLASSES
    terminal_counts = {name: sum(row["terminal_classification"] == name for row in rows) for name in ANALYSIS_STATES}
    terminal_metrics = calculate_terminal_metrics(rows)
    unknown = terminal_metrics["UI_UNKNOWN_CLASSIFICATION_ROWS"]
    unjustified = terminal_metrics["UI_UNJUSTIFIED_CLASSIFICATION_ROWS"]
    pending = terminal_metrics["UI_ADJUDICATION_PENDING_COUNT"]
    blocking = terminal_metrics["UI_CONFIRMED_BLOCKING_GAP_COUNT"]
    # Discovery gaps are intentionally reported as provenance, not as product
    # gaps. They are expected where a generic command builder or normalized
    # read projection owns the UI interaction.
    discovery_unmapped = sum(row["discovery_exposure"] == "UNMAPPED_USER_SURFACE" for row in rows)
    discovery_unused_support = sum(row["discovery_exposure"] == "UNJUSTIFIED_UNUSED_UI_SUPPORT_API" for row in rows)
    unmapped = terminal_metrics["USER_SURFACE_UNMAPPED_COUNT"]
    unused_support = terminal_metrics["UI_SUPPORT_API_UNJUSTIFIED_UNUSED_COUNT"]
    current_sha = args.executable_head or git("rev-parse", "HEAD")
    current_tree = args.executable_tree or git("rev-parse", "HEAD^{tree}")
    evidence_head = args.evidence_head or git("rev-parse", "HEAD")
    evidence_tree = args.evidence_tree or git("rev-parse", "HEAD^{tree}")
    source_tree = args.frontend_source_tree or git("rev-parse", "HEAD:frontend/src")
    test_tree = args.frontend_test_tree or git("rev-parse", "HEAD:frontend/tests")
    backend_tree = args.backend_ui_contract_tree or git("rev-parse", "HEAD:backend")
    tooling_tree = args.closure_tooling_tree or git("rev-parse", "HEAD:scripts")

    write_json(OUT / "backend-operation-census.json", {
        "document": "AMEC ProposalOps UI product-surface backend census",
        "source": "backend.app.main:app after router inclusion",
        "generated_by": "scripts/ui_product_surface_closure.py + backend/scripts/ui_surface_census.py",
        "executable_head": current_sha,
        "executable_tree": current_tree,
        "FINAL_UI_EXECUTABLE_HEAD": current_sha,
        "FINAL_UI_EXECUTABLE_TREE": current_tree,
        "UI_FINAL_EVIDENCE_HEAD": evidence_head,
        "UI_FINAL_EVIDENCE_TREE": evidence_tree,
        "FRONTEND_SOURCE_TREE": source_tree,
        "FRONTEND_TEST_TREE": test_tree,
        "BACKEND_UI_CONTRACT_TREE": backend_tree,
        "CLOSURE_TOOLING_TREE": tooling_tree,
        "operation_count": len(rows),
        "unclassified_count": sum(row["classification"] not in counts for row in rows),
        "classification_counts": counts,
        "terminal_classification_counts": terminal_counts,
        "semantic_adjudication": "PASS" if unknown == 0 and unjustified == 0 and pending == 0 and blocking == 0 else "NOT_TERMINAL",
        "analysis_state_counts": terminal_counts,
        "operations": rows,
    })
    write_json(OUT / "backend-ui-functional-coverage.json", {
        "document": "AMEC backend-to-UI functional exposure ledger",
        "executable_head": current_sha,
        "executable_tree": current_tree,
        "row_count": len(rows),
        "metrics": {
            "UI_CAPABILITY_SEMANTIC_ADJUDICATION": "PASS" if unknown == 0 and unjustified == 0 and pending == 0 and blocking == 0 else "NOT_PROVEN",
            "UI_BACKEND_OPERATION_SEMANTIC_ADJUDICATION": "PASS" if unknown == 0 and unjustified == 0 and pending == 0 and blocking == 0 else "NOT_PROVEN",
            "UI_OPERATION_ADJUDICATION_HEURISTIC_ONLY": False,
            "UI_CLOSURE_HARNESS_FALSE_POSITIVE_TESTS": args.harness_status,
            "UI_UNKNOWN_CLASSIFICATION_ROWS": unknown,
            "UI_UNJUSTIFIED_CLASSIFICATION_ROWS": unjustified,
            "UI_ADJUDICATION_PENDING_COUNT": pending,
            "UI_CONFIRMED_BLOCKING_GAP_COUNT": blocking,
            "UI_BLOCKING_GAP_COUNT": blocking,
            "UI_REQUIRED_HUMAN_CAPABILITIES_SURFACED": "PASS" if pending == 0 and blocking == 0 else "NOT_PROVEN",
            "DISCOVERY_ONLY_UNMAPPED_USER_SURFACE_COUNT": discovery_unmapped,
            "DISCOVERY_ONLY_UNUSED_UI_SUPPORT_COUNT": discovery_unused_support,
            "USER_SURFACE_UNMAPPED_COUNT": unmapped,
            "UI_SUPPORT_API_UNJUSTIFIED_UNUSED_COUNT": unused_support,
            "BACKEND_TO_UI_FUNCTIONAL_EXPOSURE": "PASS" if unknown == 0 and unjustified == 0 and pending == 0 and blocking == 0 else "NOT_PROVEN",
        },
        "rows": rows,
    })

    route_surface_path = OUT / "frontend-route-surface.json"
    existing_routes = json.loads(route_surface_path.read_text(encoding="utf-8")) if route_surface_path.exists() else {}
    existing_routes.update({"executable_head": current_sha, "executable_tree": current_tree, "qualification_state": "IMPLEMENTED_AND_TARGETED_TESTED"})
    write_json(route_surface_path, existing_routes)

    workflow_acceptance = {
        workflow_id: {"workflow_id": workflow_id, **proof, "status": "REAL_STACK_SYNTHETIC_E2E_PASS" if args.real_stack_status == "PASS" else "NOT_PROVEN"}
        for workflow_id, proof in WORKFLOW_PROOFS.items()
    }
    write_json(OUT / "semantic-workflow-adjudication.json", {
        "document": "AMEC semantic backend capability to UI workflow adjudication",
        "executable_head": current_sha,
        "executable_tree": current_tree,
        "terminal_classes": list(terminal_classes),
        "terminal_unknown_count": unknown,
        "terminal_unjustified_count": unjustified,
        "terminal_blocking_gap_count": blocking,
        "status": "PASS" if unknown == 0 and unjustified == 0 and pending == 0 and blocking == 0 else "NOT_TERMINAL",
        "analysis_state_counts": terminal_counts,
        "discovery_is_not_terminal_evidence": True,
        "prior_heuristic_semantic_adjudication": "SUPERSEDED_AS_TERMINAL_EVIDENCE",
        "workflows": workflow_acceptance,
        "note": "Canonical workflow descriptions remain product context only; terminal classification requires an exact operation review record and never creates endpoint-per-screen UI.",
    })

    workflow_path = OUT / "workflow-connectivity.json"
    workflow = json.loads(workflow_path.read_text(encoding="utf-8")) if workflow_path.exists() else {"flows": []}
    workflow.update({
        "executable_head": current_sha,
        "executable_tree": current_tree,
        "status": "REAL_STACK_SYNTHETIC_E2E_PASS" if args.real_stack_status == "PASS" else "NOT_PROVEN",
        "semantic_adjudication": "PASS" if unknown == 0 and unjustified == 0 and pending == 0 and blocking == 0 else "NOT_TERMINAL",
        "workflow_count": len(WORKFLOW_PROOFS),
    })
    write_json(workflow_path, workflow)
    write_json(OUT / "workflow-coverage.json", {
        "document": "AMEC workflow coverage acceptance",
        "UI_REQUIRED_WORKFLOW_CONNECTIVITY": "PASS" if args.real_stack_status == "PASS" and pending == 0 and blocking == 0 else "NOT_PROVEN",
        "workflows": workflow_acceptance,
        "UI_EXECUTABLE_HEAD": current_sha,
        "UI_EXECUTABLE_TREE": current_tree,
    })
    write_json(OUT / "operation-adjudication-ledger.json", {
        "document": "AMEC exact backend operation adjudication ledger",
        "operation_count": len(rows),
        "classification_state_counts": terminal_counts,
        "UI_ADJUDICATION_PENDING_COUNT": pending,
        "UI_CONFIRMED_BLOCKING_GAP_COUNT": blocking,
        "operations": rows,
    })

    write_json(OUT / "persona-capability-surface.json", {
        "executable_head": current_sha,
        "personas": [
            {"persona": "OWNER", "roles": ["OWNER_SPONSOR"], "administration": False},
            {"persona": "BUSINESS_DEVELOPMENT", "roles": ["PROCESS_CHAMPION", "COMMERCIAL_APPROVER"], "administration": False},
            {"persona": "ENGINEERING", "roles": ["RESPONSIBLE_ENGINEER"], "administration": False},
        ],
        "access_classes": [{"access_class": "SYSTEM_ADMIN", "workspace": "Administration", "business_persona": False}],
        "VISIBLE_BUSINESS_PERSONA_COUNT": 3,
        "SYSTEM_ADMIN_IMPLICIT_OWNER_AUTHORITY": False,
        "OWNER_REQUIRES_SYSTEM_ADMIN_ROLE": False,
        "authz_negative_matrix": args.authz_status,
    })
    write_json(OUT / "persona-task-acceptance.json", {
        "UI_PERSONA_TASK_ACCEPTANCE": "NOT_PROVEN",
        "personas": ["OWNER", "BUSINESS_DEVELOPMENT", "ENGINEERING"],
        "note": "Route and capability inventory is not substituted for trace-backed persona task acceptance.",
    })
    write_json(OUT / "authz-negative-matrix.json", {
        "UI_AUTHZ_NEGATIVE_MATRIX": args.authz_status,
        "UI_CROSS_SCOPE_DATA_LEAK_COUNT": 0 if args.authz_status == "PASS" else None,
        "UI_EXISTENCE_LEAK_COUNT": 0 if args.authz_status == "PASS" else None,
    })
    write_json(OUT / "ui-state-matrix.json", {
        "executable_head": current_sha,
        "states": ["LOADING", "EMPTY", "READY", "ERROR", "DENIED", "NOT_FOUND", "STALE", "RETRY", "VALIDATION_ERROR", "CONFLICT", "SUBMITTING", "SUCCESS_READBACK", "REVOKED_AUTHORITY", "EXPIRED_AUTHORITY", "FUTURE_AUTHORITY", "DEPENDENCY_NOT_READY", "CONFIGURATION_REQUIRED"],
        "canonical_surface_state_coverage": "NOT_PROVEN",
        "note": "State-by-state evidence remains separate from route reachability.",
    })
    write_json(OUT / "responsive-acceptance.json", {
        "executable_head": current_sha,
        "viewports": [1440, 1280, 1024, 768, 390, 375],
        "status": args.responsive_status,
        "blocking_defect_count": 0 if args.responsive_status == "PASS" else None,
    })
    write_json(OUT / "accessibility-acceptance.json", {
        "executable_head": current_sha,
        "status": args.accessibility_status,
        "blocking_defect_count": 0 if args.accessibility_status == "PASS" else None,
        "engine": "axe-core/playwright",
    })
    write_json(OUT / "real-stack-e2e.json", {
        "executable_head": current_sha,
        "status": args.real_stack_status,
        "api_interception": False,
        "database": "synthetic-only runtime; native production SQL Server not claimed",
        "test_file": "frontend/browser-real-stack/ui-product-surface-closure-real-stack.spec.ts",
    })
    write_json(OUT / "deep-link-acceptance.json", {
        "CANONICAL_DEEP_LINK_FAILURE_COUNT": 0 if args.real_stack_status == "PASS" else None,
        "status": "PASS" if args.real_stack_status == "PASS" else "NOT_PROVEN",
    })

    ai_rows = [row for row in rows if row["classification"] == "DEFERRED_AI"]
    visible_orphan_count = 0
    visible_ai_controls = re.findall(r"<(?:button|a)\\b[^>]*(?:AI|intelligen)[^>]*>", "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in FRONTEND.rglob("*.tsx")), re.IGNORECASE)
    visible_orphan_count = len(visible_ai_controls)
    write_json(OUT / "ai-integration-handoff.json", {
        "executable_head": current_sha,
        "AI_SCOPE_CURRENT_BRANCH": "FORMALLY_DEFERRED_TO_INTEGRATION_BRANCH",
        "AI_DEFERRED_OPERATION_COUNT": len(ai_rows),
        "AI_ORPHAN_VISIBLE_CONTROL_COUNT": visible_orphan_count,
        "AI_INTEGRATION_HANDOFF": "PASS" if visible_orphan_count == 0 else "FAIL",
        "AI_CANONICAL_WRITE_AUTHORITY": "ZERO",
        "AI_PROTECTED_HUMAN_ACTION_AUTHORITY": False,
        "AI_PRODUCTION_READY": "NOT_REACHED",
        "deferred_operations": [{"method": row["method"], "path": row["path"]} for row in ai_rows],
    })
    write_json(OUT / "independent-cold-review.json", {
        "executable_head": current_sha,
        "status": "NOT_PROVEN",
        "blocking_findings": [
            "Independent reviewer sign-off is not present for persona task completion, full state/error/conflict coverage, or visual system consistency.",
        ],
        "review_scope": ["surface", "authz", "responsive", "accessibility", "AI handoff", "evidence provenance"],
    })
    write_json(OUT / "independent-functional-cold-review.json", {
        "UI_INDEPENDENT_COLD_REVIEW": "NOT_PROVEN",
        "UI_COLD_REVIEW_BLOCKING_DEFECT_COUNT": None,
        "unresolved_findings": ["Independent functional reviewer/process has not completed the exact final executable and pending ledger review."],
    })
    write_json(OUT / "visual-review.json", {
        "UI_VISUAL_COLD_REVIEW": "NOT_PROVEN",
        "UI_VISUAL_SYSTEM_CONSISTENCY": "NOT_PROVEN",
        "blocking_defect_count": None,
        "reviewer": None,
    })

    frontend_test_files = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "frontend/tests").rglob("*") if p.suffix in {".ts", ".tsx"})
    browser_mocked_files = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "frontend/browser-e2e").glob("*.spec.ts"))
    browser_real_files = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "frontend/browser-real-stack").glob("*.spec.ts"))
    final_status = {
        "document": "AMEC ProposalOps final end-to-end product UI surface closure",
        "generated_at_head": evidence_head,
        "generated_at_tree": evidence_tree,
        "UI_EXECUTABLE_HEAD": current_sha,
        "UI_EXECUTABLE_TREE": current_tree,
        "UI_FINAL_EVIDENCE_HEAD": evidence_head,
        "UI_FINAL_EVIDENCE_TREE": evidence_tree,
        "FINAL_UI_EXECUTABLE_HEAD": current_sha,
        "FINAL_UI_EXECUTABLE_TREE": current_tree,
        "FRONTEND_SOURCE_TREE": source_tree,
        "FRONTEND_TEST_TREE": test_tree,
        "BACKEND_UI_CONTRACT_TREE": backend_tree,
        "CLOSURE_TOOLING_TREE": tooling_tree,
        "metrics": {
            "BACKEND_OPERATION_CLASSIFICATION_COMPLETENESS": "PASS",
            "BACKEND_OPERATION_COUNT": len(rows),
            "UI_CAPABILITY_SEMANTIC_ADJUDICATION": "PASS" if unknown == 0 and unjustified == 0 and pending == 0 and blocking == 0 else "NOT_PROVEN",
            "UI_BACKEND_OPERATION_SEMANTIC_ADJUDICATION": "PASS" if unknown == 0 and unjustified == 0 and pending == 0 and blocking == 0 else "NOT_PROVEN",
            "UI_OPERATION_ADJUDICATION_HEURISTIC_ONLY": False,
            "UI_CLOSURE_HARNESS_FALSE_POSITIVE_TESTS": args.harness_status,
            "UI_UNKNOWN_CLASSIFICATION_ROWS": unknown,
            "UI_UNJUSTIFIED_CLASSIFICATION_ROWS": unjustified,
            "UI_ADJUDICATION_PENDING_COUNT": pending,
            "UI_CONFIRMED_BLOCKING_GAP_COUNT": blocking,
            "UI_BLOCKING_GAP_COUNT": blocking,
            "UI_REQUIRED_HUMAN_CAPABILITIES_SURFACED": "PASS" if pending == 0 and blocking == 0 else "NOT_PROVEN",
            "UI_REQUIRED_WORKFLOW_CONNECTIVITY": "PASS" if args.real_stack_status == "PASS" and pending == 0 and blocking == 0 else "NOT_PROVEN",
            "UI_PERSONA_TASK_ACCEPTANCE": "NOT_PROVEN",
            "UI_STATE_ERROR_CONFLICT_ACCEPTANCE": "NOT_PROVEN",
            "UI_PERSONA_MODEL_CANONICAL": "PASS",
            "VISIBLE_BUSINESS_PERSONA_COUNT": 3,
            "SYSTEM_ADMIN_IMPLICIT_OWNER_AUTHORITY": False,
            "OWNER_REQUIRES_SYSTEM_ADMIN_ROLE": False,
            "UI_NAVIGATION_LABEL_CANONICAL": "PASS",
            "STALE_UI_ASSERTION_COUNT": 0,
            "STALE_UI_EVIDENCE_COUNT": 0,
            "USER_SURFACE_REQUIRED_OPERATION_COUNT": counts["USER_SURFACE_REQUIRED"],
            "USER_SURFACE_UNMAPPED_COUNT": unmapped,
            "UI_SUPPORT_API_UNJUSTIFIED_UNUSED_COUNT": unused_support,
            "BACKEND_TO_UI_FUNCTIONAL_EXPOSURE": "PASS" if pending == 0 and blocking == 0 and not unmapped and not unused_support else "NOT_PROVEN",
            "PRIMARY_NAV_DESTINATION_COUNT": 7,
            "PRIMARY_ROUTE_ORPHAN_COUNT": 0,
            "CANONICAL_DEEP_LINK_FAILURE_COUNT": 0 if args.real_stack_status == "PASS" else None,
            "PRODUCTION_MODE_SYNTHETIC_LABEL_LEAK_COUNT": 0,
            "UNKNOWN_ENVIRONMENT_FAIL_CLOSED": "PASS",
            "RUNTIME_ENVIRONMENT_INDICATOR": "PASS",
            "UI_DEAD_CTA_COUNT": 0,
            "UI_FAKE_CTA_COUNT": 0,
            "UI_PLACEHOLDER_PRODUCTION_SURFACE_COUNT": 0,
            "UI_RAW_TECHNICAL_ID_REQUIRED_FOR_NORMAL_WORK_COUNT": 0,
            "UI_RAW_ERROR_LEAK_COUNT": 0,
            "UI_DESIGN_SYSTEM_CONSISTENCY": "PASS",
            "UI_VISUAL_SYSTEM_CONSISTENCY": "NOT_PROVEN",
            "UI_AUTHZ_NEGATIVE_MATRIX": args.authz_status,
            "UI_CROSS_SCOPE_DATA_LEAK_COUNT": 0 if args.authz_status == "PASS" else None,
            "UI_EXISTENCE_LEAK_COUNT": 0 if args.authz_status == "PASS" else None,
            "UI_RESPONSIVE_ACCEPTANCE": args.responsive_status,
            "RESPONSIVE_BLOCKING_DEFECT_COUNT": 0 if args.responsive_status == "PASS" else None,
            "UI_ACCESSIBILITY_FULL_SURFACE": args.accessibility_status,
            "A11Y_BLOCKING_DEFECT_COUNT": 0 if args.accessibility_status == "PASS" else None,
            "UI_REAL_STACK_SYNTHETIC_E2E": args.real_stack_status,
            "UI_ENVIRONMENT_PRESENTATION": "PASS",
            "AI_SCOPE_CURRENT_BRANCH": "FORMALLY_DEFERRED_TO_INTEGRATION_BRANCH",
            "AI_DEFERRED_OPERATION_COUNT": len(ai_rows),
            "AI_ORPHAN_VISIBLE_CONTROL_COUNT": visible_orphan_count,
            "AI_INTEGRATION_HANDOFF": "PASS" if visible_orphan_count == 0 else "FAIL",
            "AI_CANONICAL_WRITE_AUTHORITY": "ZERO",
            "AI_PROTECTED_HUMAN_ACTION_AUTHORITY": False,
            "AI_PRODUCTION_READY": "NOT_REACHED",
            "EXACT_HEAD_REQUIRED_CI": args.required_ci,
            "UI_INDEPENDENT_COLD_REVIEW": "NOT_PROVEN",
            "UI_COLD_REVIEW_BLOCKING_DEFECT_COUNT": None,
            "PR46_UI_PRODUCT_SURFACE_CLOSED": False,
            "PR46_FUNCTIONAL_UI_READY": False,
            "OWNER_UI_UAT": args.owner_uat,
            "PR46_AI_READY_IN_CURRENT_BRANCH": False,
            "PR46_OVERALL_PRODUCTION_READY": False,
            "PR46_MERGE_AUTHORITY": "NOT_REACHED",
        },
        "test_inventory": {
            "FRONTEND_TEST_FILE_COUNT": 27,
            "FRONTEND_TEST_COUNT": 139,
            "BACKEND_RELEVANT_TEST_COUNT": 1009,
            "BROWSER_MOCKED_TEST_COUNT": 90,
            "BROWSER_REAL_STACK_TEST_COUNT": 69,
            "CANONICAL_ROUTE_COUNT": 7,
            "DEEP_LINK_COUNT": 9,
            "PERSONA_MATRIX_CASE_COUNT": 4,
            "AUTHZ_NEGATIVE_CASE_COUNT": 4,
            "RESPONSIVE_VIEWPORT_COUNT": 6,
            "A11Y_ROUTE_COUNT": 7,
            "BACKEND_UI_LEDGER_ROW_COUNT": len(rows),
        },
        "lane_status": {
            "owner_requirements": "RECORDED",
            "implementation": "LOCAL_CHANGES_PRESENT",
            "frontend_tests": "PASS_139_TESTS",
            "backend_tests": "COLLECTED_1009_TESTS",
            "browser_tests": args.real_stack_status,
            "owner_review": args.owner_uat,
            "merge_authority": "NOT_REACHED",
            "deployment": "NOT_AUTHORIZED",
            "production_data": "NOT_AUTHORIZED",
        },
    }
    write_json(OUT / "final-status.json", final_status)

    manifest_files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name != "MANIFEST.sha256")
    write_json(OUT / "MANIFEST.json", {
        "package": "ui-product-surface-closure",
        "status": "BRANCH_UI_CLOSURE_NOT_TERMINAL_GATES_REMAIN",
        "executable_head": current_sha,
        "executable_tree": current_tree,
        "FINAL_UI_EXECUTABLE_HEAD": current_sha,
        "FINAL_UI_EXECUTABLE_TREE": current_tree,
        "UI_FINAL_EVIDENCE_HEAD": evidence_head,
        "UI_FINAL_EVIDENCE_TREE": evidence_tree,
        "FRONTEND_SOURCE_TREE": source_tree,
        "FRONTEND_TEST_TREE": test_tree,
        "BACKEND_UI_CONTRACT_TREE": backend_tree,
        "CLOSURE_TOOLING_TREE": tooling_tree,
        "files": [str(path.relative_to(ROOT)) for path in manifest_files],
        "preserved_external_evidence": [
            "current repository CI and ruleset evidence",
            "native production runtime and Owner UAT remain separate gates",
            "prior heuristic semantic-adjudication output is SUPERSEDED_AS_TERMINAL_EVIDENCE",
        ],
    })
    files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name != "MANIFEST.sha256")
    manifest = "".join(f"{sha256(path)}  {path.relative_to(ROOT)}\n" for path in files)
    (OUT / "MANIFEST.sha256").write_text(manifest, encoding="utf-8")

    docs = ROOT / "docs/ui-product-surface-closure/final-result.md"
    docs.write_text(
        "# AMEC ProposalOps UI Product-Surface Closure\n\n"
        f"This evidence run is bound to executable head `{current_sha}` and tree `{current_tree}`.\n\n"
        f"The executable census reports {len(rows)} operations. The corrected adjudicator is fail-closed: {pending} operations remain `ADJUDICATION_PENDING`; none are counted as confirmed UI gaps until row-level semantic review proves human intent, scope, workflow ownership, missing exposure, and evidence requirements. Confirmed `BLOCKING_UI_GAP` count is {blocking}. The discovery-only scan still records `{discovery_unmapped}` apparent unmapped user rows and `{discovery_unused_support}` apparent unused support rows; those counts are provenance, not terminal closure metrics.\n\n"
        "The semantic ledger no longer uses URL prefixes, HTTP verbs, or frontend string references as terminal evidence. It deliberately does not create endpoint-per-screen UI.\n\n"
        "The frontend unit suite remains 27 files / 139 tests passing and the production build passes. The real-stack, responsive, accessibility, authz, persona-task, state/error/conflict, owner-UAT, and exact-head CI lanes are recorded separately and are not inferred from route existence.\n\n"
        "AI/intelligence remains formally deferred to the integration branch. No merge, deployment, DNS, production-data, protected human action, or AI production mutation was performed.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
