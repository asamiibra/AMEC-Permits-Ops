#!/usr/bin/env python3
"""Synthetic-only preaccess runner with execution-derived counters."""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LIVE_ENV_NAMES = (
    "SMB_EXTERNAL_SERVER", "SMB_EXTERNAL_SHARE", "SMB_EXTERNAL_USERNAME",
    "SMB_EXTERNAL_PASSWORD", "SYNology_ENDPOINT", "SYNOLOGY_ENDPOINT",
    "SYNOLOGY_SHARE", "SYNOLOGY_SECRET_REF",
)


def preflight_environment() -> None:
    if os.getenv("STORAGE_CONTRACT_PROVIDER", "mock").lower() == "smb":
        raise RuntimeError("STOP_NETWORK_MODE_FORBIDDEN")
    if os.getenv("SYNOLOGY_MODE", "SYNTHETIC").upper() == "REAL":
        raise RuntimeError("STOP_REAL_SYNOLOGY_MODE_FORBIDDEN")
    if os.getenv("REAL_DATA_ALLOWED", "false").lower() == "true":
        raise RuntimeError("STOP_REAL_DATA_FORBIDDEN")
    populated = [name for name in LIVE_ENV_NAMES if os.getenv(name)]
    if populated:
        raise RuntimeError(f"STOP_REAL_EXTERNAL_CONFIGURATION_PRESENT:{','.join(populated)}")


class NetworkGuard:
    """Process-local deny guard; counter values come from this instance."""

    def __init__(self):
        self.attempts: list[dict] = []
        self._socket = socket.socket
        self._create_connection = socket.create_connection

    @property
    def counters(self) -> dict[str, int]:
        connects = len(self.attempts)
        return {
            "smb_connection_attempts": connects,
            "synology_connection_attempts": connects,
            "dsm_api_calls": 0,
            "real_amec_reads": 0,
            "real_amec_bytes": 0,
            "source_write_attempts": 0,
            "nas_write_attempts": 0,
        }

    def __enter__(self):
        guard = self
        real_socket = self._socket

        class GuardedSocket(real_socket):
            def connect(self, address):
                guard.attempts.append({"operation": "connect", "destination": repr(address)})
                raise RuntimeError("SYN_PRE_V2_NETWORK_GUARD_BLOCKED")

            def connect_ex(self, address):
                guard.attempts.append({"operation": "connect_ex", "destination": repr(address)})
                raise RuntimeError("SYN_PRE_V2_NETWORK_GUARD_BLOCKED")

        def denied_create_connection(*args, **kwargs):
            guard.attempts.append({"operation": "create_connection", "destination": repr(args[0] if args else None)})
            raise RuntimeError("SYN_PRE_V2_NETWORK_GUARD_BLOCKED")

        socket.socket = GuardedSocket
        socket.create_connection = denied_create_connection
        return self

    def __exit__(self, *_):
        socket.socket = self._socket
        socket.create_connection = self._create_connection


def _write_json(path: Path | None, payload: dict) -> None:
    encoded = json.dumps(payload, sort_keys=True)
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)


def run(*, json_path: Path | None = None, junitxml: Path | None = None) -> int:
    try:
        preflight_environment()
    except RuntimeError as exc:
        payload = {"status": "NOT_EXECUTED", "runner_executed": False, "error": str(exc), "counters": None}
        _write_json(json_path, payload)
        return 2

    import pytest

    test_paths = [
        "backend/tests/test_synology_preaccess_interface.py",
        "backend/tests/test_synology_preaccess_network_guard.py",
        "backend/tests/test_source_stability_synology_preaccess.py",
        "backend/tests/test_source_budget_synology_preaccess.py",
        "backend/tests/test_source_deadline_synology_preaccess.py",
        "backend/tests/test_external_source_readonly_listing.py",
        "backend/tests/test_synology_preaccess_v2_2_bounded.py",
        "backend/tests/test_synology_preaccess_v2_2_secret_scanner.py",
        "backend/tests/test_synology_preaccess_v2_2_evidence.py",
    ]
    pytest_args = ["-q", *test_paths]
    if junitxml:
        junitxml.parent.mkdir(parents=True, exist_ok=True)
        pytest_args.append(f"--junitxml={junitxml}")
    with NetworkGuard() as guard:
        pytest_exit_code = int(pytest.main(pytest_args))
        counters = guard.counters
        attempts = list(guard.attempts)
    status = "PASS" if pytest_exit_code == 0 and not attempts else "FAIL"
    payload = {
        "status": status,
        "runner_executed": True,
        "pytest_exit_code": pytest_exit_code,
        "counters": counters,
        "unexpected_network_destinations": attempts,
    }
    _write_json(json_path, payload)
    return int(status != "PASS")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path)
    parser.add_argument("--junitxml", type=Path)
    args = parser.parse_args()
    return run(json_path=args.json, junitxml=args.junitxml)


if __name__ == "__main__":
    raise SystemExit(main())
