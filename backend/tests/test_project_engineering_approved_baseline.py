from datetime import datetime, timezone
import pytest
from sqlalchemy import delete, select, update

from backend.app.db import SessionLocal
from backend.app.models import (
    ApprovedDesignBaseline, ApprovedDesignBaselineMember, DesignChangeRequest,
    EngineeringCalculationRecord, EngineeringDeliverable, EngineeringDeliverableRevision,
    EngineeringMaterialTest, EngineeringProfessionalApproval, EngineeringProjectMember,
    EngineeringReviewFinding, EngineeringRendition, EngineeringTechnicalCheck,
    EngineeringWorkPackage, LineageEdge, Project, ProjectEngineeringReview,
    Document, DocumentVersion, TechnicalRule, TechnicalRuleSetVersion,
)


@pytest.fixture
def engineering_projects():
    ids = []
    yield ids
    with SessionLocal() as db:
        models = [
            DesignChangeRequest, ApprovedDesignBaselineMember, EngineeringMaterialTest,
            EngineeringCalculationRecord, EngineeringTechnicalCheck, EngineeringProfessionalApproval,
            EngineeringReviewFinding, ProjectEngineeringReview, EngineeringRendition,
            EngineeringDeliverableRevision, EngineeringDeliverable, EngineeringWorkPackage,
            EngineeringProjectMember, ApprovedDesignBaseline, LineageEdge,
        ]
        for project_id in ids:
            db.execute(update(EngineeringDeliverable).where(EngineeringDeliverable.project_id == project_id).values(current_revision_id=None))
            for model in models:
                if hasattr(model, "project_id"):
                    db.execute(delete(model).where(model.project_id == project_id))
            document_ids = select(Document.id).where(Document.project_id == project_id)
            db.execute(delete(DocumentVersion).where(DocumentVersion.document_id.in_(document_ids)))
            db.execute(delete(Document).where(Document.project_id == project_id))
            db.execute(delete(Project).where(Project.id == project_id))
        db.commit()


def _project(client, number: str, tracked: list[str]):
    response = client.post("/api/projects", json={"project_number": number, "project_name": "Synthetic Engineering Project", "municipality": "Synthetic Municipality", "permit_type": "Building"})
    assert response.status_code == 200, response.text
    project_id = response.json()["id"]
    with SessionLocal() as db:
        project = db.get(Project, project_id)
        project.activated_at = datetime.now(timezone.utc)
        project.activated_by = "synthetic-owner"
        db.commit()
    tracked.append(project_id)
    return project_id


