import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.ui_product_surface_closure import calculate_terminal_metrics, semantic_adjudication


def operation(method: str, path: str, name: str = "fabricated") -> dict[str, str]:
    return {"method": method, "path": path, "name": name, "classification": "USER_SURFACE_REQUIRED"}


def test_fabricated_human_post_is_a_blocking_gap():
    result = semantic_adjudication(operation("POST", "/api/fabricated-human-command"), [])
    assert result["terminal_classification"] == "BLOCKING_UI_GAP"


def test_unmatched_get_is_not_derived_support():
    result = semantic_adjudication(operation("GET", "/api/fabricated-read-model"), [])
    assert result["terminal_classification"] == "BLOCKING_UI_GAP"


def test_unmatched_post_is_not_backend_only_internal():
    result = semantic_adjudication(operation("POST", "/api/fabricated-command"), [])
    assert result["terminal_classification"] == "BLOCKING_UI_GAP"


def test_frontend_reference_does_not_supply_terminal_evidence():
    result = semantic_adjudication(operation("POST", "/api/proposals/fabricated/action"), [{"reference": "/api/proposals/fabricated/action"}])
    assert result["terminal_classification"] == "BLOCKING_UI_GAP"


def test_missing_reviewer_rationale_is_not_a_pass():
    metrics = calculate_terminal_metrics([{
        "classification": "USER_SURFACE_REQUIRED",
        "terminal_classification": "SURFACED_DIRECT",
        "semantic_reason": "",
        "reviewer_disposition": "MISSING",
    }])
    assert metrics["UI_UNJUSTIFIED_CLASSIFICATION_ROWS"] == 1


def test_unreviewed_browser_evidence_cannot_be_terminal():
    result = semantic_adjudication(operation("PATCH", "/api/fabricated/action"), [])
    assert result["terminal_classification"] == "BLOCKING_UI_GAP"
    assert result["reviewer_disposition"] == "UNREVIEWED_OPERATION"
