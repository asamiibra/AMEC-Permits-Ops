from fastapi import APIRouter, Depends

from .dependencies import AuthenticatedPrincipal, trusted_current_principal


router = APIRouter(prefix="/api/auth", tags=["auth-context"])


@router.get("/session")
def auth_session(
    principal: AuthenticatedPrincipal = Depends(trusted_current_principal),
):
    """Return only non-secret identity facts for the authenticated app shell."""
    return {
        "authenticated": True,
        "auth_mode": principal.auth_mode,
        "synthetic": True,
        "identity": {
            "user_id": principal.user_id,
            "tenant_id": principal.tenant_id,
            "object_id": principal.object_id,
            "role": principal.role.value,
        },
        "raw_auth_token_values": 0,
    }
