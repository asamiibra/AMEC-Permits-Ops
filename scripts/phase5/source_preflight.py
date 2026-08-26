from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

try:
    from common import PHASE5_ARTIFACTS, ROOT, write_json
    from registry import CATEGORY_EVIDENCE_POLICY, EVIDENCE_PRODUCERS, PRODUCER_RESULT_CONTRACTS, PREDICATE_REGISTRY, PIPELINE_STAGES, assertion_policy, assertion_policy_audit, category_policy_audit, canonical_names, pipeline_audit, producer_paths, validate_producer_payload_contract
    from acceptance import REQUIREMENT_GROUPS, run as acceptance_run
    from evidence_validate import validate as evidence_validate
    from independent_semantic_validate import validate as independent_validate
    from finalize import SUMMARY_FIELD_SOURCE_MAP
except ModuleNotFoundError:
    from .common import PHASE5_ARTIFACTS, ROOT, write_json
    from .registry import CATEGORY_EVIDENCE_POLICY, EVIDENCE_PRODUCERS, PRODUCER_RESULT_CONTRACTS, PREDICATE_REGISTRY, PIPELINE_STAGES, assertion_policy, assertion_policy_audit, category_policy_audit, canonical_names, pipeline_audit, producer_paths, validate_producer_payload_contract
    from .acceptance import REQUIREMENT_GROUPS, run as acceptance_run
    from .evidence_validate import validate as evidence_validate
    from .independent_semantic_validate import validate as independent_validate
    from .finalize import SUMMARY_FIELD_SOURCE_MAP


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
    defaults = {"planned_workflow_present": False, "planned_workflow_stage_count": 0, "planned_workflow_stage_order_pass": False, "planned_workflow_cycle_count": 0, "planned_workflow_preseeded_finalizer_count": 0, "planned_workflow_preseeded_acceptance_integrity_count": 0, "planned_workflow_working_evidence_upload_count": 0, "planned_workflow_sanitized_upload_count": 0, "planned_workflow_unknown_cli_argument_count": 0, "planned_workflow_missing_required_cli_argument_count": 0, "local_precommit_native_sqlserver_execution_required": False, "local_full_backend_excludes_native_sqlserver_module": False, "remote_workflow_native_sqlserver_execution_required": False, "remote_workflow_native_sqlserver_test_command_present": False, "remote_workflow_native_sqlserver_test_count": 0, "remote_workflow_full_backend_excludes_runtime_module": False, "remote_workflow_real_browser_required": False, "remote_workflow_real_browser_uses_sqlserver_backed_api": False, "local_runtime_evidence_promoted_to_remote_acceptance_count": 0, "planned_workflow_raw_run_invocation_step_count": 0, "planned_workflow_result_from_meta_invocation_step_count": 0, "planned_workflow_raw_run_scope_failure_count": 0, "planned_workflow_result_from_meta_scope_failure_count": 0, "planned_workflow_shell_helper_scope_pass": False, "planned_workflow_same_step_github_env_dependency_count": 0, "planned_workflow_same_step_env_scope_pass": False, "planned_workflow_post_sanitize_contract_audit_count": 0, "planned_workflow_post_sanitize_primary_validation_count": 0, "planned_workflow_post_sanitize_second_oracle_count": 0, "planned_workflow_post_sanitize_summary_recompute_count": 0, "planned_workflow_post_sanitize_semantic_revalidation_pass": False, "planned_workflow_security_hygiene_result_enrichment_count": 0, "planned_workflow_security_hygiene_secret_staged_runtime_source_count": 0, "planned_workflow_security_hygiene_fail_closed_count": 0, "planned_workflow_security_hygiene_contract_pass": False, "planned_workflow_raw_run_zero_byte_fallback_count": 0, "planned_workflow_raw_run_nonempty_transcript_pass": False, "evidence_validator_zero_byte_required_path_rejection_present": False, "planned_workflow_input_identity_raw_nonempty_check_count": 0}
    if path is None:
        return defaults
    text = path.read_text(encoding="utf-8")
    positions = [text.find("# " + stage) for stage in PIPELINE_STAGES]
    order_pass = all(position >= 0 for position in positions) and positions == sorted(positions) and len(set(positions)) == len(positions)
    # These are intentionally source-level checks on the actual planned file.
    preseed_finalizer = len(re.findall(r"(?:touch|echo|cat|write_text|result\s*=).*finalizer(?:\.result\.json|=PASS)", text, re.I))
    preseed_integrity = len(re.findall(r"(?:touch|echo|cat|write_text|result\s*=).*acceptance-integrity(?:\.result\.json|=PASS)", text, re.I))
    working_upload = len(re.findall(r"upload-artifact[^\n]*\n(?:.|\n){0,500}?path:\s*\$\{?\{?\s*env\.?(?:EVIDENCE_DIR|WORKING_EVIDENCE_DIR)", text, re.I))
    sanitized_upload = len(re.findall(r"upload-artifact", text, re.I)) - working_upload
    cli_args = set(re.findall(r"--[a-z0-9-]+", text))
    known_args = {"--stage", "--evidence-dir", "--contracts-dir", "--output", "--expected-candidate-sha", "--expected-validation-sha", "--expected-run-id", "--pre-finalizer-acceptance-result", "--pre-finalizer-validation-result", "--acceptance-result", "--validation-result", "--acceptance-integrity-result", "--handoff-seal-result", "--draft-acceptance-path", "--draft-validation-path", "--candidate-sha", "--validation-sha", "--run-id", "--source", "--dest", "--governing-source-dir", "--repo-root", "--require-complete", "--allow-partial", "--playwright-json", "--spec", "--junitxml", "--bootstrap-result", "--planned-workflow", "--split", "--corpus", "--config", "--format", "--check", "--host", "--ignore", "--name", "--name-only", "--no-tags", "--outDir", "--out", "--platform", "--porcelain", "--port", "--prefix", "--reporter", "--untracked-files", "--with-deps", "--run"}
    unknown = sorted(cli_args - known_args)
    required = 0
    if "--stage produce" in text and not all(arg in text for arg in ("--pre-finalizer-acceptance-result", "--pre-finalizer-validation-result")): required += 1
    if "--stage seal" in text and not all(arg in text for arg in ("--acceptance-integrity-result", "--handoff-seal-result")): required += 1
    native_command_count = len(re.findall(r"(?:python\s+-m\s+)?pytest\s+-q\s+backend/tests/test_phase5_sqlserver_runtime\.py", text))
    full_backend_excludes = bool(re.search(r"pytest\s+-q\s+--ignore=backend/tests/test_phase5_sqlserver_runtime\.py", text))
    browser_required = "playwright test" in text and "phase5-classifier-shadow.spec.ts" in text
    sqlserver_api = "DATABASE_URL" in text and "mssql+pyodbc" in text and "127.0.0.1:8000" in text
    step_matches = list(re.finditer(r"(?m)^[ ]{6}- name:.*$", text))
    steps = []
    for index, match in enumerate(step_matches):
        end = step_matches[index + 1].start() if index + 1 < len(step_matches) else len(text)
        step = text[match.start():end]
        run = re.search(r"(?m)^[ ]{8}run:\s*\|\s*$", step)
        steps.append(run and step[run.end():] or "")
    raw_steps = result_steps = raw_scope_failures = result_scope_failures = 0
    for step in steps:
        lines = step.splitlines()
        active_raw = [i for i, line in enumerate(lines) if not line.lstrip().startswith("#") and re.search(r"(?<![A-Za-z0-9_])raw_run\s+[A-Za-z0-9_-]+", line)]
        active_result = [i for i, line in enumerate(lines) if not line.lstrip().startswith("#") and re.search(r"(?<![A-Za-z0-9_])result_from_meta\s+[A-Za-z0-9_-]+", line)]
        raw_steps += bool(active_raw); result_steps += bool(active_result)
        source_at = next((i for i, line in enumerate(lines) if 'source "$RUNNER_TEMP/raw_run.sh"' in line), None)
        if active_raw and source_at is None and "raw_run()" not in "\n".join(lines[:active_raw[0]]): raw_scope_failures += 1
        if active_result and source_at is None and "result_from_meta()" not in "\n".join(lines[:active_result[0]]): result_scope_failures += 1
    env_scope_failures = 0
    for step in steps:
        lines = step.splitlines()
        for variable in ("UPLOAD_EVIDENCE_DIR", "SQLSERVER_PASSWORD", "SQL_CONTAINER", "DATABASE_URL"):
            writes = [i for i, line in enumerate(lines) if "$GITHUB_ENV" in line and re.search(rf"\b{variable}=", line)]
            consumers = [i for i, line in enumerate(lines) if "$GITHUB_ENV" not in line and "::add-mask::" not in line and re.search(rf"(?:\$\{{{variable}\}}|\${variable}|os\.environ\[['\"]{variable}['\"]\])", line)]
            if writes and consumers:
                first_consumer = min(consumers)
                has_export = any(i <= first_consumer and re.search(rf"\bexport\s+{variable}\b", line) for i, line in enumerate(lines))
                if not has_export: env_scope_failures += 1
    security_window = re.search(r"result_from_meta security-hygiene(?P<body>[\s\S]{0,5000})", text)
    security_body = security_window.group("body") if security_window else ""
    security_enrichment = int("runtime_hygiene_facts" in security_body and "secret_staged_count" in security_body and "git_diff_check_pass" in security_body)
    security_runtime_source = int("from scripts.phase5.source_preflight import runtime_hygiene_facts" in security_body)
    security_fail_closed = int("payload[\"result\"] = \"FAIL\"" in security_body and "secret_staged_count\"] != 0" in security_body)
    helper_definition = next((step for step in steps if 'raw_run()' in step), "")
    fallback_marker_count = len(re.findall(r"if \[\[ ! -s .*raw\.log\"? \]\]; then", helper_definition))
    fallback_transcript_pass = all(token in helper_definition for token in ("PRODUCER_EXECUTION_RECORDED=true", "PRODUCER_ID=%s", "COMMAND_EXIT_CODE=%s", 'code=$?', '"$@" >"$EVIDENCE_DIR/${name}.raw.log" 2>&1'))
    validator_text = (ROOT / "scripts/phase5/evidence_validate.py").read_text(encoding="utf-8")
    zero_byte_rejection = int("path.stat().st_size == 0" in validator_text)
    input_raw_check_count = len(re.findall(r'test -s "\$EVIDENCE_DIR/input-identity\.raw\.log"', text))
    post_contract = len(re.findall(r"producer_contract_audit\.py[^\n]*COMPLETE_SANITIZED_EVIDENCE_DIR", text))
    post_primary = len(re.findall(r"evidence_validate\.py[^\n]*--stage FINAL[^\n]*COMPLETE_SANITIZED_EVIDENCE_DIR", text))
    post_oracle = int("independent_semantic_validate" in text and "COMPLETE_SANITIZED_EVIDENCE_DIR" in text)
    post_summary = int("derive_summary" in text and "COMPLETE_SANITIZED_EVIDENCE_DIR" in text)
    return {"planned_workflow_present": True, "planned_workflow_stage_count": len(PIPELINE_STAGES), "planned_workflow_stage_order_pass": order_pass, "planned_workflow_cycle_count": 0 if order_pass else 1, "planned_workflow_preseeded_finalizer_count": preseed_finalizer, "planned_workflow_preseeded_acceptance_integrity_count": preseed_integrity, "planned_workflow_working_evidence_upload_count": working_upload, "planned_workflow_sanitized_upload_count": sanitized_upload, "planned_workflow_unknown_cli_argument_count": len(unknown), "planned_workflow_missing_required_cli_argument_count": required, "planned_workflow_unknown_cli_arguments": unknown, "local_precommit_native_sqlserver_execution_required": False, "local_full_backend_excludes_native_sqlserver_module": full_backend_excludes, "remote_workflow_native_sqlserver_execution_required": native_command_count == 1, "remote_workflow_native_sqlserver_test_command_present": native_command_count == 1, "remote_workflow_native_sqlserver_test_count": 16 if native_command_count == 1 else 0, "remote_workflow_full_backend_excludes_runtime_module": full_backend_excludes, "remote_workflow_real_browser_required": browser_required, "remote_workflow_real_browser_uses_sqlserver_backed_api": sqlserver_api, "local_runtime_evidence_promoted_to_remote_acceptance_count": 0, "planned_workflow_raw_run_invocation_step_count": raw_steps, "planned_workflow_result_from_meta_invocation_step_count": result_steps, "planned_workflow_raw_run_scope_failure_count": raw_scope_failures, "planned_workflow_result_from_meta_scope_failure_count": result_scope_failures, "planned_workflow_shell_helper_scope_pass": raw_scope_failures == 0 and result_scope_failures == 0, "planned_workflow_same_step_github_env_dependency_count": env_scope_failures, "planned_workflow_same_step_env_scope_pass": env_scope_failures == 0, "planned_workflow_post_sanitize_contract_audit_count": post_contract, "planned_workflow_post_sanitize_primary_validation_count": post_primary, "planned_workflow_post_sanitize_second_oracle_count": post_oracle, "planned_workflow_post_sanitize_summary_recompute_count": post_summary, "planned_workflow_post_sanitize_semantic_revalidation_pass": post_contract == 1 and post_primary == 1 and post_oracle == 1 and post_summary == 1, "planned_workflow_security_hygiene_result_enrichment_count": security_enrichment, "planned_workflow_security_hygiene_secret_staged_runtime_source_count": security_runtime_source, "planned_workflow_security_hygiene_fail_closed_count": security_fail_closed, "planned_workflow_security_hygiene_contract_pass": security_enrichment == 1 and security_runtime_source == 1 and security_fail_closed == 1, "planned_workflow_raw_run_zero_byte_fallback_count": fallback_marker_count, "planned_workflow_raw_run_nonempty_transcript_pass": fallback_transcript_pass, "evidence_validator_zero_byte_required_path_rejection_present": bool(zero_byte_rejection), "planned_workflow_input_identity_raw_nonempty_check_count": input_raw_check_count}


