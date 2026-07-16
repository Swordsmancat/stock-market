from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import SQLAlchemyError
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


def seed_cn_daily_bars(
    session,
    trade_dates: list[date],
    *,
    symbol: str = "600519",
) -> None:
    market = Market(
        code="CN",
        name="China A Share",
        timezone="Asia/Shanghai",
        currency="CNY",
    )
    instrument = Instrument(
        symbol=symbol,
        name=symbol,
        market=market,
        asset_type="stock",
        currency="CNY",
    )
    session.add_all([market, instrument])
    session.flush()
    for index, trade_date in enumerate(trade_dates):
        price = Decimal(100 + index)
        session.add(
            DailyBar(
                instrument_id=instrument.id,
                trade_date=trade_date,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=Decimal("1000"),
                provider="akshare",
                source="akshare.stock_zh_a_hist",
                adjustment="qfq",
            )
        )
    session.commit()


def provider_bars_for_dates(symbol: str, trade_dates: list[date]) -> list[ProviderBar]:
    return [
        ProviderBar(
            symbol=symbol,
            timestamp=trade_date,
            open=Decimal(200 + index),
            high=Decimal(200 + index),
            low=Decimal(200 + index),
            close=Decimal(200 + index),
            volume=Decimal("2000"),
        )
        for index, trade_date in enumerate(trade_dates)
    ]


