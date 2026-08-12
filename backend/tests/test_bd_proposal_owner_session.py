"""BD Proposal owner-session vertical acceptance tests."""


def _headers(role: str) -> dict[str, str]:
    return {"X-Dev-Role": role}


def _ensure_dashboard_proposal_templates(client):
    for ref, title, usage in (("F-0003", "Regression Proposal Template", "PROPOSAL_TEMPLATE"), ("F-0004", "Regression Proposal Checklist", "PROPOSAL_CHECKLIST")):
        rows = client.get("/api/master-content", params={"q": ref}, headers=_headers("SYSTEM_ADMIN")).json()
        item = next((row for row in rows if row["ref"] == ref), None)
        if not item:
            created = client.post("/api/master-content", data={"content_type": "FORM", "ref": ref, "title": title, "description": title, "used_in": '["BD"]'}, files={"file": (f"{ref}.txt", b"synthetic regression canonical content", "text/plain")}, headers=_headers("SYSTEM_ADMIN"))
            assert created.status_code == 200, created.text
            item = created.json()
        bound = client.put(f"/api/master-content/{item['id']}/module-bindings", json=[{"module": "BD", "usage_type": usage}], headers=_headers("SYSTEM_ADMIN"))
        assert bound.status_code == 200, bound.text


def test_bd_proposal_full_owner_session_flow(client):
    owner = _headers("SYSTEM_ADMIN")
    _ensure_dashboard_proposal_templates(client)

    created = client.post("/api/bd/proposals", headers=_headers("COMMERCIAL_APPROVER"), json={
        "proposal_description": "BD owner-session regression proposal",
        "project_reference": "GHCE-2026-0187",
        "client_name": "Synthetic BD Regression Client",
    })
    assert created.status_code == 200
    proposal_id = created.json()["id"]

    initial = client.get(f"/api/bd/proposals/{proposal_id}/validation", headers=owner).json()
    assert initial["ready"] is False
    assert {"SOURCE_EVIDENCE_REQUIRED", "SCOPE_OF_WORK_REQUIRED"} <= {item["code"] for item in initial["blockers"]}

    for source_type in ("TENDER_DOCUMENT", "TENDER_EMAIL", "TENDER_PHOTO", "CLIENT_DATA"):
        response = client.post(
            f"/api/bd/proposals/{proposal_id}/sources",
            headers=_headers("COMMERCIAL_APPROVER"),
            data={"source_type": source_type, "source_revision": "S1"},
            files={"file": (f"{source_type.lower()}.txt", f"synthetic {source_type}".encode(), "text/plain")},
        )
        assert response.status_code == 200
        assert response.json()["source"]["verification_state"] == "READ_BACK_VERIFIED"

    updated = client.patch(f"/api/bd/proposals/{proposal_id}", headers=_headers("COMMERCIAL_APPROVER"), json={
        "fields": {
            "client_name": "Synthetic BD Regression Client",
            "scope_of_work": "AMEC design and permitting scope",
            "client_scope_of_work": "Client tender scope",
            "process_of_work": "Review, prepare, verify, hand off",
            "price": "QAR 10000",
            "duration": "30 days",
            "inclusions": ["Drawings"],
            "exclusions": ["Authority fees"],
            "additional_information": "Regression proof",
            "definition_terms": ["Project Reference"],
            "provenance": {"scope_of_work": "manual", "client_scope_of_work": "source", "price": "manual"},
        },
        "amec_input": {"review_note": "Human AMEC review recorded."},
    })
    assert updated.status_code == 200
    ready = client.get(f"/api/bd/proposals/{proposal_id}/validation", headers=owner).json()
    assert ready["ready"] is True
    assert ready["ai_assist"]["enabled"] is False

    engineering_accept = client.post(f"/api/bd/proposals/{proposal_id}/accept", headers=_headers("RESPONSIBLE_ENGINEER"))
    assert engineering_accept.status_code == 403
    accepted = client.post(f"/api/bd/proposals/{proposal_id}/accept", headers=_headers("COMMERCIAL_APPROVER"))
    assert accepted.status_code == 200
    revision = accepted.json()["current_revision"]
    assert revision["revision_number"] == 1
    assert revision["template"]["ref"] == "F-0003"
    assert revision["checklist"]["ref"] == "F-0004"

    outputs = client.get(f"/api/bd/proposals/{proposal_id}/outputs", headers=owner)
    assert outputs.status_code == 200
    assert {item["artifact_type"] for item in outputs.json()["items"]} == {"PROPOSAL", "CHECKLIST"}
    download = client.get(f"/api/bd/proposals/{proposal_id}/outputs/proposal", headers=owner)
    assert download.status_code == 200
    assert download.headers["x-artifact-hash"]

    handoff = client.post(f"/api/bd/proposals/{proposal_id}/handoff/contract", headers=_headers("COMMERCIAL_APPROVER"))
    assert handoff.status_code == 200
    assert handoff.json()["accepted_revision_id"] == revision["id"]
    assert handoff.json()["machine_legal_contract"] is False


