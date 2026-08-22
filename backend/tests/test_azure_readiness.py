from types import SimpleNamespace

from fastapi.testclient import TestClient

from backend.app import main


class _Connection:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def exec_driver_sql(self, statement):
        assert statement == "select 1"


class _Engine:
    def connect(self):
        return _Connection()


class _HealthyStore:
    def health(self):
        return SimpleNamespace(state="HEALTHY")


def _ready_dependencies(monkeypatch, *, storage=None):
    monkeypatch.setattr(main, "engine", _Engine())
    monkeypatch.setattr(
        main,
        "repository_migration_head",
        lambda: "0059_entra_user_identity",
    )
    monkeypatch.setattr(
        main,
        "verify_database_migration_head",
        lambda: "0059_entra_user_identity",
    )
    from backend.app.storage import factory
    monkeypatch.setattr(
        factory,
        "create_binary_store",
        lambda: storage or _HealthyStore(),
    )


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
    assert response.json() == {"status": "not_ready", "failure_class": "DATABASE_UNAVAILABLE"}


def test_ready_returns_success_at_migration_head(monkeypatch):
    _ready_dependencies(monkeypatch)
    response = TestClient(main.app).get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_ready_reports_migration_mismatch(monkeypatch):
    _ready_dependencies(monkeypatch)
    monkeypatch.setattr(main, "repository_migration_head", lambda: "0058_previous")
    response = TestClient(main.app).get("/health/ready")
    assert response.status_code == 503
    assert response.json()["failure_class"] == "MIGRATION_NOT_READY"


def test_ready_reports_unhealthy_storage(monkeypatch):
    _ready_dependencies(
        monkeypatch,
        storage=SimpleNamespace(
            health=lambda: SimpleNamespace(state="UNAVAILABLE"),
        ),
    )
    response = TestClient(main.app).get("/health/ready")
    assert response.status_code == 503
    assert response.json()["failure_class"] == "STORAGE_UNAVAILABLE"


def test_ready_reports_invalid_configuration(monkeypatch):
    _ready_dependencies(monkeypatch)
    monkeypatch.setattr(
        type(main.settings),
        "validate_environment",
        lambda self: (_ for _ in ()).throw(ValueError("invalid")),
    )
    response = TestClient(main.app).get("/health/ready")
    assert response.status_code == 503
    assert response.json()["failure_class"] == "CONFIGURATION_INVALID"