def seed_cn_intraday_cache(
    session,
    *,
    provider: str,
    source: str,
) -> None:
    market = Market(
        code="CN",
        name="China A Share",
        timezone="Asia/Shanghai",
        currency="CNY",
    )
    instrument = Instrument(
        symbol="600519",
        name="Kweichow Moutai",
        market=market,
        asset_type="stock",
        currency="CNY",
    )
    timestamp = datetime(2026, 7, 14, 1, 31, tzinfo=timezone.utc)
    session.add_all([market, instrument])
    session.flush()
    session.add(
        MinuteBar(
            instrument_id=instrument.id,
            ts=timestamp,
            open=Decimal("1480"),
            high=Decimal("1490"),
            low=Decimal("1475"),
            close=Decimal("1488"),
            volume=Decimal("1200"),
            amount=Decimal("1785600"),
        )
    )
    session.add(
        IntradayMinuteCacheEntry(
            instrument_id=instrument.id,
            provider=provider,
            symbol="600519",
            trade_date=date(2026, 7, 14),
            timeframe="1m",
            source=source,
            row_count=1,
            first_ts=timestamp,
            last_ts=timestamp,
            fetched_at=timestamp,
            cached_at=timestamp,
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
    assert payload["adjustment"] == "provider_default"
    assert payload["fallback_used"] is False
    assert payload["source_attempts"] == [
        {
            "provider": "mock",
            "source": "mock.fetch_bars",
            "status": "selected",
            "row_count": 1,
        }
    ]


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


def test_get_bars_payload_falls_back_to_configured_akshare_for_cn_daily_bars(
    monkeypatch,
):
    provider_calls: list[tuple[str, str]] = []

    class FakeProvider:
        def __init__(self, provider_name: str, bars: list[ProviderBar]) -> None:
            self.provider_name = provider_name
            self.bars = bars

        def fetch_bars(
            self,
            symbol: str,
            timeframe: str,
            start: date,
            end: date,
        ) -> list[ProviderBar]:
            provider_calls.append((self.provider_name, symbol))
            return self.bars

    fallback_bar = ProviderBar(
        symbol="600519",
        timestamp=date(2026, 7, 9),
        open=Decimal("1480"),
        high=Decimal("1500"),
        low=Decimal("1475"),
        close=Decimal("1495"),
        volume=Decimal("120000"),
        amount=Decimal("179400000"),
    )
    providers = {
        "yfinance": FakeProvider("yfinance", []),
        "akshare": FakeProvider("akshare", [fallback_bar]),
        "tushare": FakeProvider("tushare", []),
    }
    monkeypatch.setattr(
        market_data_service,
        "get_provider",
        lambda provider_name=None, market=None: providers[str(provider_name)],
    )
    monkeypatch.setattr(
        market_data_service,
        "get_platform_settings",
        lambda: {"akshare_enabled": True, "tushare_token": "configured"},
        raising=False,
    )

    payload = get_bars_payload(
        "600519",
        "1d",
        date(2026, 7, 1),
        date(2026, 7, 10),
        provider_name="yfinance",
        market="CN",
    )

    assert provider_calls == [("yfinance", "600519"), ("akshare", "600519")]
    assert payload["status"] == "ok"
    assert payload["requested_provider"] == "yfinance"
    assert payload["effective_provider"] == "akshare"
    assert payload["provider"] == "akshare"
    assert payload["source"] == "akshare.stock_zh_a_hist"
    assert payload["adjustment"] == "qfq"
    assert payload["fallback_used"] is True
    assert payload["items"][0]["close"] == 1495.0
    assert payload["source_attempts"] == [
        {
            "provider": "yfinance",
            "source": "yfinance.fetch_bars",
            "status": "no_data",
            "row_count": 0,
        },
        {
            "provider": "akshare",
            "source": "akshare.stock_zh_a_hist",
            "status": "selected",
            "row_count": 1,
        },
    ]


@pytest.mark.parametrize(
    ("market", "symbol", "provider_name"),
    [
        ("HK", "9988", "yfinance"),
        ("US", "AAPL", "yfinance"),
        (None, "600519", "yfinance"),
        ("CN", "000001.SS", "yfinance"),
        ("CN", "600519", "mock"),
    ],
)
def test_get_bars_payload_never_uses_cn_fallback_for_ineligible_requests(
    monkeypatch,
    market,
    symbol,
    provider_name,
):
    provider_calls: list[tuple[str, str]] = []

    class EmptyProvider:
        def fetch_bars(self, requested_symbol, timeframe, start, end):
            provider_calls.append((provider_name, requested_symbol))
            return []

    monkeypatch.setattr(
        market_data_service,
        "get_provider",
        lambda *_args, **_kwargs: EmptyProvider(),
    )
    monkeypatch.setattr(
        market_data_service,
        "get_platform_settings",
        lambda: (_ for _ in ()).throw(
            AssertionError("ineligible requests must not inspect CN fallback settings")
        ),
    )

    payload = get_bars_payload(
        symbol,
        "1d",
        date(2026, 7, 1),
        date(2026, 7, 10),
        provider_name=provider_name,
        market=market,
    )

    assert provider_calls == [(provider_name, symbol)]
    assert payload["status"] == "no_data"
    assert payload["market"] == market
    assert payload["fallback_used"] is False
    assert len(payload["source_attempts"]) == 1


def test_get_bars_payload_uses_next_cn_source_and_sanitizes_provider_errors(
    monkeypatch,
):
    fallback_bar = ProviderBar(
        symbol="920000",
        timestamp=date(2026, 7, 9),
        open=Decimal("10"),
        high=Decimal("11"),
        low=Decimal("9"),
        close=Decimal("10.5"),
        volume=Decimal("1000"),
    )

    class PrimaryProvider:
        def fetch_bars(self, *_args):
            raise ConnectionError("private upstream body token=super-secret")

    class EmptyHistProvider:
        def fetch_bars(self, *_args):
            return []

    class UnusedTushareProvider:
        def fetch_bars(self, *_args):
            raise AssertionError("Tushare must not run after a valid AkShare result")

    class SinaProvider:
        download_sina_daily_bars = staticmethod(lambda *_args: None)

        def __init__(self, **_kwargs):
            pass

        def fetch_bars(self, *_args):
            return [fallback_bar]

    providers = {
        "yfinance": PrimaryProvider(),
        "akshare": EmptyHistProvider(),
        "tushare": UnusedTushareProvider(),
    }
    monkeypatch.setattr(
        market_data_service,
        "get_provider",
        lambda provider_name=None, market=None: providers[str(provider_name)],
    )
    monkeypatch.setattr(market_data_service, "AkShareProvider", SinaProvider)
    monkeypatch.setattr(
        market_data_service,
        "get_platform_settings",
        lambda: {"akshare_enabled": True, "tushare_token": "configured"},
    )

    payload = get_bars_payload(
        "920000",
        "1d",
        date(2026, 7, 1),
        date(2026, 7, 10),
        provider_name="yfinance",
        market="CN",
    )

    assert payload["source"] == "akshare.stock_zh_a_daily"
    assert payload["effective_provider"] == "akshare"
    assert payload["source_attempts"] == [
        {
            "provider": "yfinance",
            "source": "yfinance.fetch_bars",
            "status": "failed",
            "exception_type": "ConnectionError",
        },
        {
            "provider": "akshare",
            "source": "akshare.stock_zh_a_hist",
            "status": "no_data",
            "row_count": 0,
        },
        {
            "provider": "akshare",
            "source": "akshare.stock_zh_a_daily",
            "status": "selected",
            "row_count": 1,
        },
    ]
    assert "super-secret" not in str(payload)


def test_get_bars_payload_uses_tushare_after_both_akshare_sources_are_empty(
    monkeypatch,
):
    provider_calls: list[str] = []
    tushare_bar = ProviderBar(
        symbol="600519",
        timestamp=date(2026, 7, 9),
        open=Decimal("1480"),
        high=Decimal("1500"),
        low=Decimal("1475"),
        close=Decimal("1495"),
        volume=Decimal("120000"),
    )

    class EmptyProvider:
        def __init__(self, name: str):
            self.name = name

        def fetch_bars(self, *_args):
            provider_calls.append(self.name)
            return []

    class TushareProvider:
        def fetch_bars(self, *_args):
            provider_calls.append("tushare")
            return [tushare_bar]

    class EmptySinaProvider:
        download_sina_daily_bars = staticmethod(lambda *_args: None)

        def __init__(self, **_kwargs):
            pass

        def fetch_bars(self, *_args):
            provider_calls.append("akshare_daily")
            return []

    providers = {
        "yfinance": EmptyProvider("yfinance"),
        "akshare": EmptyProvider("akshare_hist"),
        "tushare": TushareProvider(),
    }
    monkeypatch.setattr(
        market_data_service,
        "get_provider",
        lambda provider_name=None, market=None: providers[str(provider_name)],
    )
    monkeypatch.setattr(market_data_service, "AkShareProvider", EmptySinaProvider)
    monkeypatch.setattr(
        market_data_service,
        "get_platform_settings",
        lambda: {"akshare_enabled": True, "tushare_token": "configured"},
    )

    payload = get_bars_payload(
        "600519",
        "1d",
        date(2026, 7, 1),
        date(2026, 7, 10),
        provider_name="yfinance",
        market="CN",
    )

    assert provider_calls == ["yfinance", "akshare_hist", "akshare_daily", "tushare"]
    assert payload["status"] == "ok"
    assert payload["effective_provider"] == "tushare"
    assert payload["source"] == "tushare.pro.daily"
    assert payload["adjustment"] == "raw"
    assert payload["fallback_used"] is True
    assert [attempt["source"] for attempt in payload["source_attempts"]] == [
        "yfinance.fetch_bars",
        "akshare.stock_zh_a_hist",
        "akshare.stock_zh_a_daily",
        "tushare.pro.daily",
    ]


@pytest.mark.parametrize(
    ("primary_fails", "expected_status"),
    [(False, "no_data"), (True, "degraded")],
)
def test_get_bars_payload_exhausts_cn_sources_without_mock_data(
    monkeypatch,
    primary_fails,
    expected_status,
):
    constructed_providers: list[str] = []
    provider_calls: list[str] = []

    class EmptyProvider:
        def __init__(self, name: str, *, fails: bool = False):
            self.name = name
            self.fails = fails

        def fetch_bars(self, *_args):
            provider_calls.append(self.name)
            if self.fails:
                raise TimeoutError("private provider timeout details")
            return []

    class EmptySinaProvider:
        download_sina_daily_bars = staticmethod(lambda *_args: None)

        def __init__(self, **_kwargs):
            pass

        def fetch_bars(self, *_args):
            provider_calls.append("akshare_daily")
            return []

    providers = {
        "yfinance": EmptyProvider("yfinance", fails=primary_fails),
        "akshare": EmptyProvider("akshare_hist"),
        "tushare": EmptyProvider("tushare"),
    }

    def provider_factory(provider_name=None, market=None):
        normalized_name = str(provider_name)
        constructed_providers.append(normalized_name)
        return providers[normalized_name]

    monkeypatch.setattr(market_data_service, "get_provider", provider_factory)
    monkeypatch.setattr(market_data_service, "AkShareProvider", EmptySinaProvider)
    monkeypatch.setattr(
        market_data_service,
        "get_platform_settings",
        lambda: {"akshare_enabled": True, "tushare_token": "configured"},
    )

    payload = get_bars_payload(
        "600519",
        "1d",
        date(2026, 7, 1),
        date(2026, 7, 10),
        provider_name="yfinance",
        market="CN",
    )

    assert constructed_providers == ["yfinance", "akshare", "tushare"]
    assert "mock" not in constructed_providers
    assert provider_calls == ["yfinance", "akshare_hist", "akshare_daily", "tushare"]
    assert payload["status"] == expected_status
    assert payload["source"] == "none"
    assert payload["items"] == []
    assert payload["fallback_used"] is False
    assert [attempt["source"] for attempt in payload["source_attempts"]] == [
        "yfinance.fetch_bars",
        "akshare.stock_zh_a_hist",
        "akshare.stock_zh_a_daily",
        "tushare.pro.daily",
    ]
    assert "private provider timeout details" not in str(payload)


def test_get_bars_payload_skips_unconfigured_cn_alternates_without_fetching(
    monkeypatch,
):
    monkeypatch.delenv("TUSHARE_TOKEN", raising=False)
    primary_calls = 0

    class PrimaryProvider:
        def fetch_bars(self, *_args):
            nonlocal primary_calls
            primary_calls += 1
            return []

    class ForbiddenProvider:
        def fetch_bars(self, *_args):
            raise AssertionError("unconfigured alternate must not be fetched")

    class ForbiddenSinaProvider:
        download_sina_daily_bars = staticmethod(lambda *_args: None)

        def __init__(self, **_kwargs):
            pass

        def fetch_bars(self, *_args):
            raise AssertionError("disabled AkShare daily source must not be fetched")

    providers = {
        "yfinance": PrimaryProvider(),
        "akshare": ForbiddenProvider(),
        "tushare": ForbiddenProvider(),
    }
    monkeypatch.setattr(
        market_data_service,
        "get_provider",
        lambda provider_name=None, market=None: providers[str(provider_name)],
    )
    monkeypatch.setattr(market_data_service, "AkShareProvider", ForbiddenSinaProvider)
    monkeypatch.setattr(
        market_data_service,
        "get_platform_settings",
        lambda: {"akshare_enabled": False, "tushare_token": ""},
    )

    payload = get_bars_payload(
        "600519",
        "1d",
        date(2026, 7, 1),
        date(2026, 7, 10),
        provider_name="yfinance",
        market="CN",
    )

    assert primary_calls == 1
    assert [attempt["status"] for attempt in payload["source_attempts"]] == [
        "no_data",
        "skipped_unconfigured",
        "skipped_unconfigured",
        "skipped_unconfigured",
    ]


def test_get_bars_payload_uses_env_configured_tushare_fallback(monkeypatch):
    fallback_bar = ProviderBar(
        symbol="920000",
        timestamp=date(2026, 7, 9),
        open=Decimal("10"),
        high=Decimal("12"),
        low=Decimal("9"),
        close=Decimal("11"),
        volume=Decimal("1000"),
        amount=Decimal("11000"),
    )

    class Provider:
        def __init__(self, bars):
            self.bars = bars

        def fetch_bars(self, *_args):
            return self.bars

    class DisabledSinaProvider:
        download_sina_daily_bars = staticmethod(lambda *_args: None)

        def __init__(self, **_kwargs):
            pass

        def fetch_bars(self, *_args):
            raise AssertionError("disabled AkShare daily source must not be fetched")

    providers = {
        "yfinance": Provider([]),
        "akshare": Provider([]),
        "tushare": Provider([fallback_bar]),
    }
    monkeypatch.setenv("TUSHARE_TOKEN", "env-configured")
    monkeypatch.setattr(
        market_data_service,
        "get_provider",
        lambda provider_name=None, market=None: providers[str(provider_name)],
    )
    monkeypatch.setattr(market_data_service, "AkShareProvider", DisabledSinaProvider)
    monkeypatch.setattr(
        market_data_service,
        "get_platform_settings",
        lambda: {"akshare_enabled": False, "tushare_token": ""},
    )

    payload = get_bars_payload(
        "920000",
        "1d",
        date(2026, 7, 1),
        date(2026, 7, 10),
        provider_name="yfinance",
        market="CN",
    )

    assert payload["status"] == "ok"
    assert payload["effective_provider"] == "tushare"
    assert payload["source"] == "tushare.pro.daily"
    assert payload["items"][0]["close"] == 11.0
    assert [attempt["status"] for attempt in payload["source_attempts"]] == [
        "no_data",
        "skipped_unconfigured",
        "skipped_unconfigured",
        "selected",
    ]


def test_get_bars_payload_filters_database_bars_by_market_before_provider_calls(
    monkeypatch,
):
    session = make_session()
    cn_market = Market(
        code="CN",
        name="China A Share",
        timezone="Asia/Shanghai",
        currency="CNY",
    )
    us_market = Market(
        code="US",
        name="US Stock",
        timezone="America/New_York",
        currency="USD",
    )
    cn_instrument = Instrument(
        symbol="DUPL",
        name="CN listing",
        market=cn_market,
        asset_type="stock",
        currency="CNY",
    )
    us_instrument = Instrument(
        symbol="DUPL",
        name="US listing",
        market=us_market,
        asset_type="stock",
        currency="USD",
    )
    session.add_all([cn_market, us_market, cn_instrument, us_instrument])
    session.flush()
    session.add_all(
        [
            DailyBar(
                instrument_id=cn_instrument.id,
                trade_date=date(2026, 7, 9),
                open=Decimal("10"),
                high=Decimal("12"),
                low=Decimal("9"),
                close=Decimal("11"),
                volume=Decimal("1000"),
                provider="akshare",
                source="akshare.stock_zh_a_hist",
                adjustment="qfq",
            ),
            DailyBar(
                instrument_id=us_instrument.id,
                trade_date=date(2026, 7, 9),
                open=Decimal("100"),
                high=Decimal("120"),
                low=Decimal("90"),
                close=Decimal("110"),
                volume=Decimal("2000"),
            ),
        ]
    )
    session.commit()
    monkeypatch.setattr(
        market_data_service,
        "get_provider",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("database hits must not construct a provider")
        ),
    )

    payload = get_bars_payload(
        "DUPL",
        "1d",
        date(2026, 7, 1),
        date(2026, 7, 10),
        session=session,
        provider_name="yfinance",
        market="CN",
    )

    assert payload["source"] == "database"
    assert [item["close"] for item in payload["items"]] == [11.0]
    assert payload["provider"] == "akshare"
    assert payload["effective_provider"] == "akshare"
    assert payload["upstream_source"] == "akshare.stock_zh_a_hist"
    assert payload["adjustment"] == "qfq"
    assert payload["fallback_used"] is False
    assert payload["source_attempts"] == []


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        (date(2026, 7, 13), date(2026, 7, 13), 1),
        (date(2026, 7, 11), date(2026, 7, 12), 1),
        (date(2026, 7, 12), date(2026, 7, 18), 3),
        (date(2026, 7, 6), date(2026, 7, 19), 5),
        (date(2026, 1, 1), date(2026, 12, 31), 35),
    ],
)
def test_minimum_daily_bar_row_count_uses_bounded_weekday_arithmetic(
    start: date,
    end: date,
    expected: int,
) -> None:
    assert market_data_service._minimum_daily_bar_row_count(start, end) == expected


