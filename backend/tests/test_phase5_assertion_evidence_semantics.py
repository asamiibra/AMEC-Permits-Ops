from __future__ import annotations

import json
from pathlib import Path

from scripts.phase5.acceptance import REQUIREMENT_GROUPS, _stage_categories
from scripts.phase5.registry import assertion_policy, assertion_policy_audit, category_policy_audit
from scripts.phase5.source_preflight import _run_semantic_mutation_matrix


def test_stage_cardinality_and_category_sets_are_exact():
    policy = assertion_policy(REQUIREMENT_GROUPS)
    expected = {"PRE_FINALIZER": (28, 280), "DRAFT_FINAL": (29, 290), "FINAL": (30, 300)}
    for stage, (category_count, check_count) in expected.items():
        categories = _stage_categories(stage)
        audit = category_policy_audit(set(categories), policy)
        assert len(categories) == category_count
        assert sum(len(REQUIREMENT_GROUPS[category]) for category in categories) == check_count
        assert audit["stage_category_set_match"] is True
        assert audit["category_producer_coverage_missing_count"] == 0
        assert audit["result"] == "PASS"


def test_assertion_requirements_are_row_specific_and_semantically_audited():
    policy = assertion_policy(REQUIREMENT_GROUPS)
    audit = assertion_policy_audit(REQUIREMENT_GROUPS)
    assert audit["count"] == 300
    assert audit["empty_producer_set_count"] == 0
    assert audit["generic_result_only_count"] == 0
    assert all(tuple(item["required_producer_ids"]) == tuple(dict.fromkeys(proof["producer_id"] for proof in item["proof_specs"])) for item in policy.values())
    raw = json.loads(Path("contracts/amec/phase5/AMEC_PHASE5_ASSERTION_EVIDENCE_SPEC_v2.json").read_text(encoding="utf-8"))
    assert raw["semantic_audit"]["assertion_semantic_audit_count"] == 300
    assert raw["semantic_audit"]["assertion_semantic_relevance_pass"] == 300


def test_primary_mutation_matrix_has_300_non_top_level_cases():
    result = _run_semantic_mutation_matrix(assertion_policy(REQUIREMENT_GROUPS))
    assert result["case_count"] == 300
    assert result["false_accept_count"] == 0
    assert result["only_top_level_result_count"] == 0
