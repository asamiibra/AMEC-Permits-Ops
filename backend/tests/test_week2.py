from types import SimpleNamespace
from datetime import date
from sqlalchemy import select
from backend.app.db import SessionLocal
from backend.app.models import *
from backend.app.adapters.municipality.adapter import MockMunicipalityAdapter
from backend.app.services.document_intelligence import RuleBasedDocumentClassifier
from backend.app.services.normalization import normalize_arabic_digits, normalize_identifier


def project(client, number="GHCE-2026-0142"):
    return next(p for p in client.get("/api/projects").json() if p["project_number"] == number)


def test_week2_seed_and_documents(client):
    p = project(client)
    response = client.get(f"/api/projects/{p['id']}/documents")
    assert response.status_code == 200
    assert len(response.json()) >= 6
    assert {d["document_type"] for d in response.json()} >= {"TITLE_DEED", "OWNER_QID", "DRAWING_SET"}


def test_same_hash_dedupes_and_changed_content_versions(client):
    p = project(client)
    payload = {"document_type":"OTHER","logical_name":"dedupe-control","source_filename":"one.txt","source_path_or_reference":"synthetic://one","content":"SYNTHETIC DUPLICATE CONTENT"}
    first = client.post(f"/api/projects/{p['id']}/documents", json=payload).json()["version"]
    second = client.post(f"/api/projects/{p['id']}/documents", json={**payload,"source_filename":"renamed.txt"}).json()["version"]
    assert first["id"] == second["id"]
    third = client.post(f"/api/projects/{p['id']}/documents", json={**payload,"source_filename":"rev2.txt","content":"SYNTHETIC CHANGED CONTENT"}).json()["version"]
    assert third["id"] != first["id"]
    assert client.get(f"/api/documents/{first['document_id']}/versions").json()


def test_classification_extraction_observation_not_assertion(client):
    p = project(client)
    doc = client.get(f"/api/projects/{p['id']}/documents").json()[0]
    version_id = doc["current_version_id"]
    assert client.post(f"/api/document-versions/{version_id}/classify").status_code == 200
    observations = client.post(f"/api/document-versions/{version_id}/extract").json()
    assert observations
    assertions = client.get(f"/api/projects/{p['id']}/verified-assertions").json()
    assert all(a["source_observation_id"] != observations[0]["id"] for a in assertions)


def test_classification_confirmation_and_approval_state_are_audited(client):
    p = project(client)
    doc = next(item for item in client.get(f"/api/projects/{p['id']}/documents").json() if item["document_type"] == "OTHER")
    version_id = doc["current_version_id"]
    classification = client.post(f"/api/document-versions/{version_id}/classify", json={"review_status":"HUMAN_CONFIRMED"})
    assert classification.status_code == 200 and classification.json()["review_status"] == "HUMAN_CONFIRMED"
    approval = client.patch(f"/api/document-versions/{version_id}/approval-state", json={"approval_state":"APPROVED"})
    assert approval.status_code == 200 and approval.json()["approval_state"] == "APPROVED"
    events = client.get("/api/audit").json()
    assert any(event["event_type"] == "DOCUMENT_CLASSIFICATION_CONFIRMED" for event in events)
    assert any(event["event_type"] == "DOCUMENT_APPROVAL_STATE_CHANGED" for event in events)


def test_manual_keyed_verify_and_correction_preserve_history(client):
    p = project(client)
    doc = next(d for d in client.get(f"/api/projects/{p['id']}/documents").json() if d["document_type"] == "TITLE_DEED")
    field = "PROPERTY.PLOT_NUMBER"
    manual = client.post(f"/api/projects/{p['id']}/manual-observations", json={"document_version_id":doc["current_version_id"],"field_code":field,"raw_value":"001234","page_number":1,"source_region_text":"PLOT: 001234"})
    assert manual.status_code == 200 and manual.json()["extraction_method"] == "MANUAL_KEYED"
    verified = client.post(f"/api/observations/{manual.json()['id']}/verify", json={"actor_id":"reviewer","method":"MANUAL_KEYED_VERIFIED"})
    assert verified.status_code == 200 and verified.json()["status"] == "CURRENT"
    corrected = client.post(f"/api/observations/{manual.json()['id']}/verify", json={"actor_id":"reviewer","corrected_value":"001235"})
    assert corrected.status_code == 200
    with SessionLocal() as db:
        original = db.get(FieldObservation, manual.json()["id"])
        assert original.raw_value == "001234"
        assert db.scalar(select(VerifiedAssertion).where(VerifiedAssertion.id == corrected.json()["id"])) is not None