def test_project_engineering_gate_review_approval_baseline_and_change(client, engineering_projects):
    inactive = client.post("/api/projects", json={"project_number": "ENG-INACTIVE", "project_name": "Inactive Engineering Project", "municipality": "Synthetic Municipality", "permit_type": "Building"}).json()["id"]
    engineering_projects.append(inactive)
    blocked = client.post(f"/api/projects/{inactive}/engineering/work-packages", json={"package_ref": "WP-BLOCKED", "title": "Blocked"})
    assert blocked.status_code == 409
    project_id = _project(client, "ENG-ACTIVE", engineering_projects)
    headers = {"X-Dev-Role": "RESPONSIBLE_ENGINEER", "X-Dev-Actor": "engineer-preparer"}
    package = client.post(f"/api/projects/{project_id}/engineering/work-packages", headers=headers, json={"package_ref": "WP-001", "title": "Structural package"}).json()
    deliverable = client.post(f"/api/projects/{project_id}/engineering/deliverables", headers=headers, json={"work_package_id": package["id"], "deliverable_ref": "C-001", "title": "Structural calculation package"}).json()
    revision = client.post(f"/api/projects/{project_id}/engineering/deliverables/{deliverable['id']}/revisions", headers=headers, json={"revision_code": "R1", "title": "Structural calculation R1"}).json()
    for kind in ("NATIVE", "PUBLISHED"):
        response = client.post(f"/api/projects/{project_id}/engineering/revisions/{revision['id']}/ingest", headers=headers, json={"rendition_kind": kind, "filename": f"c001-r1-{kind.lower()}.bin", "synthetic_content": kind})
        assert response.status_code == 200, response.text
    review = client.post(f"/api/projects/{project_id}/engineering/revisions/{revision['id']}/reviews", headers=headers, json={}).json()
    finding = client.post(f"/api/projects/{project_id}/engineering/reviews/{review['id']}/findings", headers=headers, json={"severity": "BLOCKING", "description": "Synthetic blocking finding"}).json()
    denied = client.post(f"/api/projects/{project_id}/engineering/revisions/{revision['id']}/professional-approval", headers={**headers, "X-Dev-Actor": "engineer-approver"}, json={"credential_reference": "SYNTHETIC-CREDENTIAL"})
    assert denied.status_code == 409
    assert client.post(f"/api/projects/{project_id}/engineering/findings/{finding['id']}/resolve", headers=headers, json={"response": "Corrected"}).status_code == 200
    assert client.post(f"/api/projects/{project_id}/engineering/reviews/{review['id']}/complete", headers=headers, json={}).status_code == 200
    with SessionLocal() as db:
        rule_set = TechnicalRuleSetVersion(code="SYNTHETIC-STRUCTURAL", name="Synthetic structural rules", discipline="STRUCTURAL", version="1", status="ACTIVE")
        db.add(rule_set); db.flush()
        rule = TechnicalRule(rule_set_version_id=rule_set.id, code="MIN-CAPACITY", name="Minimum capacity", rule_type="THRESHOLD", expression_json={"input": "capacity", "operator": "gte", "threshold": 10, "unit": "kPa"}, status="ACTIVE")
        db.add(rule); db.commit(); rule_set_id, rule_id = rule_set.id, rule.id
    check = client.post(f"/api/projects/{project_id}/engineering/revisions/{revision['id']}/technical-checks", headers=headers, json={"technical_rule_set_version_id": rule_set_id, "technical_rule_id": rule_id, "inputs": {"capacity": 12}})
    assert check.status_code == 200 and check.json()["result"] == "PASS", check.text
    approval = client.post(f"/api/projects/{project_id}/engineering/revisions/{revision['id']}/professional-approval", headers={**headers, "X-Dev-Actor": "engineer-approver"}, json={"credential_reference": "SYNTHETIC-CREDENTIAL"})
    assert approval.status_code == 200, approval.text
    immutable = client.post(f"/api/projects/{project_id}/engineering/revisions/{revision['id']}/ingest", headers=headers, json={"rendition_kind": "PUBLISHED", "synthetic_content": "replace"})
    assert immutable.status_code == 409
    baseline = client.post(f"/api/projects/{project_id}/engineering/baselines", headers=headers, json={"baseline_ref": "B1"}).json()
    rendition = client.get(f"/api/projects/{project_id}/engineering").json()["deliverables"][0]
    with SessionLocal() as db:
        from backend.app.models import EngineeringRendition
        exact = db.query(EngineeringRendition).filter(EngineeringRendition.revision_id == revision["id"], EngineeringRendition.rendition_kind == "NATIVE").first()
        rendition_id = exact.id
    assert client.post(f"/api/projects/{project_id}/engineering/baselines/{baseline['id']}/members", headers=headers, json={"revision_id": revision["id"], "rendition_id": rendition_id}).status_code == 200
    assert client.post(f"/api/projects/{project_id}/engineering/baselines/{baseline['id']}/validate", headers=headers).json()["valid"] is True
    approved = client.post(f"/api/projects/{project_id}/engineering/baselines/{baseline['id']}/approve", headers={**headers, "X-Dev-Actor": "baseline-approver"}, json={"credential_reference": "SYNTHETIC-CREDENTIAL"})
    assert approved.status_code == 200, approved.text
    assert "AMEC Approved Design Baseline" in client.get(f"/api/projects/{project_id}/engineering/baselines/{baseline['id']}/manifest", headers=headers).json()["label"]
    assert client.post(f"/api/projects/{project_id}/engineering/members", headers={**headers, "X-Dev-Actor": "owner"}, json={"actor_id": "engineer-preparer"}).status_code == 200
    other = _project(client, "ENG-OTHER", engineering_projects)
    assert client.post(f"/api/projects/{other}/engineering/members", headers={"X-Dev-Role": "SYSTEM_ADMIN", "X-Dev-Actor": "owner"}, json={"actor_id": "other-engineer"}).status_code == 200
    isolated = client.get(f"/api/projects/{other}/engineering", headers=headers)
    assert isolated.status_code == 403
