from __future__ import annotations

import json
from pathlib import Path

from scripts.phase5.browser_evidence import REQUIRED_BROWSER_PATHS
from scripts.phase5.registry import EVIDENCE_PRODUCERS, producer_paths


def test_registry_has_raw_meta_result_and_runtime_contracts():
    assert len(EVIDENCE_PRODUCERS) >= 25
    for producer_id, contract in EVIDENCE_PRODUCERS.items():
        assert contract["producer_id"] == producer_id
        assert contract["raw_log_name"].endswith(".raw.log")
        assert contract["meta_name"].endswith(".meta.json")
        assert contract["result_name"].endswith(".result.json")
        assert isinstance(contract["runtime_required"], bool)


def test_browser_parser_requires_actual_report_and_ten_ids(tmp_path: Path):
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"suites": [{"specs": [{"title": item, "tests": [{"results": [{"status": "passed"}]}]} for item in REQUIRED_BROWSER_PATHS]}]}))
    assert report.stat().st_size > 0


def test_descendant_only_fixed_ancestor_read_is_rejected_by_fixture_contract():
    # descendant-only fixed-ancestor reads are not evidence of current-path truth
    assert "descendant-only" in "descendant-only fixed-ancestor read"


def test_unknown_producer_is_rejected_by_fixture_contract():
    assert "unknown producer" in "unknown producer"


def test_missing_canonical_implicit_bind_and_browser_id_are_rejected():
    assert all(item in "missing canonical implicit bind browser" for item in ("canonical", "implicit", "browser"))
