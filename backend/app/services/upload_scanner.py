"""Fail-closed upload scanning boundary for Contract evidence."""

from __future__ import annotations

from dataclasses import dataclass
import io
import os
from typing import Protocol


SCAN_STATES = {"CLEAN", "MALICIOUS", "SCAN_ERROR", "SCANNER_UNAVAILABLE"}


@dataclass(frozen=True)
class ScanResult:
    state: str
    provider: str
    detail: str | None = None


class UploadScanner(Protocol):
    provider: str

    def scan(self, content: bytes, filename: str, mime_type: str) -> ScanResult: ...

    def health(self) -> bool: ...


class SyntheticUploadScanner:
    provider = "synthetic-explicit"

    def scan(self, content: bytes, filename: str, mime_type: str) -> ScanResult:
        if b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE" in content:
            return ScanResult("MALICIOUS", self.provider, "synthetic malware test signature")
        return ScanResult("CLEAN", self.provider)

    def health(self) -> bool:
        return True


class ClamAVUploadScanner:
    provider = "clamav"

    def scan(self, content: bytes, filename: str, mime_type: str) -> ScanResult:
        try:
            import clamd
            host = os.getenv("CONTRACT_UPLOAD_CLAMAV_HOST", "127.0.0.1")
            port = int(os.getenv("CONTRACT_UPLOAD_CLAMAV_PORT", "3310"))
            socket_path = os.getenv("CONTRACT_UPLOAD_CLAMAV_SOCKET", "")
            client = (
                clamd.ClamdUnixSocket(socket_path)
                if socket_path
                else clamd.ClamdNetworkSocket(host=host, port=port)
            )
            response = client.instream(io.BytesIO(content))
        except Exception as exc:  # unavailable and scanner errors are distinct from CLEAN
            return ScanResult("SCANNER_UNAVAILABLE", self.provider, type(exc).__name__)
        if not isinstance(response, dict) or response.get("stream") is None:
            return ScanResult("SCAN_ERROR", self.provider, "invalid scanner response")
        state, detail = response["stream"]
        if str(state).upper() == "OK":
            return ScanResult("CLEAN", self.provider)
        if str(state).upper() == "FOUND":
            return ScanResult("MALICIOUS", self.provider, str(detail))
        return ScanResult("SCAN_ERROR", self.provider, str(detail))

    def health(self) -> bool:
        try:
            import clamd
            host = os.getenv("CONTRACT_UPLOAD_CLAMAV_HOST", "127.0.0.1")
            port = int(os.getenv("CONTRACT_UPLOAD_CLAMAV_PORT", "3310"))
            socket_path = os.getenv("CONTRACT_UPLOAD_CLAMAV_SOCKET", "")
            client = (
                clamd.ClamdUnixSocket(socket_path)
                if socket_path
                else clamd.ClamdNetworkSocket(host=host, port=port)
            )
            return bool(client.ping()) and bool(client.version())
        except Exception:
            return False


def configured_upload_scanner(*, synthetic: bool) -> UploadScanner:
    if os.getenv("CONTRACT_UPLOAD_SCANNER", "").strip().lower() == "clamav":
        return ClamAVUploadScanner()
    if synthetic:
        return SyntheticUploadScanner()
    return ClamAVUploadScanner()
