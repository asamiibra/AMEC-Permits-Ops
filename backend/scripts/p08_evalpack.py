"""Run and persist the P08 critical EvalPack.

Each critical case is bound to an executable repository test.  The runner
executes every binding independently so a missing, skipped, or errored case
cannot be hidden by an aggregate pytest result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.app.services.proposal_intelligence import (  # noqa: E402
    P08_CRITICAL_CASES,
    P08_EVAL_PACK_HASH,
    P08_EVAL_PACK_ID,
    P08_EVAL_PACK_VERSION,
)


CASE_TESTS = {
    "cross-project": "backend/tests/test_context_compiler.py::test_cross_project_sources_fail_closed",
    "wrong-persona": "backend/tests/test_ai_d0_d1_architecture_auth_context.py::test_role_value_actor_and_inactive_membership_do_not_authorize",
    "missing-capability": "backend/tests/test_ai_d0_d1_architecture_auth_context.py::test_full_principal_and_exact_membership_are_required",
    "stale-revision": "backend/tests/test_ai_p08_proposal_intelligence.py::test_proposal_analysis_is_module_owned_and_revision_selective",
    "stale-document": "backend/tests/test_context_compiler.py::test_current_document_and_evidence_lineage_are_required",
    "stale-verified-assertion": "backend/tests/test_context_compiler.py::test_verified_assertion_consumption_is_current_lineage_bound_and_read_only",
    "stale-master-content": "backend/tests/test_context_compiler.py::test_master_content_exact_binding_and_ambiguity_fail_closed",
    "stale-policy": "backend/tests/test_context_compiler.py::test_policy_version_is_exact_and_source_order_does_not_allow_arbitrary_queries",
    "source-mismatch": "backend/tests/test_context_compiler.py::test_current_document_and_evidence_lineage_are_required",
    "citation-mismatch": "backend/tests/test_ai_p05_skill_runtime.py::test_unknown_citation_and_real_content_are_rejected",
    "malformed-output": "backend/tests/test_ai_p05_skill_runtime.py::test_gateway_gates_and_strict_output_fail_before_work_product",
    "trust-floor": "backend/tests/test_context_compiler.py::test_candidate_trust_floor_and_target_module_are_enforced",
    "sensitivity": "backend/tests/test_ai_d0_d1_architecture_auth_context.py::test_manifest_rejects_unsafe_currentness_or_sensitivity",
    "protected-action": "backend/tests/test_ai_p07_foundation_control_plane.py::test_review_ledger_uses_authenticated_human_and_is_only_promotion_path",
    "policy-spoof": "backend/tests/test_context_compiler.py::test_caller_cannot_spoof_persona_or_capabilities",
    "skill-spoof": "backend/tests/test_ai_p05_skill_runtime.py::test_registry_exact_identity_and_fail_closed_conflicts",
    "provider-spoof": "backend/tests/test_ai_d3_runtime_binding.py::test_runtime_binding_is_distinct_from_historical_d0_target",
    "prompt-injection": "backend/tests/test_governed_prefill_step4_adversarial.py::test_apply_records_human_audit_without_protected_action_side_effects",
    "provider-failure": "backend/tests/test_ai_p05_skill_runtime.py::test_mutated_same_key_is_conflict_and_failed_retry_requires_new_key",
    "context-race": "backend/tests/test_ai_p07_foundation_control_plane.py::test_finalization_fence_records_context_change_and_preserves_history",
    "stale-review": "backend/tests/test_phase4_corpus_app_integration.py::test_be_p4_rd_013_stale_review_version_is_rejected",
    "duplicate-review": "backend/tests/test_ai_p08_proposal_intelligence.py::test_proposal_review_duplicate_and_conflicting_decision_are_fail_closed",
    "conflicting-review": "backend/tests/test_ai_p08_proposal_intelligence.py::test_proposal_review_duplicate_and_conflicting_decision_are_fail_closed",
    "corrected-candidate": "backend/tests/test_phase4_corpus_app_integration.py::test_be_p4_rd_016_correct_creates_immutable_correction_event",
    "analysis-not-truth": "backend/tests/test_ai_p08_proposal_intelligence.py::test_proposal_analysis_is_module_owned_and_revision_selective",
    "unrelated-dependency-current": "backend/tests/test_ai_p07_foundation_control_plane.py::test_selective_idempotent_invalidation_and_stale_replay_guard",
}


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _run_case(case: str, nodeid: str) -> dict[str, object]:
    env = os.environ.copy()
    env.update({"PYTHONPATH": str(ROOT), "APP_ENV": "TEST", "SYNTHETIC_ONLY": "true", "REAL_DATA_ALLOWED": "false"})
    started = datetime.now(timezone.utc)
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--disable-warnings", "--maxfail=1", nodeid],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    output = proc.stdout[-5000:]
    skipped = bool(re.search(r"\bskipped\b", output, flags=re.IGNORECASE))
    status = "PASS" if proc.returncode == 0 and not skipped else "FAIL"
    return {
        "case": case,
        "nodeid": nodeid,
        "status": status,
        "returncode": proc.returncode,
        "skipped": skipped,
        "started_at": started.isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "output_tail": output,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    missing = [case for case in P08_CRITICAL_CASES if case not in CASE_TESTS]
    extra = sorted(set(CASE_TESTS) - set(P08_CRITICAL_CASES))
    if missing or extra:
        raise SystemExit(f"EvalPack binding mismatch; missing={missing}; extra={extra}")

    results = [_run_case(case, CASE_TESTS[case]) for case in P08_CRITICAL_CASES]
    passed = sum(item["status"] == "PASS" for item in results)
    failed = len(results) - passed
    payload = {
        "schema": "proposalops.p08.evalpack.v1",
        "eval_pack_id": P08_EVAL_PACK_ID,
        "eval_pack_version": P08_EVAL_PACK_VERSION,
        "pack_hash": P08_EVAL_PACK_HASH,
        "critical_cases": list(P08_CRITICAL_CASES),
        "critical_case_count": len(results),
        "executed": len(results),
        "passed": passed,
        "failed": failed,
        "skipped": sum(bool(item["skipped"]) for item in results),
        "critical_pass_rate": (passed / len(results)) if results else 0,
        "execution_status": "PASS" if failed == 0 else "FAIL",
        "source_sha": _git("rev-parse", "HEAD"),
        "source_tree": _git("rev-parse", "HEAD^{tree}"),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("execution_status", "critical_case_count", "executed", "passed", "failed", "skipped", "critical_pass_rate", "source_sha", "source_tree")}))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
