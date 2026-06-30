from datetime import date

from packages.services.fundamentals import get_fundamental_payload


def test_get_fundamental_payload_returns_mock_metrics_with_citation():
    payload = get_fundamental_payload("AAPL", as_of=date(2026, 1, 20))

    assert payload["symbol"] == "AAPL"
    assert payload["source"] == "mock_fundamentals"
    assert payload["citation"] == "fundamental_metrics:AAPL:2026-01-20"
    assert payload["item"]["pe_ratio"] == 28.4
    assert "PE 28.40" in payload["item"]["summary"]
