"""Clean confirmed synthetic browser/probe rows and seed the Owner demo library."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from backend.app.db import SessionLocal, engine  # noqa: E402
from backend.app.services.master_content import reconcile_owner_demo_dataset  # noqa: E402


def main() -> None:
    if engine.dialect.name != "postgresql":
        raise RuntimeError("Owner demo reconciliation requires PostgreSQL")
    with SessionLocal() as db:
        result = reconcile_owner_demo_dataset(db)
    print(json.dumps({"status": "APPLIED", "database": engine.url.render_as_string(hide_password=True), **result}, sort_keys=True))


if __name__ == "__main__":
    main()
