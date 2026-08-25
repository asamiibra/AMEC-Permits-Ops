from __future__ import annotations

import contextlib
import socket
from dataclasses import dataclass, field
from typing import Iterator


class UnexpectedNetworkDestination(RuntimeError):
    pass


@dataclass
class NetworkGuard:
    allowed_host: str
    allowed_port: int = 445
    attempted: list[tuple[str, int]] = field(default_factory=list)

    def _target(self, address) -> tuple[str, int]:
        if not isinstance(address, tuple) or len(address) < 2:
            raise UnexpectedNetworkDestination("non-TCP destination")
        return str(address[0]), int(address[1])

    def check(self, address) -> None:
        target = self._target(address)
        self.attempted.append(target)
        if target != (self.allowed_host, self.allowed_port):
            raise UnexpectedNetworkDestination(f"unexpected network destination {target[0]}:{target[1]}")

    @property
    def unique_destinations(self) -> list[tuple[str, int]]:
        return sorted(set(self.attempted))

    @contextlib.contextmanager
    def installed(self) -> Iterator["NetworkGuard"]:
        original_connect = socket.socket.connect
        original_connect_ex = socket.socket.connect_ex
        original_getaddrinfo = socket.getaddrinfo

        def connect(sock, address):
            self.check(address)
            return original_connect(sock, address)

        def connect_ex(sock, address):
            self.check(address)
            return original_connect_ex(sock, address)

        def getaddrinfo(host, port, *args, **kwargs):
            if str(host) != self.allowed_host or int(port) != self.allowed_port:
                raise UnexpectedNetworkDestination(f"unexpected network resolution {host}:{port}")
            return original_getaddrinfo(host, port, *args, **kwargs)

        socket.socket.connect = connect
        socket.socket.connect_ex = connect_ex
        socket.getaddrinfo = getaddrinfo
        try:
            yield self
        finally:
            socket.socket.connect = original_connect
            socket.socket.connect_ex = original_connect_ex
            socket.getaddrinfo = original_getaddrinfo