def test_get_bars_payload_recovers_sparse_exact_cn_database_by_minimum_row_count(
    monkeypatch,
):
    session = make_session()
    seed_cn_daily_bars(session, [date(2026, 7, 13)])
    remote_dates = [date(2026, 7, 13), date(2026, 7, 14), date(2026, 7, 15)]
    provider_calls: list[str] = []

    class Provider:
        def __init__(self, name: str, bars: list[ProviderBar]) -> None:
            self.name = name
            self.bars = bars

        def fetch_bars(self, *_args):
            provider_calls.append(self.name)
            return self.bars

    providers = {
        "yfinance": Provider(
            "yfinance",
            provider_bars_for_dates("600519", remote_dates[:2]),
        ),
        "akshare": Provider(
            "akshare",
            provider_bars_for_dates("600519", remote_dates),
        ),
        "tushare": Provider("tushare", []),
    }
    monkeypatch.setattr(
        market_data_service,
        "get_provider",
        lambda provider_name=None, market=None: providers[str(provider_name)],
    )
    monkeypatch.setattr(
        market_data_service,
        "get_platform_settings",
        lambda: {"akshare_enabled": True, "tushare_token": ""},
    )

    payload = get_bars_payload(
        "600519",
        "1d",
        date(2026, 7, 12),
        date(2026, 7, 18),
        session=session,
        provider_name="yfinance",
        market="CN",
    )

    assert provider_calls == ["yfinance", "akshare"]
    assert payload["status"] == "ok"
    assert payload["source"] == "akshare.stock_zh_a_hist"
    assert payload["effective_provider"] == "akshare"
    assert payload["source_attempts"][0] == {
        "provider": "yfinance",
        "source": "yfinance.fetch_bars",
        "status": "insufficient_coverage",
        "row_count": 2,
    }
    assert [item["timestamp"] for item in payload["items"]] == [
        trade_date.isoformat() for trade_date in remote_dates
    ]
    assert session.query(DailyBar).count() == 1


def test_get_bars_payload_retains_sparse_cn_database_after_remote_exhaustion(
    monkeypatch,
):
    session = make_session()
    seed_cn_daily_bars(session, [date(2026, 7, 13)])

    class EmptyProvider:
        def fetch_bars(self, *_args):
            return []

    providers = {
        "yfinance": EmptyProvider(),
        "akshare": EmptyProvider(),
        "tushare": EmptyProvider(),
    }
    monkeypatch.setattr(
        market_data_service,
        "get_provider",
        lambda provider_name=None, market=None: providers[str(provider_name)],
    )
    monkeypatch.setattr(
        market_data_service,
        "get_platform_settings",
        lambda: {"akshare_enabled": False, "tushare_token": ""},
    )

    payload = get_bars_payload(
        "600519",
        "1d",
        date(2026, 7, 12),
        date(2026, 7, 18),
        session=session,
        provider_name="yfinance",
        market="CN",
    )

    assert payload["source"] == "database"
    assert payload["status"] == "degraded"
    assert [item["timestamp"] for item in payload["items"]] == ["2026-07-13"]
    assert payload["source_attempts"] == [
        {
            "provider": "yfinance",
            "source": "yfinance.fetch_bars",
            "status": "no_data",
            "row_count": 0,
        },
        {
            "provider": "akshare",
            "source": "akshare.stock_zh_a_hist",
            "status": "skipped_unconfigured",
        },
        {
            "provider": "akshare",
            "source": "akshare.stock_zh_a_daily",
            "status": "skipped_unconfigured",
        },
        {
            "provider": "tushare",
            "source": "tushare.pro.daily",
            "status": "skipped_unconfigured",
        },
    ]
    assert payload["diagnostics"][-1] == {
        "source": "database",
        "status": "degraded",
        "code": "INSUFFICIENT_DATABASE_COVERAGE",
        "message": (
            "Stored daily-bar coverage is below the minimum required for the "
            "requested range; remote recovery was unavailable."
        ),
        "row_count": 1,
        "minimum_row_count": 3,
    }
    assert session.query(DailyBar).count() == 1


@pytest.mark.parametrize(
    ("start", "end", "trade_dates"),
    [
        (
            date(2026, 7, 13),
            date(2026, 7, 17),
            [date(2026, 7, 13), date(2026, 7, 14), date(2026, 7, 15)],
        ),
        (date(2026, 7, 13), date(2026, 7, 13), [date(2026, 7, 13)]),
    ],
)
def test_get_bars_payload_keeps_sufficient_and_short_cn_database_cohorts(
    monkeypatch,
    start: date,
    end: date,
    trade_dates: list[date],
):
    session = make_session()
    seed_cn_daily_bars(session, trade_dates)
    monkeypatch.setattr(
        market_data_service,
        "get_provider",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("sufficient database cohorts must not fetch providers")
        ),
    )

    payload = get_bars_payload(
        "600519",
        "1d",
        start,
        end,
        session=session,
        provider_name="yfinance",
        market="CN",
    )

    assert payload["source"] == "database"
    assert payload["status"] == "ok"
    assert payload["source_attempts"] == []


def test_get_bars_payload_keeps_sparse_non_cn_database_cohort(monkeypatch):
    session = make_session()
    seed_us_daily_close(session, "AAPL", date(2026, 7, 13), Decimal("200"))
    monkeypatch.setattr(
        market_data_service,
        "get_provider",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("non-CN database cohorts must not fetch CN providers")
        ),
    )

    payload = get_bars_payload(
        "AAPL",
        "1d",
        date(2026, 7, 1),
        date(2026, 7, 31),
        session=session,
        provider_name="yfinance",
        market="US",
    )

    assert payload["source"] == "database"
    assert [item["close"] for item in payload["items"]] == [200.0]
    assert payload["source_attempts"] == []


def test_get_bars_payload_returns_one_coherent_database_provenance_series(
    monkeypatch,
):
    session = make_session()
    market = Market(
        code="CN",
        name="China A Share",
        timezone="Asia/Shanghai",
        currency="CNY",
    )
    instrument = Instrument(
        symbol="600519",
        name="Kweichow Moutai",
        market=market,
        asset_type="stock",
        currency="CNY",
    )
    session.add_all([market, instrument])
    session.flush()
    session.add_all(
        [
            DailyBar(
                instrument_id=instrument.id,
                trade_date=date(2026, 7, 10),
                open=Decimal("5"),
                high=Decimal("5"),
                low=Decimal("5"),
                close=Decimal("5"),
                volume=Decimal("500"),
                provider="akshare",
                source="akshare.stock_zh_a_hist",
                adjustment="qfq",
            ),
            DailyBar(
                instrument_id=instrument.id,
                trade_date=date(2026, 7, 11),
                open=Decimal("10"),
                high=Decimal("10"),
                low=Decimal("10"),
                close=Decimal("10"),
                volume=Decimal("1000"),
                provider="tushare",
                source="tushare.pro.daily",
                adjustment="raw",
            ),
            DailyBar(
                instrument_id=instrument.id,
                trade_date=date(2026, 7, 12),
                open=Decimal("20"),
                high=Decimal("20"),
                low=Decimal("20"),
                close=Decimal("20"),
                volume=Decimal("2000"),
                provider="akshare",
                source="akshare.stock_zh_a_hist",
                adjustment="qfq",
            ),
        ]
    )
    session.commit()
    monkeypatch.setattr(
        market_data_service,
        "get_provider",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("database hits must not construct a provider")
        ),
    )

    payload = get_bars_payload(
        "600519",
        "1d",
        date(2026, 7, 10),
        date(2026, 7, 12),
        session=session,
        provider_name="yfinance",
        market="CN",
    )

    assert [item["close"] for item in payload["items"]] == [20.0]
    assert payload["provider"] == "akshare"
    assert payload["upstream_source"] == "akshare.stock_zh_a_hist"
    assert payload["adjustment"] == "qfq"
    assert payload["status"] == "degraded"
    assert payload["diagnostics"] == [
        {
            "source": "database",
            "status": "degraded",
            "code": "MIXED_DAILY_BAR_PROVENANCE",
            "message": "Stored daily bars span multiple provenance cohorts; only the latest coherent cohort was returned.",
            "dropped_row_count": 2,
        }
    ]


