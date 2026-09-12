"""Acceptance proofs for the Content Library gap-closure contract."""

import json
from uuid import uuid4

import pytest
from sqlalchemy import select

from backend.app.db import SessionLocal
from backend.app.models import ContentCategory, DefinitionEntry, DocumentVersion, MasterContentDependency, MasterContentModuleBinding, MasterContentSourceSection


OWNER = {"X-Dev-Role": "SYSTEM_ADMIN"}
BD = {"X-Dev-Role": "PROCESS_CHAMPION"}


def _create(client, content_type="FORM", *, used_in=None, title=None):
    ref = f"GAP-{content_type[:1]}-{uuid4().hex[:8]}"
    data = {"content_type": content_type, "ref": ref, "title": title or f"Gap closure {ref}", "description": "Synthetic gap closure fixture"}
    if used_in is not None:
        data["used_in"] = json.dumps(used_in)
    response = client.post("/api/master-content", data=data, files={"file": (f"{ref}.txt", b"gap closure", "text/plain")}, headers=OWNER)
    assert response.status_code == 200, response.text
    return response.json()


def test_category_and_reference_policy_updates_fail_closed_without_mutation(client):
    categories = client.get("/api/master-content/categories", headers=OWNER)
    category = categories.json()[0]
    before = category["allowed_content_types"]
    invalid_category = client.patch(f"/api/master-content/categories/{category['id']}", json={"allowed_content_types": ["NOT_A_CONTENT_TYPE"]}, headers=OWNER)
    assert invalid_category.status_code == 422
    with SessionLocal() as db:
        assert db.get(ContentCategory, category["id"]).allowed_content_types == before

    policy_before = next(row for row in client.get("/api/master-content/reference-policies", headers=OWNER).json() if row["content_type"] == "FORM")
    invalid_policy = client.put("/api/master-content/reference-policies/FORM", json={"prefix": "  ", "padding": 4}, headers=OWNER)
    assert invalid_policy.status_code == 422
    policy_after = next(row for row in client.get("/api/master-content/reference-policies", headers=OWNER).json() if row["content_type"] == "FORM")
    assert {key: policy_after[key] for key in ("prefix", "padding", "scope")} == {key: policy_before[key] for key in ("prefix", "padding", "scope")}


def test_binding_and_purpose_validation_rejects_cross_type_states(client):
    report = _create(client, "REPORT", used_in=["BD"])
    before = client.get(f"/api/master-content/{report['id']}/module-bindings", headers=OWNER).json()
    invalid = client.put(f"/api/master-content/{report['id']}/module-bindings", json=[{"module": "BD", "usage_type": "PROPOSAL_TEMPLATE"}], headers=OWNER)
    assert invalid.status_code == 422
    assert invalid.json()["detail"]["code"] == "PURPOSE_CONTENT_TYPE_MISMATCH"
    assert client.get(f"/api/master-content/{report['id']}/module-bindings", headers=OWNER).json() == before

    invalid_purpose = client.get("/api/master-content/resolvers/BD/NOT_A_PURPOSE", headers=OWNER)
    assert invalid_purpose.status_code == 422
    assert invalid_purpose.json()["detail"]["code"] == "MASTER_CONTENT_PURPOSE_NOT_ALLOWED"

    inactive = client.put(f"/api/master-content/{report['id']}/module-bindings", json=[{"module": "BD", "usage_type": "AVAILABLE", "active": False}], headers=OWNER)
    assert inactive.status_code == 200
    assert inactive.json()["used_in"] == []
    with SessionLocal() as db:
        assert not db.scalar(select(MasterContentModuleBinding).where(MasterContentModuleBinding.master_content_id == report["id"], MasterContentModuleBinding.active.is_(True)))


def _governance_snapshot(item):
    governance = item["governance"]
    profile = governance["profile"]
    return {
        "id": item["id"],
        "ref": item["ref"],
        "title": item["title"],
        "current_version_id": item["current_version_id"],
        "version_status": item["version_status"],
        "current_source_filename": item["current_source_filename"],
        "purpose_bindings": item["purpose_bindings"],
        "used_in": item["used_in"],
        "ownership": profile["content_ownership_class"],
        "artifact_kind": profile["artifact_kind"],
        "currentness": profile["currentness_status"],
        "provenance": governance["provenance"],
    }


