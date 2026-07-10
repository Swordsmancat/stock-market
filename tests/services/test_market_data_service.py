from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.domain.models import DailyBar, Instrument, IntradayMinuteCacheEntry, Market, MinuteBar
from packages.services import market_data as market_data_service
from packages.services.market_data import (
    MarketDataProviderError,
    MarketDataProviderPayloadError,
    MarketDataProviderRateLimitError,
    MarketDataProviderTimeoutError,
    MarketDataProviderUnavailableError,
    get_bars_payload,
    get_indicator_payload,
    get_intraday_bars_payload,
    get_latest_bar_payload,
    get_latest_bars_batch_payload,
    get_market_snapshot,
)
from packages.providers.base import ProviderBar
from packages.providers.base import ProviderFundFlow
from packages.providers.base import ProviderIntradayBar
from packages.providers.base import ProviderMarketDepthSnapshot
from packages.providers.base import ProviderOrderBookLevel
from packages.providers.base import ProviderRecentTrade


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


def test_get_bars_payload_serializes_provider_bars():
    payload = get_bars_payload(
        "AAPL",
        "1d",
        date(2026, 1, 1),
        date(2026, 1, 3),
        provider_name="mock",
    )

    assert payload["symbol"] == "AAPL"
    assert payload["timeframe"] == "1d"
    assert len(payload["items"]) == 3
    assert payload["items"][0]["close"] == 101.0


def test_get_bars_payload_reports_effective_provider_source():
    payload = get_bars_payload(
        "AAPL",
        "1d",
        date(2026, 1, 1),
        date(2026, 1, 1),
        provider_name=" Mock ",
    )

    assert payload["source"] == "mock"


def test_get_bars_payload_uses_platform_default_when_provider_is_omitted(monkeypatch):
    monkeypatch.setattr(
        market_data_service,
        "get_effective_market_data_provider",
        lambda requested=None: "mock" if requested is None else str(requested).strip().lower(),
    )

    payload = get_bars_payload(
        "AAPL",
        "1d",
        date(2026, 1, 1),
        date(2026, 1, 1),
        provider_name=None,
    )

    assert payload["source"] == "mock"


def test_get_bars_payload_marks_empty_provider_results_as_no_data():
    payload = get_bars_payload(
        "AAPL",
        "1d",
        date(2026, 1, 2),
        date(2026, 1, 1),
        provider_name="mock",
    )

    assert payload["items"] == []
    assert payload["status"] == "no_data"
    assert (
        payload["no_data_reason"]
        == "No daily bars were available for the requested symbol/date range."
    )


def test_get_intraday_bars_payload_returns_verified_provider_minutes(monkeypatch):
    class FakeIntradayProvider:
        def fetch_instruments(self, market: str, exchange: str | None = None) -> list:
            return []

        def fetch_bars(
            self, symbol: str, timeframe: str, start: date, end: date
        ) -> list[ProviderBar]:
            assert timeframe == "1d"
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

        def fetch_intraday_bars(
            self, symbol: str, trade_date: date, timeframe: str
        ) -> list[ProviderIntradayBar]:
            assert symbol == "AAPL"
            assert trade_date == date(2026, 7, 2)
            assert timeframe == "1m"
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

    monkeypatch.setattr(
        market_data_service, "get_provider", lambda provider_name=None: FakeIntradayProvider()
    )

    payload = get_intraday_bars_payload(
        "AAPL",
        date(2026, 7, 2),
        provider_name="yfinance",
    )

    assert payload["status"] == "ok"
    assert payload["source"] == "provider"
    assert payload["provider"] == "yfinance"
    assert payload["previous_close"] == 213.55
    assert payload["availability"] == {
        "status": "ok",
        "reason": None,
        "is_realtime": False,
        "is_delayed": True,
        "delay_minutes": None,
    }
    assert payload["freshness"]["status"] == "fresh"
    assert payload["freshness"]["cache_status"] == "unavailable"
    assert payload["freshness"]["data_as_of"] == "2026-07-02T13:30:00+00:00"
    assert payload["session"]["status"] == "closed_session"
    assert payload["session"]["trading_date"] == "2026-07-02"
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


