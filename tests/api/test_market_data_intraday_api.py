from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.main import app
import packages.domain.models  # noqa: F401
from packages.domain.models import DailyBar, Instrument, Market
from packages.providers.base import ProviderBar, ProviderIntradayBar
from packages.services import market_data as market_data_service
from packages.shared.database import get_session


def override_no_database_session():
    yield None


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    packages.domain.models.Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def seed_us_daily_close(session, symbol: str, trade_date: date, close: Decimal) -> None:
    market = Market(
        code="US",
        name="US Stock",
        timezone="America/New_York",
        currency="USD",
    )
    instrument = Instrument(
        symbol=symbol,
        name=symbol,
        market=market,
        asset_type="stock",
        currency="USD",
    )
    session.add_all([market, instrument])
    session.flush()
    session.add(
        DailyBar(
            instrument_id=instrument.id,
            trade_date=trade_date,
            open=close,
            high=close,
            low=close,
            close=close,
            volume=Decimal("100000"),
        )
    )
    session.commit()


def test_get_intraday_returns_verified_minute_payload_for_intraday_provider(monkeypatch):
    class FakeIntradayProvider:
        def fetch_instruments(self, market: str, exchange: str | None = None) -> list:
            return []

        def fetch_bars(self, symbol: str, timeframe: str, start: date, end: date) -> list[ProviderBar]:
            return [
                ProviderBar(
                    symbol=symbol,
                    timestamp=date(2026, 7, 1),
                    open=Decimal("213.0"),
                    high=Decimal("214.0"),
                    low=Decimal("212.0"),
                    close=Decimal("213.55"),
                    volume=Decimal("100000"),
                )
            ]

        def fetch_intraday_bars(self, symbol: str, trade_date: date, timeframe: str) -> list[ProviderIntradayBar]:
            return [
                ProviderIntradayBar(
                    symbol=symbol,
                    timestamp=datetime(2026, 7, 2, 13, 30, tzinfo=timezone.utc),
                    open=Decimal("214.1"),
                    high=Decimal("214.3"),
                    low=Decimal("213.9"),
                    close=Decimal("214.2"),
                    volume=12000,
                )
            ]

    monkeypatch.setattr(market_data_service, "get_provider", lambda provider_name=None: FakeIntradayProvider())

    app.dependency_overrides[get_session] = override_no_database_session
    try:
        client = TestClient(app)
        response = client.get(
            "/market-data/AAPL/intraday",
            params={"date": "2026-07-02", "provider": "yfinance"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert payload["timeframe"] == "1m"
    assert payload["date"] == "2026-07-02"
    assert payload["source"] == "provider"
    assert payload["provider"] == "yfinance"
    assert payload["requested_provider"] == "yfinance"
    assert payload["effective_provider"] == "yfinance"
    assert payload["status"] == "ok"
    assert payload["previous_close"] == 213.55
    assert payload["items"] == [
        {
            "timestamp": "2026-07-02T13:30:00+00:00",
            "open": 214.1,
            "high": 214.3,
            "low": 213.9,
            "close": 214.2,
            "price": 214.2,
            "average_price": None,
            "volume": 12000,
            "amount": None,
        }
    ]
    assert payload["availability"] == {
        "status": "ok",
        "reason": None,
        "is_realtime": False,
        "is_delayed": True,
        "delay_minutes": None,
    }
    assert payload["freshness"]["status"] == "fresh"
    assert payload["freshness"]["cache_status"] == "unavailable"
    assert payload["session"]["status"] == "closed_session"
    assert payload["session"]["trading_date"] == "2026-07-02"


def test_get_intraday_returns_persistent_cache_hit_without_provider_call(monkeypatch):
    session = make_session()
    seed_us_daily_close(session, "AAPL", date(2026, 7, 1), Decimal("213.55"))

    class CountingIntradayProvider:
        def __init__(self) -> None:
            self.intraday_calls = 0

        def fetch_instruments(self, market: str, exchange: str | None = None) -> list:
            return []

        def fetch_bars(self, symbol: str, timeframe: str, start: date, end: date) -> list[ProviderBar]:
            raise AssertionError("API cache hit should not call provider daily bars")

        def fetch_intraday_bars(self, symbol: str, trade_date: date, timeframe: str) -> list[ProviderIntradayBar]:
            self.intraday_calls += 1
            return [
                ProviderIntradayBar(
                    symbol=symbol,
                    timestamp=datetime(2026, 7, 2, 13, 30, tzinfo=timezone.utc),
                    open=Decimal("214.1"),
                    high=Decimal("214.3"),
                    low=Decimal("213.9"),
                    close=Decimal("214.2"),
                    volume=12000,
                )
            ]

    provider = CountingIntradayProvider()
    monkeypatch.setattr(market_data_service, "get_provider", lambda provider_name=None: provider)

    def override_database_session():
        yield session

    app.dependency_overrides[get_session] = override_database_session
    try:
        client = TestClient(app)
        first_response = client.get(
            "/market-data/AAPL/intraday",
            params={"date": "2026-07-02", "provider": "yfinance"},
        )
        second_response = client.get(
            "/market-data/AAPL/intraday",
            params={"date": "2026-07-02", "provider": "yfinance"},
        )
    finally:
        app.dependency_overrides.clear()

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert provider.intraday_calls == 1
    first_payload = first_response.json()
    second_payload = second_response.json()
    assert first_payload["source"] == "provider"
    assert first_payload["freshness"]["cache_status"] == "miss"
    assert second_payload["source"] == "cache"
    assert second_payload["freshness"]["cache_status"] == "hit"
    assert second_payload["items"] == first_payload["items"]


def test_get_intraday_returns_degraded_when_verified_minute_bars_are_unsupported(monkeypatch):
    class UnsupportedIntradayProvider:
        def fetch_instruments(self, market: str, exchange: str | None = None) -> list:
            return []

        def fetch_bars(self, symbol: str, timeframe: str, start: date, end: date) -> list:
            return []

    monkeypatch.setattr(market_data_service, "get_provider", lambda provider_name=None: UnsupportedIntradayProvider())

    app.dependency_overrides[get_session] = override_no_database_session
    try:
        client = TestClient(app)
        response = client.get(
            "/market-data/AAPL/intraday",
            params={"date": "2026-07-03", "provider": "mock"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert payload["provider"] == "mock"
    assert payload["status"] == "degraded"
    assert payload["items"] == []
    assert payload["availability"] == {
        "status": "degraded",
        "reason": market_data_service.INTRADAY_UNSUPPORTED_REASON,
        "is_realtime": False,
        "is_delayed": False,
        "delay_minutes": None,
    }
    assert payload["freshness"]["status"] == "unsupported"
    assert payload["freshness"]["cache_status"] == "skipped"
    assert payload["session"]["status"] == "unsupported_market"


def test_get_intraday_uses_platform_default_provider_when_omitted(monkeypatch):
    monkeypatch.setattr(
        market_data_service,
        "get_effective_market_data_provider",
        lambda requested=None: "mock" if requested is None else str(requested).strip().lower(),
    )

    app.dependency_overrides[get_session] = override_no_database_session
    try:
        client = TestClient(app)
        response = client.get(
            "/market-data/AAPL/intraday",
            params={"date": "2026-07-03"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["requested_provider"] is None
    assert payload["effective_provider"] == "mock"
    assert payload["status"] == "degraded"
    assert payload["items"] == []


def test_get_intraday_returns_weekend_no_data_without_minute_provider_call(monkeypatch):
    class WeekendIntradayProvider:
        def fetch_instruments(self, market: str, exchange: str | None = None) -> list:
            return []

        def fetch_bars(self, symbol: str, timeframe: str, start: date, end: date) -> list[ProviderBar]:
            raise AssertionError("weekend no-data should not call daily provider data")

        def fetch_intraday_bars(self, symbol: str, trade_date: date, timeframe: str) -> list[ProviderIntradayBar]:
            raise AssertionError("weekend no-data should not call the provider minute endpoint")

    monkeypatch.setattr(market_data_service, "get_provider", lambda provider_name=None: WeekendIntradayProvider())

    app.dependency_overrides[get_session] = override_no_database_session
    try:
        client = TestClient(app)
        response = client.get(
            "/market-data/AAPL/intraday",
            params={"date": "2026-07-04", "provider": "yfinance"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert payload["date"] == "2026-07-04"
    assert payload["provider"] == "yfinance"
    assert payload["status"] == "no_data"
    assert payload["source"] == "none"
    assert payload["previous_close"] is None
    assert payload["items"] == []
    assert payload["availability"]["status"] == "no_data"
    assert payload["availability"]["reason"] == market_data_service.INTRADAY_WEEKEND_NO_DATA_REASON
    assert payload["freshness"]["status"] == "no_data"
    assert payload["freshness"]["cache_status"] == "skipped"
    assert payload["session"]["status"] == "weekend"


def test_get_intraday_returns_future_no_data_without_minute_provider_call(monkeypatch):
    class FutureIntradayProvider:
        def fetch_instruments(self, market: str, exchange: str | None = None) -> list:
            return []

        def fetch_bars(self, symbol: str, timeframe: str, start: date, end: date) -> list[ProviderBar]:
            raise AssertionError("future no-data should not call daily provider data")

        def fetch_intraday_bars(self, symbol: str, trade_date: date, timeframe: str) -> list[ProviderIntradayBar]:
            raise AssertionError("future no-data should not call the provider minute endpoint")

    monkeypatch.setattr(market_data_service, "get_provider", lambda provider_name=None: FutureIntradayProvider())

    future_trade_date = date.today() + market_data_service.timedelta(days=1)
    app.dependency_overrides[get_session] = override_no_database_session
    try:
        client = TestClient(app)
        response = client.get(
            "/market-data/AAPL/intraday",
            params={"date": future_trade_date.isoformat(), "provider": "yfinance"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert payload["date"] == future_trade_date.isoformat()
    assert payload["provider"] == "yfinance"
    assert payload["status"] == "no_data"
    assert payload["source"] == "none"
    assert payload["previous_close"] is None
    assert payload["items"] == []
    assert payload["availability"]["status"] == "no_data"
    assert payload["availability"]["reason"] == market_data_service.INTRADAY_FUTURE_NO_DATA_REASON
    assert payload["freshness"]["status"] == "no_data"
    assert payload["freshness"]["cache_status"] == "skipped"
    assert payload["session"]["status"] == "future_date"


def test_get_intraday_returns_known_us_holiday_no_data_without_minute_provider_call(monkeypatch):
    class HolidayIntradayProvider:
        def fetch_instruments(self, market: str, exchange: str | None = None) -> list:
            return []

        def fetch_bars(self, symbol: str, timeframe: str, start: date, end: date) -> list[ProviderBar]:
            raise AssertionError("known holiday no-data should not call daily provider data")

        def fetch_intraday_bars(self, symbol: str, trade_date: date, timeframe: str) -> list[ProviderIntradayBar]:
            raise AssertionError("known holiday no-data should not call the provider minute endpoint")

    monkeypatch.setattr(market_data_service, "get_provider", lambda provider_name=None: HolidayIntradayProvider())

    app.dependency_overrides[get_session] = override_no_database_session
    try:
        client = TestClient(app)
        response = client.get(
            "/market-data/AAPL/intraday",
            params={"date": "2026-07-03", "provider": "yfinance"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert payload["date"] == "2026-07-03"
    assert payload["provider"] == "yfinance"
    assert payload["status"] == "no_data"
    assert payload["source"] == "none"
    assert payload["previous_close"] is None
    assert payload["items"] == []
    assert payload["availability"]["status"] == "no_data"
    assert payload["availability"]["reason"] == market_data_service.INTRADAY_KNOWN_HOLIDAY_NO_DATA_REASON


def test_get_intraday_returns_movable_us_holiday_no_data_without_minute_provider_call(monkeypatch):
    class MovableHolidayIntradayProvider:
        def fetch_instruments(self, market: str, exchange: str | None = None) -> list:
            return []

        def fetch_bars(self, symbol: str, timeframe: str, start: date, end: date) -> list[ProviderBar]:
            raise AssertionError("movable holiday no-data should not call daily provider data")

        def fetch_intraday_bars(self, symbol: str, trade_date: date, timeframe: str) -> list[ProviderIntradayBar]:
            raise AssertionError("movable holiday no-data should not call the provider minute endpoint")

    monkeypatch.setattr(market_data_service, "get_provider", lambda provider_name=None: MovableHolidayIntradayProvider())

    app.dependency_overrides[get_session] = override_no_database_session
    try:
        client = TestClient(app)
        response = client.get(
            "/market-data/AAPL/intraday",
            params={"date": "2026-04-03", "provider": "yfinance"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert payload["date"] == "2026-04-03"
    assert payload["provider"] == "yfinance"
    assert payload["status"] == "no_data"
    assert payload["source"] == "none"
    assert payload["previous_close"] is None
    assert payload["items"] == []
    assert payload["availability"]["status"] == "no_data"
    assert payload["availability"]["reason"] == market_data_service.INTRADAY_KNOWN_HOLIDAY_NO_DATA_REASON


def test_get_intraday_rejects_unsupported_timeframes():
    app.dependency_overrides[get_session] = override_no_database_session
    try:
        client = TestClient(app)
        response = client.get(
            "/market-data/AAPL/intraday",
            params={"date": "2026-07-03", "timeframe": "5m", "provider": "mock"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported intraday timeframe: 5m. Only 1m is supported."
