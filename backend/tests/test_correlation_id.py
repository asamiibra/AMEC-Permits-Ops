def test_correlation_id_contract(client):
    response = client.get("/health/live", headers={"X-Correlation-ID": "valid/ABC_1:2"})
    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == "valid/ABC_1:2"


def test_invalid_correlation_id_is_replaced(client):
    for value in ("x" * 129, "with space", "line\nfeed", ""):
        response = client.get("/health/live", headers={"X-Correlation-ID": value}) if value else client.get("/health/live")
        assert response.status_code == 200
        assert response.headers["X-Correlation-ID"] != value
        assert len(response.headers["X-Correlation-ID"]) == 36