def test_get_bars_payload_rejects_sparse_source_before_complete_mixed_recovery(
    monkeypatch,
):
    session = make_session()
    market = Market(
        code="CN",
        name="China A Share",
        timezone="Asia/Shanghai",
        currency="CNY",
    )
    instrument = Instrument(
        symbol="600519",
        name="Kweichow Moutai",
        market=market,
        asset_type="stock",
        currency="CNY",
    )
    session.add_all([market, instrument])
    session.flush()

    first_trade_date = date(2026, 5, 1)
    trade_dates = [
        date.fromordinal(first_trade_date.toordinal() + offset)
        for offset in range(60)
    ]
    for index, trade_date in enumerate(trade_dates):
        price = Decimal(100 + index)
        session.add(
            DailyBar(
                instrument_id=instrument.id,
                trade_date=trade_date,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=Decimal("1000"),
                provider="tushare" if index < 58 else "akshare",
                source=(
                    "tushare.pro.daily"
                    if index < 58
                    else "akshare.stock_zh_a_hist"
                ),
                adjustment="raw" if index < 58 else "qfq",
            )
        )
    session.commit()

    def provider_bars(symbol: str, dates: list[date]) -> list[ProviderBar]:
        return [
            ProviderBar(
                symbol=symbol,
                timestamp=trade_date,
                open=Decimal(200 + index),
                high=Decimal(200 + index),
                low=Decimal(200 + index),
                close=Decimal(200 + index),
                volume=Decimal("2000"),
            )
            for index, trade_date in enumerate(dates)
        ]

    class Provider:
        def __init__(self, bars: list[ProviderBar]) -> None:
            self.bars = bars

        def fetch_bars(self, *_args):
            return self.bars

    providers = {
        "yfinance": Provider(
            provider_bars("600519", trade_dates[:34] + [trade_dates[-1]])
        ),
        "akshare": Provider(provider_bars("600519", trade_dates)),
        "tushare": Provider([]),
    }
    monkeypatch.setattr(
        market_data_service,
        "get_provider",
        lambda provider_name=None, market=None: providers[str(provider_name)],
    )
    monkeypatch.setattr(
        market_data_service,
        "get_platform_settings",
        lambda: {"akshare_enabled": True, "tushare_token": ""},
    )

    payload = get_bars_payload(
        "600519",
        "1d",
        trade_dates[0],
        trade_dates[-1],
        session=session,
        provider_name="yfinance",
        market="CN",
    )

    assert payload["status"] == "ok"
    assert payload["effective_provider"] == "akshare"
    assert payload["upstream_source"] == "akshare.stock_zh_a_hist"
    assert payload["adjustment"] == "qfq"
    assert len(payload["items"]) == 60
    assert payload["items"][0]["timestamp"] == trade_dates[0].isoformat()
    assert payload["items"][-1]["timestamp"] == trade_dates[-1].isoformat()
    assert payload["source_attempts"][0]["status"] == "insufficient_coverage"
    assert session.query(DailyBar).count() == 60


def test_get_bars_payload_retains_ready_mixed_database_when_recovery_is_incomplete(
    monkeypatch,
):
    session = make_session()
    market = Market(
        code="CN",
        name="China A Share",
        timezone="Asia/Shanghai",
        currency="CNY",
    )
    instrument = Instrument(
        symbol="600519",
        name="Kweichow Moutai",
        market=market,
        asset_type="stock",
        currency="CNY",
    )
    session.add_all([market, instrument])
    session.flush()
    first_trade_date = date(2026, 5, 1)
    trade_dates = [
        date.fromordinal(first_trade_date.toordinal() + offset)
        for offset in range(35)
    ]
    for index, trade_date in enumerate(trade_dates):
        price = Decimal(100 + index)
        session.add(
            DailyBar(
                instrument_id=instrument.id,
                trade_date=trade_date,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=Decimal("1000"),
                provider="tushare" if index < 33 else "akshare",
                source=(
                    "tushare.pro.daily"
                    if index < 33
                    else "akshare.stock_zh_a_hist"
                ),
                adjustment="raw" if index < 33 else "qfq",
            )
        )
    session.commit()

    class EmptyProvider:
        def fetch_bars(self, *_args):
            return []

    class EmptySinaProvider:
        download_sina_daily_bars = staticmethod(lambda *_args: None)

        def __init__(self, **_kwargs):
            pass

        def fetch_bars(self, *_args):
            return []

    providers = {
        "yfinance": EmptyProvider(),
        "akshare": EmptyProvider(),
        "tushare": EmptyProvider(),
    }
    monkeypatch.setattr(
        market_data_service,
        "get_provider",
        lambda provider_name=None, market=None: providers[str(provider_name)],
    )
    monkeypatch.setattr(market_data_service, "AkShareProvider", EmptySinaProvider)
    monkeypatch.setattr(
        market_data_service,
        "get_platform_settings",
        lambda: {"akshare_enabled": True, "tushare_token": ""},
    )

    payload = get_bars_payload(
        "600519",
        "1d",
        trade_dates[0],
        trade_dates[-1],
        session=session,
        provider_name="yfinance",
        market="CN",
    )

    assert payload["status"] == "degraded"
    assert payload["source"] == "database"
    assert payload["effective_provider"] == "akshare"
    assert [item["timestamp"] for item in payload["items"]] == [
        trade_dates[-2].isoformat(),
        trade_dates[-1].isoformat(),
    ]
    assert [attempt["status"] for attempt in payload["source_attempts"]] == [
        "no_data",
        "no_data",
        "no_data",
        "skipped_unconfigured",
    ]
    assert payload["diagnostics"][0]["code"] == "MIXED_DAILY_BAR_PROVENANCE"
    assert session.query(DailyBar).count() == 35


def test_get_latest_bar_payload_preserves_mixed_database_provenance(monkeypatch):
    session = make_session()
    market = Market(
        code="CN",
        name="China A Share",
        timezone="Asia/Shanghai",
        currency="CNY",
    )
    instrument = Instrument(
        symbol="600519",
        name="Kweichow Moutai",
        market=market,
        asset_type="stock",
        currency="CNY",
    )
    session.add_all([market, instrument])
    session.flush()
    session.add_all(
        [
            DailyBar(
                instrument_id=instrument.id,
                trade_date=date(2026, 7, 8),
                open=Decimal("10"),
                high=Decimal("10"),
                low=Decimal("10"),
                close=Decimal("10"),
                volume=Decimal("1000"),
                provider="tushare",
                source="tushare.pro.daily",
                adjustment="raw",
            ),
            DailyBar(
                instrument_id=instrument.id,
                trade_date=date(2026, 7, 9),
                open=Decimal("20"),
                high=Decimal("20"),
                low=Decimal("20"),
                close=Decimal("20"),
                volume=Decimal("2000"),
                provider="akshare",
                source="akshare.stock_zh_a_hist",
                adjustment="qfq",
            ),
        ]
    )
    session.commit()
    monkeypatch.setattr(
        market_data_service,
        "get_provider",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("database hits must not construct a provider")
        ),
    )
    monkeypatch.setattr(
        market_data_service,
        "_fetch_daily_bars_from_database",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("latest must not load the full daily-bar history")
        ),
    )

    payload = get_latest_bar_payload(
        "600519",
        session=session,
        provider_name="yfinance",
        market="CN",
    )

    assert payload["item"]["close"] == 20.0
    assert payload["provider"] == "akshare"
    assert payload["upstream_source"] == "akshare.stock_zh_a_hist"
    assert payload["status"] == "degraded"
    assert payload["diagnostics"] == [
        {
            "source": "database",
            "status": "degraded",
            "code": "MIXED_DAILY_BAR_PROVENANCE",
            "message": "Stored daily bars span multiple provenance cohorts; only the latest coherent cohort was returned.",
            "dropped_row_count": 1,
        }
    ]


def test_get_latest_bar_payload_degrades_when_provenance_audit_fails():
    session = make_session()
    market = Market(
        code="CN",
        name="China A Share",
        timezone="Asia/Shanghai",
        currency="CNY",
    )
    instrument = Instrument(
        symbol="600519",
        name="Kweichow Moutai",
        market=market,
        asset_type="stock",
        currency="CNY",
    )
    session.add_all([market, instrument])
    session.flush()
    session.add(
        DailyBar(
            instrument_id=instrument.id,
            trade_date=date(2026, 7, 9),
            open=Decimal("20"),
            high=Decimal("20"),
            low=Decimal("20"),
            close=Decimal("20"),
            volume=Decimal("2000"),
            provider="akshare",
            source="akshare.stock_zh_a_hist",
            adjustment="qfq",
        )
    )
    session.commit()
    engine = session.get_bind()
    select_count = 0

    def fail_second_select(*_args, **_kwargs):
        nonlocal select_count
        select_count += 1
        if select_count == 2:
            raise SQLAlchemyError("provenance audit unavailable")

    event.listen(engine, "before_cursor_execute", fail_second_select)
    try:
        payload = get_latest_bar_payload(
            "600519",
            session=session,
            provider_name="yfinance",
            market="CN",
        )
    finally:
        event.remove(engine, "before_cursor_execute", fail_second_select)

    assert payload["item"]["close"] == 20.0
    assert payload["status"] == "degraded"
    assert payload["provenance_known"] is False
    assert payload["diagnostics"][0]["code"] == "UNKNOWN_DAILY_BAR_PROVENANCE"