def test_get_intraday_bars_payload_reuses_persistent_cache_without_provider_call(monkeypatch):
    session = make_session()
    seed_us_daily_close(session, "AAPL", date(2026, 7, 1), Decimal("213.55"))

    class CountingIntradayProvider:
        def __init__(self) -> None:
            self.daily_calls = 0
            self.intraday_calls = 0

        def fetch_instruments(self, market: str, exchange: str | None = None) -> list:
            return []

        def fetch_bars(
            self, symbol: str, timeframe: str, start: date, end: date
        ) -> list[ProviderBar]:
            self.daily_calls += 1
            raise AssertionError("cache-covered previous close should be read from the database")

        def fetch_intraday_bars(
            self, symbol: str, trade_date: date, timeframe: str
        ) -> list[ProviderIntradayBar]:
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
                    amount=Decimal("2570400"),
                )
            ]

    provider = CountingIntradayProvider()
    monkeypatch.setattr(market_data_service, "get_provider", lambda provider_name=None: provider)

    first_payload = get_intraday_bars_payload(
        "AAPL",
        date(2026, 7, 2),
        session=session,
        provider_name="yfinance",
    )
    second_payload = get_intraday_bars_payload(
        "AAPL",
        date(2026, 7, 2),
        session=session,
        provider_name="yfinance",
    )

    assert provider.intraday_calls == 1
    assert provider.daily_calls == 0
    assert first_payload["source"] == "provider"
    assert first_payload["freshness"]["cache_status"] == "miss"
    assert first_payload["freshness"]["cached_at"] is not None
    assert second_payload["source"] == "cache"
    assert second_payload["freshness"]["cache_status"] == "hit"
    assert second_payload["freshness"]["cached_at"] is not None
    assert second_payload["items"] == first_payload["items"]
    assert session.query(MinuteBar).count() == 1
    cache_entry = session.query(IntradayMinuteCacheEntry).one()
    assert cache_entry.provider == "yfinance"
    assert cache_entry.symbol == "AAPL"
    assert cache_entry.trade_date == date(2026, 7, 2)
    assert cache_entry.timeframe == "1m"
    assert cache_entry.row_count == 1


def test_get_intraday_bars_payload_returns_provider_data_when_cache_write_is_unavailable(
    monkeypatch,
):
    session = make_session()

    class FakeIntradayProvider:
        def fetch_instruments(self, market: str, exchange: str | None = None) -> list:
            return []

        def fetch_bars(
            self, symbol: str, timeframe: str, start: date, end: date
        ) -> list[ProviderBar]:
            return []

        def fetch_intraday_bars(
            self, symbol: str, trade_date: date, timeframe: str
        ) -> list[ProviderIntradayBar]:
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

    monkeypatch.setattr(
        market_data_service, "get_provider", lambda provider_name=None: FakeIntradayProvider()
    )
    monkeypatch.setattr(
        market_data_service,
        "_persist_intraday_cache_bars",
        lambda **_: market_data_service.IntradayCacheWriteResult(
            status="unavailable",
            fetched_at="2026-07-02T13:31:00+00:00",
            cached_at=None,
            reason=market_data_service.INTRADAY_CACHE_UNAVAILABLE_REASON,
        ),
    )

    payload = get_intraday_bars_payload(
        "AAPL",
        date(2026, 7, 2),
        session=session,
        provider_name="yfinance",
    )

    assert payload["status"] == "ok"
    assert payload["source"] == "provider"
    assert payload["freshness"]["cache_status"] == "unavailable"
    assert payload["freshness"]["reason"] == market_data_service.INTRADAY_CACHE_UNAVAILABLE_REASON
    assert payload["items"][0]["close"] == 214.2


