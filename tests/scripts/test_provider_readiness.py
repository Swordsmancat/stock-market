from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from packages.providers.base import ProviderBar, ProviderInstrument
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
