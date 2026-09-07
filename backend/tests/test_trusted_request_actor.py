import asyncio
import json

from starlette.requests import Request
from starlette.responses import Response

from backend.app import main
from backend.app.api.dependencies import (
    AuthenticatedPrincipal,
    trusted_current_principal,
)
from backend.app.models import Role


def _request(
    *,
    path: str = "/api/test",
    headers: dict[str, str] | None = None,
) -> Request:
    encoded_headers = [
        (
            key.lower().encode("latin-1"),
            value.encode("latin-1"),
        )
        for key, value
        in (headers or {}).items()
    ]

    return Request(
        {
            "type": "http",
            "asgi": {
                "version": "3.0",
            },
            "http_version": "1.1",
            "method": "GET",
            "scheme": "https",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": b"",
            "headers": encoded_headers,
            "client": (
                "127.0.0.1",
                12345,
            ),
            "server": (
                "testserver",
                443,
            ),
            "state": {},
        }
    )


def _entra_principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        auth_mode="ENTRA",
        role=Role.RESPONSIBLE_ENGINEER,
        user_id="synthetic-user-id",
        office_id="synthetic-office-id",
        tenant_id=(
            "11111111-1111-4111-8111-111111111111"
        ),
        object_id=(
            "44444444-4444-4444-8444-444444444444"
        ),
    )


def _dev_principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        auth_mode="DEV_HEADER",
        role=Role.SYSTEM_ADMIN,
    )


def _run_middleware(
    monkeypatch,
    request: Request,
    *,
    status_code: int = 200,
):
    events = []

    monkeypatch.setattr(
        main.logger,
        "info",
        lambda message: events.append(
            json.loads(message)
        ),
    )

    async def call_next(
        inner_request: Request,
    ):
        assert inner_request is request
        return Response(
            status_code=status_code
        )

    response = asyncio.run(
        main.correlation_middleware(
            request,
            call_next,
        )
    )

    assert len(events) == 1

    return response, events[0]


def test_trusted_dependency_stores_resolved_principal():
    request = _request()
    principal = _entra_principal()

    resolved = trusted_current_principal(
        request=request,
        principal=principal,
    )

    assert resolved is principal
    assert (
        request.state.authenticated_principal
        is principal
    )


def test_entra_actor_uses_internal_user_id():
    request = _request()
    request.state.authenticated_principal = (
        _entra_principal()
    )

    actor = main._trusted_request_actor(
        request
    )

    assert actor == {
        "actor": "synthetic-user-id",
        "actor_user_id": (
            "synthetic-user-id"
        ),
        "auth_mode": "ENTRA",
        "actor_role": (
            "RESPONSIBLE_ENGINEER"
        ),
    }


def test_entra_actor_does_not_expose_object_id():
    request = _request()
    request.state.authenticated_principal = (
        _entra_principal()
    )

    actor = main._trusted_request_actor(
        request
    )

    assert "object_id" not in actor
    assert "entra_object_id" not in actor
    assert (
        "44444444-4444-4444-8444-444444444444"
        not in actor.values()
    )


def test_dev_actor_uses_resolved_role():
    request = _request(
        headers={
            "X-Dev-User": "spoof-user",
            "X-Actor-Id": "spoof-actor",
        }
    )
    request.state.authenticated_principal = (
        _dev_principal()
    )

    actor = main._trusted_request_actor(
        request
    )

    assert actor == {
        "actor": "dev-role:SYSTEM_ADMIN",
        "actor_user_id": None,
        "auth_mode": "DEV_HEADER",
        "actor_role": "SYSTEM_ADMIN",
    }


def test_anonymous_actor_ignores_spoofed_headers():
    request = _request(
        path="/health",
        headers={
            "X-Dev-User": "spoof-user",
            "X-Actor-Id": "spoof-actor",
        },
    )

    assert main._trusted_request_actor(
        request
    ) == {
        "actor": "anonymous",
        "actor_user_id": None,
        "auth_mode": None,
        "actor_role": None,
    }


def test_unknown_principal_mode_fails_closed_in_logging():
    request = _request()
    request.state.authenticated_principal = (
        AuthenticatedPrincipal(
            auth_mode="UNKNOWN",
            role=Role.SYSTEM_ADMIN,
            user_id="must-not-log",
        )
    )

    assert main._trusted_request_actor(
        request
    ) == {
        "actor": "anonymous",
        "actor_user_id": None,
        "auth_mode": None,
        "actor_role": None,
    }


def test_entra_without_internal_user_id_fails_closed_in_logging():
    request = _request()
    request.state.authenticated_principal = (
        AuthenticatedPrincipal(
            auth_mode="ENTRA",
            role=Role.SYSTEM_ADMIN,
            user_id=None,
        )
    )

    assert main._trusted_request_actor(
        request
    ) == {
        "actor": "anonymous",
        "actor_user_id": None,
        "auth_mode": None,
        "actor_role": None,
    }


def test_request_log_ignores_spoofed_actor_headers_for_entra(
    monkeypatch,
):
    request = _request(
        headers={
            "X-Dev-User": "spoof-user",
            "X-Actor-Id": "spoof-actor",
            "X-Correlation-ID": (
                "synthetic-correlation"
            ),
        }
    )
    request.state.authenticated_principal = (
        _entra_principal()
    )

    response, event = _run_middleware(
        monkeypatch,
        request,
    )

    assert event["actor"] == (
        "synthetic-user-id"
    )
    assert event["actor_user_id"] == (
        "synthetic-user-id"
    )
    assert event["auth_mode"] == "ENTRA"
    assert event["actor_role"] == (
        "RESPONSIBLE_ENGINEER"
    )
    assert "spoof-user" not in event.values()
    assert "spoof-actor" not in event.values()
    assert event["correlation_id"] == (
        "synthetic-correlation"
    )
    assert response.headers[
        "X-Correlation-ID"
    ] == "synthetic-correlation"


def test_request_log_uses_trusted_dev_role(
    monkeypatch,
):
    request = _request(
        headers={
            "X-Dev-User": "spoof-user",
            "X-Actor-Id": "spoof-actor",
        }
    )
    request.state.authenticated_principal = (
        _dev_principal()
    )

    _, event = _run_middleware(
        monkeypatch,
        request,
    )

    assert event["actor"] == (
        "dev-role:SYSTEM_ADMIN"
    )
    assert event["actor_user_id"] is None
    assert event["auth_mode"] == (
        "DEV_HEADER"
    )
    assert event["actor_role"] == (
        "SYSTEM_ADMIN"
    )


def test_failed_public_or_auth_rejected_request_is_anonymous(
    monkeypatch,
):
    request = _request(
        headers={
            "X-Dev-User": "spoof-user",
            "X-Actor-Id": "spoof-actor",
        }
    )

    _, event = _run_middleware(
        monkeypatch,
        request,
        status_code=401,
    )

    assert event["actor"] == "anonymous"
    assert event["actor_user_id"] is None
    assert event["auth_mode"] is None
    assert event["actor_role"] is None
    assert event["outcome"] == "FAILED"


def test_api_auth_boundary_uses_trusted_wrapper():
    assert len(
        main.API_AUTH_DEPENDENCIES
    ) == 1

    dependency = (
        main.API_AUTH_DEPENDENCIES[0]
    )

    assert (
        dependency.dependency
        is trusted_current_principal
    )
