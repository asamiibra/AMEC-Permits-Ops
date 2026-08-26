from __future__ import annotations

import subprocess

import pytest

from scripts.synology_preaccess.secret_scan import scan


def git(repo, *args):
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def candidate_repo(tmp_path, content):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Synthetic Test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "--allow-empty", "-qm", "base"], cwd=tmp_path, check=True)
    (tmp_path / "fixture.txt").write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", "fixture.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=tmp_path, check=True)
    return git(tmp_path, "rev-parse", "HEAD^"), git(tmp_path, "rev-parse", "HEAD")


@pytest.mark.parametrize(
    "pattern_kind",
    ["ghp", "aws", "private_key", "smb_password"],
    ids=["ghp-shape", "aws-key-shape", "private-key-shape", "smb-password-shape"],
)
def test_secret_scanner_hostile_fixture_matches_without_disclosure(tmp_path, pattern_kind):
    fixtures = {
        "ghp": ("token=ghp_" + "A" * 20, "GHP_TOKEN"),
        "aws": ("token=AKIA" + "A" * 16, "AWS_ACCESS_KEY"),
        "private_key": ("-----BEGIN " + "RSA PRIVATE KEY-----", "PRIVATE_KEY_MARKER"),
        "smb_password": ("SMB_EXTERNAL_" + "PASSWORD=" + "not-a-sentinel", "SMB_EXTERNAL_PASSWORD"),
    }
    content, pattern = fixtures[pattern_kind]
    base, candidate = candidate_repo(tmp_path, content)
    result = scan(tmp_path, base_sha=base, candidate_sha=candidate, source_roots=())
    assert result["scanner_executed"] is True
    assert result["match_count"] == 1
    assert result["matches"][0]["pattern_id"] == pattern
    assert content not in str(result)


def test_secret_scanner_clean_fixture_passes(tmp_path):
    base, candidate = candidate_repo(tmp_path, "provider=synthetic\n" + "SMB_EXTERNAL_" + "PASSWORD=synthetic-placeholder\n")
    result = scan(tmp_path, base_sha=base, candidate_sha=candidate, source_roots=())
    assert result["scanner_executed"] is True and result["match_count"] == 0 and result["errors"] == [] and result["status"] == "PASS"


def test_secret_scanner_error_is_not_pass(tmp_path):
    result = scan(tmp_path, base_sha="not-a-revision", candidate_sha="also-not-a-revision", source_roots=())
    assert result["scanner_executed"] is True and result["errors"] and result["status"] == "FAIL"
