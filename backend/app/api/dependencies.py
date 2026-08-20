from fastapi import Depends, Header, HTTPException

from ..config.settings import get_settings
from ..models import Role


def current_user_role(
    x_dev_role: str | None = Header(default="SYSTEM_ADMIN"),
) -> Role:
    settings = get_settings()

    # Development headers are valid only when the runtime explicitly
    # selects DEV_HEADER authentication. Azure preprod uses ENTRA and
    # therefore must fail closed until a validated Entra identity is supplied.
    if settings.auth_mode.upper() != "DEV_HEADER":
        raise HTTPException(
            status_code=401,
            detail="Development header authentication is disabled",
        )

    aliases = {
        "COMMERCIAL_APPROVER": "PROCESS_CHAMPION",
        "BD_USER": "PROCESS_CHAMPION",
        "AUTHORIZED_ENGINEER": "RESPONSIBLE_ENGINEER",
        "ENGINEERING": "RESPONSIBLE_ENGINEER",
    }

    role_name = aliases.get(
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