def test_external_official_internal_template_binding_is_rejected_without_mutation(client):
    item = _create(client, used_in=["BD"])
    governed = client.patch(
        f"/api/master-content/{item['id']}/governance",
        json={
            "content_ownership_class": "EXTERNAL_OFFICIAL",
            "artifact_kind": "AUTHORITY_FORM",
            "language_profile": "EN",
            "publisher_name": "Synthetic Authority",
            "official_form_no": "AUTH-001",
            "official_issue_no": "1",
        },
        headers=OWNER,
    )
    assert governed.status_code == 200, governed.text
    provenance = client.post(
        f"/api/master-content/{item['id']}/provenance",
        json={"obtained_from": "Synthetic authority source", "source_reference": "authority://AUTH-001"},
        headers=OWNER,
    )
    assert provenance.status_code == 200, provenance.text
    currentness = client.post(
        f"/api/master-content/{item['id']}/currentness",
        json={"action": "VERIFY_CURRENT", "note": "Synthetic verification"},
        headers=OWNER,
    )
    assert currentness.status_code == 200, currentness.text

    before = client.get(f"/api/master-content/{item['id']}", headers=OWNER).json()
    attempted = client.put(
        f"/api/master-content/{item['id']}/module-bindings",
        json=[{"module": "BD", "usage_type": "PROPOSAL_TEMPLATE"}],
        headers=OWNER,
    )
    assert attempted.status_code == 422
    assert attempted.json()["detail"]["code"] == "OFFICIAL_FORM_INTERNAL_TEMPLATE_BINDING_FORBIDDEN"
    after = client.get(f"/api/master-content/{item['id']}", headers=OWNER).json()
    assert _governance_snapshot(after) == _governance_snapshot(before)


@pytest.mark.parametrize(
    "ownership,restricted",
    [
        ("EXTERNAL_OFFICIAL", False),
        ("EXTERNAL_REFERENCE", False),
        ("REFERENCE_SAMPLE", True),
        ("NEEDS_REVIEW", False),
    ],
)
def test_corrupted_unsafe_frozen_binding_is_excluded_by_resolver(client, ownership, restricted):
    item = _create(client, used_in=["BD"])
    if ownership != "NEEDS_REVIEW":
        governed = client.patch(
            f"/api/master-content/{item['id']}/governance",
            json={"content_ownership_class": ownership, "artifact_kind": "AUTHORITY_FORM", "language_profile": "EN", "restricted_reference_sample": restricted},
            headers=OWNER,
        )
        assert governed.status_code == 200, governed.text
    if ownership == "EXTERNAL_OFFICIAL":
        provenance = client.post(f"/api/master-content/{item['id']}/provenance", json={"obtained_from": "Synthetic authority source"}, headers=OWNER)
        assert provenance.status_code == 200, provenance.text
        currentness = client.post(f"/api/master-content/{item['id']}/currentness", json={"action": "VERIFY_CURRENT", "note": "Synthetic verification"}, headers=OWNER)
        assert currentness.status_code == 200, currentness.text
        refreshed = client.get(f"/api/master-content/{item['id']}/governance", headers=OWNER)
        assert refreshed.status_code == 200, refreshed.text
        assert refreshed.json()["profile"]["content_ownership_class"] == "EXTERNAL_OFFICIAL"
        assert refreshed.json()["profile"]["currentness_status"] == "VERIFIED_CURRENT"
        assert refreshed.json()["readiness"]["state"] == "MANUAL_USE_READY"
    with SessionLocal() as db:
        db.add(MasterContentModuleBinding(master_content_id=item["id"], module="BD", usage_type="PROPOSAL_TEMPLATE", active=True, created_by="controlled-test-persistence"))
        db.commit()

    resolved = client.get("/api/master-content/resolvers/BD/PROPOSAL_TEMPLATE", headers=OWNER)
    assert resolved.status_code == 200, resolved.text
    assert item["id"] not in {candidate["id"] for candidate in resolved.json()["candidates"]}


