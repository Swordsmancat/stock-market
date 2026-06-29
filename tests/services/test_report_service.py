from datetime import date

from packages.services.reports import generate_stock_report_payload


def test_generate_stock_report_payload_uses_market_data_citation():
    payload = generate_stock_report_payload("AAPL", date(2026, 1, 1), date(2026, 1, 15))

    assert payload["symbol"] == "AAPL"
    assert payload["report_type"] == "stock_daily"
    assert "# AAPL AI 个股报告" in payload["content_markdown"]
    assert "bars_1d:AAPL:2026-01-15" in payload["citations"]
