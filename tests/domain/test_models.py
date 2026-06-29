from packages.domain.models import Instrument, Market


def test_instrument_has_market_identity():
    market = Market(code="US", name="US Stock", timezone="America/New_York", currency="USD")
    instrument = Instrument(symbol="AAPL", name="Apple Inc.", asset_type="stock", currency="USD")
    instrument.market = market
    assert instrument.market.code == "US"
    assert instrument.symbol == "AAPL"
