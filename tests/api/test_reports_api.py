from fastapi.testclient import TestClient

from apps.api.main import app
from packages.shared.database import get_session


def override_no_database_session():
    yield None


def test_generate_stock_report_returns_markdown_with_citations():
    app.dependency_overrides[get_session] = override_no_database_session
    try:
        client = TestClient(app)
        response = client.get(
            "/reports/AAPL/stock",
            params={"start": "2026-01-01", "end": "2026-01-15"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert payload["report_type"] == "stock_daily"
    assert "# AAPL AI 个股报告" in payload["content_markdown"]
    assert "bars_1d:AAPL:2026-01-15" in payload["citations"]
    assert "本报告仅基于平台内可验证数据生成" in payload["content_markdown"]
