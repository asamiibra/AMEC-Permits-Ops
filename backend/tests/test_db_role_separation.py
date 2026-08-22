import pytest

from backend.app.provision_db_roles import _parts, provision_roles


def test_role_url_parser_requires_postgres_user_and_database():
    assert _parts("postgresql+psycopg://runtime@db/app")[0] == "runtime"
    assert _parts("postgresql+psycopg://runtime@db/app")[2:5] == ("db", 5432, "app")
    with pytest.raises(RuntimeError):
        _parts("sqlite:///app")


@pytest.mark.parametrize("env", [{}, {"DATABASE_URL": "postgresql+psycopg://r:p@db/app"}])
def test_role_provisioning_requires_separate_authority(env):
    with pytest.raises(RuntimeError):
        provision_roles(env)


def test_role_provisioning_rejects_host_or_port_mismatch(monkeypatch):
    monkeypatch.setattr(
        "backend.app.provision_db_roles.psycopg.connect",
        lambda *_: pytest.fail("must reject before connecting"),
    )
    with pytest.raises(RuntimeError, match="database targets"):
        provision_roles(
            {
                "DATABASE_MIGRATION_URL": "postgresql+psycopg://admin:p@db:5432/app",
                "DATABASE_URL": "postgresql+psycopg://runtime:p@other:5432/app",
            }
        )
