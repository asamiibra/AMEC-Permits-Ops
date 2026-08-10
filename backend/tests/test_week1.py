from backend.app.db import SessionLocal
from backend.app.models import AuditEvent, Role, User
from backend.app.services.business_case import calculate_business_case
from backend.app.adapters.municipality.adapter import MockMunicipalityAdapter


def test_health_and_correlation(client):
    response = client.get("/health", headers={"X-Correlation-ID": "test-correlation-001"})
    assert response.status_code == 200
    body = response.json()
    assert body["synthetic_only"] is True
    assert body["database_configured"] is True
    assert body["database_dialect"] in {"sqlite", "postgresql"}
    assert body["database_durable"] is (body["database_dialect"] == "postgresql")
    assert body["sqlite_fallback_active"] is False
    assert body["database_connection_valid"] is True
    assert response.headers["X-Correlation-ID"] == "test-correlation-001"


def test_seed_office_users_projects(client):
    office = client.get("/api/office").json()
    assert office["office_code"] == "QEC-DOHA"
    assert office["name_en"] == "AMEC Engineering"
    projects = client.get("/api/projects").json()
    assert len(projects) >= 4
    assert len(client.get("/api/applications").json()) >= 4


def test_linkage_and_mismatch_confirmation(client):
    project = client.get("/api/projects").json()[0]
    response = client.post(f"/api/projects/{project['id']}/external-links", json={"system_type":"SYNOLOGY","external_reference":"2026/WRONG-ROOT","display_reference":"wrong"})
    assert response.status_code == 409
    response = client.post(f"/api/projects/{project['id']}/external-links", json={"system_type":"SYNOLOGY","external_reference":"2026/WRONG-ROOT","display_reference":"wrong","confirm_mismatch":True})
    assert response.status_code == 200
    assert response.json()["mismatch"] is True


def test_business_case_is_deterministic():
    result = calculate_business_case({"applications_per_month": 25})
    assert result["applications_per_year"] == 300
    assert result["annual_manual_hours"] == 675
    assert result["estimated_annual_returned_cases"] == 105
    assert result["estimated_rework_hours"] == 525


def test_decision_raid_and_inquiry_mutations_audit(client):
    decision = client.get("/api/discovery/decisions").json()[0]
    assert client.patch(f"/api/discovery/decisions/{decision['id']}", json={"status":"CONFIRMED"}).status_code == 200
    assert client.post("/api/raid", json={"type":"ISSUE","title":"Test synthetic issue","description":"test","severity":"LOW","owner":"TEST","status":"OPEN","mitigation":"test"}).status_code == 200
    inquiry = client.get("/api/ministry-inquiries").json()[0]
    assert client.patch(f"/api/ministry-inquiries/{inquiry['id']}", json={"status":"ASKED"}).status_code == 200
    events = client.get("/api/audit").json()
    event_types = {event["event_type"] for event in events}
    assert {"DISCOVERY_DECISION_CHANGED", "RAID_ITEM_CREATED", "MINISTRY_INQUIRY_CHANGED"}.issubset(event_types)


def test_municipality_adapter_is_read_only_and_reads_synthetic_state():
    adapter = MockMunicipalityAdapter({"app-1": {"status":"RETURNED","repetition_count":2,"comments":[{"text":"synthetic"}]}})
    assert adapter.read_status("app-1")["status"] == "RETURNED"
    assert adapter.read_comments("app-1")[0]["text"] == "synthetic"
    forbidden = {"submit", "submit_application", "final_submit", "pay", "sign", "certify"}
    assert not forbidden.intersection(dir(MockMunicipalityAdapter))


def test_roles_are_seeded_and_supported():
    with SessionLocal() as db:
        roles = {user.role for user in db.query(User).all()}
    assert Role.PERMIT_PREPARER in roles
    assert Role.FINAL_SUBMITTER in roles
    assert Role.SYSTEM_ADMIN in roles
