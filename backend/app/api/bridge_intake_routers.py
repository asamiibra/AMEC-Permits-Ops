from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth.bridge import BridgeIdentity, current_bridge_identity
from ..config.settings import get_settings
from ..db import get_db
from ..schemas.bridge_intake import BridgePackageIn
from ..services.bridge_intake import ingest_bridge_package


router = APIRouter(prefix="/api/source-intake/bridge", tags=["source-intake-bridge"])


@router.get("/health")
def bridge_health(identity: BridgeIdentity = Depends(current_bridge_identity)):
    settings = get_settings()
    return {
        "status": "ready",
        "source_intake_mode": settings.source_intake_mode,
        "machine_client_id": identity.client_id,
        "audience": identity.audience,
        "dsm_contact": False,
        "real_source_read": False,
    }


@router.post("/packages")
def ingest_package(
    payload: BridgePackageIn,
    identity: BridgeIdentity = Depends(current_bridge_identity),
    db: Session = Depends(get_db),
):
    result = ingest_bridge_package(db, payload, identity, get_settings())
    db.commit()
    return result
