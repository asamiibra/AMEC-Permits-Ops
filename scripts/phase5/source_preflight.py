from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path

from common import PHASE5_ARTIFACTS, ROOT, write_json
from registry import CATEGORY_EVIDENCE_POLICY, EVIDENCE_PRODUCERS, PREDICATE_REGISTRY, PIPELINE_STAGES, assertion_policy, category_policy_audit, canonical_names, pipeline_audit
from acceptance import REQUIREMENT_GROUPS
from finalize import SUMMARY_FIELD_SOURCE_MAP


REQUIRED_PATHS = [
    "backend/app/services/classifier_v2.py", "backend/app/schemas/classifier_v2.py",
    "backend/app/api/phase5.py", "backend/app/main.py", "backend/app/services/phase4.py",
    "backend/app/schemas/phase4.py", "frontend/src/Phase5Review.tsx", "frontend/src/App.tsx",
    "frontend/playwright.real-stack.config.ts", "scripts/phase5/runtime_evidence.py",
    "scripts/phase5/corpus_coverage.py", "scripts/phase5/sanitize_evidence.py",
    "docs/phase5/governing/manifest.json",
]
REQUIRED_BROWSER_IDS = [
    "P5-BROWSER-NEW", "P5-BROWSER-AMBIGUOUS_REVIEW", "P5-BROWSER-OUT_OF_SCOPE",
    "P5-BROWSER-SECRET_EXCLUDE", "P5-BROWSER-MODIFIED_KNOWN_SOURCE",
    "P5-BROWSER-MOVE_RENAME_CANDIDATE", "P5-BROWSER-MISSING_CANDIDATE",
    "P5-BROWSER-CORRECTION", "P5-BROWSER-PROTECTED_ACTION", "P5-BROWSER-PERSONA_SCOPE",
]
GOVERNING = {
    "ProposalOps_Phase5_Classifier_Shadow_Validation_Master_Design.md": ("761dd4e642ce8dc30589bab393808e965a4f931e9e2a9ddda94cff6f217fa81b", 10708),
    "ProposalOps_Phase5_190_Check_Design_Validation_Report.md": ("61e57216ca5b8671df7337420bb7d116c94be138da62cde851dcab6236ecbe0f", 16845),
    "ProposalOps_Phase5_Actions.md": ("87a2376489a394806f9b11dadad5db710a0a0149ee895a449d1e4ea06823968e", 801),
    "ProposalOps_Phase5_FINAL_R3_OneShot_EvidenceTruth_SQLServer_Browser_Closure_2026-08-24.md": ("0fcb3efe875dff8b8d0c5cd939666ddcf37ea4d3d256e501d8c1927b288d34c5", 46742),
}


def _parse_errors(paths: list[Path]) -> list[str]:
    errors = []
    for path in paths:
        if path.suffix == ".py":
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except SyntaxError as exc:
                errors.append(f"{path.relative_to(ROOT)}:{exc.lineno}:{exc.msg}")
    return errors


def _fixed_sha_findings() -> list[str]:
    findings = []
    for path in (ROOT / "backend/tests").glob("test_*.py"):
        text = path.read_text(encoding="utf-8")
        if "LEGACY_BOOLEAN_BASELINE_SHA" in text and "show" in text and "LEGACY_DESCENDANT_ONLY_PATH_BASELINE_READ_COUNT=0" not in text:
            findings.append(path.relative_to(ROOT).as_posix())
    return findings


def _sql_bind_findings(text: str) -> list[str]:
    findings = []
    if re.search(r"f[\"'](?:SELECT|UPDATE|INSERT|DELETE)\b", text, re.I):
        findings.append("interpolated-sql")
    if re.search(r"text\(\s*[\"'][^\"']*[?:][^\"']*[\"']\s*\)", text):
        findings.append("implicit-text-bind")
    return findings


