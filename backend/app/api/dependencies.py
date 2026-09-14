from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, Request
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
    # Display-only Entra claims. They are never consulted for authorization.
    display_name: str | None = None
    preferred_username: str | None = None


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
    x_dev_user: str | None = Header(
        default=None
    ),
    db: Session = Depends(get_db),
) -> AuthenticatedPrincipal:
    settings = get_settings()
    auth_mode = settings.auth_mode.upper()

    if auth_mode == "DEV_HEADER":
        role = _resolve_dev_role(x_dev_role)
        user = None
        # Direct unit calls may omit a dependency parameter and therefore
        # receive FastAPI's Header sentinel rather than the injected None.
        supplied_dev_user = x_dev_user if isinstance(x_dev_user, str) else None
        if supplied_dev_user:
            user = db.scalar(
                select(User).where(
                    (User.id == supplied_dev_user)
                    | (User.email == supplied_dev_user),
                    User.active.is_(True),
                )
            )
        elif x_dev_role is not None:
            # Synthetic DEV_HEADER callers historically supplied only a role.
            # Resolve that explicit role to the seeded synthetic identity so
            # scoped Finance authorization can remain fail-closed without
            # weakening the production Entra path.
            seeded_email_by_role = {
                Role.OWNER_SPONSOR: "owner@amec.synthetic",
                Role.SYSTEM_ADMIN: "admin@amec.synthetic",
                Role.PROCESS_CHAMPION: "champion@amec.synthetic",
                Role.REQUIREMENT_STEWARD: "steward@amec.synthetic",
                Role.RESPONSIBLE_ENGINEER: "engineer@amec.synthetic",
                Role.PERMIT_PREPARER: "preparer@amec.synthetic",
                Role.FINAL_SUBMITTER: "submitter@amec.synthetic",
            }
            seeded_email = seeded_email_by_role.get(role)
            if seeded_email:
                user = db.scalar(
                    select(User).where(
                        User.email == seeded_email,
                        User.active.is_(True),
                    )
                )
        if user is not None and user.role != role:
            raise HTTPException(
                status_code=403,
                detail="Development role does not match development user",
            )
        return AuthenticatedPrincipal(
            auth_mode="DEV_HEADER",
            role=role,
            user_id=user.id if user is not None else None,
            office_id=user.office_id if user is not None else None,
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
        display_name=identity.display_name,
        preferred_username=identity.preferred_username,
    )


def trusted_current_principal(
    request: Request,
    principal: AuthenticatedPrincipal = Depends(
        current_principal
    ),
    db: Session | None = Depends(get_db),
) -> AuthenticatedPrincipal:
    request.state.authenticated_principal = principal
    # current_principal may have materialized an Entra User row in the
    # request session.  Release that read transaction before a route is
    # allowed to perform any external provider work.  The isinstance guard
    # preserves direct unit-test calls that pass only request/principal.
    if isinstance(db, Session):
        db.rollback()
    return principal


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
