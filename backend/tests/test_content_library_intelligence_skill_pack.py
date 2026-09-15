from __future__ import annotations

import json
from uuid import uuid4

from backend.app.ai.skill_registry import SKILL_REGISTRY
from backend.app.ai.structured_output import _strict_schema, ContentLibraryCandidateOutput
from backend.app.db import SessionLocal
from backend.app.models import DocumentVersion


OWNER = {"X-Dev-Role": "SYSTEM_ADMIN"}
BD = {"X-Dev-Role": "PROCESS_CHAMPION"}

CONTENT_SKILLS = (
    "master-content.intake-governance-analysis",
    "master-content.quality-gap-analysis",
    "master-content.version-change-analysis",
    "master-content.dependency-impact-analysis",
    "master-content.reuse-applicability-analysis",
    "master-content.description-draft",
    "master-content.source-grounded-assist",
)


def test_content_library_pack_is_exactly_registered_and_non_authoritative():
    rows = SKILL_REGISTRY.snapshot()
    definitions = [definition for key, definition in rows.items() if key[0].startswith("master-content.")]
    assert {definition.manifest.skill_id for definition in definitions} == set(CONTENT_SKILLS)
    assert len(definitions) == 7
    for definition in definitions:
        manifest = definition.manifest
        assert manifest.owning_module == "master_content"
        assert tuple(manifest.allowed_scope_types) == ("MASTER_CONTENT_ITEM", "DEFINITION_ENTRY")
        assert tuple(manifest.allowed_tools) == ()
        assert manifest.canonical_write_authority == "NONE"
        assert manifest.protected_action_authority == "NONE"
        assert manifest.canonical_or_protected_authority == "NONE"
        assert manifest.review_trigger == "ALWAYS"
        assert manifest.output_class in {"CANDIDATE", "ANALYSIS", "RECOMMENDATION", "DRAFT"}
        assert definition.output.provider_schema["additionalProperties"] is False


