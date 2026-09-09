"""Fail-closed production bootstrap with zero synthetic writes.

Production startup must never seed demo users, projects, documents, or
authority fixtures. This command validates the already-provisioned database
head and runtime storage contract, then records only a bounded status line.
"""

from __future__ import annotations

import json
import sys

from .config.settings import get_settings
from .db import verify_database_migration_head


def run_production_bootstrap() -> str:
    settings = get_settings()
    if settings.app_env.upper() != "PROD":
        raise RuntimeError("Production bootstrap requires APP_ENV=PROD.")
    if settings.synthetic_only:
        raise RuntimeError("Production bootstrap requires SYNTHETIC_ONLY=false.")
    if settings.real_data_allowed:
        raise RuntimeError("Production bootstrap requires REAL_DATA_ALLOWED=false until canary authorization.")
    if settings.source_intake_mode.upper() != "BRIDGE":
        raise RuntimeError("Production bootstrap requires SOURCE_INTAKE_MODE=BRIDGE.")
    if settings.azure_direct_synology_smb:
        raise RuntimeError("Production bootstrap forbids direct Azure Synology SMB.")
    verify_database_migration_head()
    return "PRODUCTION_BOOTSTRAP_ZERO_SYNTHETIC_PASS"


def main() -> int:
    try:
        status = run_production_bootstrap()
    except Exception as exc:
        print(json.dumps({"event": "proposalops_production_bootstrap", "status": "FAILED", "error_class": type(exc).__name__}, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps({"event": "proposalops_production_bootstrap", "status": status, "synthetic_writes": 0, "dsm_contacts": 0, "real_source_reads": 0, "real_source_bytes": 0}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