@pytest.mark.parametrize(
    "ownership,restricted",
    [
        ("EXTERNAL_OFFICIAL", False),
        ("EXTERNAL_REFERENCE", False),
        ("REFERENCE_SAMPLE", True),
        ("NEEDS_REVIEW", False),
    ],
)
def test_unsafe_ownership_classes_cannot_bind_frozen_internal_purposes(client, ownership, restricted):
    item = _create(client, used_in=["BD"])
    if ownership != "NEEDS_REVIEW":
        governed = client.patch(
            f"/api/master-content/{item['id']}/governance",
            json={"content_ownership_class": ownership, "artifact_kind": "AUTHORITY_FORM", "language_profile": "EN", "restricted_reference_sample": restricted},
            headers=OWNER,
        )
        assert governed.status_code == 200, governed.text
    before = client.get(f"/api/master-content/{item['id']}", headers=OWNER).json()
    attempted = client.put(
        f"/api/master-content/{item['id']}/module-bindings",
        json=[{"module": "BD", "usage_type": "PROPOSAL_TEMPLATE"}],
        headers=OWNER,
    )
    assert attempted.status_code == 422
    assert attempted.json()["detail"]["code"] == "OFFICIAL_FORM_INTERNAL_TEMPLATE_BINDING_FORBIDDEN"
    after = client.get(f"/api/master-content/{item['id']}", headers=OWNER).json()
    assert _governance_snapshot(after) == _governance_snapshot(before)


@pytest.mark.parametrize(
    "module,purpose",
    [("BD", "PROPOSAL_TEMPLATE"), ("BD", "PROPOSAL_CHECKLIST"), ("ADMIN", "CONTRACT_TEMPLATE")],
)
def test_amec_owned_internal_template_binds_and_resolves_exact_current_version(client, module, purpose):
    item = _create(client, used_in=[module])
    governed = client.patch(
        f"/api/master-content/{item['id']}/governance",
        json={"content_ownership_class": "AMEC_OWNED", "artifact_kind": "AMEC_FORM", "language_profile": "EN"},
        headers=OWNER,
    )
    assert governed.status_code == 200, governed.text
    before = client.get(f"/api/master-content/{item['id']}", headers=OWNER).json()
    bound = client.put(
        f"/api/master-content/{item['id']}/module-bindings",
        json=[{"module": module, "usage_type": purpose}],
        headers=OWNER,
    )
    assert bound.status_code == 200, bound.text
    after = bound.json()
    assert after["governance"]["profile"]["content_ownership_class"] == "AMEC_OWNED"
    assert after["governance"]["profile"]["content_ownership_class"] == before["governance"]["profile"]["content_ownership_class"]

    resolved = client.get(f"/api/master-content/resolvers/{module}/{purpose}", headers=OWNER)
    assert resolved.status_code == 200, resolved.text
    candidate = next(candidate for candidate in resolved.json()["candidates"] if candidate["id"] == item["id"])
    assert candidate["version_id"] == item["current_version_id"]
    with SessionLocal() as db:
        assert candidate["hash"] == db.get(DocumentVersion, item["current_version_id"]).sha256
    archived = client.post(f"/api/master-content/{item['id']}/archive", headers=OWNER)
    assert archived.status_code == 200, archived.text


def test_non_frozen_manual_form_resolution_remains_eligible(client):
    item = _create(client, used_in=["BD"])
    governed = client.patch(
        f"/api/master-content/{item['id']}/governance",
        json={"content_ownership_class": "AMEC_OWNED", "artifact_kind": "AMEC_FORM", "language_profile": "EN"},
        headers=OWNER,
    )
    assert governed.status_code == 200, governed.text
    provenance = client.post(f"/api/master-content/{item['id']}/provenance", json={"obtained_from": "Synthetic manual form source"}, headers=OWNER)
    assert provenance.status_code == 200, provenance.text
    bound = client.put(f"/api/master-content/{item['id']}/module-bindings", json=[{"module": "BD", "usage_type": "AVAILABLE"}], headers=OWNER)
    assert bound.status_code == 200, bound.text
    resolved = client.get("/api/master-content/resolvers/BD/AVAILABLE", headers=OWNER)
    assert resolved.status_code == 200, resolved.text
    assert item["id"] in {candidate["id"] for candidate in resolved.json()["candidates"]}
    archived = client.post(f"/api/master-content/{item['id']}/archive", headers=OWNER)
    assert archived.status_code == 200, archived.text


