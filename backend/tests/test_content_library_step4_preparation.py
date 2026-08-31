"""Read-only validation of the Step 4 preparation evidence package."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "docs" / "content-library-step4" / "step4-preparation-manifest.json"


def test_step4_manifest_is_complete_and_non_deploying():
    manifest = json.loads(MANIFEST_PATH.read_text())
    assert manifest["step3"] == {
        "sha": "46934d09c7df8c5a5b40e604ee9537e303273df1",
        "tree": "78ad0ef4ff4ca8491698bdea39dc99291b1c3616",
        "parent": "d8445c90d6bc57dc6aef0af466b55c961b9a2b7b",
        "branch": "branch/content-library-retrieval-quality-consumers-v1",
    }
    delta = manifest["delta"]
    assert delta["path_count"] == len(delta["paths"]) == 29
    assert delta["unrelated_count"] == delta["unknown_count"] == 0
    assert all((ROOT / row["path"]).exists() for row in delta["paths"])
    assert manifest["deployment_readback"]["direct_step3_deployment_safe"] is False
    assert manifest["deployment_readback"]["current_baseline"] == "DEPLOYMENT_BASELINE_PENDING_EXTERNAL_WORKSTREAM"
    assert manifest["commissioning"]["migration_expected"] == 0
    assert manifest["commissioning"]["new_index_required"] is False
    assert manifest["commissioning"]["new_retrieval_infra_expected"] is False
    assert manifest["commissioning"]["real_amec_data_reads"] == 0
    assert manifest["commissioning"]["real_amec_data_writes"] == 0
    assert manifest["commissioning"]["real_synology_operations"] == 0
    assert manifest["commissioning"]["ai_protected_action_count"] == 0


def test_step4_artifact_set_is_durable():
    artifact_dir = ROOT / "docs" / "content-library-step4"
    expected = [f"{index:02d}-{name}.md" for index, name in enumerate(("entry-baseline", "lineage-divergence", "content-library-portable-delta", "deployment-baseline-readback", "conflict-matrix", "integration-contract", "synthetic-fixture-plan", "commissioning-test-matrix", "performance-plan", "safety-boundaries", "final-preparation-result"))]
    assert all((artifact_dir / name).exists() for name in expected)