def test_get_intraday_bars_payload_returns_no_data_for_empty_verified_provider(monkeypatch):
    class EmptyIntradayProvider:
        def fetch_instruments(self, market: str, exchange: str | None = None) -> list:
            return []

        def fetch_bars(
            self, symbol: str, timeframe: str, start: date, end: date
        ) -> list[ProviderBar]:
            return []

        def fetch_intraday_bars(
            self, symbol: str, trade_date: date, timeframe: str
        ) -> list[ProviderIntradayBar]:
            return []

    monkeypatch.setattr(
        market_data_service, "get_provider", lambda provider_name=None: EmptyIntradayProvider()
    )

    payload = get_intraday_bars_payload(
        "AAPL",
        date(2026, 7, 2),
        provider_name="yfinance",
    )

    assert payload["status"] == "no_data"
    assert payload["source"] == "provider"
    assert payload["previous_close"] is None
    assert payload["items"] == []
    assert payload["availability"]["status"] == "no_data"
    assert payload["availability"]["reason"] == market_data_service.INTRADAY_NO_DATA_REASON
    assert payload["freshness"]["status"] == "no_data"
    assert payload["freshness"]["cache_status"] == "unavailable"
    assert payload["session"]["status"] == "closed_session"


def test_get_intraday_bars_payload_returns_weekend_no_data_without_minute_provider_call(
    monkeypatch,
):
    class WeekendIntradayProvider:
        def fetch_instruments(self, market: str, exchange: str | None = None) -> list:
            return []

        def fetch_bars(
            self, symbol: str, timeframe: str, start: date, end: date
        ) -> list[ProviderBar]:
            raise AssertionError("weekend no-data should not call daily provider data")

        def fetch_intraday_bars(
            self, symbol: str, trade_date: date, timeframe: str
        ) -> list[ProviderIntradayBar]:
            raise AssertionError("weekend no-data should not call the provider minute endpoint")

    monkeypatch.setattr(
        market_data_service, "get_provider", lambda provider_name=None: WeekendIntradayProvider()
    )

    payload = get_intraday_bars_payload(
        "AAPL",
        date(2026, 7, 4),
        provider_name="yfinance",
    )

    assert payload["status"] == "no_data"
    assert payload["source"] == "none"
    assert payload["previous_close"] is None
    assert payload["items"] == []
    assert payload["availability"]["status"] == "no_data"
    assert payload["availability"]["reason"] == market_data_service.INTRADAY_WEEKEND_NO_DATA_REASON
    assert payload["freshness"]["status"] == "no_data"
    assert payload["freshness"]["cache_status"] == "skipped"
    assert payload["session"]["status"] == "weekend"


def test_get_intraday_bars_payload_returns_future_no_data_without_minute_provider_call(monkeypatch):
    class FutureIntradayProvider:
        def fetch_instruments(self, market: str, exchange: str | None = None) -> list:
            return []

        def fetch_bars(
            self, symbol: str, timeframe: str, start: date, end: date
        ) -> list[ProviderBar]:
            raise AssertionError("future no-data should not call daily provider data")

        def fetch_intraday_bars(
            self, symbol: str, trade_date: date, timeframe: str
        ) -> list[ProviderIntradayBar]:
            raise AssertionError("future no-data should not call the provider minute endpoint")

    monkeypatch.setattr(
        market_data_service, "get_provider", lambda provider_name=None: FutureIntradayProvider()
    )

    future_trade_date = date.today() + market_data_service.timedelta(days=1)
    payload = get_intraday_bars_payload(
        "AAPL",
        future_trade_date,
        provider_name="yfinance",
    )

    assert payload["status"] == "no_data"
    assert payload["source"] == "none"
    assert payload["previous_close"] is None
    assert payload["items"] == []
    assert payload["availability"]["status"] == "no_data"
    assert payload["availability"]["reason"] == market_data_service.INTRADAY_FUTURE_NO_DATA_REASON
    assert payload["freshness"]["status"] == "no_data"
    assert payload["freshness"]["cache_status"] == "skipped"
    assert payload["session"]["status"] == "future_date"


