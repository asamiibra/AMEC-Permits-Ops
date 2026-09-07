from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

REQUIRED_BROWSER_PATHS = [
    "P5-BROWSER-NEW", "P5-BROWSER-AMBIGUOUS_REVIEW", "P5-BROWSER-OUT_OF_SCOPE",
    "P5-BROWSER-SECRET_EXCLUDE", "P5-BROWSER-MODIFIED_KNOWN_SOURCE",
    "P5-BROWSER-MOVE_RENAME_CANDIDATE", "P5-BROWSER-MISSING_CANDIDATE",
    "P5-BROWSER-CORRECTION", "P5-BROWSER-PROTECTED_ACTION", "P5-BROWSER-PERSONA_SCOPE",
]
QUALITY_IDS = ["P5-QUALITY-LOADING", "P5-QUALITY-EMPTY", "P5-QUALITY-ERROR", "P5-QUALITY-KEYBOARD", "P5-QUALITY-ACCESSIBILITY", "P5-QUALITY-DEEP-LINK", "P5-QUALITY-OBSERVABILITY"]


def _tests(node: Any, prefix: str = "") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(node, dict):
        title = str(node.get("title", ""))
        results = node.get("results", [])
        if title and results:
            statuses = [str(item.get("status", "")) for item in results if isinstance(item, dict)]
            status = "passed" if statuses and all(item == "passed" for item in statuses) else ("skipped" if statuses and all(item in {"skipped", "pending"} for item in statuses) else "failed")
            found.append((title, status))
        # Playwright's JSON reporter stores the title on the spec object and
        # the execution results on its child test object.  Keep the parser
        # tied to observed execution results rather than the spec's `ok` flag,
        # which can otherwise make a structurally valid report appear empty.
        if title and isinstance(node.get("tests"), list):
            for test in node["tests"]:
                if not isinstance(test, dict):
                    continue
                test_results = test.get("results", [])
                statuses = [
                    str(item.get("status", ""))
                    for item in test_results
                    if isinstance(item, dict)
                ]
                if statuses:
                    status = "passed" if all(item == "passed" for item in statuses) else (
                        "skipped"
                        if all(item in {"skipped", "pending"} for item in statuses)
                        else "failed"
                    )
                    found.append((title, status))
        for value in node.values():
            found.extend(_tests(value, prefix))
    elif isinstance(node, list):
        for value in node:
            found.extend(_tests(value, prefix))
    return found


def _source_checks(spec: Path) -> dict[str, Any]:
    text = spec.read_text(encoding="utf-8")
    missing = [item for item in REQUIRED_BROWSER_PATHS if item not in text]
    quality_missing = [item for item in QUALITY_IDS if item not in text]
    # Required business paths must be exercised against the running API. Error-only
    # network aborts are allowed, but fabricated route.fulfill responses are not.
    business_mock_count = len(re.findall(r"(?:page|context)\.route\s*\([^\n]*\).*?route\.fulfill", text, re.S | re.I))
    return {"missing_ids": missing, "quality_missing_ids": quality_missing, "business_api_mock_count": business_mock_count, "spec_bytes": len(text.encode())}


def run(playwright_json: Path, spec: Path, output: Path) -> dict[str, Any]:
    payload = json.loads(playwright_json.read_text(encoding="utf-8"))
    checks = _tests(payload)
    by_id: dict[str, str] = {}
    for title, status in checks:
        for identifier in REQUIRED_BROWSER_PATHS + QUALITY_IDS:
            if identifier in title:
                by_id[identifier] = status
    source = _source_checks(spec)
    required_statuses = [by_id.get(identifier, "missing") for identifier in REQUIRED_BROWSER_PATHS]
    quality_statuses = [by_id.get(identifier, "missing") for identifier in QUALITY_IDS]
    result = {
        "version": 2,
        "result": "PASS" if (all(item == "passed" for item in required_statuses) and all(item == "passed" for item in quality_statuses) and not source["missing_ids"] and not source["quality_missing_ids"] and source["business_api_mock_count"] == 0) else "FAIL",
        "required_path_count": len(REQUIRED_BROWSER_PATHS),
        "required_path_pass": sum(item == "passed" for item in required_statuses),
        "required_path_fail": sum(item in {"failed", "missing"} for item in required_statuses),
        "required_path_skip": sum(item == "skipped" for item in required_statuses),
        "quality_check_count": len(QUALITY_IDS),
        "quality_pass_count": sum(item == "passed" for item in quality_statuses),
        "quality_fail_count": sum(item in {"failed", "missing"} for item in quality_statuses),
        "quality_skip_count": sum(item == "skipped" for item in quality_statuses),
        "api_mock_count_for_required_paths": source["business_api_mock_count"],
        "declared_ids": REQUIRED_BROWSER_PATHS,
        "quality_ids": QUALITY_IDS,
        "required_path_status_by_id": {identifier: by_id.get(identifier, "missing") for identifier in REQUIRED_BROWSER_PATHS},
        "quality_status_by_id": {identifier: by_id.get(identifier, "missing") for identifier in QUALITY_IDS},
        "loading_state_proven": by_id.get("P5-QUALITY-LOADING") == "passed",
        "error_state_proven": by_id.get("P5-QUALITY-ERROR") == "passed",
        "empty_state_proven": by_id.get("P5-QUALITY-EMPTY") == "passed",
        "keyboard_action_paths_pass": by_id.get("P5-QUALITY-KEYBOARD") == "passed",
        "basic_accessibility_pass": by_id.get("P5-QUALITY-ACCESSIBILITY") == "passed",
        "deep_link_resolution_pass": by_id.get("P5-QUALITY-DEEP-LINK") == "passed",
        "correlation_id_inspectable": by_id.get("P5-QUALITY-OBSERVABILITY") == "passed",
        "root_event_inspectable": by_id.get("P5-QUALITY-OBSERVABILITY") == "passed",
        "source_checks": source,
        "report_path": str(playwright_json),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--playwright-json", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    return 0 if run(args.playwright_json, args.spec, args.output)["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
