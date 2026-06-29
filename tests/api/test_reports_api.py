from fastapi.testclient import TestClient

from apps.api.main import app


def test_generate_stock_report_returns_markdown_with_citations():
    client = TestClient(app)
    response = client.get(
        "/reports/AAPL/stock",
        params={"start": "2026-01-01", "end": "2026-01-15"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert payload["report_type"] == "stock_daily"
    assert "# AAPL AI 个股报告" in payload["content_markdown"]
    assert "bars_1d:AAPL:2026-01-15" in payload["citations"]
    assert "本报告仅基于平台内可验证数据生成" in payload["content_markdown"]
