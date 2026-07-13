from datetime import date
from decimal import Decimal

import pytest

from packages.providers.base import ProviderBar
from packages.services import ingestion
from packages.services.daily_bar_sources import (
    CN_RESILIENT_POLICY,
    STRICT_POLICY,
    DailyBarFetchCoordinator,
    DailyBarSource,
)


def _bar(symbol: str = "600519", *, close: str = "100") -> ProviderBar:
    price = Decimal(close)
    return ProviderBar(
        symbol=symbol,
        timestamp=date(2026, 7, 9),
        open=price,
        high=price + 1,
        low=price - 1,
        close=price,
        volume=Decimal("1000"),
        amount=Decimal("100000"),
    )


def _source(
    source: str,
    priority: int,
    fetch,
    *,
    provider: str = "akshare",
    configured: bool = True,
) -> DailyBarSource:
    return DailyBarSource(
        provider=provider,
        source=source,
        adjustment="qfq",
        priority=priority,
        fetch=fetch,
        configured=configured,
        min_interval_seconds=0,
    )


def test_strict_policy_never_calls_fallback_source() -> None:
    calls: list[str] = []

    def primary(*_args):
        calls.append("primary")
        raise ConnectionError("primary unavailable")

    def fallback(*_args):
        calls.append("fallback")
        return [_bar()]

    coordinator = DailyBarFetchCoordinator(
        [
            _source("akshare.stock_zh_a_hist", 0, primary),
            _source("akshare.stock_zh_a_daily", 1, fallback),
        ]
    )

    with pytest.raises(ConnectionError, match="primary unavailable"):
        coordinator.fetch(
            "600519", "1d", date(2026, 7, 1), date(2026, 7, 10), policy=STRICT_POLICY
        )

    assert calls == ["primary"]


def test_resilient_policy_selects_sina_and_records_sanitized_attempts() -> None:
    coordinator = DailyBarFetchCoordinator(
        [
            _source(
                "akshare.stock_zh_a_hist",
                0,
                lambda *_args: (_ for _ in ()).throw(ConnectionError("private upstream body")),
            ),
            _source("akshare.stock_zh_a_daily", 1, lambda *_args: [_bar()]),
        ]
    )

    result = coordinator.fetch(
        "600519", "1d", date(2026, 7, 1), date(2026, 7, 10), policy=CN_RESILIENT_POLICY
    )

    assert result.status == "ok"
    assert result.source == "akshare.stock_zh_a_daily"
    assert result.source_priority == 1
    assert result.fallback_used is True
    assert result.attempts == [
        {
            "provider": "akshare",
            "source": "akshare.stock_zh_a_hist",
            "status": "failed",
            "exception_type": "ConnectionError",
        },
        {
            "provider": "akshare",
            "source": "akshare.stock_zh_a_daily",
            "status": "selected",
            "row_count": 1,
        },
    ]
    assert "private upstream body" not in str(result.attempts)


def test_unconfigured_tushare_is_visible_but_never_called() -> None:
    tushare_calls = 0

    def tushare(*_args):
        nonlocal tushare_calls
        tushare_calls += 1
        return [_bar()]

    coordinator = DailyBarFetchCoordinator(
        [
            _source("akshare.stock_zh_a_hist", 0, lambda *_args: []),
            _source("akshare.stock_zh_a_daily", 1, lambda *_args: []),
            _source(
                "tushare.pro.daily",
                2,
                tushare,
                provider="tushare",
                configured=False,
            ),
        ]
    )

    result = coordinator.fetch(
        "600519", "1d", date(2026, 7, 1), date(2026, 7, 10), policy=CN_RESILIENT_POLICY
    )

    assert result.status == "no_data"
    assert tushare_calls == 0
    assert result.attempts[-1] == {
        "provider": "tushare",
        "source": "tushare.pro.daily",
        "status": "skipped_unconfigured",
    }


