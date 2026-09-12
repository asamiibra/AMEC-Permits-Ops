from types import SimpleNamespace

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from backend.app.models import Base
from backend.app.models import MasterContentItem, MasterContentModuleBinding
from backend.app.services import master_content


def _synthetic_preprod_settings():
    return SimpleNamespace(
        app_env="AZURE-PREPROD",
        synthetic_only=True,
        real_data_allowed=False,
        master_sor_allowed_extensions=".txt",
        master_sor_max_file_size=1024 * 1024,
        master_sor_mapping_json='{"MASTER_FORM":"master-content/forms"}',
    )


def test_deployed_synthetic_matrix_is_fail_closed(monkeypatch):
    monkeypatch.setattr(master_content, "get_settings", _synthetic_preprod_settings)
    monkeypatch.delenv("VERCEL", raising=False)
    assert master_content._deployed_synthetic() is True

    monkeypatch.setattr(
        master_content,
        "get_settings",
        lambda: SimpleNamespace(app_env="PROD", synthetic_only=True, real_data_allowed=False),
    )
    assert master_content._deployed_synthetic() is False


def test_preprod_canonical_master_content_is_exact_and_idempotent(monkeypatch):
    monkeypatch.setattr(master_content, "get_settings", _synthetic_preprod_settings)
    monkeypatch.delenv("VERCEL", raising=False)

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        first = master_content.reconcile_preprod_canonical_master_content(db)
        second = master_content.reconcile_preprod_canonical_master_content(db)
        assert set(first["created"]) == {"BD-PROP-001", "BD-CHK-001", "CT-001"}
        assert second["created"] == []
        assert set(second["preserved"]) == {"BD-PROP-001", "BD-CHK-001", "CT-001"}

        for module, purpose, title in (
            ("BD", "PROPOSAL_TEMPLATE", "AMEC Proposal Template"),
            ("BD", "PROPOSAL_CHECKLIST", "AMEC Proposal Checklist"),
            ("ADMIN", "CONTRACT_TEMPLATE", "AMEC Contract Template"),
        ):
            item = db.scalar(select(MasterContentItem).where(MasterContentItem.title == title))
            assert item is not None
            assert item.needs_review is False
            assert item.engineering_metadata["preprod_canonical"] is True
            assert db.scalar(
                select(func.count(MasterContentModuleBinding.id)).where(
                    MasterContentModuleBinding.master_content_id == item.id,
                    MasterContentModuleBinding.module == module,
                    MasterContentModuleBinding.usage_type == purpose,
                    MasterContentModuleBinding.active.is_(True),
                )
            ) == 1
            resolved = master_content.resolve_master_content_purpose(db, module=module, usage_type=purpose)
            assert resolved["status"] == "RESOLVED"
            assert resolved["canonical_count"] == 1