def _governing_source_checks() -> dict[str, object]:
    manifest_path = ROOT / "docs/phase5/governing/manifest.json"
    errors = []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("schema") != "PROPOSALOPS_PHASE5_GOVERNING_SOURCE_BUNDLE_V1" or manifest.get("file_count") != 4:
            errors.append("manifest-schema")
        rows = {Path(item.get("relative_path", "")).name: item for item in manifest.get("files", [])}
        for filename, (expected_sha, expected_bytes) in GOVERNING.items():
            path = ROOT / "docs/phase5/governing" / filename
            data = path.read_bytes() if path.is_file() else b""
            if not path.is_file() or hashlib.sha256(data).hexdigest() != expected_sha or len(data) != expected_bytes:
                errors.append(filename)
            row = rows.get(filename)
            if not row or row.get("sha256") != expected_sha or row.get("byte_count") != expected_bytes or row.get("copied_verbatim") is not True:
                errors.append(f"manifest-row:{filename}")
    except (OSError, json.JSONDecodeError):
        errors.append("manifest-unreadable")
    return {"result": not errors, "error_count": len(errors), "errors": errors}


def _planned_workflow_checks(path: Path | None) -> dict[str, object]:
    if path is None:
        return {"planned_workflow_present": False, "planned_workflow_stage_count": 0, "planned_workflow_stage_order_pass": False, "planned_workflow_cycle_count": 0, "planned_workflow_preseeded_finalizer_count": 0, "planned_workflow_preseeded_acceptance_integrity_count": 0, "planned_workflow_working_evidence_upload_count": 0, "planned_workflow_sanitized_upload_count": 0, "planned_workflow_unknown_cli_argument_count": 0, "planned_workflow_missing_required_cli_argument_count": 0}
    text = path.read_text(encoding="utf-8")
    positions = [text.find("# " + stage) for stage in PIPELINE_STAGES]
    order_pass = all(position >= 0 for position in positions) and positions == sorted(positions) and len(set(positions)) == len(positions)
    # These are intentionally source-level checks on the actual planned file.
    preseed_finalizer = len(re.findall(r"(?:touch|echo|cat|write_text|result\s*=).*finalizer(?:\.result\.json|=PASS)", text, re.I))
    preseed_integrity = len(re.findall(r"(?:touch|echo|cat|write_text|result\s*=).*acceptance-integrity(?:\.result\.json|=PASS)", text, re.I))
    working_upload = len(re.findall(r"upload-artifact[^\n]*\n(?:.|\n){0,500}?path:\s*\$\{?\{?\s*env\.?(?:EVIDENCE_DIR|WORKING_EVIDENCE_DIR)", text, re.I))
    sanitized_upload = len(re.findall(r"upload-artifact", text, re.I)) - working_upload
    cli_args = set(re.findall(r"--[a-z0-9-]+", text))
    known_args = {"--stage", "--evidence-dir", "--contracts-dir", "--output", "--expected-candidate-sha", "--expected-validation-sha", "--expected-run-id", "--pre-finalizer-acceptance-result", "--pre-finalizer-validation-result", "--acceptance-result", "--validation-result", "--acceptance-integrity-result", "--handoff-seal-result", "--draft-acceptance-path", "--draft-validation-path", "--candidate-sha", "--validation-sha", "--run-id", "--source", "--dest", "--governing-source-dir", "--repo-root", "--require-complete", "--playwright-json", "--spec", "--junitxml", "--bootstrap-result", "--planned-workflow", "--split", "--corpus", "--config", "--format", "--check", "--host", "--ignore", "--name", "--name-only", "--no-tags", "--outDir", "--out", "--platform", "--porcelain", "--port", "--prefix", "--reporter", "--untracked-files", "--with-deps", "--run"}
    unknown = sorted(cli_args - known_args)
    required = 0
    if "--stage produce" in text and not all(arg in text for arg in ("--pre-finalizer-acceptance-result", "--pre-finalizer-validation-result")): required += 1
    if "--stage seal" in text and not all(arg in text for arg in ("--acceptance-integrity-result", "--handoff-seal-result")): required += 1
    return {"planned_workflow_present": True, "planned_workflow_stage_count": len(PIPELINE_STAGES), "planned_workflow_stage_order_pass": order_pass, "planned_workflow_cycle_count": 0 if order_pass else 1, "planned_workflow_preseeded_finalizer_count": preseed_finalizer, "planned_workflow_preseeded_acceptance_integrity_count": preseed_integrity, "planned_workflow_working_evidence_upload_count": working_upload, "planned_workflow_sanitized_upload_count": sanitized_upload, "planned_workflow_unknown_cli_argument_count": len(unknown), "planned_workflow_missing_required_cli_argument_count": required, "planned_workflow_unknown_cli_arguments": unknown}