def test_ingestion_coordinator_labels_tushare_pro_daily_as_raw(monkeypatch) -> None:
    class EmptySinaProvider:
        download_sina_daily_bars = staticmethod(lambda *_args: [])

        def __init__(self, **_kwargs):
            pass

        def fetch_bars(self, *_args):
            return []

    class Provider:
        def __init__(self, bars):
            self._bars = bars

        def fetch_bars(self, *_args):
            return self._bars

    providers = {
        "akshare": Provider([]),
        "tushare": Provider([_bar()]),
    }
    monkeypatch.setattr(ingestion, "AkShareProvider", EmptySinaProvider)
    monkeypatch.setattr(
        ingestion,
        "resolve_market_data_provider_name",
        lambda provider_name: provider_name,
    )
    monkeypatch.setattr(ingestion, "get_provider", providers.__getitem__)
    monkeypatch.setattr(
        ingestion,
        "get_platform_settings",
        lambda: {"tushare_token": "configured"},
    )

    result = ingestion.build_daily_bar_fetch_coordinator("akshare").fetch(
        "600519",
        "1d",
        date(2026, 7, 1),
        date(2026, 7, 10),
        policy=CN_RESILIENT_POLICY,
    )

    assert result.status == "ok"
    assert result.source == "tushare.pro.daily"
    assert result.adjustment == "raw"

    direct_result = ingestion.build_daily_bar_fetch_coordinator("tushare").fetch(
        "600519",
        "1d",
        date(2026, 7, 1),
        date(2026, 7, 10),
        policy=STRICT_POLICY,
    )

    assert direct_result.source == "tushare.pro.daily"
    assert direct_result.adjustment == "raw"


def test_repeated_source_failures_open_run_local_circuit() -> None:
    primary_calls = 0

    def primary(*_args):
        nonlocal primary_calls
        primary_calls += 1
        raise TimeoutError("timeout")

    coordinator = DailyBarFetchCoordinator(
        [
            _source("akshare.stock_zh_a_hist", 0, primary),
            _source("akshare.stock_zh_a_daily", 1, lambda symbol, *_args: [_bar(symbol)]),
        ],
        circuit_failure_threshold=3,
    )

    for symbol in ("600000", "600001", "600002"):
        coordinator.fetch(
            symbol, "1d", date(2026, 7, 1), date(2026, 7, 10), policy=CN_RESILIENT_POLICY
        )
    result = coordinator.fetch(
        "600003", "1d", date(2026, 7, 1), date(2026, 7, 10), policy=CN_RESILIENT_POLICY
    )

    assert primary_calls == 3
    assert result.source == "akshare.stock_zh_a_daily"
    assert result.attempts[0] == {
        "provider": "akshare",
        "source": "akshare.stock_zh_a_hist",
        "status": "skipped_circuit_open",
    }


def test_open_circuit_does_not_turn_provider_failure_into_no_data() -> None:
    coordinator = DailyBarFetchCoordinator(
        [
            _source(
                "akshare.stock_zh_a_hist",
                0,
                lambda *_args: (_ for _ in ()).throw(ConnectionError("unavailable")),
            )
        ],
        circuit_failure_threshold=1,
    )
    first = coordinator.fetch(
        "600519", "1d", date(2026, 7, 1), date(2026, 7, 10), policy=CN_RESILIENT_POLICY
    )
    second = coordinator.fetch(
        "600520", "1d", date(2026, 7, 1), date(2026, 7, 10), policy=CN_RESILIENT_POLICY
    )

    assert first.status == "failed"
    assert second.status == "failed"
    assert second.attempts[0]["status"] == "skipped_circuit_open"


def test_malformed_fallback_bars_are_rejected_before_selection() -> None:
    malformed = _bar()
    object.__setattr__(malformed, "high", Decimal("90"))
    coordinator = DailyBarFetchCoordinator(
        [
            _source("akshare.stock_zh_a_hist", 0, lambda *_args: []),
            _source("akshare.stock_zh_a_daily", 1, lambda *_args: [malformed]),
        ]
    )

    result = coordinator.fetch(
        "600519", "1d", date(2026, 7, 1), date(2026, 7, 10), policy=CN_RESILIENT_POLICY
    )

    assert result.status == "failed"
    assert result.bars == []
    assert result.attempts[-1]["status"] == "invalid"
    assert result.attempts[-1]["code"] == "INVALID_OHLC"
