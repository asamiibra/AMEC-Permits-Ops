from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app import provision_user
from backend.app.models import (
    ConsultancyOffice,
    Role,
    User,
)


OID_A = (
    "44444444-4444-4444-8444-444444444444"
)

OID_B = (
    "55555555-5555-4555-8555-555555555555"
)


@pytest.fixture
def isolated_users(
    monkeypatch,
):
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
    )

    ConsultancyOffice.__table__.create(
        engine
    )

    User.__table__.create(
        engine
    )

    factory = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    with factory() as db:
        office = ConsultancyOffice(
            office_code="QEC-DOHA",
            name_en="AMEC Engineering",
            name_ar="Synthetic",
            status="ACTIVE",
        )

        db.add(
            office
        )
        db.flush()

        owner = User(
            email="owner@amec.synthetic",
            display_name="Synthetic Owner",
            role=Role.OWNER_SPONSOR,
            active=True,
            office_id=office.id,
        )

        engineer = User(
            email="engineer@amec.synthetic",
            display_name=(
                "Synthetic Engineer"
            ),
            role=(
                Role.RESPONSIBLE_ENGINEER
            ),
            active=True,
            office_id=office.id,
        )

        inactive = User(
            email="inactive@amec.synthetic",
            display_name="Inactive",
            role=Role.PROCESS_CHAMPION,
            active=False,
            office_id=office.id,
        )

        db.add_all(
            [
                owner,
                engineer,
                inactive,
            ]
        )

        db.commit()

        ids = {
            "owner": owner.id,
            "engineer": engineer.id,
            "inactive": inactive.id,
        }

    monkeypatch.setattr(
        provision_user,
        "SessionLocal",
        factory,
    )

    monkeypatch.setattr(
        provision_user,
        "get_settings",
        lambda: SimpleNamespace(
            app_env="AZURE-PREPROD",
            synthetic_only=True,
            real_data_allowed=False,
        ),
    )

    monkeypatch.setattr(
        provision_user,
        "verify_database_migration_head",
        lambda: "0059_entra_user_identity",
    )

    try:
        yield factory, ids
    finally:
        engine.dispose()


def test_oid_is_canonicalized():
    assert (
        provision_user._canonical_oid(
            OID_A.upper()
        )
        == OID_A
    )


def test_invalid_oid_is_rejected():
    with pytest.raises(
        ValueError
    ):
        provision_user._canonical_oid(
            "not-a-guid"
        )


@pytest.mark.parametrize(
    (
        "user_id",
        "app_user_email",
    ),
    [
        (
            None,
            None,
        ),
        (
            "id",
            "owner@amec.synthetic",
        ),
    ],
)
def test_exactly_one_user_selector_is_required(
    isolated_users,
    user_id,
    app_user_email,
):
    with pytest.raises(
        ValueError,
        match="exactly one",
    ):
        provision_user.provision_user(
            entra_object_id=OID_A,
            user_id=user_id,
            app_user_email=app_user_email,
        )


def test_non_preprod_is_rejected(
    monkeypatch,
    isolated_users,
):
    monkeypatch.setattr(
        provision_user,
        "get_settings",
        lambda: SimpleNamespace(
            app_env="TEST",
            synthetic_only=True,
            real_data_allowed=False,
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="restricted",
    ):
        provision_user.provision_user(
            entra_object_id=OID_A,
            app_user_email=(
                "owner@amec.synthetic"
            ),
        )


def test_missing_user_is_rejected(
    isolated_users,
):
    with pytest.raises(
        RuntimeError,
        match="not found",
    ):
        provision_user.provision_user(
            entra_object_id=OID_A,
            app_user_email=(
                "missing@amec.synthetic"
            ),
        )


def test_inactive_user_is_rejected(
    isolated_users,
):
    with pytest.raises(
        RuntimeError,
        match="inactive",
    ):
        provision_user.provision_user(
            entra_object_id=OID_A,
            app_user_email=(
                "inactive@amec.synthetic"
            ),
        )


def test_bind_by_user_id(
    isolated_users,
):
    factory, ids = (
        isolated_users
    )

    result = (
        provision_user.provision_user(
            entra_object_id=OID_A,
            user_id=ids["owner"],
        )
    )

    assert result.status == "BOUND"
    assert (
        result.user_id
        == ids["owner"]
    )

    with factory() as db:
        assert (
            db.get(
                User,
                ids["owner"],
            ).entra_object_id
            == OID_A
        )


def test_bind_by_explicit_application_email(
    isolated_users,
):
    _, ids = isolated_users

    result = (
        provision_user.provision_user(
            entra_object_id=OID_A,
            app_user_email=(
                "owner@amec.synthetic"
            ),
        )
    )

    assert result.status == "BOUND"
    assert (
        result.user_id
        == ids["owner"]
    )


def test_same_binding_is_idempotent(
    isolated_users,
):
    provision_user.provision_user(
        entra_object_id=OID_A,
        app_user_email=(
            "owner@amec.synthetic"
        ),
    )

    result = (
        provision_user.provision_user(
            entra_object_id=OID_A,
            app_user_email=(
                "owner@amec.synthetic"
            ),
        )
    )

    assert (
        result.status
        == "ALREADY_BOUND"
    )


def test_oid_cannot_be_owned_by_two_users(
    isolated_users,
):
    provision_user.provision_user(
        entra_object_id=OID_A,
        app_user_email=(
            "owner@amec.synthetic"
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="another ProposalOps user",
    ):
        provision_user.provision_user(
            entra_object_id=OID_A,
            app_user_email=(
                "engineer@amec.synthetic"
            ),
        )


def test_existing_user_binding_cannot_be_replaced(
    isolated_users,
):
    provision_user.provision_user(
        entra_object_id=OID_A,
        app_user_email=(
            "owner@amec.synthetic"
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="different Entra",
    ):
        provision_user.provision_user(
            entra_object_id=OID_B,
            app_user_email=(
                "owner@amec.synthetic"
            ),
        )