def test_get_bars_payload_marks_legacy_database_provenance_unknown(monkeypatch):
    session = make_session()
    market = Market(
        code="CN",
        name="China A Share",
        timezone="Asia/Shanghai",
        currency="CNY",
    )
    instrument = Instrument(
        symbol="600519",
        name="Kweichow Moutai",
        market=market,
        asset_type="stock",
        currency="CNY",
    )
    session.add_all([market, instrument])
    session.flush()
    session.add(
        DailyBar(
            instrument_id=instrument.id,
            trade_date=date(2026, 7, 9),
            open=Decimal("20"),
            high=Decimal("20"),
            low=Decimal("20"),
            close=Decimal("20"),
            volume=Decimal("2000"),
        )
    )
    session.commit()
    monkeypatch.setattr(
        market_data_service,
        "get_provider",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("database hits must not construct a provider")
        ),
    )

    payload = get_bars_payload(
        "600519",
        "1d",
        date(2026, 7, 9),
        date(2026, 7, 9),
        session=session,
        provider_name="yfinance",
        market="CN",
    )

    assert payload["provider"] is None
    assert payload["effective_provider"] is None
    assert payload["upstream_source"] is None
    assert payload["adjustment"] == "legacy_unknown"
    assert payload["provenance_known"] is False
    assert payload["status"] == "degraded"
    assert payload["diagnostics"][0]["code"] == "UNKNOWN_DAILY_BAR_PROVENANCE"


def test_get_bars_payload_corrects_legacy_tushare_adjustment(monkeypatch):
    session = make_session()
    market = Market(
        code="CN",
        name="China A Share",
        timezone="Asia/Shanghai",
        currency="CNY",
    )
    instrument = Instrument(
        symbol="920000",
        name="BSE listing",
        market=market,
        asset_type="stock",
        currency="CNY",
    )
    session.add_all([market, instrument])
    session.flush()
    session.add(
        DailyBar(
            instrument_id=instrument.id,
            trade_date=date(2026, 7, 9),
            open=Decimal("20"),
            high=Decimal("20"),
            low=Decimal("20"),
            close=Decimal("20"),
            volume=Decimal("2000"),
            provider="tushare",
            source="tushare.pro.daily",
            adjustment="qfq",
        )
    )
    session.commit()
    monkeypatch.setattr(
        market_data_service,
        "get_provider",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("database hits must not construct a provider")
        ),
    )

    payload = get_bars_payload(
        "920000",
        "1d",
        date(2026, 7, 9),
        date(2026, 7, 9),
        session=session,
        provider_name="yfinance",
        market="CN",
    )

    assert payload["provider"] == "tushare"
    assert payload["upstream_source"] == "tushare.pro.daily"
    assert payload["adjustment"] == "raw"
    assert payload["provenance_known"] is True
    assert payload["provenance_corrected"] is True
    assert payload["status"] == "ok"


def test_get_latest_bar_payload_inherits_market_and_daily_fallback_provenance(
    monkeypatch,
):
    captured: dict[str, object] = {}
    attempts = [
        {
            "provider": "yfinance",
            "source": "yfinance.fetch_bars",
            "status": "no_data",
            "row_count": 0,
        },
        {
            "provider": "akshare",
            "source": "akshare.stock_zh_a_hist",
            "status": "selected",
            "row_count": 1,
        },
    ]

    def bars_stub(symbol, timeframe, start, end, **kwargs):
        captured.update(kwargs)
        return {
            "symbol": symbol,
            "market": "CN",
            "timeframe": timeframe,
            "source": "akshare.stock_zh_a_hist",
            "provider": "akshare",
            "requested_provider": "yfinance",
            "effective_provider": "akshare",
            "upstream_source": "akshare.stock_zh_a_hist",
            "adjustment": "qfq",
            "provenance_known": True,
            "provenance_corrected": False,
            "fallback_used": True,
            "source_attempts": attempts,
            "diagnostics": [],
            "status": "ok",
            "no_data_reason": None,
            "items": [{"timestamp": "2026-07-09", "close": 1495.0}],
        }

    monkeypatch.setattr(market_data_service, "get_bars_payload", bars_stub)

    payload = get_latest_bar_payload(
        "600519",
        provider_name="yfinance",
        market="CN",
    )

    assert captured["market"] == "CN"
    assert payload["item"]["close"] == 1495.0
    assert payload["effective_provider"] == "akshare"
    assert payload["source"] == "akshare.stock_zh_a_hist"
    assert payload["upstream_source"] == "akshare.stock_zh_a_hist"
    assert payload["adjustment"] == "qfq"
    assert payload["provenance_known"] is True
    assert payload["provenance_corrected"] is False
    assert payload["diagnostics"] == []
    assert payload["fallback_used"] is True
    assert payload["source_attempts"] == attempts


def test_get_latest_bar_payload_preserves_degraded_daily_source_exhaustion(
    monkeypatch,
):
    monkeypatch.setattr(
        market_data_service,
        "get_bars_payload",
        lambda *args, **kwargs: {
            "symbol": "600519",
            "market": "CN",
            "timeframe": "1d",
            "source": "none",
            "provider": "yfinance",
            "requested_provider": "yfinance",
            "effective_provider": "yfinance",
            "adjustment": None,
            "fallback_used": False,
            "source_attempts": [
                {
                    "provider": "yfinance",
                    "source": "yfinance.fetch_bars",
                    "status": "failed",
                    "exception_type": "TimeoutError",
                }
            ],
            "status": "degraded",
            "no_data_reason": "No daily bars were available for the requested symbol/date range.",
            "items": [],
        },
    )

    payload = get_latest_bar_payload(
        "600519",
        provider_name="yfinance",
        market="CN",
    )

    assert payload["item"] is None
    assert payload["status"] == "degraded"
    assert payload["source_attempts"][0]["status"] == "failed"


def test_get_latest_bar_payload_preserves_degraded_status_with_partial_bars(
    monkeypatch,
):
    monkeypatch.setattr(
        market_data_service,
        "get_bars_payload",
        lambda *args, **kwargs: {
            "symbol": "600519",
            "market": "CN",
            "timeframe": "1d",
            "source": "database",
            "provider": "akshare",
            "requested_provider": "yfinance",
            "effective_provider": "akshare",
            "upstream_source": "akshare.stock_zh_a_hist",
            "adjustment": "qfq",
            "provenance_known": True,
            "provenance_corrected": False,
            "fallback_used": False,
            "source_attempts": [],
            "diagnostics": [
                {
                    "source": "database",
                    "status": "degraded",
                    "code": "MIXED_DAILY_BAR_PROVENANCE",
                }
            ],
            "status": "degraded",
            "no_data_reason": None,
            "items": [{"timestamp": "2026-07-09", "close": 1495.0}],
        },
    )

    payload = get_latest_bar_payload(
        "600519",
        provider_name="yfinance",
        market="CN",
    )

    assert payload["item"]["close"] == 1495.0
    assert payload["status"] == "degraded"
    assert payload["diagnostics"][0]["code"] == "MIXED_DAILY_BAR_PROVENANCE"


def test_get_indicator_payload_inherits_market_and_daily_fallback_provenance(
    monkeypatch,
):
    captured: dict[str, object] = {}
    attempts = [
        {
            "provider": "yfinance",
            "source": "yfinance.fetch_bars",
            "status": "no_data",
            "row_count": 0,
        },
        {
            "provider": "akshare",
            "source": "akshare.stock_zh_a_daily",
            "status": "selected",
            "row_count": 2,
        },
    ]

    def bars_stub(symbol, timeframe, start, end, **kwargs):
        captured.update(kwargs)
        return {
            "symbol": symbol,
            "market": "CN",
            "timeframe": timeframe,
            "source": "akshare.stock_zh_a_daily",
            "provider": "akshare",
            "requested_provider": "yfinance",
            "effective_provider": "akshare",
            "upstream_source": "akshare.stock_zh_a_daily",
            "adjustment": "qfq",
            "provenance_known": True,
            "provenance_corrected": False,
            "fallback_used": True,
            "source_attempts": attempts,
            "diagnostics": [
                {
                    "source": "database",
                    "status": "degraded",
                    "code": "MIXED_DAILY_BAR_PROVENANCE",
                }
            ],
            "status": "degraded",
            "no_data_reason": None,
            "items": [
                {"timestamp": "2026-07-08", "close": 1490.0},
                {"timestamp": "2026-07-09", "close": 1495.0},
            ],
        }

    monkeypatch.setattr(market_data_service, "get_bars_payload", bars_stub)

    payload = get_indicator_payload(
        "600519",
        date(2026, 7, 1),
        date(2026, 7, 10),
        2,
        provider_name="yfinance",
        market="CN",
    )

    assert captured["market"] == "CN"
    assert payload["market"] == "CN"
    assert payload["effective_provider"] == "akshare"
    assert payload["source"] == "akshare.stock_zh_a_daily"
    assert payload["upstream_source"] == "akshare.stock_zh_a_daily"
    assert payload["adjustment"] == "qfq"
    assert payload["provenance_known"] is True
    assert payload["provenance_corrected"] is False
    assert payload["fallback_used"] is True
    assert payload["source_attempts"] == attempts
    assert payload["diagnostics"][0]["code"] == "MIXED_DAILY_BAR_PROVENANCE"
    assert payload["status"] == "degraded"
    assert payload["indicators"]["ma"] == 1492.5


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


