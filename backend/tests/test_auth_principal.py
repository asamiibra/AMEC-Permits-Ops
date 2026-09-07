from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select

from backend.app.api import dependencies
from backend.app.auth.entra import (
    EntraAuthenticationError,
    EntraIdentity,
)
from backend.app.db import SessionLocal
from backend.app.models import Role, User


TENANT_ID = (
    "11111111-1111-4111-8111-111111111111"
)
OBJECT_ID = (
    "44444444-4444-4444-8444-444444444444"
)


class _StaticValidator:
    def __init__(
        self,
        identity: EntraIdentity,
    ):
        self.identity = identity

    def validate(
        self,
        token: str,
    ) -> EntraIdentity:
        return self.identity


class _RejectingValidator:
    def validate(
        self,
        token: str,
    ) -> EntraIdentity:
        raise EntraAuthenticationError(
            "synthetic invalid token"
        )


@pytest.fixture
def db():
    session = SessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _identity() -> EntraIdentity:
    return EntraIdentity(
        tenant_id=TENANT_ID,
        object_id=OBJECT_ID,
        subject="synthetic-subject",
        client_id=(
            "33333333-3333-4333-8333-"
            "333333333333"
        ),
        scopes=frozenset(
            {
                "access_as_user",
            }
        ),
    )


def _credentials() -> (
    HTTPAuthorizationCredentials
):
    return HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="synthetic-token",
    )


def _set_auth_mode(
    monkeypatch,
    mode: str,
) -> None:
    monkeypatch.setattr(
        dependencies,
        "get_settings",
        lambda: SimpleNamespace(
            auth_mode=mode
        ),
    )


def _set_validator(
    monkeypatch,
    validator,
) -> None:
    monkeypatch.setattr(
        dependencies,
        "get_entra_validator",
        lambda: validator,
    )


def _bind_engineer(
    db,
    *,
    active: bool = True,
) -> User:
    user = db.scalar(
        select(User).where(
            User.email
            == "engineer@amec.synthetic"
        )
    )

    assert user is not None

    user.entra_object_id = OBJECT_ID
    user.active = active
    db.flush()

    return user


def test_dev_header_defaults_to_system_admin(
    monkeypatch,
    db,
):
    _set_auth_mode(
        monkeypatch,
        "DEV_HEADER",
    )

    principal = dependencies.current_principal(
        credentials=None,
        x_dev_role=None,
        db=db,
    )

    assert (
        principal.auth_mode
        == "DEV_HEADER"
    )
    assert principal.role == Role.SYSTEM_ADMIN
    assert principal.user_id is None
    assert principal.object_id is None


def test_dev_header_alias_is_preserved(
    monkeypatch,
    db,
):
    _set_auth_mode(
        monkeypatch,
        "DEV_HEADER",
    )

    principal = dependencies.current_principal(
        credentials=None,
        x_dev_role="ENGINEERING",
        db=db,
    )

    assert (
        principal.role
        == Role.RESPONSIBLE_ENGINEER
    )


def test_unknown_dev_role_is_rejected(
    monkeypatch,
    db,
):
    _set_auth_mode(
        monkeypatch,
        "DEV_HEADER",
    )

    with pytest.raises(
        HTTPException
    ) as exc_info:
        dependencies.current_principal(
            credentials=None,
            x_dev_role="UNKNOWN_ROLE",
            db=db,
        )

    assert exc_info.value.status_code == 403


def test_entra_requires_bearer_token(
    monkeypatch,
    db,
):
    _set_auth_mode(
        monkeypatch,
        "ENTRA",
    )

    with pytest.raises(
        HTTPException
    ) as exc_info:
        dependencies.current_principal(
            credentials=None,
            x_dev_role="SYSTEM_ADMIN",
            db=db,
        )

    assert exc_info.value.status_code == 401
    assert (
        exc_info.value.headers[
            "WWW-Authenticate"
        ]
        == "Bearer"
    )


def test_invalid_entra_token_is_rejected(
    monkeypatch,
    db,
):
    _set_auth_mode(
        monkeypatch,
        "ENTRA",
    )
    _set_validator(
        monkeypatch,
        _RejectingValidator(),
    )

    with pytest.raises(
        HTTPException
    ) as exc_info:
        dependencies.current_principal(
            credentials=_credentials(),
            x_dev_role="SYSTEM_ADMIN",
            db=db,
        )

    assert exc_info.value.status_code == 401


def test_unbound_entra_identity_is_rejected(
    monkeypatch,
    db,
):
    _set_auth_mode(
        monkeypatch,
        "ENTRA",
    )
    _set_validator(
        monkeypatch,
        _StaticValidator(
            _identity()
        ),
    )

    with pytest.raises(
        HTTPException
    ) as exc_info:
        dependencies.current_principal(
            credentials=_credentials(),
            x_dev_role="SYSTEM_ADMIN",
            db=db,
        )

    assert exc_info.value.status_code == 403


def test_inactive_bound_user_is_rejected(
    monkeypatch,
    db,
):
    _bind_engineer(
        db,
        active=False,
    )

    _set_auth_mode(
        monkeypatch,
        "ENTRA",
    )
    _set_validator(
        monkeypatch,
        _StaticValidator(
            _identity()
        ),
    )

    with pytest.raises(
        HTTPException
    ) as exc_info:
        dependencies.current_principal(
            credentials=_credentials(),
            x_dev_role="SYSTEM_ADMIN",
            db=db,
        )

    assert exc_info.value.status_code == 403


def test_active_bound_user_receives_database_role(
    monkeypatch,
    db,
):
    user = _bind_engineer(db)

    _set_auth_mode(
        monkeypatch,
        "ENTRA",
    )
    _set_validator(
        monkeypatch,
        _StaticValidator(
            _identity()
        ),
    )

    principal = dependencies.current_principal(
        credentials=_credentials(),
        x_dev_role="SYSTEM_ADMIN",
        db=db,
    )

    assert principal.auth_mode == "ENTRA"
    assert principal.user_id == user.id
    assert (
        principal.office_id
        == user.office_id
    )
    assert (
        principal.role
        == Role.RESPONSIBLE_ENGINEER
    )
    assert (
        principal.tenant_id
        == TENANT_ID
    )
    assert (
        principal.object_id
        == OBJECT_ID
    )


def test_dev_role_header_cannot_override_entra_role(
    monkeypatch,
    db,
):
    _bind_engineer(db)

    _set_auth_mode(
        monkeypatch,
        "ENTRA",
    )
    _set_validator(
        monkeypatch,
        _StaticValidator(
            _identity()
        ),
    )

    principal = dependencies.current_principal(
        credentials=_credentials(),
        x_dev_role="SYSTEM_ADMIN",
        db=db,
    )

    assert (
        principal.role
        == Role.RESPONSIBLE_ENGINEER
    )


def test_unknown_auth_mode_fails_closed(
    monkeypatch,
    db,
):
    _set_auth_mode(
        monkeypatch,
        "UNKNOWN",
    )

    with pytest.raises(
        HTTPException
    ) as exc_info:
        dependencies.current_principal(
            credentials=None,
            x_dev_role=None,
            db=db,
        )

    assert exc_info.value.status_code == 500
