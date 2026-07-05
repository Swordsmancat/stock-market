from datetime import date, datetime, timezone
from decimal import Decimal

import pandas as pd
import pytest

from packages.providers.base import ProviderBar
from packages.providers.base import ProviderInstrument
from packages.providers.base import ProviderIntradayBar
from packages.providers.base import ProviderMarketDepthSnapshot
from packages.providers.base import ProviderOrderBookLevel
from packages.providers.yfinance_provider import YFinanceProvider
from scripts import provider_readiness


class FakeSuccessfulProvider:
    def fetch_instruments(
        self,
        market: str,
        exchange: str | None = None,
    ) -> list[ProviderInstrument]:
        instrument = ProviderInstrument(
            symbol="AAPL",
            name="Apple Inc.",
            market=market,
            exchange="NASDAQ",
            asset_type="stock",
            currency="USD",
        )
        if exchange is not None and exchange != instrument.exchange:
            return []
        return [instrument]

    def fetch_bars(
        self,
        symbol: str,
        timeframe: str,
        start: date,
        end: date,
    ) -> list[ProviderBar]:
        return [
            ProviderBar(
                symbol=symbol,
                timestamp=start,
                open=Decimal("100.00"),
                high=Decimal("101.00"),
                low=Decimal("99.00"),
                close=Decimal("100.50"),
                volume=Decimal("1000000"),
                amount=Decimal("100500000"),
            )
        ]


class FakeMarketDepthProvider(FakeSuccessfulProvider):
    def fetch_bars(
        self,
        symbol: str,
        timeframe: str,
        start: date,
        end: date,
    ) -> list[ProviderBar]:
        raise AssertionError("daily bars must not be used for market-depth readiness")

    def fetch_market_depth(self, symbol: str, depth_levels: int) -> ProviderMarketDepthSnapshot:
        assert symbol == "600519"
        assert depth_levels == 5
        return ProviderMarketDepthSnapshot(
            provider="akshare",
            source="akshare.fixture",
            as_of=None,
            is_realtime=False,
            is_delayed=True,
            delay_minutes=15,
            bids=[ProviderOrderBookLevel(price=Decimal("101.20"), volume=Decimal("1000"))],
            asks=[],
            recent_trades=[],
            fund_flow=None,
            availability={"status": "ok", "reason": None},
        )


class FakeDiagnosticMarketDepthProvider(FakeSuccessfulProvider):
    def fetch_bars(
        self,
        symbol: str,
        timeframe: str,
        start: date,
        end: date,
    ) -> list[ProviderBar]:
        raise AssertionError("daily bars must not be used for market-depth readiness")

    def fetch_market_depth(self, symbol: str, depth_levels: int) -> ProviderMarketDepthSnapshot:
        assert symbol == "600519"
        assert depth_levels == 5
        return ProviderMarketDepthSnapshot(
            provider="akshare",
            source="akshare.fixture",
            as_of=None,
            is_realtime=False,
            is_delayed=True,
            delay_minutes=15,
            bids=[],
            asks=[],
            recent_trades=[],
            fund_flow=None,
            availability={
                "status": "degraded",
                "reason": "AkShare order-book payload could not be normalized.",
                "raw_shape": "3x2",
                "raw_columns": ["item", "value"],
                "raw_fields_sample": ["bid_one", "bid_one_volume"],
            },
        )


class FakeIntradayProvider(FakeSuccessfulProvider):
    def fetch_bars(
        self,
        symbol: str,
        timeframe: str,
        start: date,
        end: date,
    ) -> list[ProviderBar]:
        raise AssertionError("daily bars must not be used for intraday readiness")

    def fetch_intraday_bars(
        self,
        symbol: str,
        trade_date: date,
        timeframe: str,
    ) -> list[ProviderIntradayBar]:
        assert symbol == "AAPL"
        assert trade_date == date(2026, 7, 2)
        assert timeframe == "1m"
        return [
            ProviderIntradayBar(
                symbol="AAPL",
                timestamp=datetime(2026, 7, 2, 13, 30, tzinfo=timezone.utc),
                open=Decimal("214.10"),
                high=Decimal("214.30"),
                low=Decimal("213.90"),
                close=Decimal("214.20"),
                volume=12000,
            )
        ]


