from typing import Any
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from ..models import AuditEvent


def audit(db: Session, *, correlation_id: str, event_type: str, entity_type: str, entity_id: str,
          actor_id: str | None = None, before: Any = None, after: Any = None,
          metadata: dict[str, Any] | None = None,
          actor_type: str = "DEV_USER") -> AuditEvent:
    try:
        from ..api.dependencies import authenticated_principal_context
        principal = authenticated_principal_context()
    except Exception:  # pragma: no cover - import safety for migration tooling
        principal = None
    principal_metadata = {
        "auth_mode": principal.auth_mode,
        "user_id": principal.user_id,
        "object_id": principal.object_id,
        "tenant_id": principal.tenant_id,
        "office_id": principal.office_id,
        "role": principal.role.value,
    } if principal else {}
    event = AuditEvent(correlation_id=correlation_id, actor_type=("ENTRA_USER" if principal and principal.auth_mode == "ENTRA" else actor_type), actor_id=actor_id,
                       event_type=event_type, entity_type=entity_type, entity_id=entity_id,
                       before_json=jsonable_encoder(before) if before is not None else None,
                       after_json=jsonable_encoder(after) if after is not None else None,
                       metadata_json=jsonable_encoder({**principal_metadata, **(metadata or {})}))
    db.add(event)
    db.flush()
    return event