def test_get_intraday_bars_payload_returns_known_us_holiday_no_data_without_minute_provider_call(
    monkeypatch,
):
    class HolidayIntradayProvider:
        def fetch_instruments(self, market: str, exchange: str | None = None) -> list:
            return []

        def fetch_bars(
            self, symbol: str, timeframe: str, start: date, end: date
        ) -> list[ProviderBar]:
            raise AssertionError("known holiday no-data should not call daily provider data")

        def fetch_intraday_bars(
            self, symbol: str, trade_date: date, timeframe: str
        ) -> list[ProviderIntradayBar]:
            raise AssertionError(
                "known holiday no-data should not call the provider minute endpoint"
            )

    monkeypatch.setattr(
        market_data_service, "get_provider", lambda provider_name=None: HolidayIntradayProvider()
    )

    payload = get_intraday_bars_payload(
        "AAPL",
        date(2026, 7, 3),
        provider_name="yfinance",
    )

    assert payload["status"] == "no_data"
    assert payload["source"] == "none"
    assert payload["previous_close"] is None
    assert payload["items"] == []
    assert payload["availability"]["status"] == "no_data"
    assert (
        payload["availability"]["reason"]
        == market_data_service.INTRADAY_KNOWN_HOLIDAY_NO_DATA_REASON
    )


def test_get_intraday_bars_payload_returns_movable_us_holiday_no_data_without_minute_provider_call(
    monkeypatch,
):
    class MovableHolidayIntradayProvider:
        def fetch_instruments(self, market: str, exchange: str | None = None) -> list:
            return []

        def fetch_bars(
            self, symbol: str, timeframe: str, start: date, end: date
        ) -> list[ProviderBar]:
            raise AssertionError("movable holiday no-data should not call daily provider data")

        def fetch_intraday_bars(
            self, symbol: str, trade_date: date, timeframe: str
        ) -> list[ProviderIntradayBar]:
            raise AssertionError(
                "movable holiday no-data should not call the provider minute endpoint"
            )

    monkeypatch.setattr(
        market_data_service,
        "get_provider",
        lambda provider_name=None: MovableHolidayIntradayProvider(),
    )

    payload = get_intraday_bars_payload(
        "AAPL",
        date(2026, 4, 3),
        provider_name="yfinance",
    )

    assert payload["status"] == "no_data"
    assert payload["source"] == "none"
    assert payload["previous_close"] is None
    assert payload["items"] == []
    assert payload["availability"]["status"] == "no_data"
    assert (
        payload["availability"]["reason"]
        == market_data_service.INTRADAY_KNOWN_HOLIDAY_NO_DATA_REASON
    )


def test_get_intraday_bars_payload_keeps_unsupported_provider_degraded_without_daily_minute_call(
    monkeypatch,
):
    requested_timeframes: list[str] = []

    class UnsupportedIntradayProvider:
        def fetch_instruments(self, market: str, exchange: str | None = None) -> list:
            return []

        def fetch_bars(
            self, symbol: str, timeframe: str, start: date, end: date
        ) -> list[ProviderBar]:
            requested_timeframes.append(timeframe)
            return []

    monkeypatch.setattr(
        market_data_service,
        "get_provider",
        lambda provider_name=None: UnsupportedIntradayProvider(),
    )

    payload = get_intraday_bars_payload(
        "AAPL",
        date(2026, 7, 3),
        provider_name="mock",
    )

    assert payload["status"] == "degraded"
    assert payload["source"] == "none"
    assert payload["items"] == []
    assert payload["availability"]["reason"] == market_data_service.INTRADAY_UNSUPPORTED_REASON
    assert requested_timeframes == []


