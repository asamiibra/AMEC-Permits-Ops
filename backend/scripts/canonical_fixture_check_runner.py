"""Clean, repository-native canonical fixture check command."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


DB_PATH = Path("canonical_fixture_check.db")
DB_PATH.unlink(missing_ok=True)
os.environ.update({"APP_ENV": "TEST", "SYNTHETIC_ONLY": "true", "DATABASE_URL": f"sqlite:///{DB_PATH}", "PYTHONPATH": "."})
subprocess.run(["python3", "-m", "alembic", "upgrade", "head"], check=True)
subprocess.run(["python3", "-m", "backend.app.seed.cli", "seed"], check=True)

from backend.scripts.canonical_fixture_check import check  # noqa: E402

print(check())
