"""Negative coverage for the Proposal production/synthetic boundary."""

from backend.app.config.settings import get_settings
from backend.app.db import SessionLocal
from backend.app.models import AuditEvent
from backend.app.storage import StorageError, create_binary_store

from .test_bd_proposal_owner_session import _headers


def test_production_proposal_requires_canonical_client_account(client, monkeypatch):
    settings = get_settings()
    original = (settings.app_env, settings.synthetic_only, settings.auth_mode)
    monkeypatch.setattr(settings, "app_env", "PROD")
    monkeypatch.setattr(settings, "synthetic_only", False)
    monkeypatch.setattr(settings, "auth_mode", "DEV_HEADER")
    try:
        response = client.post(
            "/api/bd/proposals",
            headers=_headers("COMMERCIAL_APPROVER"),
            json={"proposal_description": "Production guard negative", "client_name": "Caller supplied client"},
        )
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "CANONICAL_CLIENT_ACCOUNT_REQUIRED"
    finally:
        settings.app_env, settings.synthetic_only, settings.auth_mode = original


def test_audit_identity_ignores_caller_actor(client):
    response = client.post(
        "/api/bd/proposals",
        headers={**_headers("COMMERCIAL_APPROVER"), "X-Dev-Actor": "spoofed-caller"},
        json={"proposal_description": "Principal audit negative", "client_name": "Synthetic audit client"},
    )
    assert response.status_code == 200, response.text
    with SessionLocal() as db:
        event = db.query(AuditEvent).filter(AuditEvent.entity_id == response.json()["id"], AuditEvent.event_type == "BD_PROPOSAL_DRAFT_CREATED").one()
        assert event.actor_id == "dev-role:PROCESS_CHAMPION"
        assert event.actor_id != "spoofed-caller"
        assert event.metadata_json["auth_mode"] == "DEV_HEADER"


def test_production_shaped_environment_rejects_mock_storage(monkeypatch):
    settings = get_settings()
    original = (settings.app_env, settings.synthetic_only, settings.storage_provider)
    monkeypatch.setattr(settings, "app_env", "AZURE-PREPROD")
    monkeypatch.setattr(settings, "synthetic_only", True)
    monkeypatch.setattr(settings, "storage_provider", "mock")
    try:
        try:
            create_binary_store()
        except StorageError as exc:
            assert exc.code.value == "STORAGE_CONFIGURATION_ERROR"
        else:
            raise AssertionError("mock storage must be unavailable in production-shaped environments")
    finally:
        settings.app_env, settings.synthetic_only, settings.storage_provider = original