class FakeWindowIntradayProvider(FakeSuccessfulProvider):
    def __init__(self) -> None:
        self.attempted_dates: list[date] = []

    def fetch_bars(
        self,
        symbol: str,
        timeframe: str,
        start: date,
        end: date,
    ) -> list[ProviderBar]:
        raise AssertionError("daily bars must not be used for intraday readiness")

    def fetch_intraday_bars(
        self,
        symbol: str,
        trade_date: date,
        timeframe: str,
    ) -> list[ProviderIntradayBar]:
        assert symbol == "AAPL"
        assert timeframe == "1m"
        self.attempted_dates.append(trade_date)
        if trade_date != date(2026, 7, 2):
            return []
        return [
            ProviderIntradayBar(
                symbol="AAPL",
                timestamp=datetime(2026, 7, 2, 13, 30, tzinfo=timezone.utc),
                open=Decimal("213.10"),
                high=Decimal("213.30"),
                low=Decimal("212.90"),
                close=Decimal("213.20"),
                volume=12000,
            )
        ]


class FakeFutureIntradayProvider(FakeSuccessfulProvider):
    def fetch_bars(
        self,
        symbol: str,
        timeframe: str,
        start: date,
        end: date,
    ) -> list[ProviderBar]:
        raise AssertionError("daily bars must not be used for intraday readiness")

    def fetch_intraday_bars(
        self,
        symbol: str,
        trade_date: date,
        timeframe: str,
    ) -> list[ProviderIntradayBar]:
        raise AssertionError("future trade-date readiness should not call the provider minute endpoint")


