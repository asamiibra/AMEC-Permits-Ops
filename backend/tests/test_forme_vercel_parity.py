from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.app.models import Base, MasterContentItem
from backend.app.services.master_content import create_master_content, reconcile_owner_demo_dataset, resolve_master_content_purpose
from backend.app.fixtures.forme_parity import FORME_MASTER_SPECS


def _isolated_session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def test_forme_parity_seed_is_exact_and_idempotent():
    # The reconciler is a persistent owner-demo bootstrap.  Keep this exact
    # parity contract isolated from the session-scoped TEST database so the
    # canonical Contract Template it creates cannot become a second active
    # resolver candidate for unrelated contract tests.
    Session = _isolated_session_factory()
    with Session() as db:
        first = reconcile_owner_demo_dataset(db, actor="owner-demo-seed")
        rows = list(db.scalars(select(MasterContentItem).where(MasterContentItem.content_type == "FORM", MasterContentItem.status == "ACTIVE")).all())
        forme = {row.title: row for row in rows if (row.engineering_metadata or {}).get("forme_parity")}
        assert len(forme) == 14
        assert sum(not row.needs_review for row in forme.values()) == 7
        assert sum(row.needs_review for row in forme.values()) == 7
        assert all(row.status == "ACTIVE" for row in forme.values())
        assert all(row.current_document_version_id for row in forme.values())
        assert {row.review_note for row in forme.values() if row.needs_review} == {spec["review_note"] for spec in FORME_MASTER_SPECS if spec["status"] == "NEEDS_REVIEW"}
        assert not any(row.title in {"Consultant Form", "Authorization Form"} for row in rows)

        current_titles = {spec["title"] for spec in FORME_MASTER_SPECS if spec["status"] == "CURRENT"}
        needs_review_titles = {spec["title"] for spec in FORME_MASTER_SPECS if spec["status"] == "NEEDS_REVIEW"}
        resolver = resolve_master_content_purpose(db, module="PERMIT", usage_type="AVAILABLE")
        resolved_titles = {row["title"] for row in resolver["candidates"]}
        assert needs_review_titles.isdisjoint(resolved_titles)
        assert current_titles.issubset(resolved_titles)

        second = reconcile_owner_demo_dataset(db, actor="owner-demo-seed")
        assert second["forme_parity"]["created"] == []
        assert second["forme_parity"]["preserved"] == [spec["stable_key"] for spec in FORME_MASTER_SPECS]
        assert second["generic_placeholder_analysis"]["unclassified"] == []
        assert second["forme_parity"]["current"] == 7
        assert second["forme_parity"]["needs_review"] == 7


def test_generic_seed_placeholder_cleanup_handles_dependency_column_names():
    # This reconciliation also creates the canonical owner-demo templates;
    # isolate it for the same reason as the exact parity contract above.
    Session = _isolated_session_factory()
    with Session() as db:
        created = create_master_content(
            db,
            content_type="FORM",
            ref="F-0001",
            title="Consultant Form",
            category_id=None,
            description="Legacy owner-demo placeholder",
            filename="F-0001-owner-demo.txt",
            mime_type="text/plain",
            content=b"legacy placeholder",
            actor="owner-demo-seed",
            idempotency_key="owner-demo-placeholder-regression",
            correlation_id="owner-demo-placeholder-regression",
        )
        item = db.get(MasterContentItem, created["id"])
        version = item.document.versions[0]
        version.source_filename = "F-0001-owner-demo.txt"
        version.metadata_json = {**version.metadata_json, "business_ref": "F-0001"}
        db.commit()

        result = reconcile_owner_demo_dataset(db)

        assert "F-0001" in result["generic_placeholder_analysis"]["archived"]