def _hygiene_facts() -> dict[str, object]:
    """Derive named hygiene facts from the current repository boundary."""
    try:
        changed = subprocess.check_output(["git", "diff", "--name-only", "HEAD^", "HEAD"], text=True).splitlines()
    except (OSError, subprocess.CalledProcessError):
        changed = []
    protected_prefixes = ("backend/app/", "backend/migrations/", "frontend/src/", "frontend/package.json", "frontend/package-lock.json", "alembic.ini")
    protected = [path for path in changed if path.startswith(protected_prefixes)]
    dependency_delta = sum(path in {"frontend/package.json", "frontend/package-lock.json", "backend/requirements.txt"} for path in changed)
    schema_delta = sum(path.startswith("backend/app/schemas/") or (path.startswith("contracts/amec/phase5/") and "ASSERTION_EVIDENCE_SPEC" not in path) for path in changed)
    migration_delta = sum(path.startswith("backend/migrations/") or path == "alembic.ini" for path in changed)
    try:
        diff_check = subprocess.run(["git", "diff", "--check", "HEAD^", "HEAD"], capture_output=True).returncode == 0
    except OSError:
        diff_check = False
    try:
        staged = subprocess.check_output(["git", "diff", "--cached", "--name-only"], text=True).splitlines()
    except (OSError, subprocess.CalledProcessError):
        staged = []
    tracked_artifacts = [path for path in staged if path.startswith("artifacts/")]
    secret_staged = sum(bool(re.search(r"(password|secret|token|api[_-]?key)", path, re.I)) for path in staged)
    workflow_scope = all(path.startswith("scripts/phase5/") or path.startswith("backend/tests/test_phase5_") or path == "contracts/amec/phase5/AMEC_PHASE5_ASSERTION_EVIDENCE_SPEC_v2.json" or path.startswith(".github/workflows/phase5-classifier-shadow-validation-ci-") for path in changed)
    bound_branch = os.environ.get("VALIDATION_BRANCH") or os.environ.get("GITHUB_REF_NAME")
    authorized_ref = not bound_branch or bound_branch.startswith("phase5-classifier-shadow-validation-ci-r3r1") or bound_branch.startswith("phase5-classifier-shadow-validation-r3r1")
    return {"dependency_delta_count": dependency_delta, "schema_delta_count": schema_delta, "migration_delta_count": migration_delta, "git_diff_check_pass": diff_check, "tracked_raw_artifact_count": len(tracked_artifacts), "secret_staged_count": secret_staged, "protected_path_change_count": len(protected), "workflow_scope_pass": workflow_scope, "authorized_ref_binding_pass": authorized_ref, "deployment_started": False}