def test_mock_provider_succeeds(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setitem(provider_readiness.PROVIDER_FACTORIES, "mock", FakeSuccessfulProvider)

    exit_code = provider_readiness.main(["--provider", "mock", "--market", "US"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "OK provider readiness" in output
    assert "mock returned 1 bars for AAPL" in output
    assert "Summary: OK=1 WARN=0 FAIL=0" in output


def test_unknown_provider_returns_fail(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = provider_readiness.main(["--provider", "unknown", "--market", "US"])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "FAIL provider readiness" in output
    assert "unknown provider: unknown" in output
    assert "Summary: OK=0 WARN=0 FAIL=1" in output


def test_yfinance_without_real_network_returns_warn(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_if_yfinance_is_constructed() -> FakeSuccessfulProvider:
        pytest.fail("yfinance provider should not be constructed without --real-network")

    monkeypatch.setitem(provider_readiness.PROVIDER_FACTORIES, "yfinance", fail_if_yfinance_is_constructed)

    exit_code = provider_readiness.main(
        ["--provider", "yfinance", "--market", "US", "--symbol", "AAPL"]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "WARN provider readiness" in output
    assert "requires explicit real-network opt-in" in output
    assert "--real-network" in output
    assert "Summary: OK=0 WARN=1 FAIL=0" in output


def test_yfinance_with_fake_downloader_returning_bars_returns_ok(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_downloader(ticker: str, start: date, end: date) -> pd.DataFrame:
        assert ticker == "AAPL"
        assert start <= end
        return pd.DataFrame(
            {
                "Open": [100.0],
                "High": [101.0],
                "Low": [99.0],
                "Close": [100.5],
                "Volume": [1000000],
            },
            index=pd.to_datetime([start]),
        )

    monkeypatch.setitem(
        provider_readiness.PROVIDER_FACTORIES,
        "yfinance",
        lambda: YFinanceProvider(downloader=fake_downloader),
    )

    exit_code = provider_readiness.main(
        [
            "--provider",
            "yfinance",
            "--market",
            "US",
            "--symbol",
            "AAPL",
            "--real-network",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "OK provider readiness" in output
    assert "yfinance returned 1 bars for AAPL" in output
    assert "Summary: OK=1 WARN=0 FAIL=0" in output


def test_akshare_depth_without_real_network_returns_warn(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_if_akshare_is_constructed() -> FakeSuccessfulProvider:
        pytest.fail("akshare provider should not be constructed without --real-network")

    monkeypatch.setitem(provider_readiness.PROVIDER_FACTORIES, "akshare", fail_if_akshare_is_constructed)

    exit_code = provider_readiness.main(
        ["--provider", "akshare", "--market", "CN", "--symbol", "600519", "--check-depth"]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "WARN provider readiness" in output
    assert "akshare market-depth readiness requires explicit real-network opt-in" in output
    assert "--check-depth" in output
    assert "--real-network" in output
    assert "Summary: OK=0 WARN=1 FAIL=0" in output


def test_akshare_depth_with_fake_provider_returns_ok(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setitem(provider_readiness.PROVIDER_FACTORIES, "akshare", FakeMarketDepthProvider)

    exit_code = provider_readiness.main(
        [
            "--provider",
            "akshare",
            "--market",
            "CN",
            "--symbol",
            "600519",
            "--check-depth",
            "--real-network",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "OK provider depth readiness" in output
    assert "akshare returned verified market-depth sections for 600519" in output
    assert "bids=1" in output
    assert "database_writes=none" in output
    assert "Summary: OK=1 WARN=0 FAIL=0" in output


def test_akshare_depth_readiness_prints_schema_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setitem(provider_readiness.PROVIDER_FACTORIES, "akshare", FakeDiagnosticMarketDepthProvider)

    exit_code = provider_readiness.main(
        [
            "--provider",
            "akshare",
            "--market",
            "CN",
            "--symbol",
            "600519",
            "--check-depth",
            "--real-network",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "FAIL provider depth readiness" in output
    assert "availability_reason=AkShare order-book payload could not be normalized." in output
    assert "availability_raw_shape=3x2" in output
    assert "availability_raw_columns=item,value" in output
    assert "availability_raw_fields_sample=bid_one,bid_one_volume" in output
    assert "database_writes=none" in output


def test_depth_check_for_provider_without_explicit_depth_returns_warn(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setitem(provider_readiness.PROVIDER_FACTORIES, "mock", FakeSuccessfulProvider)

    exit_code = provider_readiness.main(
        ["--provider", "mock", "--market", "US", "--symbol", "AAPL", "--check-depth"]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "WARN provider depth readiness" in output
    assert "mock does not expose explicit fetch_market_depth support" in output
    assert "Do not infer depth from daily bars or minute bars" in output
    assert "Summary: OK=0 WARN=1 FAIL=0" in output


def test_yfinance_intraday_without_real_network_returns_warn(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_if_yfinance_is_constructed() -> FakeSuccessfulProvider:
        pytest.fail("yfinance provider should not be constructed without --real-network")

    monkeypatch.setitem(provider_readiness.PROVIDER_FACTORIES, "yfinance", fail_if_yfinance_is_constructed)

    exit_code = provider_readiness.main(
        ["--provider", "yfinance", "--market", "US", "--symbol", "AAPL", "--check-intraday"]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "WARN provider readiness" in output
    assert "yfinance intraday readiness requires explicit real-network opt-in" in output
    assert "--check-intraday" in output
    assert "--real-network" in output
    assert "Summary: OK=0 WARN=1 FAIL=0" in output


def test_yfinance_intraday_with_fake_provider_returns_ok(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setitem(provider_readiness.PROVIDER_FACTORIES, "yfinance", FakeIntradayProvider)

    exit_code = provider_readiness.main(
        [
            "--provider",
            "yfinance",
            "--market",
            "US",
            "--symbol",
            "AAPL",
            "--check-intraday",
            "--trade-date",
            "2026-07-02",
            "--real-network",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "OK provider intraday readiness" in output
    assert "yfinance returned 1 verified intraday bars for AAPL" in output
    assert "trade_date=2026-07-02" in output
    assert "bars=1" in output
    assert "database_writes=none" in output
    assert "Summary: OK=1 WARN=0 FAIL=0" in output


def test_yfinance_intraday_known_us_holiday_returns_warn_without_provider_call(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setitem(provider_readiness.PROVIDER_FACTORIES, "yfinance", FakeFutureIntradayProvider)

    exit_code = provider_readiness.main(
        [
            "--provider",
            "yfinance",
            "--market",
            "US",
            "--symbol",
            "AAPL",
            "--check-intraday",
            "--trade-date",
            "2026-07-03",
            "--real-network",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "WARN provider intraday readiness" in output
    assert "skipped known market holiday" in output
    assert "reason=known_market_holiday" in output
    assert "database_writes=none" in output
    assert "Summary: OK=0 WARN=1 FAIL=0" in output


def test_yfinance_intraday_movable_us_holiday_returns_warn_without_provider_call(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setitem(provider_readiness.PROVIDER_FACTORIES, "yfinance", FakeFutureIntradayProvider)

    exit_code = provider_readiness.main(
        [
            "--provider",
            "yfinance",
            "--market",
            "US",
            "--symbol",
            "AAPL",
            "--check-intraday",
            "--trade-date",
            "2026-04-03",
            "--real-network",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "WARN provider intraday readiness" in output
    assert "skipped known market holiday" in output
    assert "reason=known_market_holiday" in output
    assert "database_writes=none" in output
    assert "Summary: OK=0 WARN=1 FAIL=0" in output


def test_intraday_check_for_provider_without_explicit_intraday_returns_warn(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setitem(provider_readiness.PROVIDER_FACTORIES, "mock", FakeSuccessfulProvider)

    exit_code = provider_readiness.main(
        ["--provider", "mock", "--market", "US", "--symbol", "AAPL", "--check-intraday"]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "WARN provider intraday readiness" in output
    assert "mock does not expose explicit fetch_intraday_bars support" in output
    assert "Do not infer intraday minutes from daily bars" in output
    assert "Summary: OK=0 WARN=1 FAIL=0" in output


def test_default_intraday_trade_date_rolls_weekend_back_to_friday() -> None:
    assert provider_readiness.resolve_default_intraday_trade_date(date(2026, 7, 4)) == date(2026, 7, 3)
    assert provider_readiness.resolve_default_intraday_trade_date(date(2026, 7, 5)) == date(2026, 7, 3)
    assert provider_readiness.resolve_default_intraday_trade_date(date(2026, 7, 6)) == date(2026, 7, 6)


def test_intraday_recent_weekday_dates_skip_weekends() -> None:
    assert provider_readiness.iter_recent_weekday_dates(lookback_days=5, today=date(2026, 7, 5)) == [
        date(2026, 7, 3),
        date(2026, 7, 2),
        date(2026, 7, 1),
        date(2026, 6, 30),
        date(2026, 6, 29),
    ]


def test_intraday_readiness_window_tries_recent_weekdays_until_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = FakeWindowIntradayProvider()

    monkeypatch.setattr(
        provider_readiness,
        "iter_recent_weekday_dates",
        lambda *, lookback_days, today=None: [date(2026, 7, 3), date(2026, 7, 2), date(2026, 7, 1)],
    )

    result = provider_readiness.check_intraday_readiness_window(
        provider=provider,
        provider_name="yfinance",
        market="US",
        symbol="AAPL",
        lookback_days=3,
    )

    assert result.status == provider_readiness.ReadinessStatus.OK
    assert provider.attempted_dates == [date(2026, 7, 2)]
    assert "trade_date=2026-07-02" in result.details
    assert "attempted_dates=2026-07-03,2026-07-02,2026-07-01" in result.details
    assert "database_writes=none" in result.details


def test_intraday_readiness_skips_future_trade_date_without_provider_call() -> None:
    future_trade_date = date.today() + provider_readiness.timedelta(days=1)

    result = provider_readiness.check_intraday_readiness(
        provider=FakeFutureIntradayProvider(),
        provider_name="yfinance",
        market="US",
        symbol="AAPL",
        trade_date=future_trade_date,
    )

    assert result.status == provider_readiness.ReadinessStatus.WARN
    assert "future trade date" in result.message
    assert f"trade_date={future_trade_date.isoformat()}" in result.details
    assert "reason=future_trade_date" in result.details
    assert "database_writes=none" in result.details
