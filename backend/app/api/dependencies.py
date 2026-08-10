from fastapi import Header, HTTPException
from ..models import Role


def current_user_role(x_dev_role: str | None = Header(default="SYSTEM_ADMIN")) -> Role:
    aliases = {"COMMERCIAL_APPROVER": "PROCESS_CHAMPION", "BD_USER": "PROCESS_CHAMPION", "AUTHORIZED_ENGINEER": "RESPONSIBLE_ENGINEER", "ENGINEERING": "RESPONSIBLE_ENGINEER"}
    try: return Role(aliases.get(x_dev_role or "SYSTEM_ADMIN", x_dev_role or "SYSTEM_ADMIN"))
    except ValueError: raise HTTPException(status_code=403, detail="Unknown development role")


def require_roles(*roles: Role):
    def dependency(role: Role = current_user_role):
        if role not in roles: raise HTTPException(status_code=403, detail="Role is not authorized for this action")
        return role
    return dependency