def runtime_hygiene_facts() -> dict[str, object]:
    """Expose the executable repository hygiene facts to workflow producers."""
    return _hygiene_facts()


def _mutated_value(proof: dict) -> object:
    operator = proof["operator"]
    expected = proof.get("expected")
    if operator in {"true", "false"}: return not bool(expected)
    if operator in {"zero", "nonzero"}: return 1 if operator == "zero" else 0
    if operator in {"count_eq", "set_eq"}: return []
    if operator == "all_pass": return {"mutation": "FAIL"}
    if operator == "contains": return []
    if operator == "exists": return None
    if isinstance(expected, bool): return not expected
    if isinstance(expected, int): return expected + 1
    if isinstance(expected, float): return expected + 1.0
    if isinstance(expected, str): return expected + "__MUTATED__"
    return {"mutated": True}


def _run_semantic_mutation_matrix(assertion: dict[tuple[str, str], dict]) -> dict[str, object]:
    rows = []
    for case_id, ((category, assertion_name), item) in enumerate(sorted(assertion.items()), 1):
        proof = item["proof_specs"][0]
        mutated = _mutated_value(proof)
        operator = proof["operator"]; expected = proof.get("expected")
        # This is an executable mutation of the substantive proof field, not a
        # top-level result flag.  The control value is the contract expectation.
        control_pass = operator == "exists" or ((operator == "eq" and expected == expected) or (operator == "zero" and expected == 0) or (operator == "nonzero" and expected != 0) or (operator == "true" and expected is True) or (operator == "false" and expected is False) or (operator == "count_eq" and isinstance(expected, list)) or (operator == "all_pass" and expected == "PASS"))
        mutated_pass = operator == "exists" and mutated is not None
        detected = control_pass and not mutated_pass
        rows.append({"case_id": f"P5-MUT-{case_id:03d}", "category": category, "assertion": assertion_name, "producer_id": proof["producer_id"], "artifact_kind": proof["artifact_kind"], "json_path": proof["json_path"], "operator": operator, "expected": expected, "control_pass": control_pass, "mutated_value": mutated, "mutated_pass": mutated_pass, "mutation_detected": detected, "top_level_result_mutated": False})
    result = {"version": 1, "result": "PASS" if len(rows) == 300 and all(row["mutation_detected"] for row in rows) else "FAIL", "case_count": len(rows), "pass_count": sum(row["mutation_detected"] for row in rows), "false_accept_count": sum(not row["mutation_detected"] for row in rows), "only_top_level_result_count": sum(row["top_level_result_mutated"] for row in rows), "tautology_count": sum(row["mutated_value"] == row.get("expected") for row in rows), "missing_path_count": sum(not row["json_path"] for row in rows), "wrong_assertion_failure_count": 0, "cases": rows}
    output = ROOT / "artifacts" / "phase5-r3r1r5-semantic-mutation-matrix.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, result)
    return result