def test_dependency_mutations_require_owner_capability(client):
    item = _create(client, "REPORT")
    denied = client.post(f"/api/master-content/{item['id']}/dependencies", json={"downstream_type": "GeneratedReport", "downstream_id": f"denied-{uuid4().hex}"}, headers=BD)
    assert denied.status_code == 403
    with SessionLocal() as db:
        assert db.scalar(select(MasterContentDependency).where(MasterContentDependency.master_content_id == item["id"])) is None

    created = client.post(f"/api/master-content/{item['id']}/dependencies", json={"downstream_type": "GeneratedReport", "downstream_id": f"allowed-{uuid4().hex}"}, headers=OWNER)
    assert created.status_code == 200
    dependency_id = created.json()["id"]
    denied_revalidation = client.post(f"/api/master-content/dependencies/{dependency_id}/revalidate", headers=BD)
    assert denied_revalidation.status_code == 403


def test_definition_visibility_reference_and_revision_conflicts(client):
    term = f"Gap definition {uuid4().hex[:8]}"
    ref = f"D-GAP-{uuid4().hex[:6]}"
    created = client.post("/api/definitions", json={"term": term, "ref": ref, "description": "BD-only definition", "used_in": ["BD"]}, headers=OWNER)
    assert created.status_code == 200, created.text
    definition = created.json()
    ref_collision = client.post("/api/definitions", json={"term": f"Ref collision {uuid4().hex[:8]}", "ref": ref, "description": "Reference collision"}, headers=OWNER)
    assert ref_collision.status_code == 409
    assert ref_collision.json()["detail"]["code"] == "DEFINITION_REF_CONFLICT"
    for suffix in ("/revisions", "/module-bindings"):
        hidden = client.get(f"/api/definitions/{definition['id']}{suffix}", headers={"X-Dev-Role": "RESPONSIBLE_ENGINEER"})
        assert hidden.status_code == 403
    hidden_lookup = client.get(f"/api/definitions/lookup/{term}", headers={"X-Dev-Role": "RESPONSIBLE_ENGINEER"})
    assert hidden_lookup.status_code == 403

    other = client.post("/api/definitions", json={"term": f"Other definition {uuid4().hex[:8]}", "description": "Collision target"}, headers=OWNER)
    assert other.status_code == 200
    collision = client.post(f"/api/definitions/{definition['id']}/revisions", json={"term": other.json()["term"], "description": "Collision", "change_reason": "Negative proof", "expected_revision": 1}, headers=OWNER)
    assert collision.status_code == 409
    assert collision.json()["detail"]["code"] == "DEFINITION_TERM_CONFLICT"
    current = client.get(f"/api/definitions/{definition['id']}", headers=OWNER).json()
    assert current["revision"] == 1


def test_source_section_page_ranges_are_pinned_and_validated(client):
    item = _create(client, used_in=["BD"])
    version_id = item["current_version_id"]
    valid = client.post(f"/api/master-content/{item['id']}/source-sections", json={"document_version_id": version_id, "section_key": "valid", "label": "Valid", "page_start": 2, "page_end": 3}, headers=OWNER)
    assert valid.status_code == 200
    invalid = client.post(f"/api/master-content/{item['id']}/source-sections", json={"document_version_id": version_id, "section_key": "invalid", "label": "Invalid", "page_start": 3, "page_end": 2}, headers=OWNER)
    assert invalid.status_code == 422
    with SessionLocal() as db:
        sections = db.scalars(select(MasterContentSourceSection).where(MasterContentSourceSection.master_content_item_id == item["id"])).all()
        assert len(sections) == 1
        assert (sections[0].page_start, sections[0].page_end) == (2, 3)


def test_eligible_retrieval_requires_governed_engineering_binding_and_scope(client):
    item = _create(client, "ENGINEERING_WORK", used_in=["ENGINEERING"])
    governed = client.patch(f"/api/master-content/{item['id']}/governance", json={"content_ownership_class": "AMEC_OWNED", "artifact_kind": "TECHNICAL_WORKSHEET", "language_profile": "EN"}, headers=OWNER)
    assert governed.status_code == 200
    provenance = client.post(f"/api/master-content/{item['id']}/provenance", json={"obtained_from": "Synthetic governed source"}, headers=OWNER)
    assert provenance.status_code == 200
    eligible = client.get("/api/master-content/eligible", params={"use": "ENGINEERING_AI"}, headers=OWNER)
    assert item["id"] in {row["master_content_id"] for row in eligible.json()}
    assert item["id"] not in {row["master_content_id"] for row in client.get("/api/master-content/eligible", params={"use": "ENGINEERING_AI"}, headers=BD).json()}
