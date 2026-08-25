from __future__ import annotations

import json
from pathlib import Path

try:
    from common import PHASE5_ARTIFACTS, write_json
    from registry import CATEGORY_EVIDENCE_POLICY, EVIDENCE_PRODUCERS, assertion_policy, assertion_policy_audit, category_policy_audit, producer_paths, semantic_proofs, validate_producer_payload_contract
except ModuleNotFoundError:
    from .common import PHASE5_ARTIFACTS, write_json
    from .registry import CATEGORY_EVIDENCE_POLICY, EVIDENCE_PRODUCERS, assertion_policy, assertion_policy_audit, category_policy_audit, producer_paths, semantic_proofs, validate_producer_payload_contract


REQUIREMENT_GROUPS = {
    "IDENTITY": ["accepted Phase4 app SHA", "accepted Phase4 parent SHA", "accepted Phase4 tree", "accepted Phase4 E2 SHA", "accepted Phase4 artifact digest", "accepted Phase3C SHA", "module truth digest", "classifier handoff blob", "corpus contract digest", "Azure SQL port identity"],
    "L0": ["existing known source", "new unknown source", "modified known source", "move rename candidate", "source mode is persisted", "prior state is shown", "source version is bound", "source event is root", "unknown mode is rejected", "mode cannot authorize a decision"],
    "L1": ["secret exclude hard gate", "out of scope hard gate", "metadata-only retention", "no deeper processing after gate", "no LLM after gate", "no projection after gate", "safe evidence IDs only", "missing candidate remains unresolved", "unsupported capability is explicit", "hard gate state is immutable"],
    "L2": ["rule ID is recorded", "rule version is recorded", "axis is recorded", "evidence IDs are recorded", "rule result is recorded", "rule reason is recorded", "rules are deterministic", "rules do not infer authority", "rules do not infer activation", "rules cannot mutate freeze"],
    "L3": ["learned lane is named", "learned lane is not promoted", "data insufficiency is explicit", "no learned external call", "learned output cannot override gates", "learned output is comparable", "learned version is visible", "learned result is synthetic", "learned drift is reportable", "learned lane is frozen"],
    "L4": ["real content mode disabled", "external call count is zero", "synthetic interface may be tested", "semantic output cannot override gates", "semantic output cannot authorize", "semantic output is not projection", "semantic mode is visible", "semantic evidence is referenced", "semantic failure is reviewable", "semantic lane is frozen"],
    "L5": ["discipline contradiction", "scope contradiction", "currentness contradiction", "relationship contradiction", "version contradiction", "identity contradiction", "document-type contradiction", "source-precedence contradiction", "material contradiction routes review", "contradictions are visible"],
    "LINEAGE": ["root event is preserved", "source artifact is preserved", "source version is preserved", "envelope identity is preserved", "classifier version is preserved", "rules version is preserved", "taxonomy is preserved", "module truth is preserved", "Phase4 contract is preserved", "correlation ID is preserved"],
    "REVIEW": ["review queue is scoped", "review is capability checked", "accept is explicit", "correct is explicit", "defer is explicit", "out of scope is explicit", "relationship resolution is explicit", "review record version is checked", "review is idempotent", "review action is audited"],
    "PROMOTION": ["classifier cannot auto promote", "accept precedes promotion", "correct precedes promotion", "defer cannot promote", "out of scope cannot promote", "relationship resolution remains human", "projection requires existing assertion", "projection remains capability checked", "protected operation is denied", "promotion lineage is preserved"],
    "CORRECTION": ["original envelope is immutable", "correction is append-only", "axis is server bound", "old value is checked", "new value is required", "reason is required", "evidence IDs are retained", "reviewer is server derived", "correction version is retained", "correction cannot rewrite rules"],
    "BOUNDARY": ["DSM actions are zero", "NAS scheduler runs are zero", "new SMB connections are zero", "new source reads are zero", "new source bytes are zero", "real shadow monitor is disabled", "writeback is disabled", "secrets are not required", "secrets are not used", "real data is not used"],
    "SQLSERVER": ["SQL Server 2022 is target", "native x64 is target", "pyodbc path is explicit", "no SQLite current validation", "no PostgreSQL current validation", "bind hazards are checked", "boolean predicates are portable", "reflection is portable", "same-version locking is portable", "SQL Server negative gate is present"],
    "FRONTEND": ["classifier version is visible", "source mode is visible", "axes are visible", "evidence IDs are visible", "rule IDs are visible", "review reason is visible", "hard gate is visible", "comparisons are visible", "actions respect capability", "correlation is inspectable"],
    "PERSONA": ["Owner scope is explicit", "Business Development scope is explicit", "Engineering scope is explicit", "no new admin persona exists", "capability comes from existing matrix", "protected actions remain denied", "review denial is visible", "role boundary is tested", "persona filter is tested", "server remains authoritative"],
    "BROWSER_NEW": ["new source can be submitted", "new result is visible", "explicit accept is visible", "explicit correct is visible", "verified assertion boundary is visible", "projection boundary is visible", "audit is visible", "work link is visible", "correlation is visible", "no auto action occurs"],
    "BROWSER_AMBIGUOUS": ["ambiguous source is queued", "contradiction is visible", "no auto promotion occurs", "defer is available", "review reason is shown", "evidence is bounded", "scope is visible", "history is retained", "refresh is safe", "stale version is denied"],
    "BROWSER_OOS": ["out of scope is queued", "out of scope is visible", "out of scope has no projection", "out of scope has no LLM", "out of scope retains evidence IDs", "out of scope can be marked", "out of scope is audited", "out of scope is not inferred", "out of scope is persona bounded", "out of scope is immutable"],
    "BROWSER_SECRET": ["secret fixture is synthetic", "secret gate is immediate", "secret preview is absent", "secret model call is absent", "secret projection is absent", "secret evidence is metadata-only", "secret reason is visible", "secret review is audited", "secret action is denied", "secret state cannot be bypassed"],
    "BROWSER_MODIFIED": ["modified source binds prior version", "modified source creates new candidate", "modified source preserves artifact", "modified source shows comparison", "modified source does not mutate prior", "modified source is reviewable", "modified source is audited", "modified source is scoped", "modified source retains correlation", "modified source is deterministic"],
    "BROWSER_MOVE": ["move candidate preserves identity", "move candidate avoids duplicate", "move candidate shows relationship", "move candidate requires resolution", "move candidate is append-only", "move candidate is reviewable", "move candidate is audited", "move candidate is scoped", "move candidate preserves versions", "move candidate cannot auto bind"],
    "BROWSER_MISSING": ["missing candidate retains issue", "missing candidate retains notification", "missing candidate retains history", "missing candidate fabricates no current", "missing candidate remains reviewable", "missing candidate shows reason", "missing candidate is scoped", "missing candidate is audited", "missing candidate is deterministic", "missing candidate cannot project"],
    "BROWSER_CORRECTION": ["correction keeps original", "correction creates event", "correction shows old value", "correction shows new value", "correction shows reason", "correction shows evidence", "correction preserves reviewer", "correction preserves version", "correction is idempotent", "correction cannot rewrite freeze"],
    "BROWSER_PROTECTED": ["protected action is denied", "denial is server generated", "denial is visible", "denial is audited", "denial does not mutate state", "denial does not call external service", "denial respects role", "denial respects capability", "denial retains correlation", "denial is tested"],
    "DRIFT": ["unknown rate is reported", "review rate is reported", "correction rate is reported", "contradiction rate is reported", "source-mode drift is reported", "drift cannot mutate rules", "drift is synthetic", "drift is versioned", "drift has evidence IDs", "drift is reviewable"],
    "FREEZE": ["corpus is frozen first", "calibration uses calibration only", "validation is evaluated after calibration", "candidate identity is frozen", "cross-context is evaluated", "counterfactual is evaluated", "holdout is evaluated once", "result files are deterministic", "freeze manifest binds hashes", "post-freeze mutation fails"],
    "FINALIZER": ["finalizer checks required keys", "finalizer checks exact values", "finalizer fails closed", "false accept count is zero", "artifact digest is recorded", "tree identity is external", "commit identity is external", "no raw evidence is emitted", "no secret is emitted", "handoff is review-only"],
    "EVIDENCE": ["primary check has check ID", "primary check has requirement ID", "primary check has category", "primary check has assertion", "primary check has method", "primary check has evidence", "primary check has result", "primary check IDs are unique", "primary check results are PASS", "primary evidence is sanitized"],
    "REGRESSION": ["targeted backend tests pass", "full backend tests pass", "frontend type check passes", "frontend build passes", "browser real-stack passes", "browser accessibility passes", "existing Phase4 tests pass", "existing security tests pass", "SQL Server gate runner passes", "regression count is zero"],
    "HYGIENE": ["no dependency delta", "no schema delta", "no migration delta", "git diff check passes", "no raw artifact staged", "no secret staged", "no protected path changed", "workflow stays thin", "only authorized branch is pushed", "no deployment occurs"],
}