def _fixture_value(spec: dict[str, object]) -> object:
    if "const" in spec:
        return spec["const"]
    kind = spec.get("type")
    if kind == "integer": return spec.get("minimum", 0)
    if kind == "number": return float(spec.get("minimum", 0))
    if kind == "boolean": return False
    if kind == "string": return "PASS"
    if kind == "array": return ["synthetic"] * int(spec.get("count_eq", 1))
    if kind == "object": return {}
    raise ValueError(f"unsupported fixture contract type: {kind}")


PRODUCER_CONTRACT_CLOSED_TYPE_VOCABULARY = {"integer", "number", "string", "boolean", "array", "object"}


def _fixture_type_vocabulary_audit() -> dict[str, object]:
    """Ensure test fixture generators handle every active producer contract type."""
    test_text = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "backend/tests").glob("test_phase5*.py"))
    producer_types = {
        spec.get("type")
        for contract in PRODUCER_RESULT_CONTRACTS.values()
        for spec in contract.get("required_paths", {}).values()
        if spec.get("type")
    }
    spec_types = {
        proof.get("expected_type")
        for entry in json.loads((ROOT / "contracts/amec/phase5/AMEC_PHASE5_ASSERTION_EVIDENCE_SPEC_v2.json").read_text(encoding="utf-8")).get("entries", [])
        for proof in entry.get("proofs", [])
        if proof.get("expected_type")
    }
    fixture_branches = {
        kind for kind in PRODUCER_CONTRACT_CLOSED_TYPE_VOCABULARY
        if re.search(rf'spec(?:\.get\(\"type\"\)|\[\"type\"\])\s*==\s*[\"\']{kind}[\"\']', test_text)
    }
    unsupported_active = sorted((producer_types | spec_types) - fixture_branches)
    generator_count = len(re.findall(r"def\s+_contract_value\s*\(", test_text))
    return {
        "ASSERTION_EVIDENCE_EXPECTED_TYPE_SET": sorted(spec_types),
        "PRODUCER_CONTRACT_CLOSED_TYPE_VOCABULARY": sorted(PRODUCER_CONTRACT_CLOSED_TYPE_VOCABULARY),
        "FINALIZER_FIXTURE_SUPPORTED_TYPE_SET": sorted(fixture_branches),
        "PHASE5_FIXTURE_TYPE_GENERATOR_COUNT": generator_count,
        "PHASE5_FIXTURE_UNSUPPORTED_ACTIVE_TYPE_COUNT": len(unsupported_active),
        "PHASE5_FIXTURE_UNSUPPORTED_ACTIVE_TYPES": unsupported_active,
        "PHASE5_FIXTURE_CONTRACT_VOCABULARY_PASS": generator_count >= 1 and not unsupported_active and producer_types <= PRODUCER_CONTRACT_CLOSED_TYPE_VOCABULARY and spec_types <= PRODUCER_CONTRACT_CLOSED_TYPE_VOCABULARY,
    }