def test_get_market_depth_payload_returns_verified_provider_sections(monkeypatch):
    class FakeDepthProvider:
        def fetch_instruments(self, market: str, exchange: str | None = None) -> list:
            return []

        def fetch_bars(
            self, symbol: str, timeframe: str, start: date, end: date
        ) -> list[ProviderBar]:
            raise AssertionError("Daily bars must not be used for market depth")

        def fetch_market_depth(self, symbol: str, depth_levels: int) -> ProviderMarketDepthSnapshot:
            assert symbol == "AAPL"
            assert depth_levels == 5
            return ProviderMarketDepthSnapshot(
                provider="fake_depth",
                source="provider",
                as_of=datetime(2026, 7, 3, 13, 30, tzinfo=timezone.utc),
                is_realtime=False,
                is_delayed=True,
                delay_minutes=15,
                bids=[
                    ProviderOrderBookLevel(
                        price=Decimal("101.20"),
                        volume=Decimal("1000"),
                        amount=Decimal("101200"),
                        order_count=5,
                    )
                ],
                asks=[
                    ProviderOrderBookLevel(
                        price=Decimal("101.30"),
                        volume=Decimal("800"),
                        amount=Decimal("81040"),
                        order_count=4,
                    )
                ],
                recent_trades=[
                    ProviderRecentTrade(
                        timestamp=datetime(2026, 7, 3, 13, 31, tzinfo=timezone.utc),
                        price=Decimal("101.25"),
                        volume=Decimal("15000"),
                        amount=Decimal("1518750"),
                        side="buy",
                    )
                ],
                fund_flow=ProviderFundFlow(
                    currency="CNY",
                    net_inflow=Decimal("1234567"),
                    main_net_inflow=Decimal("765432"),
                    retail_net_inflow=Decimal("-12345"),
                    source_definition="provider-defined verified fund-flow",
                ),
                availability={"reason": "Depth snapshot from fixture provider."},
            )

    monkeypatch.setattr(
        market_data_service, "get_provider", lambda provider_name=None: FakeDepthProvider()
    )

    payload = market_data_service.get_market_depth_payload(
        "AAPL",
        provider_name="akshare",
        depth_levels=5,
        large_order_threshold_amount=Decimal("1000000"),
    )

    assert payload["status"] == "ok"
    assert payload["source"] == "provider"
    assert payload["provider"] == "fake_depth"
    assert payload["effective_provider"] == "akshare"
    assert payload["as_of"] == "2026-07-03T13:30:00+00:00"
    assert payload["is_delayed"] is True
    assert payload["delay_minutes"] == 15
    assert payload["order_book"]["status"] == "ok"
    assert payload["order_book"]["bids"][0]["price"] == 101.2
    assert payload["recent_trades"]["status"] == "ok"
    assert payload["recent_trades"]["items"][0]["amount"] == 1518750.0
    assert payload["large_orders"]["status"] == "ok"
    assert payload["large_orders"]["items"][0]["threshold_amount"] == 1000000.0
    assert payload["fund_flow"]["status"] == "ok"
    assert payload["fund_flow"]["net_inflow"] == 1234567.0
    assert payload["availability"]["capabilities"] == {
        "order_book": True,
        "recent_trades": True,
        "large_orders": True,
        "fund_flow": True,
    }


def test_get_market_depth_payload_keeps_partial_sections_degraded(monkeypatch):
    class PartialDepthProvider:
        def fetch_instruments(self, market: str, exchange: str | None = None) -> list:
            return []

        def fetch_bars(
            self, symbol: str, timeframe: str, start: date, end: date
        ) -> list[ProviderBar]:
            raise AssertionError("Daily bars must not be used for market depth")

        def fetch_market_depth(self, symbol: str, depth_levels: int) -> ProviderMarketDepthSnapshot:
            return ProviderMarketDepthSnapshot(
                provider="partial_depth",
                source="provider",
                as_of=datetime(2026, 7, 3, 13, 30, tzinfo=timezone.utc),
                is_realtime=False,
                is_delayed=True,
                delay_minutes=15,
                bids=[ProviderOrderBookLevel(price=Decimal("101.20"), volume=Decimal("1000"))],
                asks=[],
                recent_trades=[],
                fund_flow=None,
            )

    monkeypatch.setattr(
        market_data_service, "get_provider", lambda provider_name=None: PartialDepthProvider()
    )

    payload = market_data_service.get_market_depth_payload("AAPL", provider_name="akshare")

    assert payload["status"] == "ok"
    assert payload["order_book"]["status"] == "ok"
    assert payload["recent_trades"]["status"] == "degraded"
    assert payload["large_orders"]["status"] == "degraded"
    assert payload["fund_flow"]["status"] == "degraded"
    assert payload["availability"]["capabilities"] == {
        "order_book": True,
        "recent_trades": False,
        "large_orders": False,
        "fund_flow": False,
    }