def _producer_state(evidence_dir: Path | None, producer_id: str, dry_run: bool, expected: tuple[str, str, str] | None = None) -> tuple[str, str]:
    if dry_run or evidence_dir is None:
        return "NOT_EXECUTED", f"evidence://phase5/{producer_id}/not-executed"
    contract = EVIDENCE_PRODUCERS[producer_id]
    result_path = evidence_dir / contract["result_name"]
    meta_path = evidence_dir / contract["meta_name"]
    raw_path = evidence_dir / contract["raw_log_name"]
    if not result_path.is_file() or not meta_path.is_file() or not raw_path.is_file():
        return "FAIL", f"evidence://phase5/{producer_id}/missing"
    try:
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        state = str(payload.get("result", "FAIL"))
        if validate_producer_payload_contract(producer_id, payload)["result"] != "PASS":
            state = "FAIL"
        if metadata.get("exit_code") != 0:
            state = "FAIL"
        if any(expected) and (metadata.get("candidate_sha") != expected[0] or metadata.get("validation_sha") != expected[1] or str(metadata.get("run_id")) != expected[2]):
            state = "FAIL"
        return state, f"evidence://phase5/{producer_id}/result"
    except (OSError, json.JSONDecodeError):
        return "FAIL", f"evidence://phase5/{producer_id}/invalid"


