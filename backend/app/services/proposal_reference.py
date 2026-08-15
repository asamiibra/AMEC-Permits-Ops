"""Concurrency-safe provisional Proposal reference allocation."""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import MasterContentReferenceSequence, Opportunity


def allocate_proposal_reference(db: Session) -> str:
    sequence = db.scalar(select(MasterContentReferenceSequence).where(MasterContentReferenceSequence.content_type == "PROPOSAL_REFERENCE", MasterContentReferenceSequence.scope == "GLOBAL", MasterContentReferenceSequence.active.is_(True)).with_for_update())
    if not sequence:
        sequence = MasterContentReferenceSequence(content_type="PROPOSAL_REFERENCE", prefix="AMEC-SYN-PROP", padding=4, scope="GLOBAL", active=True, current_value=0)
        db.add(sequence)
        db.flush()
    pattern = re.compile(rf"^{re.escape(sequence.prefix)}-(\d+)$")
    existing_max = 0
    for reference in db.scalars(select(Opportunity.opportunity_reference)).all():
        match = pattern.match(reference or "")
        if match:
            existing_max = max(existing_max, int(match.group(1)))
    sequence.current_value = max(sequence.current_value, existing_max) + 1
    db.flush()
    return f"{sequence.prefix}-{sequence.current_value:0{sequence.padding}d}"
