import os
import atexit
import shutil
import tempfile
from pathlib import Path
import pytest

os.environ.setdefault("APP_ENV", "TEST")
_sqlite_test_path = Path(tempfile.gettempdir()) / f"permitops_pytest_{os.getpid()}.db"
database_url = os.environ.setdefault("DATABASE_URL", f"sqlite:///{_sqlite_test_path}")
os.environ.setdefault("SYNTHETIC_ONLY", "true")
_synthetic_test_root = Path(tempfile.mkdtemp(prefix="permitops-test-workspace-"))
os.environ.setdefault("SYNTHETIC_TEST_ROOT", str(_synthetic_test_root))
os.environ.setdefault("MOCK_SYSTEMS_ROOT", str(_synthetic_test_root / "mock-systems"))
atexit.register(lambda: shutil.rmtree(_synthetic_test_root, ignore_errors=True))

from backend.app.seed.cli import seed
from backend.app.main import app
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def seeded_environment():
    db_path = _sqlite_test_path
    if database_url.startswith("sqlite") and db_path.exists(): db_path.unlink()
    seed()
    yield
    if database_url.startswith("sqlite") and db_path.exists(): db_path.unlink()


@pytest.fixture
def client():
    with TestClient(app) as value:
        yield value