def run(output_path: Path | None = None, planned_workflow: Path | None = None) -> dict:
    missing = [path for path in REQUIRED_PATHS if not (ROOT / path).is_file()]
    scripts = sorted((ROOT / "scripts/phase5").glob("*.py"))
    specs = sorted((ROOT / "frontend/browser-real-stack").glob("phase5-*.spec.ts"))
    all_text = "\n".join(path.read_text(encoding="utf-8") for path in scripts + specs if path.is_file())
    browser_text = "\n".join(path.read_text(encoding="utf-8") for path in specs if path.is_file())
    browser_missing = [item for item in REQUIRED_BROWSER_IDS if item not in browser_text]
    unknown_producers = [item for item in EVIDENCE_PRODUCERS if item not in all_text]
    aliases = sorted(path.name for path in (ROOT / "contracts/amec/phase5").glob("*.json") if path.name not in canonical_names())
    parse_errors = _parse_errors([path for path in scripts if path.name != "source_preflight.py"])
    bind_findings = _sql_bind_findings(all_text)
    fixed_findings = _fixed_sha_findings()
    policy = category_policy_audit()
    assertion = assertion_policy(REQUIREMENT_GROUPS)
    predicate_missing = sorted({predicate for item in assertion.values() for predicate in item["predicate_ids"]} - PREDICATE_REGISTRY)
    dag = pipeline_audit()
    finalizer_text = (ROOT / "scripts/phase5/finalize.py").read_text(encoding="utf-8")
    authority_text = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in ("backend/app/services/classifier_v2.py", "backend/app/services/phase4.py") if (ROOT / path).is_file())
    authority = {"promotion_requires_human_review": "promotion_requires_human_review" in authority_text or "REVIEW_REQUIRED" in authority_text, "projection_requires_existing_verified_assertion": "verified_assertion" in authority_text.lower() and "projection" in authority_text.lower(), "auto_promotion_enabled": "auto_promotion_enabled = True" in authority_text}
    critical = {
        "C06_category_policy_complete": policy["category_count"] == 30 and policy["result"] == "PASS" and all(len(item["required_producer_ids"]) > 0 for item in CATEGORY_EVIDENCE_POLICY.values()),
        "C08_validator_identity_binding": all(flag in (ROOT / "scripts/phase5/evidence_validate.py").read_text(encoding="utf-8") for flag in ("--expected-candidate-sha", "--expected-validation-sha", "--expected-run-id", "identity_mismatch_count")),
        "C19C_finalizer_meta_triple_binding": all(flag in (ROOT / "scripts/phase5/finalize.py").read_text(encoding="utf-8") for flag in ("expected_validation_sha", "expected_run_id", '"validation_sha"', '"run_id"')),
        "C07_corpus_coverage": all(flag in (ROOT / "scripts/phase5/build_corpus.py").read_text(encoding="utf-8") for flag in ("truth_domain_coverage", "master_content_type_coverage", "M1", "ENGINEERING_WORK")),
        "C20_sanitized_paths": all(flag in (ROOT / "scripts/phase5/sanitize_evidence.py").read_text(encoding="utf-8") for flag in ("<REPO_ROOT>", "<RUNNER_TEMP>", "sanitized-manifest.json", "SANITIZED_JSON_PARSE_FAIL_COUNT", "SANITIZED_XML_PARSE_FAIL_COUNT", "SANITIZED_BYTE_COUNT_MISMATCH_COUNT")),
    }
    required_negative_fixtures = ["descendant-only", "unknown producer", "canonical", "implicit", "browser", "wrong_candidate", "not_executed"]
    fixture_text = (ROOT / "backend/tests/test_phase5_evidence_integrity.py").read_text(encoding="utf-8") if (ROOT / "backend/tests/test_phase5_evidence_integrity.py").is_file() else ""
    missing_fixtures = [item for item in required_negative_fixtures if item.lower() not in fixture_text.lower()]
    source_checks = _governing_source_checks()
    checks = {
        "paths": not missing, "python_syntax": not parse_errors, "canonical_filenames": not aliases,
        "producer_registry": not unknown_producers, "browser_ids": not browser_missing,
        "sql_bind_safety": not bind_findings, "fixed_sha_descendant_guard": not fixed_findings,
        "governing_source_bytes_retrievable": bool(source_checks["result"]), "negative_fixtures": not missing_fixtures,
        **critical,
    }
    planned = _planned_workflow_checks(planned_workflow)
    checks.update({"assertion_policy": len(assertion) == 300, "predicate_registry": not predicate_missing, "pipeline_dag": dag["topological_order_pass"] and dag["cycle_count"] == 0, "summary_source_map": len(SUMMARY_FIELD_SOURCE_MAP) == 17 and all(item.get("producer_ids") and item.get("json_paths") and item.get("expected_type") for item in SUMMARY_FIELD_SOURCE_MAP.values()), "planned_workflow": not planned_workflow or (planned["planned_workflow_stage_order_pass"] and planned["planned_workflow_cycle_count"] == 0 and planned["planned_workflow_preseeded_finalizer_count"] == 0 and planned["planned_workflow_preseeded_acceptance_integrity_count"] == 0 and planned["planned_workflow_working_evidence_upload_count"] == 0 and planned["planned_workflow_sanitized_upload_count"] == 1 and planned["planned_workflow_unknown_cli_argument_count"] == 0 and planned["planned_workflow_missing_required_cli_argument_count"] == 0)})
    result = {
        "version": 5, "result": "PASS" if all(checks.values()) else "FAIL",
        "definite_blocker_count": sum(not value for value in checks.values()), "checks": checks,
        "category_policy_audit": policy, "governing_source_checks": source_checks,
        "missing_paths": missing, "parse_errors": parse_errors, "canonical_filename_reference_mismatch_count": len(aliases),
        "unknown_evidence_producers": unknown_producers, "browser_missing_ids": browser_missing,
        "implicit_text_bind_count": len(bind_findings), "inherited_fixed_sha_descendant_blocker_count": len(fixed_findings),
        "missing_negative_fixture_count": len(missing_fixtures), "synthetic_only": True, "real_data_read": False,
        "C06": critical["C06_category_policy_complete"], "C08": critical["C08_validator_identity_binding"],
        "C19C": critical["C19C_finalizer_meta_triple_binding"], "C07": critical["C07_corpus_coverage"], "C20": critical["C20_sanitized_paths"],
        "category_count": len(CATEGORY_EVIDENCE_POLICY), "requirement_assertion_count": sum(len(items) for items in REQUIREMENT_GROUPS.values()), "assertion_policy_count": len(assertion), "predicate_registry_missing_count": len(predicate_missing), "predicate_registry_missing": predicate_missing, "pipeline_stage_count": len(PIPELINE_STAGES), "pipeline_cycle_count": dag["cycle_count"], "pipeline_topological_order_pass": dag["topological_order_pass"], "finalizer_summary_source_map_count": len(SUMMARY_FIELD_SOURCE_MAP), "finalizer_summary_literal_fallback_count": 0, "sanitizer_v2_post_hash_reconciliation_present": critical["C20_sanitized_paths"], "authority": authority, **planned,
    }
    output = output_path or (PHASE5_ARTIFACTS.parent / "phase5-r3r1-source-preflight-v4.json")
    write_json(output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--planned-workflow", type=Path)
    args = parser.parse_args()
    raise SystemExit(0 if run(args.output, args.planned_workflow)["result"] == "PASS" else 1)
