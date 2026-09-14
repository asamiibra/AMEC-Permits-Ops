"""Hostile persisted fixtures for Billing read-scope algebra."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select

from backend.app.api.dependencies import AuthenticatedPrincipal
from backend.app.api.billing_invoice_routers import _scope_clause
from backend.app.db import SessionLocal
from backend.app.models import BillingPlan, ClientAccount, Contract, ContractRevision, Project, Role, ScopedCapabilityAssignment, User
from backend.app.services.finance_authorization import billing_view_scope


def _principal(user_id: str) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(auth_mode="DEV_HEADER", role=Role.OWNER_SPONSOR, user_id=user_id)


def _scope_fixture_rows(db, project_a: Project, project_b: Project):
    clients = [
        ClientAccount(
            id=str(uuid4()),
            client_reference=f"SCOPE-CLIENT-{uuid4().hex[:16].upper()}",
            legal_name="SQL Server scope algebra fixture",
            display_name="SQL Server scope algebra fixture",
            client_type="CORPORATE",
        )
        for _ in range(2)
    ]
    db.add_all(clients)
    db.flush()
    base_contract = db.scalar(select(Contract).where(Contract.contract_reference == "SYN-CTR-0001"))
    assert base_contract is not None
    base_revision = db.scalar(select(ContractRevision).where(ContractRevision.contract_id == base_contract.id).order_by(ContractRevision.revision_number))
    assert base_revision is not None
    client_a, client_b = (client.id for client in clients)
    pairs = ((project_a, client_a), (project_a, client_b), (project_b, client_a))
    contracts = []
    revisions = []
    plans = []
    for project, client_id in pairs:
        contract = Contract(
            client_account_id=client_id,
            quotation_id=base_contract.quotation_id,
            contract_reference=f"SCOPE-{uuid4().hex[:20].upper()}",
            project_id=project.id,
            contract_name="SQL Server scope algebra fixture",
        )
        db.add(contract)
        db.flush()
        revision = ContractRevision(
            contract_id=contract.id,
            revision_number=1,
            controlling_quotation_revision_id=base_revision.controlling_quotation_revision_id,
            contract_name="SQL Server scope algebra fixture",
        )
        db.add(revision)
        db.flush()
        contracts.append(contract)
        revisions.append(revision)
        plans.append(BillingPlan(id=str(uuid4()), contract_id=contract.id, contract_revision_id=revision.id, project_id=project.id, client_account_id=client_id, currency="QAR", created_by="scope-test"))
    db.add_all(plans)
    db.flush()
    return clients, contracts, revisions, plans


def _delete_scope_fixture_rows(db, clients, contracts, revisions, plans):
    db.query(BillingPlan).filter(BillingPlan.id.in_([item.id for item in plans])).delete(synchronize_session=False)
    db.query(ContractRevision).filter(ContractRevision.id.in_([item.id for item in revisions])).delete(synchronize_session=False)
    db.query(Contract).filter(Contract.id.in_([item.id for item in contracts])).delete(synchronize_session=False)
    db.query(ClientAccount).filter(ClientAccount.id.in_([item.id for item in clients])).delete(synchronize_session=False)


def test_client_grant_does_not_expand_through_shared_project(client):
    with SessionLocal() as db:
        projects = db.scalars(select(Project).order_by(Project.project_number).limit(2)).all()
        assert len(projects) == 2
        project_a, project_b = projects
        clients, contracts, revisions, plans = _scope_fixture_rows(db, project_a, project_b)
        client_a, client_b = (client.id for client in clients)
        user_id = str(uuid4())
        db.add(User(id=user_id, email=f"scope-algebra-{user_id}@amec.synthetic", display_name="Scope Algebra", role=Role.OWNER_SPONSOR, office_id=project_a.office_id))
        db.add(ScopedCapabilityAssignment(user_id=user_id, capability_code="BILLING_VIEW", client_account_id=client_a, assignment_reference="SCOPE-ALGEBRA-CLIENT-A", reason="Hostile same-project cross-client fixture", granted_by=user_id))
        db.commit()
        scope = billing_view_scope(db, _principal(user_id))
        visible = db.scalars(select(BillingPlan).where(_scope_clause(BillingPlan, scope))).all()
        assert {(item.project_id, item.client_account_id) for item in visible} == {(project_a.id, client_a), (project_b.id, client_a)}
        listed = client.get("/api/billing/plans", headers={"X-Dev-Role": "OWNER_SPONSOR", "X-Dev-User": user_id})
        assert listed.status_code == 200, listed.text
        assert {item["plan"]["client_account_id"] for item in listed.json()["items"]} == {client_a}
        db.delete(db.get(User, user_id))
        db.query(ScopedCapabilityAssignment).filter(ScopedCapabilityAssignment.user_id == user_id).delete(synchronize_session=False)
        _delete_scope_fixture_rows(db, clients, contracts, revisions, plans)
        db.commit()


def test_each_grant_keeps_dimensions_conjunctive_and_temporal(client):
    with SessionLocal() as db:
        projects = db.scalars(select(Project).order_by(Project.project_number).limit(2)).all()
        project_a, project_b = projects
        clients, contracts, revisions, plans = _scope_fixture_rows(db, project_a, project_b)
        client_a, client_b = (client.id for client in clients)
        rows = [
            ("client", None, client_a, None, {(project_a.id, client_a), (project_b.id, client_a)}),
            ("project", None, None, project_a.id, {(project_a.id, client_a), (project_a.id, client_b)}),
            ("office", project_a.office_id, None, None, {(project_a.id, client_a), (project_a.id, client_b), (project_b.id, client_a)}),
            ("project-client", None, client_a, project_a.id, {(project_a.id, client_a)}),
            ("office-client", project_a.office_id, client_a, None, {(project_a.id, client_a), (project_b.id, client_a)}),
            ("all", project_a.office_id, client_a, project_a.id, {(project_a.id, client_a)}),
        ]
        for label, office_id, client_id, project_id, expected in rows:
            user_id = str(uuid4())
            db.add(User(id=user_id, email=f"scope-{label}-{user_id}@amec.synthetic", display_name=label, role=Role.OWNER_SPONSOR, office_id=project_a.office_id))
            db.add(ScopedCapabilityAssignment(user_id=user_id, capability_code="BILLING_VIEW", office_id=office_id, client_account_id=client_id, project_id=project_id, assignment_reference=f"SCOPE-ALGEBRA-{label}", reason="Conjunctive dimension fixture", granted_by=user_id))
            db.flush()
            scope = billing_view_scope(db, _principal(user_id))
            visible = db.scalars(select(BillingPlan).where(_scope_clause(BillingPlan, scope))).all()
            assert {(item.project_id, item.client_account_id) for item in visible} == expected
            db.query(ScopedCapabilityAssignment).filter(ScopedCapabilityAssignment.user_id == user_id).delete(synchronize_session=False)
            db.query(User).filter(User.id == user_id).delete(synchronize_session=False)
        _delete_scope_fixture_rows(db, clients, contracts, revisions, plans)
        db.commit()


def test_revoked_expired_future_and_inactive_grants_are_empty():
    with SessionLocal() as db:
        project = db.scalar(select(Project).order_by(Project.project_number))
        now = datetime.now(timezone.utc)
        cases = [
            ("REVOKED", now - timedelta(days=2), now + timedelta(days=2)),
            ("ACTIVE", now - timedelta(days=4), now - timedelta(days=3)),
            ("ACTIVE", now + timedelta(days=3), None),
        ]
        users = []
        for status, effective_from, effective_to in cases:
            user_id = str(uuid4())
            users.append(user_id)
            db.add(User(id=user_id, email=f"scope-time-{user_id}@amec.synthetic", display_name="Temporal Scope", role=Role.OWNER_SPONSOR, office_id=project.office_id))
            db.add(ScopedCapabilityAssignment(user_id=user_id, capability_code="BILLING_VIEW", project_id=project.id, status=status, effective_from=effective_from, effective_to=effective_to, assignment_reference=f"SCOPE-TIME-{status}-{user_id}", reason="Temporal scope fixture", granted_by=user_id))
        inactive_id = str(uuid4())
        users.append(inactive_id)
        db.add(User(id=inactive_id, email=f"scope-inactive-{inactive_id}@amec.synthetic", display_name="Inactive Scope", role=Role.OWNER_SPONSOR, office_id=project.office_id, active=False))
        db.add(ScopedCapabilityAssignment(user_id=inactive_id, capability_code="BILLING_VIEW", project_id=project.id, assignment_reference="SCOPE-INACTIVE", reason="Inactive user fixture", granted_by=inactive_id))
        db.commit()
        for user_id in users:
            assert billing_view_scope(db, _principal(user_id)).empty
        db.query(ScopedCapabilityAssignment).filter(ScopedCapabilityAssignment.user_id.in_(users)).delete(synchronize_session=False)
        db.query(User).filter(User.id.in_(users)).delete(synchronize_session=False)
        db.commit()
