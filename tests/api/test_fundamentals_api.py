from fastapi.testclient import TestClient

from apps.api.main import app


def test_fundamentals_api_returns_mock_metrics_with_citation():
    client = TestClient(app)

    response = client.get("/fundamentals/AAPL", params={"as_of": "2026-01-20"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert payload["source"] == "mock_fundamentals"
    assert payload["as_of"] == "2026-01-20"
    assert payload["citation"] == "fundamental_metrics:AAPL:2026-01-20"
    assert payload["item"]["pe_ratio"] == 28.4
    assert payload["item"]["revenue_growth"] == 0.08
    assert "PE 28.40" in payload["item"]["summary"]
