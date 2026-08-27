"""Standard-library T3-only path-scope validator used by CI and local tests."""

from __future__ import annotations

from pathlib import PurePosixPath

ALLOWED = (
    "scripts/synology_t3/",
    "contracts/amec/synology_t3/",
    "backend/tests/test_synology_t3_",
    ".github/workflows/synology-t3-handoff-build-r1.yml",
    ".github/workflows/synology-t3-handoff-build-r1r1.yml",
    ".github/workflows/synology-t3-handoff-build-r1r2.yml",
    ".github/workflows/synology-t3-handoff-build-r1r3.yml",
    ".github/workflows/synology-t3-handoff-build-r1r4.yml",
    ".github/workflows/synology-t3-handoff-build-r1r5.yml",
    ".github/workflows/synology-t3-handoff-build-r1r6r1.yml",
    ".github/workflows/synology-t3-handoff-build-r1r6r2.yml",
    ".github/workflows/synology-t3-handoff-build-r1r6r2r1.yml",
)
FORBIDDEN = (
    "backend/app/",
    "backend/requirements.txt",
    "frontend/",
    "scripts/phase5/",
    "contracts/amec/phase5/",
    "infra/",
    "deploy/",
    "migrations/",
)


def validate_paths(paths: list[str]) -> list[str]:
    errors: list[str] = []
    for raw in paths:
        path = PurePosixPath(raw)
        normalized = path.as_posix()
        if path.is_absolute() or ".." in path.parts:
            errors.append(f"unsafe path:{raw}")
            continue
        if any(normalized.startswith(prefix) for prefix in FORBIDDEN):
            errors.append(f"forbidden path:{raw}")
            continue
        if not (
            normalized.startswith("scripts/synology_t3/")
            or normalized.startswith("contracts/amec/synology_t3/")
            or normalized.startswith("backend/tests/test_synology_t3_")
            or normalized in set(ALLOWED[3:])
        ):
            errors.append(f"unexpected T3 path:{raw}")
    return errors


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args()
    errors = validate_paths(args.paths)
    if errors:
        print("\n".join(errors))
        raise SystemExit(1)
    print("T3_SCOPE_VALIDATION=PASS")
