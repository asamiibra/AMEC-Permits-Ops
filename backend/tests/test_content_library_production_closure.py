from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from backend.app.api.source18_routers import _actor
from backend.app.api import master_content_routers
from backend.app.api.dependencies import AuthenticatedPrincipal
from backend.app.models import Role
from backend.app.services import master_content


def test_upload_gate_rejects_pdf_signature_mismatch(monkeypatch):
    monkeypatch.setattr(master_content, "get_settings", lambda: SimpleNamespace(master_sor_allowed_extensions=".pdf", master_sor_max_file_size=1024))
    with pytest.raises(HTTPException) as caught:
        master_content._allowed_file("sample.pdf", b"not a pdf")
    assert caught.value.detail["code"] == "FILE_SIGNATURE_MISMATCH"


def test_create_upload_is_bounded_before_service_persistence(client, monkeypatch):
    settings = SimpleNamespace(master_sor_allowed_extensions=".txt", master_sor_max_file_size=4)
    monkeypatch.setattr(master_content, "get_settings", lambda: settings)
    monkeypatch.setattr(master_content_routers, "get_settings", lambda: settings)
    response = client.post(
        "/api/master-content",
        data={"content_type": "FORM", "ref": "BOUND-CREATE-TEST", "title": "Bounded create"},
        files={"file": ("bounded.txt", b"12345", "text/plain")},
        headers={"X-Dev-Role": "SYSTEM_ADMIN"},
    )
    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "FILE_TOO_LARGE"


def test_upload_gate_rejects_dangerous_archive_member(monkeypatch):
    monkeypatch.setattr(master_content, "get_settings", lambda: SimpleNamespace(master_sor_allowed_extensions=".docx", master_sor_max_file_size=1024 * 1024))
    import io
    import zipfile
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("../escape.txt", "synthetic")
    with pytest.raises(HTTPException) as caught:
        master_content._allowed_file("sample.docx", output.getvalue())
    assert caught.value.detail["code"] == "DANGEROUS_ARCHIVE_MEMBER"


def test_entra_source18_actor_ignores_dev_header():
    request = Request({"type": "http", "headers": [(b"x-dev-actor", b"spoofed")], "method": "GET", "path": "/", "query_string": b"", "client": ("test", 1), "server": ("test", 80), "scheme": "http"})
    request.state.authenticated_principal = AuthenticatedPrincipal(auth_mode="ENTRA", role=Role.SYSTEM_ADMIN, user_id="entra-user-123", object_id="entra-object-123")
    assert _actor(request, Role.SYSTEM_ADMIN) == "entra-user-123"


def test_source18_official_forms_are_read_only_typed_projections(client):
    response = client.get("/api/master-content/official-forms", headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert response.status_code == 200, response.text
    assert response.json()["projection_type"] == "SOURCE18_OFFICIAL_FORM_READ_ONLY"
    assert response.json()["read_only"] is True
    assert response.json()["items"]
    item = response.json()["items"][0]
    assert item["authority_owner"] == "SOURCE18"
    assert item["reuse"]["allowed"] is True
    assert client.get("/api/master-content/official-forms/resolve", headers={"X-Dev-Role": "SYSTEM_ADMIN"}).status_code == 200


def test_dashboard_v2_direct_form_reads_enforce_persona_applicability(client):
    response = client.post(
        "/api/master-content",
        data={"content_type": "FORM", "ref": "V2-AUTHZ-DIRECT-TEST", "title": "Administration-only direct read", "used_in": '["ADMIN"]'},
        files={"file": ("v2-authz-direct.txt", b"synthetic", "text/plain")},
        headers={"X-Dev-Role": "SYSTEM_ADMIN"},
    )
    assert response.status_code == 200, response.text
    item_id = response.json()["id"]
    for suffix in ("applicability", "policy-lineage", "technical-lineage", "automation"):
        denied = client.get(f"/api/dashboard-v2/forms/{item_id}/{suffix}", headers={"X-Dev-Role": "PROCESS_CHAMPION"})
        assert denied.status_code == 403, (suffix, denied.text)
