from types import SimpleNamespace

from fastapi.testclient import TestClient

from backend.app import main


def test_live_does_not_need_database(monkeypatch):
    def fail():
        raise AssertionError("database must not be queried")
    monkeypatch.setattr(main, "engine", SimpleNamespace(connect=fail))
    response = TestClient(main.app).get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_ready_reports_bounded_failure(monkeypatch):
    class Broken:
        def connect(self):
            raise RuntimeError("offline")
    monkeypatch.setattr(main, "engine", Broken())
    response = TestClient(main.app).get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "failure_class": "MIGRATION_NOT_READY"}
