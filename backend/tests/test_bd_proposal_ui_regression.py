"""Regression contracts for the BD Proposal register and initial source flow."""

import pytest


def _headers(role="COMMERCIAL_APPROVER"):
    return {"X-Dev-Role": role}


def test_register_lane_counts_reconcile_with_the_same_filtered_rows(client):
    rows = client.get("/api/bd/proposals", headers=_headers()).json()
    assert rows["lane_counts"]["ALL"] == len(rows["items"])
    for lane in ("NEED_ACTION", "AUTHORITY_REVIEW", "READY_CLOSE"):
        filtered = client.get("/api/bd/proposals", params={"lane": lane}, headers=_headers()).json()
        assert filtered["lane_counts"][lane] == filtered["count"] == len(filtered["items"])


def test_register_public_response_contract_serializes_every_visible_row(client):
    response = client.get("/api/bd/proposals", headers=_headers())
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["predicate_version"] == "bd-proposal-register-v2"
    assert payload["rows"] == payload["items"]
    assert isinstance(payload["count"], int)
    assert all(isinstance(value, int) and value >= 0 for value in payload["lane_counts"].values())
    for row in payload["items"]:
        assert {"id", "proposal", "client", "activity", "stage", "stage_code", "next_action", "owner_lane", "contract_eligible", "validation"} <= row.keys()


def test_register_does_not_materialize_detail_projection(client, monkeypatch):
    import backend.app.api.bd_proposal_routers as routers

    def fail_if_detail_projection_is_called(*args, **kwargs):
        raise AssertionError("the register must not invoke the full Proposal detail projection")

    monkeypatch.setattr(routers, "proposal_projection", fail_if_detail_projection_is_called)
    response = client.get("/api/bd/proposals", headers=_headers())
    assert response.status_code == 200, response.text


def test_proposal_intake_clients_returns_active_canonical_choices(client):
    response = client.get("/api/bd/proposals/clients", headers=_headers())
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["count"] == len(payload["items"])
    assert all({"id", "name", "reference", "status"} <= item.keys() for item in payload["items"])
    assert all(item["status"] == "ACTIVE" for item in payload["items"])


@pytest.mark.parametrize(
    ("source_type", "filename", "mime_type", "file_body"),
    (
        ("TENDER_EMAIL", "tender.eml", "message/rfc822", b"From: synthetic@example.test\nSubject: Tender"),
        ("TENDER_DOCUMENT", "tender.pdf", "application/pdf", b"%PDF-1.7 synthetic tender"),
        ("TENDER_PHOTO", "site-photo.jpg", "image/jpeg", b"synthetic photo bytes"),
        ("CLIENT_DATA", "client-data.txt", "text/plain", b"Client-provided information"),
    ),
)
def test_initial_source_creation_is_typed_and_links_source_after_proposal_creation(
    client, source_type, filename, mime_type, file_body
):
    response = client.post(
        "/api/bd/proposals/intake",
        headers=_headers(),
        data={
            "proposal_description": f"Initial {source_type} regression",
            "project_reference": f"UI-REG-{source_type}",
            "client_name": "UI Regression Client",
            "initial_source_type": source_type,
            "source_title": "Tender invitation",
            "source_date": "2026-08-14",
            "source_notes": "Human-entered source context",
        },
        files={"file": (filename, file_body, mime_type)},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["next_route"] == f"/opportunities/{payload['proposal']['id']}"
    assert payload["source"]["source_type"] == source_type
    assert any(item["source_type"] == source_type for item in payload["proposal"]["sources"])


def test_proposal_creation_without_initial_source_remains_available(client):
    response = client.post(
        "/api/bd/proposals",
        headers=_headers(),
        json={"proposal_description": "No initial source regression", "client_name": "UI Regression Client"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["sources"] == []


def test_arabic_proposal_values_round_trip_through_json_and_persistence(client):
    title = "مركز الوطن - عرض فني"
    client_name = "شركة آرت مارك الهندسية"
    created = client.post(
        "/api/bd/proposals",
        headers=_headers(),
        json={"proposal_description": title, "client_name": client_name, "idempotency_key": "unicode-api-roundtrip-v1"},
    )
    assert created.status_code == 200, created.text
    payload = created.json()
    proposal_id = payload["id"]
    assert payload["title"] == title
    detail = client.get(f"/api/bd/proposals/{proposal_id}", headers=_headers())
    assert detail.status_code == 200, detail.text
    assert detail.json()["title"] == title
    assert detail.json()["client_name"] == client_name


def test_client_information_without_file_persists_contact_and_client_source(client):
    response = client.post(
        "/api/bd/proposals/intake",
        headers=_headers(),
        data={
            "proposal_description": "Client context without file",
            "client_name": "UI Regression Client",
            "initial_source_type": "CLIENT_DATA",
            "contact_name": "Nadia Owner",
            "contact_email": "nadia@example.test",
            "source_title": "Client briefing",
            "source_notes": "Human-entered client context",
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["source"]["source_type"] == "CLIENT_DATA"
    assert payload["proposal"]["forms_v2"]["proposal_contact"]["display_name"] == "Nadia Owner"
    assert payload["proposal"]["forms_v2"]["proposal_contact"]["email"] == "nadia@example.test"
    assert payload["proposal"]["sources"][0]["provenance"]["context"] == "CLIENT_INFORMATION"
    assert payload["proposal"]["sources"][0]["verification_state"] == "READ_BACK_VERIFIED"


def test_initial_source_requires_a_file_and_does_not_claim_success(client):
    response = client.post(
        "/api/bd/proposals/intake",
        headers=_headers(),
        data={"proposal_description": "Missing source file", "client_name": "UI Regression Client", "initial_source_type": "TENDER_DOCUMENT"},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INITIAL_SOURCE_FILE_REQUIRED"
