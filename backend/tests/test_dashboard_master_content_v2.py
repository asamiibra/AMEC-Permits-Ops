import re
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

from backend.app.db import SessionLocal, engine
from backend.app.services.master_content import create_master_content


def _create(client, content_type, title, filename="source.txt", body=b"source", used_in=None, role="SYSTEM_ADMIN", idempotency_key=None, ref=None):
    data = {"content_type": content_type, "title": title}
    if used_in is not None:
        data["used_in"] = used_in
    if ref is not None:
        data["ref"] = ref
    return client.post("/api/master-content", data=data, files={"file": (filename, body, "application/pdf" if filename.endswith(".pdf") else "text/plain")}, headers={"X-Dev-Role": role, "Idempotency-Key": idempotency_key or str(uuid4())})


def test_v2_auto_references_are_stable_and_sor_preview_is_truthful(client):
    form = _create(client, "FORM", "Auto Form", used_in='["MY_WORK","BD","ADMIN","PERMIT"]')
    report = _create(client, "REPORT", "Auto Report")
    engineering = _create(client, "ENGINEERING_WORK", "Auto Engineering")
    definition = client.post("/api/definitions", json={"term": f"Client ID {uuid4().hex[:6]}", "category": "Client", "description": "Synthetic identifier", "used_in": ["BD", "PERMIT"]}, headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert form.status_code == report.status_code == engineering.status_code == definition.status_code == 200
    assert re.fullmatch(r"F-\d{4}", form.json()["ref"])
    assert re.fullmatch(r"R-\d{4}", report.json()["ref"])
    assert re.fullmatch(r"E-\d{4}", engineering.json()["ref"])
    assert re.fullmatch(r"D-\d{4}", definition.json()["ref"])
    assert form.json()["used_in"] == ["ADMIN", "BD", "MY_WORK", "PERMIT"]
    assert form.json()["preview"]["status"] == "RENDITION_NOT_AVAILABLE"

    pdf = _create(client, "FORM", "PDF Form", filename="source.pdf", body=b"%PDF-synthetic")
    assert pdf.status_code == 200, pdf.text
    assert pdf.json()["preview"] == {"status": "SOURCE_PDF", "available": True}
    version_id = pdf.json()["current_version_id"]
    rendition = client.get(f"/api/master-content/{pdf.json()['id']}/versions/{version_id}/rendition")
    assert rendition.status_code == 200
    assert rendition.content == b"%PDF-synthetic"


def test_v2_module_bindings_metadata_patch_and_ai_disabled(client):
    created = _create(client, "REPORT", "Binding Report")
    assert created.status_code == 200, created.text
    item = created.json()
    bindings = client.put(f"/api/master-content/{item['id']}/module-bindings", json=[{"module": "REPORTS", "usage_type": "REPORT_SOURCE"}, {"module": "ENGINEERING", "usage_type": "REFERENCE"}], headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert bindings.status_code == 200, bindings.text
    assert bindings.json()["used_in"] == ["ENGINEERING", "REPORTS"]
    assert client.get("/api/master-content", params={"content_type": "REPORT", "module": "REPORTS"}).json()[0]["id"] == item["id"]

    patched = client.patch(f"/api/master-content/{item['id']}/metadata", json={"description": "Updated meaning", "used_in": ["REPORTS"], "change_reason": "Owner metadata correction"}, headers={"X-Dev-Role": "SYSTEM_ADMIN", "Idempotency-Key": str(uuid4())})
    assert patched.status_code == 200, patched.text
    assert patched.json()["description"] == "Updated meaning"
    assert patched.json()["used_in"] == ["REPORTS"]
    assert len(patched.json()["versions"]) == 1
    assert patched.json()["versions"][0]["change_kind"] == "CREATE"

    denied = client.put(f"/api/master-content/{item['id']}/module-bindings", json=[], headers={"X-Dev-Role": "COMMERCIAL_APPROVER"})
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "CAPABILITY_DENIED"
    ai = client.post("/api/master-content/ai-assist", json={"request_type": "CATEGORY_SUGGESTION"}, headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert ai.status_code == 409
    assert ai.json()["detail"]["code"] == "AI_ASSIST_NOT_ENABLED"


def test_v2_metadata_edit_keeps_current_document_version(client):
    created = _create(client, "FORM", "Metadata Form")
    assert created.status_code == 200, created.text
    item = created.json()
    original_version = item["current_version_id"]
    patched = client.patch(f"/api/master-content/{item['id']}/metadata", json={"description": "Owner wording", "used_in": ["ADMIN"], "change_reason": "Clarify owner instructions"}, headers={"X-Dev-Role": "SYSTEM_ADMIN", "Idempotency-Key": str(uuid4())})
    assert patched.status_code == 200, patched.text
    assert patched.json()["current_version_id"] == original_version
    assert len(patched.json()["versions"]) == 1
    assert patched.json()["description"] == "Owner wording"


def test_v2_create_retry_is_idempotent_without_consuming_a_reference(client):
    key = str(uuid4())
    first = _create(client, "FORM", "Idempotent Form", idempotency_key=key)
    retry = _create(client, "FORM", "Idempotent Form", idempotency_key=key)
    next_item = _create(client, "FORM", "Next Form")
    assert first.status_code == retry.status_code == next_item.status_code == 200
    assert retry.json()["id"] == first.json()["id"]
    assert retry.json()["ref"] == first.json()["ref"]
    assert int(next_item.json()["ref"].split("-")[-1]) == int(first.json()["ref"].split("-")[-1]) + 1


def test_v2_postgresql_reference_allocation_is_concurrency_safe():
    if engine.dialect.name != "postgresql":
        pytest.skip("concurrency proof requires PostgreSQL row locking")

    def create_one(index):
        with SessionLocal() as db:
            return create_master_content(
                db,
                content_type="REPORT",
                ref=None,
                title=f"Concurrent Report {uuid4().hex[:8]}-{index}",
                category_id=None,
                description="Concurrency proof",
                filename=f"concurrent-{index}.txt",
                mime_type="text/plain",
                content=f"concurrent-{index}".encode(),
                actor="SYSTEM_ADMIN",
                idempotency_key=str(uuid4()),
                correlation_id=str(uuid4()),
            )["ref"]

    with ThreadPoolExecutor(max_workers=8) as pool:
        refs = list(pool.map(create_one, range(8)))
    assert len(refs) == len(set(refs)) == 8


def test_v2_definition_revision_retains_category_and_used_in_history(client):
    created = client.post("/api/definitions", json={"term": f"Project Reference {uuid4().hex[:6]}", "category": "Project", "description": "Initial meaning", "used_in": ["PROPOSAL"]}, headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert created.status_code == 200, created.text
    row = created.json()
    revised = client.post(f"/api/definitions/{row['id']}/revisions", json={"term": row["term"], "category": "Contract", "description": "Updated meaning", "used_in": ["CONTRACT"], "change_reason": "Owner clarification", "expected_revision": 1}, headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert revised.status_code == 200, revised.text
    history = revised.json()["revisions"]
    assert history[0]["category"] == "Contract"
    assert history[0]["used_in"] == ["CONTRACT"]
    assert history[1]["category"] == "Project"
    assert history[1]["used_in"] == ["PROPOSAL"]
