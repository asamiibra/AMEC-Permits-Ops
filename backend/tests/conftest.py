import os
from pathlib import Path
import pytest

os.environ.setdefault("APP_ENV", "TEST")
database_url = os.environ.setdefault("DATABASE_URL", "sqlite:///./test_permitops.db")
os.environ.setdefault("SYNTHETIC_ONLY", "true")

from backend.app.seed.cli import seed
from backend.app.main import app
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def seeded_environment():
    db_path = Path("test_permitops.db")
    if database_url.startswith("sqlite") and db_path.exists(): db_path.unlink()
    seed()
    yield
    if database_url.startswith("sqlite") and db_path.exists(): db_path.unlink()


@pytest.fixture
def client():
    with TestClient(app) as value:
        yield value
