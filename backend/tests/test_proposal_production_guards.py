"""Negative coverage for the Proposal production/synthetic boundary."""

import pytest
from uuid import uuid4

from backend.app.config.settings import get_settings
from backend.app.api.dependencies import AuthenticatedPrincipal
from backend.app.db import SessionLocal
from backend.app.models import AuditEvent, ConsultancyOffice, Project, Role
from backend.app.storage import StorageError, create_binary_store
from backend.app.services.proposal_production_boundary import require_authorized_office

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


def test_production_office_context_denies_cross_office_project(monkeypatch):
    settings = get_settings()
    original = (settings.app_env, settings.synthetic_only)
    monkeypatch.setattr(settings, "app_env", "PROD")
    monkeypatch.setattr(settings, "synthetic_only", False)
    with SessionLocal() as db:
        office_a = ConsultancyOffice(office_code=f"TEST-A-{uuid4().hex[:8]}", name_en="Office A", name_ar="مكتب أ", status="ACTIVE")
        office_b = ConsultancyOffice(office_code=f"TEST-B-{uuid4().hex[:8]}", name_en="Office B", name_ar="مكتب ب", status="ACTIVE")
        db.add_all([office_a, office_b])
        db.flush()
        project = Project(project_number=f"TEST-{uuid4().hex[:8]}", project_name="Cross-office negative", office_id=office_b.id, workstream="BD", status="DRAFT", municipality="Doha", permit_type="BUILDING")
        db.add(project)
        db.flush()
        principal = AuthenticatedPrincipal(auth_mode="ENTRA", role=Role.PROCESS_CHAMPION, office_id=office_a.id)
        with pytest.raises(Exception) as caught:
            require_authorized_office(db, principal, project_id=project.id)
        assert getattr(caught.value, "detail", {}).get("code") == "OFFICE_CONTEXT_MISMATCH"
        db.rollback()
    settings.app_env, settings.synthetic_only = original