def test_arabic_and_identifier_normalization_is_controlled():
    assert normalize_arabic_digits("٠٠١٢٣٤") == "001234"
    assert normalize_identifier(" ٠٠١٢٣٤ ") == "001234"
    assert RuleBasedDocumentClassifier().classify(SimpleNamespace(metadata_json={"synthetic_text":"TITLE_DEED\nPLOT: 001234"})).predicted_type == "TITLE_DEED"
    assert RuleBasedDocumentClassifier().classify(SimpleNamespace(metadata_json={"synthetic_text":"unclassified content"})).predicted_type == "OTHER"


def test_conflict_and_drawing_mismatch_do_not_auto_resolve(client):
    p = project(client, "GHCE-2026-0187")
    conflicts = client.get(f"/api/projects/{p['id']}/conflicts").json()
    assert conflicts and any(c["severity"] in {"CRITICAL", "MAJOR"} for c in conflicts)
    drawing = client.get(f"/api/config/scenarios/DEMO_BUILDING_PERMIT_V1/drawing-controls/evaluate/{p['id']}").json()
    assert any(item["result"] == "FAIL" for item in drawing)


def test_configuration_and_expired_dependency_semantics(client):
    base = "/api/config/scenarios/DEMO_BUILDING_PERMIT_V1"
    assert len(client.get(base + "/fields").json()["fields"]) >= 10
    assert len(client.get(base + "/documents").json()["documents"]) >= 10
    assert len(client.get(base + "/requirements").json()["requirements"]) >= 4
    p = project(client, "GHCE-2026-0187")
    reqs = client.get(base + f"/requirements/evaluate/{p['id']}").json()
    civil = next(r for r in reqs if r["requirement_code"] == "CIVIL_DEFENCE_NOC")
    assert civil["status"] == "REQUIRED" and civil["evidence"] is False
    plot = next(field for field in client.get(base + "/fields").json()["fields"] if field["field_code"] == "PROPERTY.PLOT_NUMBER")
    assert any(rule["primary_source_type"] == "TITLE_DEED" for rule in plot["authority_rules"])


def test_mock_authority_configuration_grids_save_reopen_validation_precheck(client):
    app = client.get("/api/applications").json()[0]
    config = client.get(f"/mock-authority/applications/{app['id']}/configuration")
    assert config.status_code == 200
    assert len(config.json()["tabs_json"]) == 10
    assert {x["key"] for x in config.json()["grids_json"]} >= {"buildings", "floors"}
    state = {"plot_number":"1234","buildings":[{"building_ref":"B1"},{"building_ref":"B1"}]}
    assert client.put(f"/mock-authority/applications/{app['id']}/draft", json={"state_json":state}).status_code == 200
    assert client.get(f"/mock-authority/applications/{app['id']}/draft").json()["state_json"] == state
    validation = client.get(f"/mock-authority/applications/{app['id']}/validation").json()
    assert validation["status"] == "FINDINGS"
    assert client.get(f"/mock-authority/applications/{app['id']}/precheck-results").status_code == 200
    assert "SUBMIT_APPLICATION" not in {x["operation"] for x in config.json()["operations_json"]}


def test_real_document_gate_and_synthetic_spike(client):
    denied = client.post("/api/evaluation/spikes", json={"dataset_type":"APPROVED_REAL_TEST","environment":"TEST"})
    assert denied.status_code == 403 and "REAL_DOCUMENT_TEST_NOT_APPROVED" in denied.text
    created = client.post("/api/evaluation/spikes", json={"dataset_type":"SYNTHETIC","environment":"TEST"})
    assert created.status_code == 200
    result = client.post(f"/api/evaluation/spikes/{created.json()['id']}/run")
    assert result.status_code == 200
    metrics = result.json()["metrics_json"]
    assert metrics["classification_agreement"] >= 0
    assert "automation_quality_note" in metrics


def test_submission_confirmation_has_no_submission_action(client):
    app = client.get("/api/applications").json()[0]
    response = client.post("/api/submission-confirmations", json={"application_id":app["id"],"request_reference":app["external_request_number"],"visible_status":"DRAFT","evidence_reference":"synthetic://status-evidence"})
    assert response.status_code == 200
    assert not any("submit" in name.lower() for name in dir(MockMunicipalityAdapter))
