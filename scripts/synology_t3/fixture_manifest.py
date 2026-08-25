from __future__ import annotations

import hashlib
import json
import argparse
import unicodedata
from pathlib import Path


def _repeat(label: str, size: int) -> bytes:
    seed = label.encode("utf-8")
    return (seed * ((size // len(seed)) + 1))[:size]


def fixture_bytes(relative: str) -> bytes:
    if relative == "basic/empty.bin":
        return b""
    if relative == "basic/small.txt":
        return b"ProposalOps SYN-T3 synthetic fixture; no client data.\n"
    if relative == "unicode/تقرير-قطر.txt":
        return "تقرير قطر — بيانات صناعية فقط\n".encode("utf-8")
    if relative == "unicode/AMEC-تقرير-mixed.txt":
        return "AMEC synthetic mixed Unicode — لا بيانات عميل\n".encode("utf-8")
    if relative == "unicode/nfc-synthetic.txt":
        return unicodedata.normalize("NFC", "Cafe\u0301 synthetic\n").encode("utf-8")
    if relative == "unicode/nfd-synthetic.txt":
        return unicodedata.normalize("NFD", "Café synthetic\n").encode("utf-8")
    if relative == "paths/spaces and punctuation/file.bin":
        return b"safe path with spaces and punctuation\n"
    if relative == "paths/deep/bounded/nested/level/file.bin":
        return b"bounded nested synthetic path\n"
    if relative == "range/range-4MiB.bin":
        return _repeat("SYN-T3-RANGE-4MIB-", 4 * 1024 * 1024)
    if relative == "stream/stream-8MiB.bin":
        return _repeat("SYN-T3-STREAM-8MIB-", 8 * 1024 * 1024)
    if relative == "mutation/change-during-read.bin":
        return b"SYN-T3-MUTATION-CANARY-V1\n"
    if relative == "acl/rename-me.bin":
        return b"SYN-T3-ACL-RENAME-CANARY\n"
    if relative == "acl/delete-me.bin":
        return b"SYN-T3-ACL-DELETE-CANARY\n"
    if relative.startswith("listing/entry-") and relative.endswith(".bin"):
        return (relative.removeprefix("listing/").removesuffix(".bin") + "\n").encode("ascii")
    raise KeyError(relative)


def fixture_paths() -> list[str]:
    paths = [
        "basic/empty.bin",
        "basic/small.txt",
        "unicode/تقرير-قطر.txt",
        "unicode/AMEC-تقرير-mixed.txt",
        "unicode/nfc-synthetic.txt",
        "unicode/nfd-synthetic.txt",
        "paths/spaces and punctuation/file.bin",
        "paths/deep/bounded/nested/level/file.bin",
        "range/range-4MiB.bin",
        "stream/stream-8MiB.bin",
        "mutation/change-during-read.bin",
        "acl/rename-me.bin",
        "acl/delete-me.bin",
    ]
    paths.extend(f"listing/entry-{index:04d}.bin" for index in range(1, 258))
    return paths


def build_fixture_manifest(output_root: Path) -> dict:
    staging_root = output_root / "cert" / "v1"
    staging_root.mkdir(parents=True, exist_ok=True)
    rows = []
    for relative in fixture_paths():
        content = fixture_bytes(relative)
        path = staging_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        rows.append({"relative_path": relative, "size": len(content), "sha256": hashlib.sha256(content).hexdigest(), "purpose": _purpose(relative)})
    return {"fixture_set": "SYN-T3-OWNER-DSM-V1", "root": "cert/v1", "staging_root": "cert/v1", "entry_count": len(rows), "entries": rows}


def _purpose(relative: str) -> str:
    if relative.startswith("listing/"):
        return "bounded directory listing and continuation"
    if relative.startswith("range/"):
        return "bounded range read"
    if relative.startswith("stream/"):
        return "bounded streaming read"
    if relative.startswith("unicode/"):
        return "Unicode and normalization behavior"
    if relative.startswith("acl/"):
        return "read-only ACL negative probe canary"
    if relative.startswith("mutation/"):
        return "optional source-change-during-read race"
    return "path, size, hash, and read-only source behavior"


def write_manifest(output_root: Path, output_path: Path) -> dict:
    manifest = build_fixture_manifest(output_root)
    output_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(write_manifest(args.output_root, args.manifest), ensure_ascii=False, sort_keys=True))