def test_get_market_depth_payload_keeps_unsupported_provider_degraded_without_bar_fabrication(
    monkeypatch,
):
    called_operations: list[str] = []

    class UnsupportedDepthProvider:
        def fetch_instruments(self, market: str, exchange: str | None = None) -> list:
            return []

        def fetch_bars(
            self, symbol: str, timeframe: str, start: date, end: date
        ) -> list[ProviderBar]:
            called_operations.append(f"fetch_bars:{timeframe}")
            return []

        def fetch_intraday_bars(
            self, symbol: str, trade_date: date, timeframe: str
        ) -> list[ProviderIntradayBar]:
            called_operations.append(f"fetch_intraday_bars:{timeframe}")
            return []

    monkeypatch.setattr(
        market_data_service, "get_provider", lambda provider_name=None: UnsupportedDepthProvider()
    )

    payload = market_data_service.get_market_depth_payload("AAPL", provider_name="mock")

    assert payload["status"] == "degraded"
    assert payload["source"] == "none"
    assert payload["order_book"]["bids"] == []
    assert payload["recent_trades"]["items"] == []
    assert payload["large_orders"]["items"] == []
    assert called_operations == []


def test_get_indicator_payload_returns_latest_values():
    payload = get_indicator_payload(
        "AAPL",
        date(2026, 1, 1),
        date(2026, 1, 15),
        3,
        provider_name="mock",
    )

    assert payload["symbol"] == "AAPL"
    assert payload["indicators"]["ma"] == 114.0
    assert 0 <= payload["indicators"]["rsi"] <= 100


def test_get_indicator_payload_handles_empty_bars():
    payload = get_indicator_payload(
        "AAPL",
        date(2026, 1, 2),
        date(2026, 1, 1),
        3,
        provider_name="mock",
    )

    assert payload["symbol"] == "AAPL"
    assert payload["as_of"] is None
    assert payload["indicators"] == {"ma": None, "rsi": None}


def test_get_indicator_payload_returns_nulls_for_insufficient_ma_data():
    payload = get_indicator_payload(
        "AAPL",
        date(2026, 1, 1),
        date(2026, 1, 2),
        3,
        provider_name="mock",
    )

    assert payload["symbol"] == "AAPL"
    assert payload["as_of"] == "2026-01-02"
    assert payload["indicators"]["ma"] is None
    assert payload["indicators"]["rsi"] is None


def test_get_bars_payload_wraps_unexpected_provider_failures(monkeypatch):
    class FailingProvider:
        def fetch_instruments(self, market: str, exchange: str | None = None) -> list:
            return []

        def fetch_bars(self, symbol: str, timeframe: str, start: date, end: date) -> list:
            raise RuntimeError("provider unavailable token=secret123")

    def get_failing_provider(provider_name: str = "mock") -> FailingProvider:
        return FailingProvider()

    monkeypatch.setattr(market_data_service, "get_provider", get_failing_provider)

    with pytest.raises(MarketDataProviderError) as raised_error:
        get_bars_payload(
            "AAPL",
            "1d",
            date(2026, 1, 1),
            date(2026, 1, 1),
            provider_name="mock",
        )

    provider_error = raised_error.value
    assert provider_error.provider_name == "mock"
    assert provider_error.operation == "fetching bars"
    assert isinstance(provider_error.original_error, RuntimeError)
    assert provider_error.category == "provider_error"
    assert provider_error.http_status_code == 502
    assert "secret123" not in str(provider_error)
    assert "secret123" in str(provider_error.original_error)


