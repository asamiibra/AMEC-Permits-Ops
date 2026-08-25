from __future__ import annotations

import json
import os
import re
import subprocess
import sys

import pytest

from scripts.synology_preaccess.artifact_hygiene_scan import scan_artifact
from scripts.synology_preaccess.evidence_audit import audit
from backend.tests.test_synology_preaccess_v2_2_evidence import complete_artifact


def put_scan_scope(root, content: str) -> None:
    (root / "raw").mkdir(parents=True, exist_ok=True)
    (root / "evidence").mkdir(parents=True, exist_ok=True)
    (root / "raw" / "synthetic.junit.xml").write_text(content, encoding="utf-8")
    (root / "source_manifest.json").write_text("{}\n", encoding="utf-8")


@pytest.mark.parametrize("shape", ["ghp", "aws", "private_key", "smb_password"], ids=["ghp-shape", "aws-key-shape", "private-key-shape", "smb-password-shape"])
def test_artifact_hygiene_rejects_each_secret_shape(tmp_path, shape):
    values = {
        "ghp": "ghp_" + "A" * 20,
        "aws": "AKIA" + "A" * 16,
        "private_key": "-----BEGIN " + "RSA PRIVATE KEY-----",
        "smb_password": "SMB_EXTERNAL_" + "PASSWORD=" + "not-a-sentinel",
    }
    put_scan_scope(tmp_path, values[shape])
    result = scan_artifact(tmp_path)
    assert result["status"] == "FAIL" and result["match_count"] == 1 and result["errors"] == []


def test_clean_artifact_passes(tmp_path):
    put_scan_scope(tmp_path, "synthetic placeholder only\n" + "SMB_EXTERNAL_" + "PASSWORD=synthetic-placeholder\n")
    result = scan_artifact(tmp_path)
    assert result["status"] == "PASS" and result["match_count"] == 0 and result["errors"] == []


def test_scanner_error_is_fail(tmp_path):
    result = scan_artifact(tmp_path / "missing-artifact")
    assert result["status"] == "FAIL" and result["errors"]


def test_missing_hygiene_evidence_fails_acceptance_audit(tmp_path):
    root = complete_artifact(tmp_path)
    (root / "evidence" / "52_ARTIFACT_HYGIENE.json").unlink()
    result = audit(root)
    assert result["status"] == "FAIL" and any("hygiene" in error for error in result["errors"])


@pytest.mark.parametrize("target", ["registry", "handoff"], ids=["registry", "handoff"])
def test_registry_and_handoff_secret_shape_fails_scan(tmp_path, target):
    root = complete_artifact(tmp_path)
    path = root / "evidence" / ("50_ACCEPTANCE_REGISTRY.json" if target == "registry" else "51_FINAL_HANDOFF.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["synthetic_probe"] = "ghp_" + "A" * 20
    path.write_text(json.dumps(payload), encoding="utf-8")
    result = scan_artifact(root)
    assert result["status"] == "FAIL" and result["match_count"] == 1


def test_hostile_scanner_junit_has_no_secret_shaped_testcase_ids(tmp_path):
    junit_path = tmp_path / "hostile.junit.xml"
    environment = os.environ.copy()
    for name in ("DATABASE_URL", "SYNTHETIC_TEST_ROOT", "MOCK_SYSTEMS_ROOT"):
        environment.pop(name, None)
    environment.update({"APP_ENV": "TEST", "SYNTHETIC_ONLY": "true"})
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "backend/tests/test_synology_preaccess_v2_2_secret_scanner.py", "--junitxml", str(junit_path)],
        cwd=str(__import__("pathlib").Path(__file__).resolve().parents[2]),
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    junit = junit_path.read_text(encoding="utf-8")
    assert not re.search(r"ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----|SMB_EXTERNAL_PASSWORD\s*=\s*(\S+)", junit)
