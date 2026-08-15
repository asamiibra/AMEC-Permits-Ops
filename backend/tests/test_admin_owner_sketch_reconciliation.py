"""Owner-sketch register invariants over the existing canonical APIs."""


OWNER = {"X-Dev-Role": "SYSTEM_ADMIN"}


def test_contract_lane_counts_and_search_are_backend_derived(client):
    all_rows = client.get("/api/admin/contracts", params={"filter": "ALL"}, headers=OWNER)
    assert all_rows.status_code == 200
    body = all_rows.json()
    assert body["count"] == len(body["items"])
    for lane in ("ALL", "NEEDS_ACTION", "AUTHORITY_REVIEW", "READY_CLOSE"):
        response = client.get("/api/admin/contracts", params={"filter": lane}, headers=OWNER)
        assert response.status_code == 200
        filtered = response.json()
        assert filtered["count"] == len(filtered["items"])
        if lane == "AUTHORITY_REVIEW":
            assert all(item["stage"] == "AUTHORITY_REVIEW" for item in filtered["items"])
        if lane == "NEEDS_ACTION":
            assert all(item["blockers_count"] > 0 for item in filtered["items"])
    if body["items"]:
        reference = body["items"][0]["contract_reference"]
        searched = client.get("/api/admin/contracts", params={"q": reference, "filter": "ALL"}, headers=OWNER)
        assert searched.status_code == 200
        assert searched.json()["count"] >= 1


def test_invoice_lane_counts_and_search_are_backend_derived(client):
    response = client.get("/api/billing/invoices", headers=OWNER)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == len(body["items"])
    assert {"all", "need_action", "authority_review", "ready_close"} <= set(body["lanes"])
    for lane in ("ALL", "NEED_ACTION", "AUTHORITY_REVIEW", "READY_CLOSE"):
        filtered = client.get("/api/billing/invoices", params={"lane": lane}, headers=OWNER)
        assert filtered.status_code == 200
        assert filtered.json()["total"] == len(filtered.json()["items"])
    if body["items"]:
        reference = body["items"][0]["invoice"]["invoice_reference"]
        searched = client.get("/api/billing/invoices", params={"q": reference}, headers=OWNER)
        assert searched.status_code == 200
        assert searched.json()["total"] >= 1
