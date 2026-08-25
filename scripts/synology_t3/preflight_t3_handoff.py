"""Owner-side immutable handoff/image preflight; never starts the T3 runner."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import sys

try:
    from scripts.synology_t3.validate_t3_return import validate_handoff
except ModuleNotFoundError:
    repo_root = Path(__file__).resolve().parents[2]
    handoff_harness = Path(__file__).resolve().parent / "harness_source"
    sys.path.insert(0, str(handoff_harness if (handoff_harness / "t3_common.py").is_file() else repo_root))
    try:
        from scripts.synology_t3.validate_t3_return import validate_handoff
    except ModuleNotFoundError:
        import importlib.util
        spec = importlib.util.spec_from_file_location("handoff_validator", Path(__file__).resolve().parent / "validate_t3_return.py")
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        validate_handoff = module.validate_handoff


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--handoff-root", type=Path, required=True)
    parser.add_argument("--image-tar", type=Path, required=True)
    parser.add_argument("--image-ref", required=True)
    args = parser.parse_args()
    root = args.handoff_root.resolve()
    errors = validate_handoff(root)["errors"]
    policy = json.loads((root / "06_IMAGE_BUILD_POLICY.json").read_text(encoding="utf-8"))
    actual_tar_sha = hashlib.sha256(args.image_tar.read_bytes()).hexdigest()
    if actual_tar_sha != policy.get("image_tar_sha256"):
        errors.append("image tar digest mismatch")
    if errors:
        print(json.dumps({"status": "STOP_T3_HANDOFF_OR_IMAGE_IDENTITY_MISMATCH", "errors": errors}, sort_keys=True))
        return 2
    subprocess.run(["docker", "load", "--input", str(args.image_tar)], check=True, stdout=subprocess.PIPE, text=True)
    inspect = json.loads(subprocess.check_output(["docker", "image", "inspect", args.image_ref, "--format", "{{json .}}"], text=True))
    labels = inspect.get("Config", {}).get("Labels", {}) or {}
    expected_app = policy["application_sha"]
    expected_harness = policy["harness_sha"]
    if labels.get("org.opencontainers.image.proposalops-application-revision") != expected_app:
        errors.append("application image label mismatch")
    if labels.get("org.opencontainers.image.revision") != expected_harness:
        errors.append("harness image label mismatch")
    if labels.get("org.opencontainers.image.synthetic-only") != "true":
        errors.append("synthetic-only label missing")
    if str(inspect.get("Config", {}).get("User", "")) not in {"10001", "10001:10001"}:
        errors.append("image is not configured for non-root user")
    result = {"status": "PASS" if not errors else "STOP_T3_HANDOFF_OR_IMAGE_IDENTITY_MISMATCH", "errors": errors, "image_id": inspect.get("Id"), "application_sha": expected_app, "harness_sha": expected_harness}
    print(json.dumps(result, sort_keys=True))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
