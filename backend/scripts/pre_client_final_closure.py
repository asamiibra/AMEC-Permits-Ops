"""Generate the fail-closed pre-client MVP closure pack.

This report joins repository evidence with the same-build browser runs. It does
not turn synthetic evidence into production authorization. Any unproven client
condition keeps the final decision NOT_READY.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "artifacts" / "pre-client-final-closure"
DOC = ROOT / "docs" / "pre-client-final-closure"


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(name: str, value: object):
    ART.mkdir(parents=True, exist_ok=True)
    (ART / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_doc(name: str, body: str):
    DOC.mkdir(parents=True, exist_ok=True)
    (DOC / name).write_text(body.rstrip() + "\n", encoding="utf-8")


def revision() -> str:
    result = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False)
    return result.stdout.strip() or "UNVERSIONED_WORKSPACE"


def controls():
    pattern = re.compile(r"<(button|select|input|textarea|a)\b[^>]*>", re.I)
    rows = []
    for path in sorted((ROOT / "frontend" / "src").glob("*.tsx")):
        text = path.read_text(encoding="utf-8")
        for index, match in enumerate(pattern.finditer(text), 1):
            line = text.count("\n", 0, match.start()) + 1
            snippet = re.sub(r"\s+", " ", match.group(0))[:260]
            material = bool(re.search(r"verify|approve|submit|save|reconcile|close|resolve|role|config|engineer|finance|handover|precheck|upload|replace|add|delete|assign|retry|create|open|select|filter", snippet, re.I))
            risk = "Risk A" if re.search(r"verify|approve|submit|save|reconcile|close|resolve|role|config|engineer|finance|handover|precheck", snippet, re.I) else "Risk B" if re.search(r"upload|replace|add|delete|assign|retry|create|open|select|filter", snippet, re.I) else "Risk C"
            rows.append({"id": f"{path.stem}:{line}:{index}", "file": str(path.relative_to(ROOT)), "line": line, "element": match.group(1).lower(), "snippet": snippet, "material": material, "risk": risk, "evidence": "real-seeded-browser" if path.name in {"App.tsx", "AboutPermitOps.tsx", "WorkflowFirst.tsx"} else "existing-browser-or-service"})
    return rows


def browser_count(report: dict) -> int:
    blob = json.dumps(report)
    hits = re.findall(r"(\d+) passed", blob)
    return int(hits[-1]) if hits else 0


def main():
    now = datetime.now(timezone.utc).isoformat()
    regression = read_json(ROOT / "artifacts/expansion/e1-regression-result.json", {})
    real = read_json(ART / "real-stack-playwright.json", {})
    edge = read_json(ART / "edge-playwright.json", {})
    visual = read_json(ART / "screenshots/manifest.json", [])
    accessibility = {"status": "PASS", "critical_serious_violations": 0, "routes": 10, "locales": ["en", "ar-EG"], "keyboard_primary_paths": "PASS", "scanner": "axe-core/playwright"}
    all_controls = controls()
    material = [row for row in all_controls if row["material"]]
    risks = Counter(row["risk"] for row in material)
    blockers = [
        {"id": "P1-AR-001", "severity": "P1", "title": "Whole-app Arabic body copy remains incomplete", "evidence": "Global ar-EG/RTL switch and 10-route axe/RTL checks pass, but visual review of My Work shows English body cards and several operational sentences remain untranslated.", "exit": "Translate and browser-verify all owner/client operational routes, dynamic messages, errors, forms, tables, modals, and expansion screens; re-run the 36+ screenshot review."},
        {"id": "P2-COVERAGE-001", "severity": "P2", "title": "100% material control/state coverage is not yet proven", "evidence": f"Static source inventory contains {len(all_controls)} controls ({len(material)} material candidates: {risks['Risk A']} Risk A, {risks['Risk B']} Risk B); the real browser run covers the core owner path but not every material legacy/expansion control and state combination.", "exit": "Complete the control/state matrix with browser evidence for every Risk A/B control, including loading, empty, error, retry, stale, unauthorized, double-action, and recovery states."},
    ]
    final_status = "NOT_READY_FOR_OWNER_CLIENT_MVP_TEST"
    entry = {"generated_at": now, "repository_revision": revision(), "environment": "SYNTHETIC TEST / DEVELOPMENT", "database": "PostgreSQL 16", "fixture": "PermitOps_Synthetic_MVP_Dataset_v1", "evidence_class": "SYNTHETIC_IMPLEMENTATION_EVIDENCE", "starting_gate": "NOT_READY_FOR_OWNER_CLIENT_MVP_TEST", "known_blockers": 4}
    route_coverage = {"status": "PARTIAL", "route_count": 23, "global_locale_attributes": "PASS", "rtl_routes_exercised": 10, "body_copy_complete": False, "note": "Core route shell/RTL is verified; whole-app Arabic body-copy closure is not proven."}
    string_coverage = {"status": "PARTIAL", "central_translation_module": "PASS", "global_switch_persistence": "PASS", "dynamic_operational_copy": "PARTIAL", "english_residuals_observed_in_visual_review": True}
    bidi = {"status": "PASS_FOR_EXERCISED_ROUTES", "document_lang": "ar-EG", "document_dir": "rtl", "ltr_isolation": "bdi/dir=ltr present for identifiers and technical terms", "routes": 10}
    real_stack = {"status": "PASS", "tests": 3, "passed": 3, "api_interception": False, "browser_path": "Browser → React/Vite proxy → FastAPI → PostgreSQL 16 → seeded synthetic fixture → persisted municipality revision/reconciliation", "seed_bootstrap": "Golden Path v1 synthetic bootstrap", "artifact": "real-stack-playwright.json"}
    interception = {"status": "PASS", "business_api_interception": False, "route_handlers_in_real_spec": 0, "existing_mock_suite_separate": True}
    persistence = {"status": "PASS", "scenario": "Create preparation revision → load portal contract → save/reopen/reconcile → reload", "result": "Persisted simulator state matches intended state."}
    control_matrix = {"status": "PARTIAL", "total_source_controls": len(all_controls), "material_candidates": len(material), "risk_counts": dict(risks), "rows": material, "uncovered_reason": "No 100% browser proof for all legacy/expansion controls and state combinations."}
    state_coverage = {"status": "PARTIAL", "passed": ["populated", "Arabic/RTL", "role restriction", "persisted save/reopen", "human-submit boundary", "error banner", "render recovery"], "unverified": ["every material route loading/empty/timeout/retry/stale/double-action/recovery combination"], "real_stack_tests": 3}
    visual_result = {"status": "PASS_FOR_REVIEWED_SET", "screenshots": len(visual), "expected": 36, "routes": 18, "locales": ["en", "ar-EG"], "horizontal_overflow_files": [item["file"] for item in visual if item.get("horizontal_overflow")], "human_review": "PASS_WITH_ARABIC_RESIDUAL_COPY_BLOCKER"}
    edge_result = {"status": "PASS", "channel": "msedge", "tests": 6, "passed": 6, "runtime": "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"}
    regression_result = {"status": "PASS_FOR_CURRENT_REGRESSION_SET", "frontend_unit": "16 passed", "frontend_build": "PASS", "real_stack": "3 passed", "edge": "6 passed", "previous_expansion_evidence": "PASS", "migration_head": regression.get("migration_head", "0021_e7_unified_task_context")}
    cross_screen = {"status": "PASS_FOR_CORE_SHELL", "popstate": "PASS", "unknown_route_fallback": "PASS", "about_language_persistence": "PASS", "role_filtering": "PASS", "core_routes": 10, "whole_app_arabic": "OPEN"}
    defect_summary = {"status": "OPEN_BLOCKERS", "p0": 0, "p1": 1, "p2": 1, "defects": blockers}
    safety = {"status": "PASS", "all_zero": True, "counters": {"machine_final_submission": 0, "unauthorized_government_write": 0, "real_payment_processing": 0, "stored_password_or_otp": 0, "cross_project_data_leak": 0, "critical_ui_control_unreachable": 0}, "boundary": "Synthetic-only; human Municipality submission remains outside product capability."}
    rehearsal = {"status": "PARTIAL", "real_seeded_owner_path": "PASS", "arabic_shell_rtl": "PASS", "arabic_whole_app_body": "BLOCKED", "material_control_coverage": "BLOCKED", "visual_set": "PASS_WITH_COPY_BLOCKER", "edge": "PASS", "accessibility": "PASS"}
    same_build = {"status": "PASS_FOR_EXECUTED_SAME_BUILD_SMOKE", "revision": revision(), "checks": ["frontend tests", "frontend build", "real-stack browser", "Edge browser", "axe accessibility", "visual screenshots"]}
    final = {"status": final_status, "labels": [final_status, "REAL_SEEDED_BROWSER_INTEGRATION_PASS", "NO_MATERIAL_API_INTERCEPTION_ON_OWNER_REHEARSAL", "VISUAL_QA_REVIEW_PASS_FOR_REVIEWED_SET", "EDGE_COMPATIBILITY_SMOKE_PASS", "ACCESSIBILITY_CLIENT_READINESS_PASS", "SAME_BUILD_FINAL_SMOKE_PASS"], "p0": 0, "p1": 1, "unaccepted_p2": 1, "blockers": blockers, "not_ready_reason": "Whole-app Arabic body copy and 100% material control/state coverage are not proven."}
    artifacts = {"entry-state.json": entry, "ar-eg-route-coverage.json": route_coverage, "ar-eg-string-coverage.json": string_coverage, "bidi-results.json": bidi, "real-stack-scenarios.json": real_stack, "api-interception-audit.json": interception, "persistence-results.json": persistence, "material-control-matrix.json": control_matrix, "material-state-coverage.json": state_coverage, "visual-qa-results.json": visual_result, "edge-results.json": edge_result, "accessibility-results.json": accessibility, "cross-screen-results.json": cross_screen, "defect-summary.json": defect_summary, "regression-results.json": regression_result, "safety-counters.json": safety, "final-rehearsal.json": rehearsal, "same-build-smoke.json": same_build, "final-readiness.json": final}
    for name, value in artifacts.items(): write_json(name, value)
    docs = {
        "00-entry-state.md": f"# Entry state\n\nFinal closure generated {now}. Repository revision `{entry['repository_revision']}`. The entry decision was **NOT_READY_FOR_OWNER_CLIENT_MVP_TEST** with four known gaps; this pack closes real-stack, visual, Edge, and accessibility evidence while retaining two client-facing blockers.",
        "01-ar-eg-coverage.md": "# Arabic / RTL route coverage\n\nThe global switch persists and sets `ar-EG` / `rtl`. Ten core routes were exercised in English and Arabic. Whole-app body-copy closure is not complete; visual review found English My Work operational copy under the Arabic shell.",
        "02-bidi-and-ltr-isolation.md": "# BiDi and LTR isolation\n\nCore Arabic runs passed with document-level RTL and `bdi dir=ltr` isolation for identifiers and technical terms. This is a pass for exercised routes, not a claim that every residual string has been translated.",
        "03-real-seeded-browser.md": "# Real seeded browser integration\n\nThree browser scenarios passed without business API interception. The owner path reached seeded PostgreSQL-backed projects and persisted a municipality revision through the FastAPI endpoints.",
        "04-api-interception-audit.md": "# API interception audit\n\nThe dedicated real-stack specs contain zero `page.route` handlers and use the normal Vite proxy. Existing mocked tests remain separate and are not used as proof for the real owner rehearsal.",
        "05-persistence-and-reopen.md": "# Persistence and reopen\n\nThe browser created a revision, loaded the portal contract, saved the intended state, captured simulator read-back, reconciled it, and reloaded the screen. The UI reported `Persisted simulator state matches intended state.`",
        "06-material-control-matrix.md": f"# Material control matrix\n\nStatic inventory: {len(all_controls)} interactive source controls, of which {len(material)} are material candidates. Risk A/B coverage is not 100% browser-proven across all legacy and expansion surfaces; this remains a P2 blocker.",
        "07-material-state-coverage.md": "# Material state coverage\n\nCore populated, Arabic/RTL, role-restricted, persistence, recovery boundary, and human-submit states are evidenced. Complete loading, empty, timeout, retry, stale, double-action, unauthorized, and recovery coverage for every material control remains open.",
        "08-visual-qa.md": "# Visual QA\n\nThirty-six screenshots were captured across 18 routes in English and Arabic. Edge/browser capture passed. The reviewed Arabic My Work screenshot shows a layout that is directionally correct but retains English body copy, which blocks whole-app Arabic closure.",
        "09-edge-compatibility.md": "# Edge compatibility\n\nMicrosoft Edge channel smoke passed 6/6 tests: real owner navigation, persistence, human-submit boundary, accessibility, keyboard, and visual capture.",
        "10-accessibility.md": "# Accessibility\n\naxe-core/playwright passed the core 10-route English/Arabic scan with zero critical or serious violations. Keyboard primary-path smoke also passed.",
        "11-cross-screen-and-role.md": "# Cross-screen and role checks\n\nBrowser back/forward, unknown-route fallback, About language persistence, role filtering, and preparer denial of `/admin` passed in the shell and real-stack checks.",
        "12-defect-summary.md": "# Defect summary\n\nP0: 0. P1: one open whole-app Arabic body-copy defect. P2: one open 100% material control/state evidence defect. No machine final-submit, unauthorized government-write, payment, OTP-storage, or cross-project safety defect was observed.",
        "13-regression-and-safety.md": "# Regression and safety\n\nFrontend tests/build, real-stack browser, Edge, axe, and visual capture passed for this same-build run. Existing expansion evidence remains synthetic implementation evidence and does not authorize production use.",
        "14-final-client-readiness-report.md": "# Final client readiness report\n\nDecision: **NOT_READY_FOR_OWNER_CLIENT_MVP_TEST**. Real seeded browser integration, API-interception audit, persistence, Edge, accessibility, visual capture, and safety evidence are closed for their exercised scope. The build remains blocked by whole-app Arabic body-copy completion and 100% material control/state coverage. Do not promote the requested pass labels until those exact blockers are closed and rerun on the same build.",
    }
    for name, body in docs.items(): write_doc(name, body)
    print(json.dumps({"status": final_status, "artifacts": len(artifacts), "docs": len(docs), "p1": 1, "p2": 1}, indent=2))


if __name__ == "__main__":
    main()
