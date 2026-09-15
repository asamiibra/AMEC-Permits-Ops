from types import ModuleType
import sys

from backend.app.services.upload_scanner import ClamAVUploadScanner, configured_upload_scanner


def _fake_clamd(response, *, ping="PONG", version="ClamAV 1.0"):
    module = ModuleType("clamd")

    class Client:
        def __init__(self, host, port):
            assert host == "127.0.0.1"
            assert port == 3310

        def instream(self, _content):
            return response

        def ping(self):
            return ping

        def version(self):
            return version

    module.ClamdNetworkSocket = Client
    module.ClamdUnixSocket = lambda _path: Client("127.0.0.1", 3310)
    return module


def test_configured_clamav_scanner_uses_loopback_network_socket(monkeypatch):
    monkeypatch.setenv("CONTRACT_UPLOAD_SCANNER", "clamav")
    monkeypatch.setenv("CONTRACT_UPLOAD_CLAMAV_HOST", "127.0.0.1")
    monkeypatch.setenv("CONTRACT_UPLOAD_CLAMAV_PORT", "3310")
    monkeypatch.setitem(sys.modules, "clamd", _fake_clamd({"stream": ("OK", None)}))

    scanner = configured_upload_scanner(synthetic=True)
    assert isinstance(scanner, ClamAVUploadScanner)
    assert scanner.health() is True
    assert scanner.scan(b"clean", "clean.pdf", "application/pdf").state == "CLEAN"


def test_clamav_results_are_fail_closed_and_health_is_bounded(monkeypatch):
    monkeypatch.setenv("CONTRACT_UPLOAD_CLAMAV_HOST", "127.0.0.1")
    monkeypatch.setenv("CONTRACT_UPLOAD_CLAMAV_PORT", "3310")
    monkeypatch.setitem(sys.modules, "clamd", _fake_clamd({"stream": ("FOUND", "EICAR-Test")}))
    scanner = ClamAVUploadScanner()
    assert scanner.scan(b"eicar", "sample.txt", "text/plain").state == "MALICIOUS"
    assert scanner.health() is True

    monkeypatch.setitem(sys.modules, "clamd", _fake_clamd({"unexpected": True}))
    assert scanner.scan(b"fault", "fault.txt", "text/plain").state == "SCAN_ERROR"

    monkeypatch.setitem(sys.modules, "clamd", _fake_clamd({"stream": ("OK", None)}, version=""))
    assert scanner.health() is False
