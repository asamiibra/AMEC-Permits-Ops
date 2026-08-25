"""Pure host-bootstrap gates shared by the Owner wrapper and synthetic tests."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Any, Dict, Optional

import sys

sys.dont_write_bytecode = True


def bytecode_counts(root: Path) -> Dict[str, int]:
    pyc = 0
    pycache = 0
    for path in root.rglob("*"):
        if path.is_dir() and path.name == "__pycache__":
            pycache += 1
        elif path.is_file() and path.suffix == ".pyc":
            pyc += 1
    return {"pyc_count": pyc, "pycache_dir_count": pycache}


def safe_child(root: Path, candidate: Path) -> bool:
    root_real = root.resolve()
    candidate_real = candidate.resolve()
    try:
        candidate_real.relative_to(root_real)
    except ValueError:
        return False
    return candidate_real != root_real


def owner_mode(path: Path) -> Dict[str, int]:
    info = path.stat()
    return {"uid": info.st_uid, "gid": info.st_gid, "mode": stat.S_IMODE(info.st_mode)}


def policy_matches(path: Path, uid: int, gid: int, mode: int, *, regular: bool = True) -> bool:
    if not path.exists() or path.is_symlink():
        return False
    if regular and not path.is_file():
        return False
    observed = owner_mode(path)
    return observed == {"uid": uid, "gid": gid, "mode": mode}


def control_dir_is_valid(control_root: Path, control_dir: Path) -> bool:
    return control_root.is_dir() and not control_root.is_symlink() and safe_child(control_root, control_dir) and control_dir.is_dir() and not control_dir.is_symlink() and policy_matches(control_dir, 0, 0, 0o700, regular=False)


def collision_status(uid: int = 10001, gid: int = 10001, passwd_path: Path = Path("/etc/passwd"), group_path: Path = Path("/etc/group")) -> Dict[str, bool]:
    uid_collision = False
    gid_collision = False
    for line in passwd_path.read_text(encoding="utf-8").splitlines():
        fields = line.split(":")
        if len(fields) > 2 and fields[2].isdigit() and int(fields[2]) == uid:
            uid_collision = True
    for line in group_path.read_text(encoding="utf-8").splitlines():
        fields = line.split(":")
        if len(fields) > 2 and fields[2].isdigit() and int(fields[2]) == gid:
            gid_collision = True
    return {"uid_10001_collision": uid_collision, "gid_10001_collision": gid_collision}


def image_identity_errors(inspect: Optional[Dict[str, Any]], policy: Dict[str, Any]) -> list:
    if inspect is None:
        return ["image tag absent"]
    labels = inspect.get("Config", {}).get("Labels", {}) or {}
    errors = []
    if inspect.get("Id") != policy.get("image_id"):
        errors.append("image ID mismatch")
    if labels.get("org.opencontainers.image.proposalops-application-revision") != policy.get("application_sha"):
        errors.append("application label mismatch")
    if labels.get("org.opencontainers.image.revision") != policy.get("harness_sha"):
        errors.append("harness label mismatch")
    if labels.get("org.opencontainers.image.synthetic-only") != "true":
        errors.append("synthetic-only label mismatch")
    if inspect.get("Os") != "linux" or inspect.get("Architecture") != "amd64":
        errors.append("platform mismatch")
    if inspect.get("Config", {}).get("User") != "10001:10001":
        errors.append("image user mismatch")
    return errors


def classify_image_ref(inspect: Optional[Dict[str, Any]], policy: Dict[str, Any]) -> str:
    """Classify a tag before load: absent, exact reusable, or conflicting."""
    if inspect is None:
        return "absent"
    return "exact" if not image_identity_errors(inspect, policy) else "conflict"
