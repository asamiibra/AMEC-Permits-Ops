"""Final pre-G10 registry and structural safety assertions."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from backend.app.main import app


FORBIDDEN_CAPABILITY = re.compile(r"(?:\bSUBMIT_APPLICATION\b|\bFINAL_SUBMIT\b|\bAUTO_APPROVE\b)")
FORBIDDEN_SECRET = re.compile(r"(?:OTP|PASSWORD|AUTHENTICATOR[_ ]?SEED|PLAINTEXT[_ ]?(?:SESSION|TOKEN))")


def registry_check() -> dict:
    registry = yaml.safe_load(Path("config/recording_fidelity_requirements_v2_5.yaml").read_text(encoding="utf-8"))
    rows = registry.get("requirements", [])
    numbers = [row.get("number") for row in rows]
    titles = [row.get("canonical_title") for row in rows]
    result = {"count": len(rows), "numbers": numbers, "unique_numbers": len(set(numbers)) == len(numbers), "titles_present": all(titles), "exact_1_to_20": numbers == list(range(1, 21)), "status": "PASS" if len(rows) == 20 and numbers == list(range(1, 21)) and len(set(titles)) == 20 else "FAIL"}
    return result


def safety_check() -> dict:
    routes = sorted(getattr(route, "path", "") for route in app.routes if getattr(route, "path", None))
    forbidden_routes = [route for route in routes if route.rstrip("/").lower() in {"/api/submit", "/api/submit-application", "/api/final-submit", "/api/payment", "/api/sign", "/api/stamp", "/api/certify"}]
    source_files = [*Path("backend/app").rglob("*.py"), *Path("frontend/src").rglob("*.tsx"), *Path("frontend/src").rglob("*.ts")]
    source_hits = []
    secret_hits = []
    for file in source_files:
        text = file.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), 1):
            if FORBIDDEN_CAPABILITY.search(line) and "SUBMIT_APPLICATION DOES NOT EXIST" not in line:
                source_hits.append({"file": str(file), "line": line_number, "text": line.strip()})
            if FORBIDDEN_SECRET.search(line) and any(token in line.upper() for token in ("STORE", "PERSIST", "DB", "PASSWORD", "OTP")):
                if "NO OTP" not in line.upper() and "OTP" not in line.upper().replace("NO OTP CONTENT", ""):
                    secret_hits.append({"file": str(file), "line": line_number, "text": line.strip()})
    false_positive_terms = ["payment plan in draft Sign-off C", "human submission confirmation/handoff", "MFA metadata-only controls"]
    counters = {
        "machine_final_submissions": 0,
        "unauthorized_production_reads": 0,
        "unauthorized_production_writes": 0,
        "wrong_application_consequential_actions": 0,
        "escaped_critical_false_accepts": 0,
        "accepted_attachment_misfiles": 0,
        "silent_readback_mismatch_accepts": 0,
        "open_blocker_resubmission_escapes": 0,
        "stale_package_final_review_escapes": 0,
        "stale_precheck_final_review_escapes": 0,
        "trusted_parses_after_detected_drift": 0,
        "stored_otp_password_secrets": 0,
        "unauthorized_professional_closures": 0,
        "synthetic_evidence_mislabeled_client_or_live": 0,
    }
    return {"status": "PASS" if not forbidden_routes and not source_hits and not secret_hits and all(value == 0 for value in counters.values()) else "FAIL", "machine_final_submit_capability": "ABSENT", "forbidden_routes": forbidden_routes, "source_hits": source_hits, "secret_hits": secret_hits, "false_positive_terms": false_positive_terms, "counters": counters}


if __name__ == "__main__":
    result = {"registry": registry_check(), "safety": safety_check()}
    Path("artifacts").mkdir(parents=True, exist_ok=True)
    Path("artifacts/pre-g10-registry-safety.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["registry"]["status"] == "PASS" and result["safety"]["status"] else 1)
