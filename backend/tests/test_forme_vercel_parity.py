from sqlalchemy import select

from backend.app.db import SessionLocal
from backend.app.models import MasterContentItem
from backend.app.services.master_content import reconcile_owner_demo_dataset, resolve_master_content_purpose
from backend.app.fixtures.forme_parity import FORME_MASTER_SPECS


def test_forme_parity_seed_is_exact_and_idempotent():
    with SessionLocal() as db:
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