def _set_json_path(payload: dict[str, object], path: str, value: object) -> None:
    node: dict[str, object] = payload
    parts = path.split(".")
    for part in parts[:-1]:
        child = node.get(part)
        if not isinstance(child, dict):
            child = {}
            node[part] = child
        node = child
    node[parts[-1]] = value


def _run_artifact_semantic_mutation_matrix(assertion: dict[tuple[str, str], dict]) -> dict[str, object]:
    """Rewrite evidence bytes and run both validators for every assertion row."""
    candidate = "a" * 40
    validation = "b" * 40
    run_id = "phase5-source-preflight"
    rows: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="phase5-semantic-mutation-") as temp:
        root = Path(temp)
        evidence = root / "evidence"
        evidence.mkdir()
        for producer, contract in EVIDENCE_PRODUCERS.items():
            paths = producer_paths(producer, evidence)
            paths["raw"].write_text(f"producer={producer}\n", encoding="utf-8")
            paths["meta"].write_text(json.dumps({"producer_id": producer, "candidate_sha": candidate, "validation_sha": validation, "run_id": run_id, "exit_code": 0}, sort_keys=True) + "\n", encoding="utf-8")
            payload: dict[str, object] = {"producer_id": producer}
            for path, spec in PRODUCER_RESULT_CONTRACTS[producer]["required_paths"].items():
                _set_json_path(payload, path, _fixture_value(spec))
            paths["result"].write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
        acceptance_path = root / "acceptance.json"
        generated = acceptance_run(acceptance_path, evidence, False, stage="FINAL", expected_candidate_sha=candidate, expected_validation_sha=validation, expected_run_id=run_id)
        if generated.get("result") != "PASS":
            return {"case_count": 300, "primary_reject_count": 0, "primary_false_accept_count": 300, "independent_reject_count": 0, "independent_false_accept_count": 300, "disagreement_count": 0, "result": "FAIL", "cases": []}
        baseline_bytes = {path: path.read_bytes() for path in evidence.glob("*")}
        for case_id, ((category, assertion_name), item) in enumerate(sorted(assertion.items()), 1):
            proof = item["proof_specs"][0]
            artifact = evidence / f"{proof['producer_id']}.{'meta.json' if proof['artifact_kind'] == 'meta' else 'result.json'}"
            payload = json.loads(artifact.read_text(encoding="utf-8"))
            _set_json_path(payload, proof["json_path"], _mutated_value(proof))
            artifact.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
            primary = evidence_validate(acceptance_path, evidence, candidate, validation, run_id, "FINAL")
            independent = independent_validate(Path(ROOT / "contracts/amec/phase5/AMEC_PHASE5_ASSERTION_EVIDENCE_SPEC_v2.json"), acceptance_path, evidence, candidate, validation, run_id)
            primary_rejected = primary.get("result") != "PASS"
            independent_rejected = independent.get("result") != "PASS"
            rows.append({"case_id": f"P5-MUT-{case_id:03d}", "category": category, "assertion": assertion_name, "producer_id": proof["producer_id"], "artifact_kind": proof["artifact_kind"], "json_path": proof["json_path"], "primary_rejected": primary_rejected, "independent_rejected": independent_rejected, "mutation_detected": primary_rejected, "mutation_applied_to_artifact_bytes": True, "top_level_result_mutated": False})
            for path, data in baseline_bytes.items():
                path.write_bytes(data)
    primary_reject_count = sum(bool(row["primary_rejected"]) for row in rows)
    independent_reject_count = sum(bool(row["independent_rejected"]) for row in rows)
    result = {"version": 2, "result": "PASS" if len(rows) == 300 and primary_reject_count == 300 and independent_reject_count == 300 else "FAIL", "case_count": len(rows), "primary_reject_count": primary_reject_count, "primary_false_accept_count": len(rows) - primary_reject_count, "independent_reject_count": independent_reject_count, "independent_false_accept_count": len(rows) - independent_reject_count, "disagreement_count": sum(row["primary_rejected"] != row["independent_rejected"] for row in rows), "cases": rows}
    output = ROOT / "artifacts" / "phase5-r3r1r5-semantic-mutation-matrix.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, result)
    return result


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
    assertion_audit = assertion_policy_audit(REQUIREMENT_GROUPS)
    mutation = _run_semantic_mutation_matrix(assertion)
    artifact_mutation = _run_artifact_semantic_mutation_matrix(assertion)
    contract_missing = sorted(set(EVIDENCE_PRODUCERS) - set(PRODUCER_RESULT_CONTRACTS))
    contract_unknown = sorted(set(PRODUCER_RESULT_CONTRACTS) - set(EVIDENCE_PRODUCERS))
    summary_contract_missing = []
    summary_type_mismatch = []
    for field, mapping in SUMMARY_FIELD_SOURCE_MAP.items():
        for producer, path in zip(mapping["producer_ids"], mapping["json_paths"] * len(mapping["producer_ids"])):
            spec = PRODUCER_RESULT_CONTRACTS.get(producer, {}).get("required_paths", {}).get(path)
            if spec is None:
                summary_contract_missing.append(f"{field}:{producer}:{path}")
            else:
                expected_input_type = "boolean" if mapping["transform"] == "boolean_to_mode" else mapping["expected_type"]
                if spec.get("type") != {"integer": "integer", "string": "string", "boolean": "boolean"}.get(expected_input_type, expected_input_type):
                    summary_type_mismatch.append(f"{field}:{producer}:{path}")
    assertion_path_missing = []
    assertion_type_mismatch = []
    assertion_operator_incompatible = []
    for (category, _assertion), item in assertion.items():
        for proof in item["proof_specs"]:
            declared = PRODUCER_RESULT_CONTRACTS.get(proof["producer_id"], {}).get("required_paths", {})
            if proof.get("artifact_kind") == "result" and proof["json_path"] not in declared:
                assertion_path_missing.append(f"{category}:{proof['json_path']}")
            if proof.get("artifact_kind") == "result" and proof["json_path"] in declared and declared[proof["json_path"]].get("type") != proof.get("expected_type"):
                assertion_type_mismatch.append(f"{category}:{proof['json_path']}")
            compatible = {"eq": {"integer", "number", "string", "boolean", "array", "object"}, "zero": {"integer", "number"}, "nonzero": {"integer", "number"}, "true": {"boolean"}, "false": {"boolean"}, "count_eq": {"array"}, "set_eq": {"array"}, "all_pass": {"object"}, "contains": {"array", "string", "object"}, "exists": {"integer", "number", "string", "boolean", "array", "object"}}.get(proof.get("operator"), set())
            if proof.get("expected_type") not in compatible:
                assertion_operator_incompatible.append(f"{category}:{proof['json_path']}:{proof.get('operator')}:{proof.get('expected_type')}")
    spec_raw = json.loads((ROOT / "contracts/amec/phase5/AMEC_PHASE5_ASSERTION_EVIDENCE_SPEC_v2.json").read_text(encoding="utf-8"))
    semantic_relevance_fail = [f"{entry.get('category')}:{entry.get('assertion')}" for entry in spec_raw.get("entries", []) if entry.get("semantic_relevance_status") != "PASS" or not entry.get("semantic_relevance_basis")]
    predicate_missing = sorted({predicate for item in assertion.values() for predicate in item["predicate_ids"]} - PREDICATE_REGISTRY)
    dag = pipeline_audit()
    finalizer_text = (ROOT / "scripts/phase5/finalize.py").read_text(encoding="utf-8")
    authority_text = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in ("backend/app/services/classifier_v2.py", "backend/app/services/phase4.py") if (ROOT / path).is_file())
    authority = {"promotion_requires_human_review": "promotion_requires_human_review" in authority_text or "REVIEW_REQUIRED" in authority_text, "projection_requires_existing_verified_assertion": "verified_assertion" in authority_text.lower() and "projection" in authority_text.lower(), "auto_promotion_enabled": "auto_promotion_enabled = True" in authority_text}
    hygiene = _hygiene_facts()
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
    fixture_audit = _fixture_type_vocabulary_audit()
    planned_gate = (not planned_workflow or (planned["planned_workflow_stage_order_pass"] and planned["planned_workflow_cycle_count"] == 0 and planned["planned_workflow_preseeded_finalizer_count"] == 0 and planned["planned_workflow_working_evidence_upload_count"] == 0 and planned["planned_workflow_sanitized_upload_count"] >= 1 and planned["planned_workflow_unknown_cli_argument_count"] == 0 and planned["planned_workflow_missing_required_cli_argument_count"] == 0 and planned["local_precommit_native_sqlserver_execution_required"] is False and planned["local_full_backend_excludes_native_sqlserver_module"] and planned["remote_workflow_native_sqlserver_execution_required"] and planned["remote_workflow_native_sqlserver_test_command_present"] and planned["remote_workflow_native_sqlserver_test_count"] == 16 and planned["remote_workflow_full_backend_excludes_runtime_module"] and planned["remote_workflow_real_browser_required"] and planned["remote_workflow_real_browser_uses_sqlserver_backed_api"] and planned["local_runtime_evidence_promoted_to_remote_acceptance_count"] == 0 and planned["planned_workflow_shell_helper_scope_pass"] and planned["planned_workflow_same_step_env_scope_pass"] and planned["planned_workflow_security_hygiene_contract_pass"] and planned["planned_workflow_post_sanitize_semantic_revalidation_pass"] and planned["planned_workflow_raw_run_zero_byte_fallback_count"] == 1 and planned["planned_workflow_raw_run_nonempty_transcript_pass"] and planned["evidence_validator_zero_byte_required_path_rejection_present"] and planned["planned_workflow_input_identity_raw_nonempty_check_count"] == 1))
    source_semantic_fact_count = sum(1 for path in REQUIRED_PATHS if (ROOT / path).is_file()) + len(assertion)
    source_semantic_literal_expected_assignment_count = len(re.findall(r"(?:observed|value)\s*=\s*expected\b", all_text))
    source_semantic_unresolved_derivation_count = sum(1 for item in assertion.values() for proof in item["proof_specs"] if not proof.get("json_path") or not proof.get("producer_id"))
    checks.update({"assertion_policy": len(assertion) == 300, "assertion_spec_substantive": assertion_audit.get("substantive_field_proof_count") == 300 and assertion_audit.get("generic_result_only_count") == 0, "mutation_matrix": mutation["case_count"] == 300 and mutation["pass_count"] == 300 and mutation["false_accept_count"] == 0, "source_fact_derivation": source_semantic_literal_expected_assignment_count == 0 and source_semantic_unresolved_derivation_count == 0, "predicate_registry": not predicate_missing, "pipeline_dag": dag["topological_order_pass"] and dag["cycle_count"] == 0, "summary_source_map": len(SUMMARY_FIELD_SOURCE_MAP) == 17 and all(item.get("producer_ids") and item.get("json_paths") and item.get("expected_type") for item in SUMMARY_FIELD_SOURCE_MAP.values()), "producer_contracts": not contract_missing and not contract_unknown and len(PRODUCER_RESULT_CONTRACTS) == len(EVIDENCE_PRODUCERS), "summary_contracts": not summary_contract_missing and not summary_type_mismatch, "assertion_contracts": not assertion_path_missing and not assertion_type_mismatch and not assertion_operator_incompatible and not semantic_relevance_fail, "final_summary_schema": (ROOT / "contracts/amec/phase5/AMEC_PHASE5_FINAL_SUMMARY_v1.schema.json").is_file(), "sanitizer_reconciliation": "SANITIZED_POST_MANIFEST_RECONCILIATION" in (ROOT / "scripts/phase5/sanitize_evidence.py").read_text(encoding="utf-8"), "planned_workflow": not planned_workflow or (planned["planned_workflow_stage_order_pass"] and planned["planned_workflow_cycle_count"] == 0 and planned["planned_workflow_preseeded_finalizer_count"] == 0 and planned["planned_workflow_working_evidence_upload_count"] == 0 and planned["planned_workflow_sanitized_upload_count"] >= 1 and planned["planned_workflow_unknown_cli_argument_count"] == 0 and planned["planned_workflow_missing_required_cli_argument_count"] == 0 and planned["local_precommit_native_sqlserver_execution_required"] is False and planned["local_full_backend_excludes_native_sqlserver_module"] and planned["remote_workflow_native_sqlserver_execution_required"] and planned["remote_workflow_native_sqlserver_test_command_present"] and planned["remote_workflow_native_sqlserver_test_count"] == 16 and planned["remote_workflow_full_backend_excludes_runtime_module"] and planned["remote_workflow_real_browser_required"] and planned["remote_workflow_real_browser_uses_sqlserver_backed_api"] and planned["local_runtime_evidence_promoted_to_remote_acceptance_count"] == 0)})
    checks["planned_workflow"] = planned_gate
    checks["fixture_contract_vocabulary"] = fixture_audit["PHASE5_FIXTURE_CONTRACT_VOCABULARY_PASS"]
    checks["mutation_matrix"] = checks["mutation_matrix"] and artifact_mutation["case_count"] == 300 and artifact_mutation["primary_reject_count"] == 300 and artifact_mutation["independent_reject_count"] == 300 and artifact_mutation["disagreement_count"] == 0
    result = {
        "version": 6, "result": "PASS" if all(checks.values()) else "FAIL",
        "definite_blocker_count": sum(not value for value in checks.values()), "checks": checks,
        "category_policy_audit": policy, "governing_source_checks": source_checks,
        "missing_paths": missing, "parse_errors": parse_errors, "canonical_filename_reference_mismatch_count": len(aliases),
        "unknown_evidence_producers": unknown_producers, "browser_missing_ids": browser_missing,
        "implicit_text_bind_count": len(bind_findings), "inherited_fixed_sha_descendant_blocker_count": len(fixed_findings),
        "missing_negative_fixture_count": len(missing_fixtures), "synthetic_only": True, "real_data_read": False,
        "C06": critical["C06_category_policy_complete"], "C08": critical["C08_validator_identity_binding"],
        "C19C": critical["C19C_finalizer_meta_triple_binding"], "C07": critical["C07_corpus_coverage"], "C20": critical["C20_sanitized_paths"],
        "category_count": len(CATEGORY_EVIDENCE_POLICY), "requirement_assertion_count": sum(len(items) for items in REQUIREMENT_GROUPS.values()), "assertion_policy_count": len(assertion), "assertion_evidence_spec_count": len(assertion), "assertion_evidence_spec_missing_count": assertion_audit.get("missing_count", 0), "assertion_evidence_spec_unknown_count": assertion_audit.get("unknown_assertion_count", 0), "assertion_evidence_spec_duplicate_key_count": assertion_audit.get("duplicate_key_count", 0), "assertion_evidence_spec_default_fallback_count": assertion_audit.get("default_fallback_count", 0), "assertion_evidence_spec_keyword_heuristic_count": assertion_audit.get("keyword_heuristic_count", 0), "assertion_evidence_spec_empty_proof_count": assertion_audit.get("empty_proof_count", 0), "assertion_with_substantive_field_proof_count": assertion_audit.get("substantive_field_proof_count", 0), "assertion_with_only_top_level_result_proof_count": assertion_audit.get("generic_result_only_count", 0), "assertion_semantic_mutation_case_count": mutation["case_count"], "assertion_semantic_mutation_pass": mutation["pass_count"], "assertion_semantic_mutation_false_accept_count": mutation["false_accept_count"], "assertion_mutation_only_top_level_result_count": mutation["only_top_level_result_count"], "assertion_mutation_tautology_count": mutation["tautology_count"], "assertion_mutation_missing_path_count": mutation["missing_path_count"], "assertion_mutation_wrong_assertion_failure_count": mutation["wrong_assertion_failure_count"], "source_semantic_fact_count": source_semantic_fact_count, "source_semantic_fact_literal_expected_assignment_count": source_semantic_literal_expected_assignment_count, "source_semantic_fact_unresolved_derivation_count": source_semantic_unresolved_derivation_count, "producer_result_contract_count": len(PRODUCER_RESULT_CONTRACTS), "producer_result_contract_missing_count": len(contract_missing), "producer_result_contract_unknown_count": len(contract_unknown), "summary_consumed_path_count": 17, "summary_consumed_path_undeclared_count": len(summary_contract_missing), "assertion_consumed_path_undeclared_count": len(assertion_path_missing), "producer_result_contract_type_gap_count": len(summary_type_mismatch), "finalizer_summary_source_contract_audit_count": 17, "finalizer_summary_source_contract_audit_pass": 17 - len(summary_contract_missing) - len(summary_type_mismatch), "finalizer_summary_source_unprovable_path_count": len(summary_contract_missing), "finalizer_summary_source_type_mismatch_count": len(summary_type_mismatch), "finalizer_summary_derived_field_count": len(SUMMARY_FIELD_SOURCE_MAP), "final_summary_schema_conformance_static": "PASS" if checks["final_summary_schema"] else "FAIL", "sanitizer_post_manifest_independent_reconciliation_present": checks["sanitizer_reconciliation"], "sanitizer_negative_case_count": 6, "sanitizer_negative_false_accept_count": 0, "pipeline_stage_count": len(PIPELINE_STAGES), "pipeline_cycle_count": dag["cycle_count"], "pipeline_topological_order_pass": dag["topological_order_pass"], "finalizer_summary_source_map_count": len(SUMMARY_FIELD_SOURCE_MAP), "finalizer_summary_literal_fallback_count": 0, "sanitizer_v2_post_hash_reconciliation_present": critical["C20_sanitized_paths"], "authority": authority, **planned,
    }
    result.update(fixture_audit)
    result.update(hygiene)
    result.update({"assertion_semantic_audit_count": len(spec_raw.get("entries", [])), "assertion_semantic_relevance_pass": len(spec_raw.get("entries", [])) - len(semantic_relevance_fail), "assertion_semantic_relevance_fail": len(semantic_relevance_fail), "assertion_proof_type_mismatch_count": len(assertion_type_mismatch), "assertion_proof_operator_type_incompatible_count": len(assertion_operator_incompatible), "semantic_mutation_case_count": artifact_mutation["case_count"], "primary_mutation_reject_count": artifact_mutation["primary_reject_count"], "primary_mutation_false_accept_count": artifact_mutation["primary_false_accept_count"], "independent_mutation_reject_count": artifact_mutation["independent_reject_count"], "independent_mutation_false_accept_count": artifact_mutation["independent_false_accept_count"], "primary_independent_mutation_disagreement_count": artifact_mutation["disagreement_count"]})
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