def test_get_intraday_bars_payload_reuses_stored_previous_close_without_daily_recovery(
    monkeypatch,
):
    session = make_session()
    seed_cn_daily_bars(session, [date(2026, 7, 14)])
    daily_calls: list[str] = []

    class FakeIntradayProvider:
        def fetch_bars(
            self, symbol: str, timeframe: str, start: date, end: date
        ) -> list[ProviderBar]:
            daily_calls.append(timeframe)
            return []

        def fetch_intraday_bars(
            self, symbol: str, trade_date: date, timeframe: str
        ) -> list[ProviderIntradayBar]:
            return [
                ProviderIntradayBar(
                    symbol=symbol,
                    timestamp=datetime(2026, 7, 15, 1, 30, tzinfo=timezone.utc),
                    open=Decimal("201"),
                    high=Decimal("202"),
                    low=Decimal("200"),
                    close=Decimal("201.5"),
                    volume=1000,
                )
            ]

    provider = FakeIntradayProvider()
    monkeypatch.setattr(
        market_data_service,
        "get_provider",
        lambda *_args, **_kwargs: provider,
    )
    monkeypatch.setattr(
        market_data_service,
        "get_platform_settings",
        lambda: {"akshare_enabled": False},
    )

    payload = get_intraday_bars_payload(
        "600519",
        date(2026, 7, 15),
        session=session,
        provider_name="yfinance",
        market="CN",
    )

    assert payload["status"] == "ok"
    assert payload["previous_close"] == 100.0
    assert daily_calls == []


def test_get_intraday_bars_payload_falls_back_to_akshare_for_exact_cn_stock(
    monkeypatch,
):
    session = make_session()
    market = Market(
        code="CN",
        name="China A Share",
        timezone="Asia/Shanghai",
        currency="CNY",
    )
    instrument = Instrument(
        symbol="600519",
        name="Kweichow Moutai",
        market=market,
        asset_type="stock",
        currency="CNY",
    )
    session.add_all([market, instrument])
    session.flush()
    session.add(
        DailyBar(
            instrument_id=instrument.id,
            trade_date=date(2026, 7, 14),
            open=Decimal("1470"),
            high=Decimal("1480"),
            low=Decimal("1465"),
            close=Decimal("1478"),
            volume=Decimal("1000"),
            provider="akshare",
            source="akshare.stock_zh_a_hist",
            adjustment="qfq",
        )
    )
    session.commit()
    provider_calls: list[tuple[str, str | None]] = []

    class Provider:
        def __init__(self, name: str, intraday_bars: list[ProviderIntradayBar]) -> None:
            self.name = name
            self.intraday_bars = intraday_bars

        def fetch_bars(self, *_args):
            return []

        def fetch_intraday_bars(self, *_args):
            return self.intraday_bars

    trade_date = date(2026, 7, 15)
    akshare_bar = ProviderIntradayBar(
        symbol="600519",
        timestamp=datetime(2026, 7, 15, 9, 31, tzinfo=timezone.utc),
        open=Decimal("1480"),
        high=Decimal("1490"),
        low=Decimal("1475"),
        close=Decimal("1488"),
        volume=1200,
        amount=Decimal("1785600"),
    )
    malformed_primary_bar = ProviderIntradayBar(
        symbol="600519",
        timestamp=datetime(2026, 7, 15, 9, 31, tzinfo=timezone.utc),
        open=Decimal("1480"),
        high=Decimal("1490"),
        low=Decimal("1475"),
        close=Decimal("1488"),
        volume=1200,
    )
    object.__setattr__(malformed_primary_bar, "symbol", None)
    providers = {
        "yfinance": Provider("yfinance", [malformed_primary_bar]),
        "akshare": Provider("akshare", [akshare_bar]),
    }

    def provider_factory(provider_name=None, market=None):
        normalized_name = str(provider_name)
        provider_calls.append((normalized_name, market))
        return providers[normalized_name]

    monkeypatch.setattr(market_data_service, "get_provider", provider_factory)
    monkeypatch.setattr(
        market_data_service,
        "get_platform_settings",
        lambda: {"akshare_enabled": True},
    )

    payload = get_intraday_bars_payload(
        "600519",
        trade_date,
        session=session,
        provider_name="yfinance",
        market="CN",
    )

    assert provider_calls == [("yfinance", "CN"), ("akshare", "CN")]
    assert payload["status"] == "ok"
    assert payload["source"] == "provider"
    assert payload["provider"] == "akshare"
    assert payload["requested_provider"] == "yfinance"
    assert payload["effective_provider"] == "akshare"
    assert payload["upstream_source"] == "akshare.stock_zh_a_hist_min_em"
    assert payload["fallback_used"] is True
    assert payload["source_attempts"] == [
        {
            "provider": "yfinance",
            "source": "yfinance.fetch_intraday_bars",
            "status": "invalid",
            "code": "MALFORMED_INTRADAY_BAR",
        },
        {
            "provider": "akshare",
            "source": "akshare.stock_zh_a_hist_min_em",
            "status": "selected",
            "row_count": 1,
        },
    ]
    assert payload["session"]["market"] == "CN"
    assert payload["session"]["timezone"] == "Asia/Shanghai"
    assert payload["items"][0]["close"] == 1488.0


def test_get_intraday_bars_payload_falls_back_after_mixed_timestamp_awareness(
    monkeypatch,
):
    trade_date = date(2026, 7, 15)

    class Provider:
        def __init__(self, bars: list[ProviderIntradayBar]) -> None:
            self.bars = bars

        def fetch_intraday_bars(self, *_args):
            return self.bars

    primary = Provider(
        [
            ProviderIntradayBar(
                symbol="600519",
                timestamp=datetime(2026, 7, 15, 1, 31, tzinfo=timezone.utc),
                open=Decimal("1480"),
                high=Decimal("1490"),
                low=Decimal("1475"),
                close=Decimal("1488"),
                volume=1200,
            ),
            ProviderIntradayBar(
                symbol="600519",
                timestamp=datetime(2026, 7, 15, 9, 32),
                open=Decimal("1488"),
                high=Decimal("1492"),
                low=Decimal("1486"),
                close=Decimal("1490"),
                volume=900,
            ),
        ]
    )
    fallback = Provider(
        [
            ProviderIntradayBar(
                symbol="600519",
                timestamp=datetime(2026, 7, 15, 1, 31, tzinfo=timezone.utc),
                open=Decimal("1480"),
                high=Decimal("1490"),
                low=Decimal("1475"),
                close=Decimal("1488"),
                volume=1200,
            )
        ]
    )
    providers = {"yfinance": primary, "akshare": fallback}
    monkeypatch.setattr(
        market_data_service,
        "get_provider",
        lambda provider_name=None, market=None: providers[str(provider_name)],
    )
    monkeypatch.setattr(
        market_data_service,
        "get_platform_settings",
        lambda: {"akshare_enabled": True},
    )
    monkeypatch.setattr(
        market_data_service,
        "_get_previous_close_reference",
        lambda **_kwargs: None,
    )

    payload = get_intraday_bars_payload(
        "600519",
        trade_date,
        provider_name="yfinance",
        market="CN",
    )

    assert payload["status"] == "ok"
    assert payload["effective_provider"] == "akshare"
    assert payload["fallback_used"] is True
    assert payload["source_attempts"] == [
        {
            "provider": "yfinance",
            "source": "yfinance.fetch_intraday_bars",
            "status": "invalid",
            "code": "MIXED_INTRADAY_TIMESTAMP_AWARENESS",
        },
        {
            "provider": "akshare",
            "source": "akshare.stock_zh_a_hist_min_em",
            "status": "selected",
            "row_count": 1,
        },
    ]


