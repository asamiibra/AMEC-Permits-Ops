from typing import Any
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from ..models import AuditEvent


def audit(db: Session, *, correlation_id: str, event_type: str, entity_type: str, entity_id: str,
          actor_id: str | None = None, before: Any = None, after: Any = None,
          metadata: dict[str, Any] | None = None) -> AuditEvent:
    event = AuditEvent(correlation_id=correlation_id, actor_type="DEV_USER", actor_id=actor_id,
                       event_type=event_type, entity_type=entity_type, entity_id=entity_id,
                       before_json=jsonable_encoder(before) if before is not None else None,
                       after_json=jsonable_encoder(after) if after is not None else None,
                       metadata_json=jsonable_encoder(metadata or {}))
    db.add(event)
    db.flush()
    return event
