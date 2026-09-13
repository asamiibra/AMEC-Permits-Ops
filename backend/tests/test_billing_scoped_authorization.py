"""Live route proof for persisted scoped Billing capability authorization."""

from uuid import uuid4

from sqlalchemy import select

from backend.app.db import SessionLocal
from backend.app.models import Project, Role, ScopedCapabilityAssignment, User


def _headers(user_id: str) -> dict[str, str]:
    return {"X-Dev-Role": "OWNER_SPONSOR", "X-Dev-User": user_id}


def _project_ids() -> tuple[str, str]:
    with SessionLocal() as db:
        projects = db.scalars(select(Project).order_by(Project.project_number).limit(2)).all()
        return projects[0].id, projects[1].id


def test_live_billing_mutation_fails_closed_without_scoped_assignment(client):
    project_id, _ = _project_ids()
    user_id = str(uuid4())
    with SessionLocal() as db:
        project = db.get(Project, project_id)
        db.add(User(id=user_id, email=f"unassigned-{user_id}@amec.synthetic", display_name="Unassigned Owner", role=Role.OWNER_SPONSOR, office_id=project.office_id))
        db.commit()

    response = client.post(
        f"/api/billing/projects/{project_id}/expected-exp",
        headers=_headers(user_id),
        json={"value_percent": 25, "source_or_note": "synthetic negative authorization proof"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "SCOPED_FINANCE_CAPABILITY_REQUIRED"


def test_live_billing_mutation_requires_exact_capability_and_project_scope(client):
    project_id, other_project_id = _project_ids()
    user_id = str(uuid4())
    with SessionLocal() as db:
        project = db.get(Project, project_id)
        db.add(User(id=user_id, email=f"scoped-{user_id}@amec.synthetic", display_name="Scoped Owner", role=Role.OWNER_SPONSOR, office_id=project.office_id))
        db.add(ScopedCapabilityAssignment(
            user_id=user_id,
            capability_code="BILLING_FX_RATE_MANAGE",
            office_id=project.office_id,
            assignment_reference="SYNTHETIC-NEGATIVE-WRONG-CAPABILITY",
            reason="Prove capability identity is exact",
            granted_by=user_id,
        ))
        db.add(ScopedCapabilityAssignment(
            user_id=user_id,
            capability_code="PROJECT_EXPECTED_EXP_EDIT",
            project_id=project_id,
            assignment_reference="SYNTHETIC-PROJECT-SCOPE",
            reason="Prove project-scoped assignment is enforced",
            granted_by=user_id,
        ))
        db.commit()

    allowed = client.post(
        f"/api/billing/projects/{project_id}/expected-exp",
        headers=_headers(user_id),
        json={"value_percent": 30, "source_or_note": "synthetic exact project authorization proof"},
    )
    assert allowed.status_code == 200, allowed.text

    wrong_project = client.post(
        f"/api/billing/projects/{other_project_id}/expected-exp",
        headers=_headers(user_id),
        json={"value_percent": 31, "source_or_note": "synthetic wrong-project authorization proof"},
    )
    assert wrong_project.status_code == 403
    assert wrong_project.json()["detail"]["code"] == "SCOPED_FINANCE_CAPABILITY_REQUIRED"


def test_owner_can_manage_assignment_and_revoke_is_auditable(client):
    project_id, _ = _project_ids()
    with SessionLocal() as db:
        target = db.scalar(select(User).where(User.email == "engineer@amec.synthetic"))
        assert target is not None
        target_id = target.id
    created = client.post(
        "/api/admin/capability-assignments",
        headers={"X-Dev-Role": "OWNER_SPONSOR"},
        json={
            "user_id": target_id,
            "capability_code": "PROJECT_EXPECTED_EXP_EDIT",
            "project_id": project_id,
            "assignment_reference": "SYNTHETIC-ADMIN-MANAGEMENT-PROOF",
            "reason": "Synthetic owner assignment management proof",
        },
    )
    assert created.status_code == 200, created.text
    assignment_id = created.json()["id"]
    revoked = client.post(
        f"/api/admin/capability-assignments/{assignment_id}/revoke",
        headers={"X-Dev-Role": "OWNER_SPONSOR"},
        json={},
    )
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["status"] == "REVOKED"
