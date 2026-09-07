#!/usr/bin/env python3
"""Verify the immutable Rebaseline V5 historical provenance supplement."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


REPOSITORY = "asamiibra/AMEC-Permits-Ops"
R13_SHA = "96c4b90968754efd8e5998cd1b1793b67c23d2bc"
R13_PARENT_SHA = "dd24e1c9ac65d6137614252f821d3a3e6b1263c2"
R13_TREE_SHA = "c547005d3a18a9c71965a40a5327aa46edb28c6f"
R13_VERSIONS_TREE_SHA = "4b5df36eaba0816df17bb2078958da946a6442d6"
ACCEPTED_SHA = "8dfcc55a48f44ba88ee5cb9fb9c0c7dd096f42dd"
ARCHIVE_ROOT = "backend/migrations/history/postgresql_r13_0001_0059"
SOURCE_ROOT = "backend/migrations/versions"
LEGACY_HEAD = "0059_entra_user_identity"


def git(repo: Path, *args: str, text: bool = True) -> str | bytes:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=text,
    )
    return result.stdout


def git_exists(repo: Path, spec: str) -> bool:
    return subprocess.run(
        ["git", "cat-file", "-e", spec],
        cwd=repo,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


def git_bytes(repo: Path, commit: str, path: str) -> bytes:
    return git(repo, "show", f"{commit}:{path}", text=False)  # type: ignore[return-value]


def literal_assignments(source: bytes) -> dict[str, Any]:
    tree = ast.parse(source.decode("utf-8"), type_comments=True)
    values: dict[str, Any] = {}
    for node in tree.body:
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets = node.targets
            value = node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
            value = node.value
        else:
            continue
        for target in targets:
            if isinstance(target, ast.Name) and target.id in {"revision", "down_revision"}:
                values[target.id] = ast.literal_eval(value)
    if "revision" not in values or "down_revision" not in values:
        raise ValueError("migration is missing literal revision metadata")
    return values


def down_revision_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (tuple, list)) and all(isinstance(item, str) for item in value):
        return list(value)
    raise ValueError(f"unsupported down_revision value: {value!r}")


def tree_paths(repo: Path, commit: str, root: str) -> list[str]:
    output = git(repo, "ls-tree", "-r", "--name-only", commit, "--", root)
    return [line for line in str(output).splitlines() if line]


def build_manifest(repo: Path) -> dict[str, Any]:
    if not git_exists(repo, f"{R13_SHA}^{{commit}}"):
        raise ValueError("R13 source commit is missing")
    if not git_exists(repo, f"{ACCEPTED_SHA}^{{commit}}"):
        raise ValueError("accepted rebaseline commit is missing")
    if git(repo, "rev-parse", f"{R13_SHA}^").strip() != R13_PARENT_SHA:
        raise ValueError("R13 parent mismatch")
    if git(repo, "rev-parse", f"{R13_SHA}^{{tree}}").strip() != R13_TREE_SHA:
        raise ValueError("R13 tree mismatch")
    if git(repo, "rev-parse", f"{R13_SHA}:{SOURCE_ROOT}").strip() != R13_VERSIONS_TREE_SHA:
        raise ValueError("R13 versions tree mismatch")

    source_paths = tree_paths(repo, R13_SHA, SOURCE_ROOT)
    archive_paths = tree_paths(repo, ACCEPTED_SHA, ARCHIVE_ROOT)
    source_files = [path for path in source_paths if path.endswith(".py")]
    archive_files = [path for path in archive_paths if path.endswith(".py")]
    if len(source_files) != 59 or len(archive_files) != 59:
        raise ValueError(f"migration count mismatch: source={len(source_files)} archive={len(archive_files)}")

    manifest_present = git_exists(repo, f"{ACCEPTED_SHA}:{ARCHIVE_ROOT}/manifest.json")
    versions_present = bool(git(repo, "ls-tree", "-d", "--name-only", ACCEPTED_SHA, f"{ARCHIVE_ROOT}/versions").strip())
    if manifest_present or versions_present:
        raise ValueError("accepted historical archive unexpectedly contains V4 layout markers")

    entries: list[dict[str, Any]] = []
    revisions: list[str] = []
    archived_names = {Path(path).name for path in archive_files}
    for ordinal, source_path in enumerate(sorted(source_files), start=1):
        basename = Path(source_path).name
        archived_path = f"{ARCHIVE_ROOT}/{basename}"
        required_path = f"{ARCHIVE_ROOT}/versions/{basename}"
        if basename not in archived_names or not git_exists(repo, f"{ACCEPTED_SHA}:{archived_path}"):
            raise ValueError(f"missing accepted archive migration: {basename}")
        source_bytes = git_bytes(repo, R13_SHA, source_path)
        archived_bytes = git_bytes(repo, ACCEPTED_SHA, archived_path)
        source_blob = str(git(repo, "rev-parse", f"{R13_SHA}:{source_path}")).strip()
        archived_blob = str(git(repo, "rev-parse", f"{ACCEPTED_SHA}:{archived_path}")).strip()
        metadata = literal_assignments(source_bytes)
        revision = metadata["revision"]
        if not isinstance(revision, str):
            raise ValueError(f"non-string revision in {source_path}")
        revisions.append(revision)
        entries.append(
            {
                "ordinal": ordinal,
                "original_path": source_path,
                "archived_path": archived_path,
                "v4_required_archived_path": required_path,
                "git_blob_sha": source_blob,
                "archived_git_blob_sha": archived_blob,
                "sha256": hashlib.sha256(source_bytes).hexdigest(),
                "archived_sha256": hashlib.sha256(archived_bytes).hexdigest(),
                "byte_identical": source_bytes == archived_bytes,
                "revision": revision,
                "down_revision": metadata["down_revision"],
            }
        )

    if len(set(revisions)) != 59:
        raise ValueError("duplicate migration revisions")
    down_revisions = {value for entry in entries for value in down_revision_values(entry["down_revision"])}
    heads = [revision for revision in revisions if revision not in down_revisions]
    if heads != [LEGACY_HEAD]:
        raise ValueError(f"unexpected migration heads: {heads!r}")
    if any(not entry["byte_identical"] or entry["git_blob_sha"] != entry["archived_git_blob_sha"] or entry["sha256"] != entry["archived_sha256"] for entry in entries):
        raise ValueError("historical migration byte parity failed")

    return {
        "accepted_8df_actual_archive_root": ARCHIVE_ROOT,
        "accepted_8df_manifest_present": False,
        "accepted_8df_versions_subdir_present": False,
        "accepted_rebaseline_sha": ACCEPTED_SHA,
        "entries": entries,
        "format_version": "1.0.0",
        "legacy_head": LEGACY_HEAD,
        "legacy_migration_count": 59,
        "original_v4_physical_layout_conforms": False,
        "rebaseline_acceptance_revoked": False,
        "remediation_class": "SUPPLEMENTAL_PROVENANCE_WITHOUT_HISTORY_REWRITE",
        "repository": REPOSITORY,
        "schema_runtime_rerun_required": False,
        "source_branch": "azure-a1-f1-batch3a-step4c",
        "source_parent_sha": R13_PARENT_SHA,
        "source_sha": R13_SHA,
        "source_tree_sha": R13_TREE_SHA,
        "source_versions_tree_sha": R13_VERSIONS_TREE_SHA,
        "v4_required_versions_subdir": f"{ARCHIVE_ROOT}/versions",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--evidence-out", type=Path)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    expected = build_manifest(repo)
    expected_bytes = (json.dumps(expected, indent=2, sort_keys=True) + "\n").encode("utf-8")
    actual_bytes = args.manifest.read_bytes()
    if actual_bytes != expected_bytes:
        raise SystemExit("supplemental manifest is not the deterministic expected output")
    entries = expected["entries"]
    evidence = {
        "result": "PASS",
        "repository": REPOSITORY,
        "source_sha": R13_SHA,
        "accepted_rebaseline_sha": ACCEPTED_SHA,
        "accepted_8df_manifest_present": False,
        "accepted_8df_versions_subdir_present": False,
        "original_v4_physical_layout_conforms": False,
        "supplement_manifest_entry_count": len(entries),
        "supplement_duplicate_original_path_count": len(entries) - len({entry["original_path"] for entry in entries}),
        "supplement_duplicate_archived_path_count": len(entries) - len({entry["archived_path"] for entry in entries}),
        "supplement_duplicate_revision_count": len(entries) - len({entry["revision"] for entry in entries}),
        "supplement_missing_revision_count": sum("revision" not in entry for entry in entries),
        "supplement_head": LEGACY_HEAD,
        "supplement_git_blob_parity_verified": sum(entry["git_blob_sha"] == entry["archived_git_blob_sha"] for entry in entries),
        "supplement_sha256_parity_verified": sum(entry["sha256"] == entry["archived_sha256"] for entry in entries),
        "supplement_byte_identical_count": sum(entry["byte_identical"] for entry in entries),
        "supplement_byte_mismatch_count": sum(not entry["byte_identical"] for entry in entries),
        "supplemental_provenance_closure": "PASS",
    }
    if args.evidence_out:
        args.evidence_out.parent.mkdir(parents=True, exist_ok=True)
        args.evidence_out.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("SUPPLEMENTAL_PROVENANCE_CLOSURE=PASS")
    print("SUPPLEMENT_MANIFEST_ENTRY_COUNT=59")
    print("SUPPLEMENT_GIT_BLOB_PARITY_VERIFIED=59")
    print("SUPPLEMENT_SHA256_PARITY_VERIFIED=59")
    print("SUPPLEMENT_BYTE_IDENTICAL_COUNT=59")
    print("SUPPLEMENT_BYTE_MISMATCH_COUNT=0")
    print("SUPPLEMENT_HEAD=0059_entra_user_identity")
    print("ORIGINAL_V4_PHYSICAL_ARCHIVE_LAYOUT_CONFORMS=false")
    return 0


if __name__ == "__main__":
    main()
