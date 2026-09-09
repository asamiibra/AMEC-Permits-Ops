from fastapi import APIRouter, Depends

from ..auth.bridge import BridgeIdentity, current_bridge_identity
from ..config.settings import get_settings


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