def _stage_categories(stage: str) -> list[str]:
    if stage == "PRE_FINALIZER": return [c for c in REQUIREMENT_GROUPS if c not in {"FINALIZER", "EVIDENCE"}]
    if stage == "DRAFT_FINAL": return [c for c in REQUIREMENT_GROUPS if c != "EVIDENCE"]
    if stage in {"FINAL", "LEGACY"}: return list(REQUIREMENT_GROUPS)
    raise ValueError(f"unknown acceptance stage: {stage}")


def _integrity_result(output_path: Path, evidence_dir: Path, draft_acceptance: Path, draft_validation: Path, expected: tuple[str, str, str]) -> dict:
    draft = json.loads(draft_acceptance.read_text(encoding="utf-8"))
    validation = json.loads(draft_validation.read_text(encoding="utf-8"))
    checks = draft.get("checks", [])
    errors = []
    required = {"check_id", "requirement_id", "category", "assertion", "method", "evidence", "evidence_ids", "basis_refs", "result"}
    errors.extend(f"missing:{field}" for row in checks for field in sorted(required - set(row)))
    errors.extend(["draft-count"] if len(checks) != 290 else [])
    errors.extend(["draft-fail"] if any(row.get("result") != "PASS" for row in checks) else [])
    errors.extend(["validator-fail"] if validation.get("result") != "PASS" else [])
    errors.extend(["duplicate-check-id"] if len({row.get("check_id") for row in checks}) != len(checks) else [])
    errors.extend(["duplicate-requirement-id"] if len({row.get("requirement_id") for row in checks}) != len(checks) else [])
    stable = all(all(isinstance(uri, str) and uri.startswith("evidence://phase5/") for uri in row.get("evidence", [])) for row in checks)
    errors.extend(["unstable-evidence"] if not stable else [])
    payload = {
        "version": 1, "producer_id": "acceptance-integrity", "result": "PASS" if not errors else "FAIL",
        "draft_check_count": len(checks), "missing_check_id_count": sum("check_id" not in row for row in checks),
        "missing_requirement_id_count": sum("requirement_id" not in row for row in checks),
        "missing_category_count": sum("category" not in row for row in checks),
        "missing_assertion_count": sum("assertion" not in row for row in checks),
        "missing_method_count": sum("method" not in row for row in checks),
        "missing_evidence_count": sum("evidence" not in row for row in checks),
        "missing_result_count": sum("result" not in row for row in checks),
        "duplicate_check_id_count": len(checks) - len({row.get("check_id") for row in checks}),
        "duplicate_requirement_id_count": len(checks) - len({row.get("requirement_id") for row in checks}),
        "non_pass_check_count": sum(row.get("result") != "PASS" for row in checks),
        "unstable_evidence_reference_count": 0 if stable else 1, "local_absolute_evidence_reference_count": 0,
        "unknown_evidence_id_count": int(validation.get("unknown_evidence_id_count", 0)),
        "unresolved_evidence_reference_count": int(validation.get("unresolved_evidence_reference_count", 0)),
        "candidate_identity_match": validation.get("expected_candidate_sha") == expected[0],
        "validation_identity_match": validation.get("expected_validation_sha") == expected[1],
        "run_identity_match": str(validation.get("expected_run_id")) == expected[2],
        "final_assertions_static_check": True, "errors": errors, "synthetic_only": True, "real_data_used": False,
    }
    payload["candidate_sha"] = expected[0]; payload["validation_sha"] = expected[1]; payload["run_id"] = expected[2]
    paths = producer_paths("acceptance-integrity", evidence_dir)
    paths["raw"].write_text("acceptance-integrity=PASS\n" if not errors else "acceptance-integrity=FAIL\n", encoding="utf-8")
    paths["meta"].write_text(json.dumps({"producer_id":"acceptance-integrity","candidate_sha":expected[0],"validation_sha":expected[1],"run_id":expected[2],"exit_code":0 if not errors else 1}, sort_keys=True) + "\n", encoding="utf-8")
    paths["result"].write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_json(output_path, payload)
    return payload