def test_get_bars_payload_preserves_provider_value_errors(monkeypatch):
    class FailingProvider:
        def fetch_instruments(self, market: str, exchange: str | None = None) -> list:
            return []

        def fetch_bars(self, symbol: str, timeframe: str, start: date, end: date) -> list:
            raise ValueError("unsupported timeframe")

    def get_failing_provider(provider_name: str = "mock") -> FailingProvider:
        return FailingProvider()

    monkeypatch.setattr(market_data_service, "get_provider", get_failing_provider)

    with pytest.raises(ValueError, match="unsupported timeframe"):
        get_bars_payload(
            "AAPL",
            "1h",
            date(2026, 1, 1),
            date(2026, 1, 1),
            provider_name="mock",
        )


@pytest.mark.parametrize(
    ("provider_exception", "expected_error_type", "expected_category", "expected_status_code"),
    [
        (TimeoutError("request timed out"), MarketDataProviderTimeoutError, "timeout", 504),
        (
            ConnectionError("connection refused"),
            MarketDataProviderUnavailableError,
            "unavailable",
            503,
        ),
        (
            RuntimeError("upstream rate limit exceeded"),
            MarketDataProviderRateLimitError,
            "rate_limited",
            429,
        ),
        (KeyError("close"), MarketDataProviderPayloadError, "malformed_payload", 502),
    ],
)
def test_get_bars_payload_classifies_provider_failures(
    monkeypatch,
    provider_exception,
    expected_error_type,
    expected_category,
    expected_status_code,
):
    class FailingProvider:
        def fetch_instruments(self, market: str, exchange: str | None = None) -> list:
            return []

        def fetch_bars(self, symbol: str, timeframe: str, start: date, end: date) -> list:
            raise provider_exception

    def get_failing_provider(provider_name: str = "mock") -> FailingProvider:
        return FailingProvider()

    monkeypatch.setattr(market_data_service, "get_provider", get_failing_provider)

    with pytest.raises(expected_error_type) as raised_error:
        get_bars_payload(
            "AAPL",
            "1d",
            date(2026, 1, 1),
            date(2026, 1, 1),
            provider_name="mock",
        )

    provider_error = raised_error.value
    assert provider_error.provider_name == "mock"
    assert provider_error.operation == "fetching bars"
    assert provider_error.category == expected_category
    assert provider_error.http_status_code == expected_status_code


def test_get_bars_payload_wraps_malformed_provider_bar_payloads(monkeypatch):
    class MalformedProvider:
        def fetch_instruments(self, market: str, exchange: str | None = None) -> list:
            return []

        def fetch_bars(self, symbol: str, timeframe: str, start: date, end: date) -> list:
            return [object()]

    def get_malformed_provider(provider_name: str = "mock") -> MalformedProvider:
        return MalformedProvider()

    monkeypatch.setattr(market_data_service, "get_provider", get_malformed_provider)

    with pytest.raises(MarketDataProviderPayloadError) as raised_error:
        get_bars_payload(
            "AAPL",
            "1d",
            date(2026, 1, 1),
            date(2026, 1, 1),
            provider_name="mock",
        )

    provider_error = raised_error.value
    assert provider_error.provider_name == "mock"
    assert provider_error.operation == "serializing bars"
    assert provider_error.category == "malformed_payload"
    assert provider_error.http_status_code == 502


def test_get_market_snapshot_includes_instruments_and_bars():
    snapshot = get_market_snapshot(
        "US",
        date(2026, 1, 1),
        date(2026, 1, 2),
        provider_name="mock",
    )

    assert snapshot["market"] == "US"
    assert snapshot["instrument_count"] == 1
    assert snapshot["instruments"][0]["symbol"] == "AAPL"
    assert len(snapshot["instruments"][0]["bars"]) == 2


def test_get_latest_bar_payload_uses_provider_when_database_empty():
    payload = get_latest_bar_payload("AAPL", session=None, provider_name="mock")

    assert payload["symbol"] == "AAPL"
    assert payload["item"] is not None
    assert float(payload["item"]["close"]) > 0


def test_get_latest_bars_batch_payload_returns_one_entry_per_symbol():
    payload = get_latest_bars_batch_payload(["AAPL", "0700"], session=None, provider_name="mock")

    assert len(payload["items"]) == 2
    assert payload["items"][0]["symbol"] == "AAPL"
    assert payload["items"][0]["item"] is not None
