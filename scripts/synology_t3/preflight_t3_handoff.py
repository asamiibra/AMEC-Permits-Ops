"""Owner-side immutable handoff/image preflight; never starts the T3 runner."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import sys

sys.dont_write_bytecode = True

try:
    from scripts.synology_t3.host_bootstrap import bytecode_counts, classify_image_ref, image_identity_errors
    from scripts.synology_t3.validate_t3_return import validate_handoff
except ModuleNotFoundError:
    repo_root = Path(__file__).resolve().parents[2]
    handoff_harness = Path(__file__).resolve().parent / "harness_source"
    sys.path.insert(0, str(handoff_harness if (handoff_harness / "t3_common.py").is_file() else repo_root))
    try:
        from host_bootstrap import bytecode_counts, classify_image_ref, image_identity_errors
        from scripts.synology_t3.validate_t3_return import validate_handoff
    except ModuleNotFoundError:
        import importlib.util
        helper_spec = importlib.util.spec_from_file_location("host_bootstrap", Path(__file__).resolve().parent / "host_bootstrap.py")
        helper = importlib.util.module_from_spec(helper_spec)
        assert helper_spec.loader is not None
        helper_spec.loader.exec_module(helper)
        bytecode_counts = helper.bytecode_counts
        classify_image_ref = helper.classify_image_ref
        image_identity_errors = helper.image_identity_errors
        spec = importlib.util.spec_from_file_location("handoff_validator", Path(__file__).resolve().parent / "validate_t3_return.py")
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        validate_handoff = module.validate_handoff


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--handoff-root", type=Path, required=True)
    parser.add_argument("--image-tar", type=Path, required=True)
    parser.add_argument("--image-ref")
    args = parser.parse_args()
    root = args.handoff_root.resolve()
    errors = validate_handoff(root)["errors"]
    policy = json.loads((root / "06_IMAGE_BUILD_POLICY.json").read_text(encoding="utf-8"))
    policy_image_ref = policy.get("image_ref")
    if not policy_image_ref:
        errors.append("image_ref missing from immutable policy")
    if args.image_ref and args.image_ref != policy_image_ref:
        errors.append("image ref override does not equal immutable policy")
    image_ref = policy_image_ref or args.image_ref
    counts_before = bytecode_counts(root)
    if counts_before["pyc_count"] or counts_before["pycache_dir_count"]:
        errors.append("STOP_T3_HANDOFF_BYTECODE_CONTAMINATION")
    actual_tar_sha = hashlib.sha256(args.image_tar.read_bytes()).hexdigest()
    if actual_tar_sha != policy.get("image_tar_sha256"):
        errors.append("image tar digest mismatch")
    if errors:
        print(json.dumps({"status": "STOP_T3_HANDOFF_OR_IMAGE_IDENTITY_MISMATCH", "errors": errors}, sort_keys=True))
        return 2
    expected_app = policy["application_sha"]
    expected_harness = policy["harness_sha"]
    try:
        existing = json.loads(subprocess.check_output(["docker", "image", "inspect", image_ref, "--format", "{{json .}}"], text=True))
    except subprocess.CalledProcessError:
        existing = None
    state = classify_image_ref(existing, policy)
    if state == "conflict":
        print(json.dumps({"status": "STOP_T3_IMAGE_TAG_COLLISION", "errors": image_identity_errors(existing, policy), "image_ref_preexisting": True, "image_ref_preexisting_exact": False, "docker_load_count": 0}, sort_keys=True))
        return 2
    load_count = 0
    image_reused = state == "exact"
    if state == "absent":
        subprocess.run(["docker", "load", "--input", str(args.image_tar)], check=True, stdout=subprocess.PIPE, text=True)
        load_count = 1
        inspect = json.loads(subprocess.check_output(["docker", "image", "inspect", image_ref, "--format", "{{json .}}"], text=True))
    else:
        inspect = existing
    errors.extend(image_identity_errors(inspect, policy))
    counts_after = bytecode_counts(root)
    if counts_after["pyc_count"] or counts_after["pycache_dir_count"]:
        errors.append("STOP_T3_HANDOFF_BYTECODE_CONTAMINATION")
    result = {"status": "PASS" if not errors else "STOP_T3_HANDOFF_OR_IMAGE_IDENTITY_MISMATCH", "errors": errors, "image_id": inspect.get("Id") if inspect else None, "application_sha": expected_app, "harness_sha": expected_harness, "image_ref_preexisting": state != "absent", "image_ref_preexisting_exact": state == "exact", "docker_load_count": load_count, "image_reused": image_reused, "handoff_pyc_before": counts_before["pyc_count"], "handoff_pyc_after": counts_after["pyc_count"], "handoff_pyc_cache_before": counts_before["pycache_dir_count"], "handoff_pyc_cache_after": counts_after["pycache_dir_count"]}
    print(json.dumps(result, sort_keys=True))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