def test_bd_proposal_dashboard_seams_and_engineering_read_only(client):
    owner = _headers("SYSTEM_ADMIN")
    _ensure_dashboard_proposal_templates(client)
    resolved = client.get("/api/bd/proposals/master-content", headers=_headers("COMMERCIAL_APPROVER"))
    assert resolved.status_code == 200
    assert resolved.json()["proposal_template"]["status"] == "RESOLVED"
    assert resolved.json()["proposal_checklist"]["status"] == "RESOLVED"
    assert resolved.json()["definitions"]["truth"] == "DASHBOARD_DEFINITIONS"

    denied = client.post("/api/bd/proposals", headers=_headers("RESPONSIBLE_ENGINEER"), json={"proposal_description": "Denied", "client_name": "Denied"})
    assert denied.status_code == 403

    settings = client.get("/api/bd/proposals/settings/go-live", headers=owner)
    assert settings.status_code == 200
    assert settings.json()["safe_default"] is True


def test_bd_proposal_source_replacement_preserves_history_without_permanent_conflict(client):
    _ensure_dashboard_proposal_templates(client)
    created = client.post("/api/bd/proposals", headers=_headers("COMMERCIAL_APPROVER"), json={"proposal_description": "Source history regression", "client_name": "Synthetic Source History Client"})
    assert created.status_code == 200
    proposal_id = created.json()["id"]
    first = client.post(f"/api/bd/proposals/{proposal_id}/sources", headers=_headers("COMMERCIAL_APPROVER"), data={"source_type": "TENDER_DOCUMENT", "source_revision": "v1"}, files={"file": ("tender-v1.txt", b"original tender", "text/plain")})
    second = client.post(f"/api/bd/proposals/{proposal_id}/sources", headers=_headers("COMMERCIAL_APPROVER"), data={"source_type": "TENDER_DOCUMENT", "source_revision": "v2"}, files={"file": ("tender-v2.txt", b"revised tender", "text/plain")})
    assert first.status_code == second.status_code == 200
    sources = second.json()["proposal"]["sources"]
    assert len(sources) == 2
    assert {item["status"] for item in sources} == {"CURRENT", "CONFLICT"}
    validation = second.json()["proposal"]["validation"]
    assert "SOURCE_CONFLICTS_UNRESOLVED" not in {item["code"] for item in validation["blockers"]}
    assert "SOURCE_CONFLICT_HISTORY" in {item["code"] for item in validation["warnings"]}


def test_bd_proposal_acceptance_pins_template_and_checklist_history(client):
    _ensure_dashboard_proposal_templates(client)
    created = client.post("/api/bd/proposals", headers=_headers("COMMERCIAL_APPROVER"), json={"proposal_description": "Template history regression", "client_name": "Synthetic Template History Client"})
    assert created.status_code == 200
    proposal_id = created.json()["id"]
    for source_type in ("TENDER_DOCUMENT", "TENDER_EMAIL", "TENDER_PHOTO", "CLIENT_DATA"):
        response = client.post(f"/api/bd/proposals/{proposal_id}/sources", headers=_headers("COMMERCIAL_APPROVER"), data={"source_type": source_type, "source_revision": "H1"}, files={"file": (f"{source_type.lower()}-h1.txt", b"history source", "text/plain")})
        assert response.status_code == 200
    fields = {"scope_of_work": "AMEC scope", "client_scope_of_work": "Client scope", "process_of_work": "Review", "price": "QAR 100", "duration": "1 day"}
    assert client.patch(f"/api/bd/proposals/{proposal_id}", headers=_headers("COMMERCIAL_APPROVER"), json={"fields": fields}).status_code == 200
    first = client.post(f"/api/bd/proposals/{proposal_id}/accept", headers=_headers("COMMERCIAL_APPROVER")).json()["current_revision"]
    template_id = first["template"]["ref"]
    checklist_id = first["checklist"]["ref"]
    for ref, label in ((template_id, "template v2"), (checklist_id, "checklist v2")):
        item = next(row for row in client.get("/api/master-content", params={"q": ref}, headers=_headers("SYSTEM_ADMIN")).json() if row["ref"] == ref)
        versioned = client.post(f"/api/master-content/{item['id']}/versions", headers=_headers("SYSTEM_ADMIN"), data={"expected_current_version": "1", "change_reason": label}, files={"file": (f"{ref}-v2.txt", label.encode(), "text/plain")})
        assert versioned.status_code == 200, versioned.text
    assert client.patch(f"/api/bd/proposals/{proposal_id}", headers=_headers("COMMERCIAL_APPROVER"), json={"fields": {"proposal_details": "Updated after master revision"}}).status_code == 200
    second = client.post(f"/api/bd/proposals/{proposal_id}/accept", headers=_headers("COMMERCIAL_APPROVER")).json()
    history = {row["revision_number"]: row for row in second["revision_history"]}
    assert history[1]["revision_number"] == 1
    assert second["current_revision"]["revision_number"] == 2
    assert second["current_revision"]["template"]["version"] == "2"
    assert second["current_revision"]["checklist"]["version"] == "2"
    assert history[1]["content_hash"] != second["current_revision"]["content_hash"]
