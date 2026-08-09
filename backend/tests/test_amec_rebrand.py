from sqlalchemy import func, select

from backend.app.db import SessionLocal
from backend.app.fixtures.canonical import CANONICAL_APPLICATION_IDS, CANONICAL_PROJECT_IDS
from backend.app.models import ConsultancyOffice, Project, PermitApplication


def test_active_synthetic_consultancy_is_amec_and_ids_are_preserved(client):
    office = client.get("/api/office").json()
    assert office["name_en"] == "AMEC Engineering"
    projects = client.get("/api/projects").json()
    applications = client.get("/api/applications").json()
    assert [item["project_number"] for item in projects] == CANONICAL_PROJECT_IDS
    assert [item["external_request_number"] for item in applications] == CANONICAL_APPLICATION_IDS
    with SessionLocal() as db:
        offices = db.scalars(select(ConsultancyOffice)).all()
        assert len(offices) == 1
        assert offices[0].name_en == "AMEC Engineering"
        assert db.scalar(select(func.count(Project.id)).where(Project.office_id == offices[0].id)) == len(CANONICAL_PROJECT_IDS)
        assert db.scalar(select(func.count(PermitApplication.id))) == len(CANONICAL_APPLICATION_IDS)
