from packages.services.portfolios import get_demo_portfolio_payload


def test_get_demo_portfolio_payload_uses_latest_market_data_price():
    payload = get_demo_portfolio_payload()

    assert payload["id"] == "demo"
    assert payload["positions"][0]["symbol"] == "AAPL"
    assert payload["positions"][0]["latest_price"] == 101.0
    assert payload["positions"][0]["market_value"] == 1010.0
    assert payload["recommendation"]["status"] == "simulated"