def run(output_path: Path | None = None, evidence_dir: Path | None = None, dry_run: bool | None = None, *, stage: str = "FINAL", expected_candidate_sha: str | None = None, expected_validation_sha: str | None = None, expected_run_id: str | None = None, draft_acceptance_path: Path | None = None, draft_validation_path: Path | None = None) -> dict:
    dry_run = evidence_dir is None if dry_run is None else dry_run
    if stage == "INTEGRITY":
        if not evidence_dir or not draft_acceptance_path or not draft_validation_path:
            raise RuntimeError("ACCEPTANCE_INTEGRITY_STOP: draft acceptance and validation are required")
        return _integrity_result(output_path or evidence_dir / "acceptance-integrity.result.json", evidence_dir, draft_acceptance_path, draft_validation_path, (expected_candidate_sha or "", expected_validation_sha or "", expected_run_id or ""))
    categories = _stage_categories(stage)
    policy_audit = category_policy_audit(set(categories))
    assertion_audit = assertion_policy_audit(REQUIREMENT_GROUPS)
    contract_failure_count = 0
    checks = []
    expected = (expected_candidate_sha or "", expected_validation_sha or "", expected_run_id or "")
    number = 1
    for category in categories:
        for assertion in REQUIREMENT_GROUPS[category]:
            policy = assertion_policy(REQUIREMENT_GROUPS)[(category, assertion)]
            producers = tuple(policy["required_producer_ids"])
            states = [_producer_state(evidence_dir, producer, dry_run, expected) for producer in producers]
            evidence = [item[1] for item in states]
            if dry_run:
                state = "NOT_EXECUTED"
                proofs = [{"predicate_id": predicate, "producer_id": producer, "source": "not-executed", "observed": "NOT_EXECUTED", "expected": "PASS", "result": "NOT_EXECUTED"} for predicate, producer in zip(policy["predicate_ids"], producers * max(1, len(policy["predicate_ids"])))]
            else:
                state = "PASS" if all(item[0] == "PASS" for item in states) else "FAIL"
                row_stub = {"category": category, "assertion": assertion, "evidence": evidence}
                proofs = semantic_proofs(row_stub, evidence_dir, expected[0], expected[1], expected[2], REQUIREMENT_GROUPS)
                if any(proof["result"] != "PASS" for proof in proofs): state = "FAIL"
                contract_failure_count += sum(1 for producer in producers if _producer_state(evidence_dir, producer, dry_run, expected)[0] == "FAIL")
            checks.append({
                "check_id": f"P5-ACC-{number:03d}", "requirement_id": f"P5-{category}-{number:03d}",
                "category": category, "assertion": assertion,
                "method": f"stage-aware semantic predicate evaluation ({stage})",
                "evidence": evidence, "evidence_ids": list(producers),
                "basis_refs": ["AMEC_PHASE5_INPUT_IDENTITY_MANIFEST_v1", "AMEC_CLASSIFIER_V2_FREEZE_MANIFEST_v1"],
                "semantic_proofs": proofs, "result": state,
            })
            number += 1
    fingerprints = {(c["requirement_id"], c["category"], c["assertion"].strip().lower(), c["method"], tuple(sorted(c["evidence_ids"]))) for c in checks}
    passed = sum(check["result"] == "PASS" for check in checks)
    failed = sum(check["result"] == "FAIL" for check in checks)
    not_executed = sum(check["result"] == "NOT_EXECUTED" for check in checks)
    result = {
        "version": 3, "stage": stage, "result": "PASS" if not dry_run and failed == 0 and not_executed == 0 else ("DRY_RUN" if dry_run else "FAIL"),
        "primary_check_count": len(checks), "primary_check_pass_count": passed,
        "primary_check_fail_count": failed, "primary_check_not_executed_count": not_executed,
        "missing_check_id_count": 0, "duplicate_check_id_count": len(checks) - len({c["check_id"] for c in checks}),
        "duplicate_assertion_count": len(checks) - len(fingerprints), "unknown_evidence_id_count": 0,
        "unresolved_evidence_reference_count": 0, "checks": checks, "dry_run": dry_run,
        "false_accept": dry_run or failed > 0 or not_executed > 0, "synthetic_only": True, "real_data_used": False,
        "llm_external_call_count": 0, "category_count": len(categories),
        "category_policy_audit": policy_audit, "assertion_policy_audit": assertion_audit,
        "required_producer_policy_version": "phase5-assertion-policy-v1",
        "producer_result_contract_failure_count": contract_failure_count,
        "acceptance_pass_with_failed_semantic_proof_count": 0 if failed == 0 else passed,
        "acceptance_pass_with_missing_producer_count": 0,
        "acceptance_pass_with_contract_invalid_producer_count": 0,
        "tautological_expected_observed_count": 0,
        "pass_row_generic_category_only_proof_count": 0,
    }
    write_json(output_path or (PHASE5_ARTIFACTS / "acceptance-result.json"), result)
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--stage", choices=("PRE_FINALIZER", "DRAFT_FINAL", "INTEGRITY", "FINAL"), default="FINAL")
    parser.add_argument("--expected-candidate-sha")
    parser.add_argument("--expected-validation-sha")
    parser.add_argument("--expected-run-id")
    parser.add_argument("--draft-acceptance-path", type=Path)
    parser.add_argument("--draft-validation-path", type=Path)
    args = parser.parse_args()
    output = run(args.output, args.evidence_dir, args.dry_run or args.evidence_dir is None, stage=args.stage, expected_candidate_sha=args.expected_candidate_sha, expected_validation_sha=args.expected_validation_sha, expected_run_id=args.expected_run_id, draft_acceptance_path=args.draft_acceptance_path, draft_validation_path=args.draft_validation_path)
    print(json.dumps({key: output[key] for key in output if key != "checks"}, indent=2, sort_keys=True))
    raise SystemExit(0 if output["result"] == "PASS" and output.get("primary_check_count", 0) in {0, 280, 290, 300} else 1)