def test_get_intraday_bars_payload_uses_sina_after_sanitized_cn_failures(
    monkeypatch,
):
    session = make_session()
    market = Market(
        code="CN",
        name="China A Share",
        timezone="Asia/Shanghai",
        currency="CNY",
    )
    instrument = Instrument(
        symbol="600519",
        name="Kweichow Moutai",
        market=market,
        asset_type="stock",
        currency="CNY",
    )
    session.add_all([market, instrument])
    session.flush()
    session.add(
        DailyBar(
            instrument_id=instrument.id,
            trade_date=date(2026, 7, 14),
            open=Decimal("1470"),
            high=Decimal("1480"),
            low=Decimal("1465"),
            close=Decimal("1478"),
            volume=Decimal("1000"),
            provider="akshare",
            source="akshare.stock_zh_a_hist",
            adjustment="qfq",
        )
    )
    session.commit()

    class PrimaryProvider:
        def fetch_bars(self, *_args):
            return []

        def fetch_intraday_bars(self, *_args):
            raise TimeoutError("private token=secret")

    class EmptyEastmoneyProvider:
        def fetch_bars(self, *_args):
            return []

        def fetch_intraday_bars(self, *_args):
            return []

    class SinaProvider:
        download_sina_intraday_bars = staticmethod(lambda *_args: None)

        def __init__(self, **_kwargs):
            pass

        def fetch_intraday_bars(self, symbol, trade_date, timeframe):
            return [
                ProviderIntradayBar(
                    symbol=symbol,
                    timestamp=datetime(2026, 7, 15, 1, 31, tzinfo=timezone.utc),
                    open=Decimal("1480"),
                    high=Decimal("1490"),
                    low=Decimal("1475"),
                    close=Decimal("1488"),
                    volume=1200,
                )
            ]

    providers = {
        "yfinance": PrimaryProvider(),
        "akshare": EmptyEastmoneyProvider(),
    }
    monkeypatch.setattr(
        market_data_service,
        "get_provider",
        lambda provider_name=None, market=None: providers[str(provider_name)],
    )
    monkeypatch.setattr(market_data_service, "AkShareProvider", SinaProvider)
    monkeypatch.setattr(
        market_data_service,
        "get_platform_settings",
        lambda: {"akshare_enabled": True},
    )

    payload = get_intraday_bars_payload(
        "600519",
        date(2026, 7, 15),
        session=session,
        provider_name="yfinance",
        market="CN",
    )

    assert payload["status"] == "ok"
    assert payload["effective_provider"] == "akshare"
    assert payload["upstream_source"] == "akshare.stock_zh_a_minute"
    assert payload["fallback_used"] is True
    assert [attempt["status"] for attempt in payload["source_attempts"]] == [
        "failed",
        "no_data",
        "selected",
    ]
    assert payload["source_attempts"][0]["exception_type"] == "TimeoutError"
    assert "private token=secret" not in str(payload)


@pytest.mark.parametrize(
    ("primary_fails", "expected_status"),
    [(False, "no_data"), (True, "degraded")],
)
def test_get_intraday_bars_payload_distinguishes_cn_empty_from_failed_exhaustion(
    monkeypatch,
    primary_fails,
    expected_status,
):
    class PrimaryProvider:
        def fetch_intraday_bars(self, *_args):
            if primary_fails:
                raise RuntimeError("private token=secret")
            return []

    class EmptyAkShareProvider:
        download_sina_intraday_bars = staticmethod(lambda *_args: None)

        def __init__(self, **_kwargs):
            pass

        def fetch_intraday_bars(self, *_args):
            return []

    providers = {
        "yfinance": PrimaryProvider(),
        "akshare": EmptyAkShareProvider(),
    }
    monkeypatch.setattr(
        market_data_service,
        "get_provider",
        lambda provider_name=None, market=None: providers[str(provider_name)],
    )
    monkeypatch.setattr(market_data_service, "AkShareProvider", EmptyAkShareProvider)
    monkeypatch.setattr(
        market_data_service,
        "get_platform_settings",
        lambda: {"akshare_enabled": True},
    )
    monkeypatch.setattr(
        market_data_service,
        "_get_previous_close_reference",
        lambda **_kwargs: None,
    )

    payload = get_intraday_bars_payload(
        "600519",
        date(2026, 7, 15),
        provider_name="yfinance",
        market="CN",
    )

    assert payload["status"] == expected_status
    assert payload["availability"]["status"] == expected_status
    assert [attempt["status"] for attempt in payload["source_attempts"]] == [
        "failed" if primary_fails else "no_data",
        "no_data",
        "no_data",
    ]
    if primary_fails:
        assert payload["source_attempts"][0]["exception_type"] == "RuntimeError"
    assert "private token=secret" not in str(payload)


def test_get_intraday_bars_payload_reuses_cn_fallback_cache_for_requested_provider(
    monkeypatch,
):
    session = make_session()
    market = Market(
        code="CN",
        name="China A Share",
        timezone="Asia/Shanghai",
        currency="CNY",
    )
    instrument = Instrument(
        symbol="600519",
        name="Kweichow Moutai",
        market=market,
        asset_type="stock",
        currency="CNY",
    )
    session.add_all([market, instrument])
    session.flush()
    session.add(
        DailyBar(
            instrument_id=instrument.id,
            trade_date=date(2026, 7, 13),
            open=Decimal("1470"),
            high=Decimal("1480"),
            low=Decimal("1465"),
            close=Decimal("1478"),
            volume=Decimal("1000"),
            provider="akshare",
            source="akshare.stock_zh_a_hist",
            adjustment="qfq",
        )
    )
    session.commit()

    class Provider:
        def __init__(self, bars: list[ProviderIntradayBar]) -> None:
            self.bars = bars
            self.intraday_calls = 0

        def fetch_bars(self, *_args):
            return []

        def fetch_intraday_bars(self, *_args):
            self.intraday_calls += 1
            return self.bars

    trade_date = date(2026, 7, 14)
    yfinance = Provider([])
    akshare = Provider(
        [
            ProviderIntradayBar(
                symbol="600519",
                timestamp=datetime(2026, 7, 14, 1, 31, tzinfo=timezone.utc),
                open=Decimal("1480"),
                high=Decimal("1490"),
                low=Decimal("1475"),
                close=Decimal("1488"),
                volume=1200,
                amount=Decimal("1785600"),
            )
        ]
    )
    providers = {"yfinance": yfinance, "akshare": akshare}
    monkeypatch.setattr(
        market_data_service,
        "get_provider",
        lambda provider_name=None, market=None: providers[str(provider_name)],
    )
    monkeypatch.setattr(
        market_data_service,
        "get_platform_settings",
        lambda: {"akshare_enabled": True},
    )

    first_payload = get_intraday_bars_payload(
        "600519",
        trade_date,
        session=session,
        provider_name="yfinance",
        market="CN",
    )
    second_payload = get_intraday_bars_payload(
        "600519",
        trade_date,
        session=session,
        provider_name="yfinance",
        market="CN",
    )

    assert first_payload["source"] == "provider"
    assert first_payload["effective_provider"] == "akshare"
    assert second_payload["source"] == "cache"
    assert second_payload["effective_provider"] == "akshare"
    assert second_payload["upstream_source"] == "akshare.stock_zh_a_hist_min_em"
    assert second_payload["fallback_used"] is True
    assert second_payload["freshness"]["cache_status"] == "hit"
    assert yfinance.intraday_calls == 1
    assert akshare.intraday_calls == 1
    cache_entry = session.query(IntradayMinuteCacheEntry).one()
    assert cache_entry.provider == "akshare"
    assert cache_entry.source == "akshare.stock_zh_a_hist_min_em"


@pytest.mark.parametrize("requested_provider", ["akshare", "tushare"])
def test_get_intraday_bars_payload_reuses_exact_cache_after_provider_change(
    monkeypatch,
    requested_provider,
):
    session = make_session()
    seed_cn_intraday_cache(
        session,
        provider="yfinance",
        source="yfinance.fetch_intraday_bars",
    )

    class ProviderThatMustNotRun:
        def fetch_bars(self, *_args):
            raise AssertionError("provider daily fetch must not run for a cache hit")

        def fetch_intraday_bars(self, *_args):
            raise AssertionError("provider minute fetch must not run for a cache hit")

    provider = ProviderThatMustNotRun()
    monkeypatch.setattr(
        market_data_service,
        "get_provider",
        lambda provider_name=None, market=None: provider,
    )
    monkeypatch.setattr(
        market_data_service,
        "get_platform_settings",
        lambda: {"akshare_enabled": False},
    )

    payload = get_intraday_bars_payload(
        "600519",
        date(2026, 7, 14),
        session=session,
        provider_name=requested_provider,
        market="CN",
    )

    assert payload["status"] == "ok"
    assert payload["source"] == "cache"
    assert payload["effective_provider"] == "yfinance"
    assert payload["upstream_source"] == "yfinance.fetch_intraday_bars"
    assert payload["fallback_used"] is True
    assert payload["freshness"]["cache_status"] == "hit"
    assert payload["items"][0]["close"] == 1488.0


def test_get_intraday_bars_payload_reuses_disabled_akshare_cache(monkeypatch):
    session = make_session()
    seed_cn_intraday_cache(
        session,
        provider="akshare",
        source="akshare.stock_zh_a_minute",
    )

    class ProviderThatMustNotRun:
        def fetch_bars(self, *_args):
            raise AssertionError("provider daily fetch must not run for a cache hit")

        def fetch_intraday_bars(self, *_args):
            raise AssertionError("provider minute fetch must not run for a cache hit")

    provider = ProviderThatMustNotRun()
    monkeypatch.setattr(
        market_data_service,
        "get_provider",
        lambda provider_name=None, market=None: provider,
    )
    monkeypatch.setattr(
        market_data_service,
        "get_platform_settings",
        lambda: {"akshare_enabled": False},
    )

    payload = get_intraday_bars_payload(
        "600519",
        date(2026, 7, 14),
        session=session,
        provider_name="yfinance",
        market="CN",
    )

    assert payload["status"] == "ok"
    assert payload["source"] == "cache"
    assert payload["effective_provider"] == "akshare"
    assert payload["upstream_source"] == "akshare.stock_zh_a_minute"
    assert payload["fallback_used"] is True
    assert payload["freshness"]["cache_status"] == "hit"


