from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth.entra import (
    EntraAuthenticationError,
    get_entra_validator,
)
from ..config.settings import get_settings
from ..db import get_db
from ..models import Role, User


bearer_scheme = HTTPBearer(auto_error=False)

_DEV_ROLE_ALIASES = {
    "COMMERCIAL_APPROVER": "PROCESS_CHAMPION",
    "BD_USER": "PROCESS_CHAMPION",
    "AUTHORIZED_ENGINEER": "RESPONSIBLE_ENGINEER",
    "ENGINEERING": "RESPONSIBLE_ENGINEER",
}


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    auth_mode: str
    role: Role
    user_id: str | None = None
    office_id: str | None = None
    tenant_id: str | None = None
    object_id: str | None = None


def _resolve_dev_role(
    x_dev_role: str | None,
) -> Role:
    role_name = _DEV_ROLE_ALIASES.get(
        x_dev_role or "SYSTEM_ADMIN",
        x_dev_role or "SYSTEM_ADMIN",
    )

    try:
        return Role(role_name)
    except ValueError as exc:
        raise HTTPException(
            status_code=403,
            detail="Unknown development role",
        ) from exc


def current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
    x_dev_role: str | None = Header(
        default="SYSTEM_ADMIN"
    ),
    db: Session = Depends(get_db),
) -> AuthenticatedPrincipal:
    settings = get_settings()
    auth_mode = settings.auth_mode.upper()

    if auth_mode == "DEV_HEADER":
        return AuthenticatedPrincipal(
            auth_mode="DEV_HEADER",
            role=_resolve_dev_role(x_dev_role),
        )

    if auth_mode != "ENTRA":
        raise HTTPException(
            status_code=500,
            detail="Authentication mode is not configured",
        )

    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
        or not credentials.credentials.strip()
    ):
        raise HTTPException(
            status_code=401,
            detail="Bearer token is required",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    try:
        identity = get_entra_validator().validate(
            credentials.credentials
        )
    except EntraAuthenticationError as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid bearer token",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        ) from exc

    user = db.scalar(
        select(User).where(
            User.entra_object_id
            == identity.object_id
        )
    )

    if user is None or not user.active:
        raise HTTPException(
            status_code=403,
            detail="ProposalOps access is not authorized",
        )

    return AuthenticatedPrincipal(
        auth_mode="ENTRA",
        role=user.role,
        user_id=user.id,
        office_id=user.office_id,
        tenant_id=identity.tenant_id,
        object_id=identity.object_id,
    )


def current_user_role(
    principal: AuthenticatedPrincipal = Depends(
        current_principal
    ),
) -> Role:
    return principal.role


def require_roles(*roles: Role):
    def dependency(
        role: Role = Depends(current_user_role),
    ) -> Role:
        if role not in roles:
            raise HTTPException(
                status_code=403,
                detail="Role is not authorized for this action",
            )
        return role

    return dependency
