"""Idempotently reconcile preprod acceptance Clients with the production boundary.

This is an internal, authorized acceptance-data operation. It is deliberately
not exposed as an HTTP route and refuses to run outside the synthetic Azure
preprod envelope. Fixture provenance remains in the seeded Proposal/domain
records; canonical Client identity fields stay free of synthetic governance
markers so the same production enforcement used for real records can run.
"""

from __future__ import annotations

from backend.app.config.settings import get_settings
from backend.app.db import SessionLocal
from backend.app.models import ClientAccount


CLIENT_RECONCILIATION = {
    "SYN-CLIENT-001": "PO-ACCEPT-001",
    "AMEC-SYN-CLIENT-0002": "PO-ACCEPT-002",
    "AMEC-SYN-CLIENT-0003": "PO-ACCEPT-003",
    "OWNER-TEST-PROPOSAL-CLIENT": "PO-OWNER-004",
}


def reconcile() -> dict[str, object]:
    settings = get_settings()
    if settings.app_env.upper() != "AZURE-PREPROD":
        raise RuntimeError("Acceptance Client reconciliation requires APP_ENV=AZURE-PREPROD")
    if not settings.synthetic_only:
        raise RuntimeError("Acceptance Client reconciliation requires SYNTHETIC_ONLY=true")
    if settings.real_data_allowed:
        raise RuntimeError("Acceptance Client reconciliation requires REAL_DATA_ALLOWED=false")
    if not settings.owner_test_mode:
        raise RuntimeError("Acceptance Client reconciliation requires OWNER_TEST_MODE=true")

    changed: list[dict[str, str]] = []
    with SessionLocal() as db:
        for old_reference, new_reference in CLIENT_RECONCILIATION.items():
            client = db.query(ClientAccount).filter(ClientAccount.client_reference == old_reference).one_or_none()
            if client is None:
                continue
            client.client_reference = new_reference
            client.commercial_registration_number = f"{new_reference}-CR"
            client.data_classification = "INTERNAL_TEST"
            changed.append({"id": client.id, "client_reference": new_reference})
        db.commit()
    return {"status": "APPLIED", "changed": changed, "owner_test_only": True, "real_data_count": 0}


if __name__ == "__main__":
    print(reconcile())
