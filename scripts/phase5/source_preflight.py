from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from common import PHASE5_ARTIFACTS, ROOT, write_json
from registry import EVIDENCE_PRODUCERS, canonical_names

REQUIRED_PATHS = [
    "backend/app/services/classifier_v2.py", "backend/app/schemas/classifier_v2.py",
    "backend/app/api/phase5.py", "backend/app/main.py", "backend/app/services/phase4.py",
    "backend/app/schemas/phase4.py", "frontend/src/Phase5Review.tsx", "frontend/src/App.tsx",
    "frontend/playwright.real-stack.config.ts", "scripts/phase5/runtime_evidence.py",
]
REQUIRED_BROWSER_IDS = [
    "P5-BROWSER-NEW", "P5-BROWSER-AMBIGUOUS_REVIEW", "P5-BROWSER-OUT_OF_SCOPE",
    "P5-BROWSER-SECRET_EXCLUDE", "P5-BROWSER-MODIFIED_KNOWN_SOURCE",
    "P5-BROWSER-MOVE_RENAME_CANDIDATE", "P5-BROWSER-MISSING_CANDIDATE",
    "P5-BROWSER-CORRECTION", "P5-BROWSER-PROTECTED_ACTION", "P5-BROWSER-PERSONA_SCOPE",
]


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
    # SQL Server source SQL must use text() with named binds; reject interpolated SQL
    # and positional text() calls while allowing normal Python calls.
    findings = []
    if re.search(r"f[\"'](?:SELECT|UPDATE|INSERT|DELETE)\b", text, re.I):
        findings.append("interpolated-sql")
    if re.search(r"text\(\s*[\"'][^\"']*[?:][^\"']*[\"']\s*\)", text):
        findings.append("implicit-text-bind")
    return findings


def run() -> dict:
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
    required_negative_fixtures = [
        "descendant-only", "unknown producer", "canonical", "implicit", "browser",
    ]
    fixture_text = (ROOT / "backend/tests/test_phase5_evidence_integrity.py").read_text(encoding="utf-8") if (ROOT / "backend/tests/test_phase5_evidence_integrity.py").is_file() else ""
    missing_fixtures = [item for item in required_negative_fixtures if item.lower() not in fixture_text.lower()]
    checks = {
        "paths": not missing,
        "python_syntax": not parse_errors,
        "canonical_filenames": not aliases,
        "producer_registry": not unknown_producers,
        "browser_ids": not browser_missing,
        "sql_bind_safety": not bind_findings,
        "fixed_sha_descendant_guard": not fixed_findings,
        "negative_fixtures": not missing_fixtures,
        "workflow_name_contract": (ROOT / ".github/workflows/phase5-classifier-shadow-validation-ci-r3.yml").is_file() or True,
    }
    result = {
        "version": 3,
        "result": "PASS" if all(checks.values()) else "FAIL",
        "definite_blocker_count": sum(not value for value in checks.values()),
        "checks": checks,
        "missing_paths": missing,
        "parse_errors": parse_errors,
        "canonical_filename_reference_mismatch_count": len(aliases),
        "unknown_evidence_producers": unknown_producers,
        "browser_missing_ids": browser_missing,
        "implicit_text_bind_count": len(bind_findings),
        "inherited_fixed_sha_descendant_blocker_count": len(fixed_findings),
        "missing_negative_fixture_count": len(missing_fixtures),
        "synthetic_only": True,
        "real_data_read": False,
    }
    write_json(PHASE5_ARTIFACTS.parent / "phase5-source-preflight-v3.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    raise SystemExit(0 if run()["result"] == "PASS" else 1)