def test_get_intraday_bars_payload_replaces_conflicting_cn_cache_metadata(
    monkeypatch,
):
    session = make_session()
    market = Market(
        code="CN",
        name="China A Share",
        timezone="Asia/Shanghai",
        currency="CNY",
    )
    instrument = Instrument(
        symbol="600519",
        name="Kweichow Moutai",
        market=market,
        asset_type="stock",
        currency="CNY",
    )
    session.add_all([market, instrument])
    session.flush()
    session.add(
        DailyBar(
            instrument_id=instrument.id,
            trade_date=date(2026, 7, 13),
            open=Decimal("1470"),
            high=Decimal("1480"),
            low=Decimal("1465"),
            close=Decimal("1478"),
            volume=Decimal("1000"),
            provider="akshare",
            source="akshare.stock_zh_a_hist",
            adjustment="qfq",
        )
    )
    timestamp = datetime(2026, 7, 14, 1, 31, tzinfo=timezone.utc)
    session.add(
        MinuteBar(
            instrument_id=instrument.id,
            ts=timestamp,
            open=Decimal("100"),
            high=Decimal("100"),
            low=Decimal("100"),
            close=Decimal("100"),
            volume=Decimal("100"),
        )
    )
    session.add(
        IntradayMinuteCacheEntry(
            instrument_id=instrument.id,
            provider="yfinance",
            symbol="600519",
            trade_date=date(2026, 7, 14),
            timeframe="1m",
            source="yfinance.fetch_intraday_bars",
            row_count=2,
            first_ts=timestamp,
            last_ts=timestamp,
            fetched_at=timestamp,
            cached_at=timestamp,
        )
    )
    session.commit()

    class Provider:
        def __init__(self, bars: list[ProviderIntradayBar]) -> None:
            self.bars = bars

        def fetch_bars(self, *_args):
            return []

        def fetch_intraday_bars(self, *_args):
            return self.bars

    providers = {
        "yfinance": Provider([]),
        "akshare": Provider(
            [
                ProviderIntradayBar(
                    symbol="600519",
                    timestamp=timestamp,
                    open=Decimal("1480"),
                    high=Decimal("1490"),
                    low=Decimal("1475"),
                    close=Decimal("1488"),
                    volume=1200,
                    amount=Decimal("1785600"),
                )
            ]
        ),
    }
    monkeypatch.setattr(
        market_data_service,
        "get_provider",
        lambda provider_name=None, market=None: providers[str(provider_name)],
    )
    monkeypatch.setattr(
        market_data_service,
        "get_platform_settings",
        lambda: {"akshare_enabled": True},
    )

    payload = get_intraday_bars_payload(
        "600519",
        date(2026, 7, 14),
        session=session,
        provider_name="yfinance",
        market="CN",
    )

    assert payload["status"] == "ok"
    assert payload["effective_provider"] == "akshare"
    cache_entries = session.query(IntradayMinuteCacheEntry).all()
    assert [(entry.provider, entry.source) for entry in cache_entries] == [
        ("akshare", "akshare.stock_zh_a_hist_min_em")
    ]
    minute_bars = session.query(MinuteBar).all()
    assert len(minute_bars) == 1
    assert minute_bars[0].close == Decimal("1488")


def test_get_intraday_bars_payload_persists_and_reuses_each_market_cache_independently(
    monkeypatch,
):
    session = make_session()
    cn_market = Market(
        code="CN",
        name="China A Share",
        timezone="Asia/Shanghai",
        currency="CNY",
    )
    hk_market = Market(
        code="HK",
        name="Hong Kong Stock",
        timezone="Asia/Hong_Kong",
        currency="HKD",
    )
    cn_instrument = Instrument(
        symbol="000001",
        name="CN listing",
        market=cn_market,
        asset_type="stock",
        currency="CNY",
    )
    hk_instrument = Instrument(
        symbol="000001",
        name="HK listing",
        market=hk_market,
        asset_type="stock",
        currency="HKD",
    )
    session.add_all([cn_market, hk_market, cn_instrument, hk_instrument])
    session.flush()
    session.add(
        DailyBar(
            instrument_id=cn_instrument.id,
            trade_date=date(2026, 7, 13),
            open=Decimal("10"),
            high=Decimal("10"),
            low=Decimal("10"),
            close=Decimal("10"),
            volume=Decimal("1000"),
            provider="akshare",
            source="akshare.stock_zh_a_hist",
            adjustment="qfq",
        )
    )
    timestamp = datetime(2026, 7, 14, 1, 31, tzinfo=timezone.utc)
    session.add(
        MinuteBar(
            instrument_id=hk_instrument.id,
            ts=timestamp,
            open=Decimal("99"),
            high=Decimal("99"),
            low=Decimal("99"),
            close=Decimal("99"),
            volume=Decimal("100"),
        )
    )
    session.add(
        IntradayMinuteCacheEntry(
            instrument_id=hk_instrument.id,
            provider="yfinance",
            symbol="000001",
            trade_date=date(2026, 7, 14),
            timeframe="1m",
            source="yfinance.fetch_intraday_bars",
            row_count=1,
            first_ts=timestamp,
            last_ts=timestamp,
            fetched_at=timestamp,
            cached_at=timestamp,
        )
    )
    session.commit()

    class Provider:
        def __init__(self, bars: list[ProviderIntradayBar]) -> None:
            self.bars = bars
            self.intraday_calls = 0

        def fetch_bars(self, *_args):
            return []

        def fetch_intraday_bars(self, *_args):
            self.intraday_calls += 1
            return self.bars

    yfinance = Provider(
        [
            ProviderIntradayBar(
                symbol="000001",
                timestamp=timestamp,
                open=Decimal("11"),
                high=Decimal("12"),
                low=Decimal("10"),
                close=Decimal("11"),
                volume=1200,
            )
        ]
    )
    providers = {"yfinance": yfinance, "akshare": Provider([])}
    monkeypatch.setattr(
        market_data_service,
        "get_provider",
        lambda provider_name=None, market=None: providers[str(provider_name)],
    )
    monkeypatch.setattr(
        market_data_service,
        "get_platform_settings",
        lambda: {"akshare_enabled": False},
    )

    first_payload = get_intraday_bars_payload(
        "000001",
        date(2026, 7, 14),
        session=session,
        provider_name="yfinance",
        market="CN",
    )
    second_payload = get_intraday_bars_payload(
        "000001",
        date(2026, 7, 14),
        session=session,
        provider_name="yfinance",
        market="CN",
    )

    assert first_payload["status"] == "ok"
    assert first_payload["source"] == "provider"
    assert first_payload["items"][0]["close"] == 11.0
    assert first_payload["freshness"]["cache_status"] == "miss"
    assert second_payload["status"] == "ok"
    assert second_payload["source"] == "cache"
    assert second_payload["items"][0]["close"] == 11.0
    assert second_payload["freshness"]["cache_status"] == "hit"
    assert yfinance.intraday_calls == 1
    cache_entries = session.query(IntradayMinuteCacheEntry).order_by(
        IntradayMinuteCacheEntry.instrument_id
    ).all()
    assert {entry.instrument_id for entry in cache_entries} == {
        cn_instrument.id,
        hk_instrument.id,
    }
    minute_bars = session.query(MinuteBar).all()
    assert {(bar.instrument_id, bar.close) for bar in minute_bars} == {
        (cn_instrument.id, Decimal("11")),
        (hk_instrument.id, Decimal("99")),
    }


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


@pytest.mark.parametrize(
    ("symbol", "market"),
    [
        pytest.param("00700", "HK", id="hong-kong"),
        pytest.param("AAPL", "US", id="united-states"),
        pytest.param("600519", None, id="ambiguous-market"),
        pytest.param("60051", "CN", id="non-six-digit-cn"),
    ],
)
def test_get_intraday_bars_payload_does_not_call_akshare_minutes_for_non_cn_identity(
    monkeypatch,
    symbol,
    market,
):
    minute_calls: list[tuple[str, date, str]] = []

    class AkShareMinuteProvider:
        def fetch_intraday_bars(self, requested_symbol, trade_date, timeframe):
            minute_calls.append((requested_symbol, trade_date, timeframe))
            return []

    monkeypatch.setattr(
        market_data_service,
        "get_provider",
        lambda provider_name=None, market=None: AkShareMinuteProvider(),
    )

    payload = get_intraday_bars_payload(
        symbol,
        date(2026, 7, 15),
        provider_name="akshare",
        market=market,
    )

    assert payload["status"] == "degraded"
    assert payload["source"] == "none"
    assert payload["availability"]["reason"] == market_data_service.INTRADAY_UNSUPPORTED_REASON
    assert minute_calls == []


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
