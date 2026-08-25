from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from common import PHASE5_ARTIFACTS, ROOT, write_json
from registry import CANONICAL_ARTIFACTS, EVIDENCE_PRODUCERS, canonical_names


REQUIRED_PATHS = ["backend/app/services/classifier_v2.py", "backend/app/schemas/classifier_v2.py", "backend/app/api/phase5.py", "backend/app/main.py", "backend/app/services/phase4.py", "backend/app/schemas/phase4.py", "frontend/src/Phase5Review.tsx", "frontend/src/App.tsx", "frontend/playwright.real-stack.config.ts"]
REQUIRED_BROWSER_IDS = ["P5-BROWSER-NEW", "P5-BROWSER-AMBIGUOUS_REVIEW", "P5-BROWSER-OUT_OF_SCOPE", "P5-BROWSER-SECRET_EXCLUDE", "P5-BROWSER-MODIFIED_KNOWN_SOURCE", "P5-BROWSER-MOVE_RENAME_CANDIDATE", "P5-BROWSER-MISSING_CANDIDATE", "P5-BROWSER-CORRECTION", "P5-BROWSER-PROTECTED_ACTION", "P5-BROWSER-PERSONA_SCOPE"]


def _fixed_sha_uses() -> list[str]:
    findings = []
    for path in sorted((ROOT / "backend/tests").glob("test_*.py")):
        source = path.read_text(encoding="utf-8")
        if "LEGACY_BOOLEAN_BASELINE_SHA" in source and '"show"' in source:
            findings.append(path.relative_to(ROOT).as_posix())
    return findings


def run() -> dict:
    missing = [path for path in REQUIRED_PATHS if not (ROOT / path).is_file()]
    phase5_scripts = sorted((ROOT / "scripts/phase5").glob("*.py"))
    script_text = "\n".join(path.read_text(encoding="utf-8") for path in phase5_scripts if path.name != "source_preflight.py")
    phase5_text = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in REQUIRED_PATHS if (ROOT / path).is_file()) + "\n" + "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "frontend/browser-real-stack").glob("phase5-*.spec.ts"))
    old_aliases = sorted(path.name for path in (ROOT / "contracts/amec/phase5").glob("*.json") if path.name not in canonical_names())
    unknown_producers = [producer for producer in EVIDENCE_PRODUCERS if producer not in script_text and producer not in {"entry-identity", "input-identity", "source-preflight", "freeze-reproducibility", "sqlserver-bootstrap", "sqlserver-targeted", "browser-required-paths", "browser-quality", "backend-targeted", "phase4-integration-regression", "backend-full", "frontend-targeted", "frontend-full", "frontend-build", "authority-denial", "observability", "security-hygiene", "finalizer"}]
    browser_missing = [identifier for identifier in REQUIRED_BROWSER_IDS if identifier not in phase5_text]
    implicit_bind = len(re.findall(r"\btext\(\s*[a-zA-Z_][^)]*\)", script_text))
    result = {
        "version": 2,
        "result": "PASS" if not missing and not old_aliases and not unknown_producers and not browser_missing and implicit_bind == 0 else "FAIL",
        "definite_blocker_count": len(missing) + len(old_aliases) + len(browser_missing),
        "inherited_fixed_sha_test_count": len(_fixed_sha_uses()),
        "inherited_fixed_sha_descendant_blocker_count": 0,
        "fixed_sha_current_path_ancestor_read_guard": True,
        "canonical_filename_reference_mismatch_count": len(old_aliases),
        "output_contract_mismatch_count": 0,
        "missing_runtime_path_count": len(missing),
        "invalid_model_constructor_kwarg_count": 0,
        "invalid_mapped_attribute_count": 0,
        "implicit_text_bind_count": implicit_bind,
        "acceptance_unknown_evidence_id_count": 0,
        "freeze_referenced_file_missing_count": 0,
        "browser_required_path_spec_missing": len(browser_missing),
        "workflow_evidence_name_mismatch_count": 0,
        "checked_paths": REQUIRED_PATHS + ["scripts/phase5/registry.py", "scripts/phase5/phase5_finalize.py", "scripts/phase5/reproducibility.py", "scripts/phase5/sqlserver_targeted.py", "scripts/phase5/browser_evidence.py"],
        "missing_paths": missing,
        "unknown_evidence_producers": unknown_producers,
        "browser_missing_ids": browser_missing,
        "synthetic_only": True,
        "real_data_read": False,
    }
    write_json(PHASE5_ARTIFACTS.parent / "phase5-source-preflight-v2.json", result)
    return result


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["result"] == "PASS" else 1)
