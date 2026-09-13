"""Shared persisted scoped-capability resolution for protected Finance work."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api.dependencies import AuthenticatedPrincipal
from ..models import Role, ScopedCapabilityAssignment, User


@dataclass(frozen=True)
class BillingAuthorizationContext:
    office_id: str | None = None
    client_account_id: str | None = None
    project_id: str | None = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _effective(value: datetime | None, now: datetime) -> bool:
    if value is None:
        return True
    observed = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    return observed <= now


def _not_expired(value: datetime | None, now: datetime) -> bool:
    if value is None:
        return True
    observed = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    return observed >= now


def assignment_matches(assignment: ScopedCapabilityAssignment, context: BillingAuthorizationContext) -> bool:
    """Match only explicit assignment dimensions; omitted dimensions are broad within the supplied context."""
    if not any((assignment.office_id, assignment.client_account_id, assignment.project_id)):
        return False
    if assignment.office_id and assignment.office_id != context.office_id:
        return False
    if assignment.client_account_id and assignment.client_account_id != context.client_account_id:
        return False
    if assignment.project_id and assignment.project_id != context.project_id:
        return False
    if assignment.project_id and not context.project_id:
        return False
    if assignment.client_account_id and not context.client_account_id:
        return False
    if assignment.office_id and not context.office_id:
        return False
    return True


def active_assignments(
    db: Session,
    principal: AuthenticatedPrincipal,
    *,
    capability_code: str | None = None,
) -> list[ScopedCapabilityAssignment]:
    if not principal.user_id:
        return []
    statement = select(ScopedCapabilityAssignment).where(
        ScopedCapabilityAssignment.user_id == principal.user_id,
        ScopedCapabilityAssignment.status == "ACTIVE",
    )
    if capability_code:
        statement = statement.where(ScopedCapabilityAssignment.capability_code == capability_code)
    return list(db.scalars(statement).all())


def resolve_billing_capability(
    db: Session,
    principal: AuthenticatedPrincipal,
    *,
    capability_code: str,
    allowed_roles: Iterable[Role],
    context: BillingAuthorizationContext,
    request: Request | None = None,
) -> ScopedCapabilityAssignment:
    """Authorize a Billing mutation from identity + role constraint + active scoped grant."""
    if principal.role not in set(allowed_roles):
        raise HTTPException(403, {"code": "CAPABILITY_DENIED", "capability": capability_code})
    if not principal.user_id:
        raise HTTPException(403, {"code": "SCOPED_FINANCE_CAPABILITY_REQUIRED", "capability": capability_code})
    user = db.get(User, principal.user_id)
    if not user or not user.active:
        raise HTTPException(403, {"code": "SCOPED_FINANCE_CAPABILITY_REQUIRED", "capability": capability_code})
    now = _utc_now()
    matches = [
        item for item in active_assignments(db, principal, capability_code=capability_code)
        if _effective(item.effective_from, now) and _not_expired(item.effective_to, now) and assignment_matches(item, context)
    ]
    if not matches:
        raise HTTPException(403, {"code": "SCOPED_FINANCE_CAPABILITY_REQUIRED", "capability": capability_code})
    # Prefer the narrowest applicable assignment when multiple explicit grants overlap.
    assignment = sorted(matches, key=lambda item: sum(bool(value) for value in (item.project_id, item.client_account_id, item.office_id)), reverse=True)[0]
    if request is not None:
        request.state.billing_authorization_assignment_id = assignment.id
        request.state.billing_authorization_capability = capability_code
    return assignment


def effective_billing_capabilities(
    db: Session,
    principal: AuthenticatedPrincipal,
    *,
    context: BillingAuthorizationContext,
) -> set[str]:
    """Return only capabilities explicitly assigned in the current context."""
    now = _utc_now()
    return {
        item.capability_code
        for item in active_assignments(db, principal)
        if _effective(item.effective_from, now) and _not_expired(item.effective_to, now) and assignment_matches(item, context)
    }
