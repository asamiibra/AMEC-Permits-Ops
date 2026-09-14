from backend.app.api.auth_context_routers import auth_session
from backend.app.api.dependencies import AuthenticatedPrincipal
from backend.app.models import Role


def test_auth_session_exposes_only_safe_display_identity_facts():
    principal = AuthenticatedPrincipal(
        auth_mode="ENTRA",
        role=Role.OWNER_SPONSOR,
        user_id="user-1",
        tenant_id="tenant-1",
        object_id="object-1",
        display_name="Synthetic Owner",
        preferred_username="owner@example.invalid",
    )

    payload = auth_session(principal)

    assert payload["identity"] == {
        "user_id": "user-1",
        "tenant_id": "tenant-1",
        "object_id": "object-1",
        "display_name": "Synthetic Owner",
        "preferred_username": "owner@example.invalid",
        "role": "OWNER_SPONSOR",
    }
    assert "access_token" not in payload
    assert "id_token" not in payload
    assert "refresh_token" not in payload


def test_display_identity_claims_do_not_change_server_role():
    owner = AuthenticatedPrincipal(
        auth_mode="ENTRA",
        role=Role.OWNER_SPONSOR,
        user_id="user-1",
        display_name="SYSTEM_ADMIN Global Administrator",
        preferred_username="admin@example.invalid",
    )
    renamed = AuthenticatedPrincipal(
        auth_mode="ENTRA",
        role=Role.OWNER_SPONSOR,
        user_id="user-1",
        display_name="Ordinary User",
        preferred_username="ordinary@example.invalid",
    )

    assert auth_session(owner)["identity"]["role"] == auth_session(renamed)["identity"]["role"]