def test_content_library_provider_schemas_are_azure_strict():
    schema = _strict_schema(ContentLibraryCandidateOutput)

    def visit(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node["additionalProperties"] is False
                assert set(node["required"]) == set(node.get("properties", {}))
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(schema)
    metadata = schema["properties"]["candidate_metadata"]
    assert metadata["properties"] == {}
    assert metadata["required"] == []


def _form(client):
    category = client.get("/api/master-content/categories", headers=OWNER)
    assert category.status_code == 200, category.text
    category_id = next(row["id"] for row in category.json() if "FORM" in row["allowed_content_types"])
    response = client.post(
        "/api/master-content",
        data={
            "content_type": "FORM",
            "ref": f"AI-CL-{uuid4().hex[:8]}",
            "title": "Content Library intelligence fixture",
            "description": "Synthetic governed fixture",
            "category_id": category_id,
            "used_in": json.dumps(["ADMIN"]),
            "needs_review": "false",
        },
        files={"file": ("content-library.txt", b"synthetic governed source", "text/plain")},
        headers={**OWNER, "Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _definition(client):
    response = client.post(
        "/api/definitions",
        json={
            "term": f"AI Content Library {uuid4().hex[:8]}",
            "category": "Reference",
            "description": "Synthetic governed definition fixture",
            "used_in": ["ADMIN"],
        },
        headers=OWNER,
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_content_library_intelligence_uses_shared_runtime_and_requires_owner_review(client):
    item = _form(client)
    with SessionLocal() as db:
        version = db.get(DocumentVersion, item["current_version_id"])
        version.source_system = "SYNTHETIC"
        version.source_path_or_reference = "synthetic://content-library/intelligence-fixture"
        version.metadata_json = {**(version.metadata_json or {}), "synthetic_only": True, "master_status": "CURRENT"}
        db.commit()
    response = client.post(
        f"/api/master-content/{item['id']}/intelligence/master-content.description-draft",
        headers={**OWNER, "Idempotency-Key": "content-library-intelligence-once"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["review_required"] is True
    assert payload["canonical_state_mutated"] is False
    assert payload["protected_action_count"] == 0
    assert payload["review_task_id"]
    assert payload["work_product_id"]
    assert payload["output"]["draft_only"] is True
    assert payload["output"]["human_review_required"] is True

    replay = client.post(
        f"/api/master-content/{item['id']}/intelligence/master-content.description-draft",
        headers={**OWNER, "Idempotency-Key": "content-library-intelligence-once"},
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["review_task_id"] == payload["review_task_id"]
    reviews = client.get(f"/api/master-content/{item['id']}/intelligence/reviews", headers=OWNER)
    assert reviews.status_code == 200, reviews.text
    assert len(reviews.json()["reviews"]) == 1

    denied = client.post(
        f"/api/master-content/{item['id']}/intelligence/master-content.quality-gap-analysis",
        headers={**BD, "Idempotency-Key": str(uuid4())},
    )
    assert denied.status_code == 403, denied.text


def test_content_library_owner_can_review_complete_structured_results_without_canonical_mutation(client):
    item = _form(client)
    with SessionLocal() as db:
        version = db.get(DocumentVersion, item["current_version_id"])
        version.source_system = "SYNTHETIC"
        version.source_path_or_reference = "synthetic://content-library/seven-skill-fixture"
        version.metadata_json = {**(version.metadata_json or {}), "synthetic_only": True, "master_status": "CURRENT"}
        db.commit()
    skill_results = {}
    for index, skill_id in enumerate(CONTENT_SKILLS):
        response = client.post(
            f"/api/master-content/{item['id']}/intelligence/{skill_id}",
            headers={**OWNER, "Idempotency-Key": f"content-library-seven-{index}"},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        skill_results[skill_id] = payload
        assert payload["output"]["citations"]
        assert payload["citations"]
        assert payload["output"]["findings"]
        assert payload["output"]["human_review_required"] is True
        assert payload["output"]["canonical_state_mutated"] is False
        assert payload["review_precondition_version"]

    description = skill_results["master-content.description-draft"]
    assert description["draft_fields"]["title"] == "Content Library intelligence fixture"
    assert description["draft_fields"]["description"]
    review = client.post(
        f"/api/master-content/{item['id']}/intelligence/{description['work_product_id']}/review",
        json={
            "decision": "ACCEPT",
            "idempotency_key": "content-library-seven-review",
            "precondition_version": description["review_precondition_version"],
            "accepted_fields": description["draft_fields"],
            "reason": "Owner accepted the reviewed description draft.",
        },
        headers=OWNER,
    )
    assert review.status_code == 200, review.text
    assert review.json()["decision"] == "ACCEPT"
    assert review.json()["accepted_fields"] == description["draft_fields"]
    assert review.json()["canonical_state_mutated"] is False

    persisted = client.get(f"/api/master-content/{item['id']}", headers=OWNER)
    assert persisted.status_code == 200, persisted.text
    assert persisted.json()["title"] == item["title"]
    assert persisted.json()["description"] == item["description"]
    reviews = client.get(f"/api/master-content/{item['id']}/intelligence/reviews", headers=OWNER)
    assert reviews.status_code == 200, reviews.text
    assert any(row["decision"] == "ACCEPT" for row in reviews.json()["reviews"])


def test_content_library_intelligence_is_available_for_definitions(client):
    definition = _definition(client)
    results = {}
    for index, skill_id in enumerate(CONTENT_SKILLS):
        response = client.post(
            f"/api/definitions/{definition['id']}/intelligence/{skill_id}",
            headers={**OWNER, "Idempotency-Key": f"content-library-definition-{index}"},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        results[skill_id] = payload
        assert payload["citations"]
        assert payload["output"]["findings"]
        assert payload["review_precondition_version"]
        assert payload["canonical_state_mutated"] is False

    description = results["master-content.description-draft"]
    assert description["draft_fields"]["description"]
    review = client.post(
        f"/api/definitions/{definition['id']}/intelligence/{description['work_product_id']}/review",
        json={
            "decision": "ACCEPT",
            "idempotency_key": "content-library-definition-review",
            "precondition_version": description["review_precondition_version"],
            "accepted_fields": description["draft_fields"],
            "reason": "Owner accepted the reviewed definition draft.",
        },
        headers=OWNER,
    )
    assert review.status_code == 200, review.text
    assert review.json()["canonical_state_mutated"] is False
    persisted = client.get(f"/api/definitions/{definition['id']}", headers=OWNER)
    assert persisted.status_code == 200, persisted.text
    assert persisted.json()["description"] == definition["description"]
