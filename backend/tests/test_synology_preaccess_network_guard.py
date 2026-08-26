from __future__ import annotations

import socket

import pytest


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    calls = []
    real_socket = socket.socket

    class GuardedSocket(real_socket):
        def connect(self, address):
            calls.append(("connect", address))
            raise AssertionError("SYN_PRE_V2_NETWORK_GUARD_BLOCKED")

        def connect_ex(self, address):
            calls.append(("connect_ex", address))
            raise AssertionError("SYN_PRE_V2_NETWORK_GUARD_BLOCKED")

    def denied_create_connection(*args, **kwargs):
        calls.append(("create_connection", args[0] if args else None))
        raise AssertionError("SYN_PRE_V2_NETWORK_GUARD_BLOCKED")

    monkeypatch.setattr(socket, "socket", GuardedSocket)
    monkeypatch.setattr(socket, "create_connection", denied_create_connection)
    yield calls
    assert calls == []


def test_network_guard_is_installed_and_no_source_call_is_attempted(no_network):
    assert no_network == []
