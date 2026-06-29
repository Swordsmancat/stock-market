from datetime import date

from packages.providers.mock_provider import MockProvider


def test_mock_provider_returns_bars_for_symbol():
    provider = MockProvider()
    bars = provider.fetch_bars("AAPL", "1d", date(2026, 1, 1), date(2026, 1, 3))
    assert len(bars) == 3
    assert bars[0].symbol == "AAPL"
    assert bars[0].close > 0
