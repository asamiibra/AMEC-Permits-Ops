import pytest

from backend.app.provision_db_roles import _parts, provision_roles


def test_role_url_parser_requires_postgres_user_and_database():
    assert _parts("postgresql+psycopg://runtime@db/app")[0] == "runtime"
    with pytest.raises(RuntimeError):
        _parts("sqlite:///app")


@pytest.mark.parametrize("env", [{}, {"DATABASE_URL": "postgresql+psycopg://r:p@db/app"}])
def test_role_provisioning_requires_separate_authority(env):
    with pytest.raises(RuntimeError):
        provision_roles(env)
