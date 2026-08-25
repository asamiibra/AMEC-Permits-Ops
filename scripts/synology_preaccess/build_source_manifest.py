#!/usr/bin/env python3
"""Record exact Git blob identity for source paths cited by evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo_root.resolve()
    names = git(repo, "ls-tree", "-r", "--name-only", args.candidate_sha).splitlines()
    prefixes = ("backend/app/storage/", "backend/tests/test_", "scripts/synology_preaccess/", "contracts/amec/synology_preaccess/")
    rows = []
    for path in names:
        if not path.startswith(prefixes):
            continue
        blob_sha = git(repo, "rev-parse", f"{args.candidate_sha}:{path}")
        content = subprocess.check_output(["git", "cat-file", "blob", blob_sha], cwd=repo)
        rows.append({"repo": "asamiibra/AMEC-Permits-Ops", "candidate_sha": args.candidate_sha, "path": path, "blob_sha": blob_sha, "sha256": hashlib.sha256(content).hexdigest()})
    payload = {"repo": "asamiibra/AMEC-Permits-Ops", "candidate_sha": args.candidate_sha, "rows": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"candidate_sha": args.candidate_sha, "row_count": len(rows), "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
