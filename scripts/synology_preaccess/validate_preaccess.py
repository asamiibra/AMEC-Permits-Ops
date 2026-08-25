#!/usr/bin/env python3
"""One-shot synthetic pre-access validation runner.

It installs a process-local network guard before importing/running the new
tests. It never constructs an SMB provider and rejects live configuration.
"""

from __future__ import annotations

import os
import socket
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


LIVE_ENV_NAMES = (
    "SMB_EXTERNAL_SERVER",
    "SMB_EXTERNAL_SHARE",
    "SMB_EXTERNAL_USERNAME",
    "SMB_EXTERNAL_PASSWORD",
    "SYNology_ENDPOINT",
    "SYNOLOGY_ENDPOINT",
    "SYNOLOGY_SHARE",
    "SYNOLOGY_SECRET_REF",
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
    def __init__(self):
        self.attempts: list[dict] = []
        self._socket = socket.socket
        self._create_connection = socket.create_connection

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


def run() -> int:
    preflight_environment()
    import pytest

    test_paths = [
        str(ROOT / "backend/tests/test_synology_preaccess_interface.py"),
        str(ROOT / "backend/tests/test_synology_preaccess_network_guard.py"),
        str(ROOT / "backend/tests/test_source_stability_synology_preaccess.py"),
        str(ROOT / "backend/tests/test_source_budget_synology_preaccess.py"),
        str(ROOT / "backend/tests/test_source_deadline_synology_preaccess.py"),
        str(ROOT / "backend/tests/test_external_source_readonly_listing.py"),
    ]
    with NetworkGuard() as guard:
        result = pytest.main(["-q", *test_paths])
    print(f"SYNTHETIC_PREACCESS_RESULT={'PASS' if result == 0 and not guard.attempts else 'FAIL'}")
    print(f"SMB_CONNECTION_ATTEMPTS={len(guard.attempts)}")
    print("SYNOLOGY_CONNECTION_ATTEMPTS=0")
    print("REAL_AMEC_READS=0")
    print("REAL_AMEC_BYTES=0")
    return int(result != 0 or bool(guard.attempts))


if __name__ == "__main__":
    raise SystemExit(run())
