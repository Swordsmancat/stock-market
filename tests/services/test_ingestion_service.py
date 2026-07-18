from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from packages.domain.models import DailyBar, Instrument
from packages.providers.base import ProviderBar, ProviderInstrument
from packages.services import market_data as market_data_service
from packages.services import ingestion as ingestion_service
from packages.shared.database import Base
from packages.services.ingestion import ingest_market_snapshot, ingest_mock_market_snapshot
from packages.services.ingestion import ingest_symbol_daily_bars_batch
from packages.services.ingestion import ingest_symbol_daily_bars
from packages.services.daily_bar_sources import (
    CN_RESILIENT_POLICY,
    DailyBarFetchCoordinator,
    DailyBarSource,
)


@pytest.fixture
def sqlite_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = test_session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


class CountingSnapshotProvider:
    def __init__(self) -> None:
        self.instrument_fetch_count = 0
        self.bar_fetch_counts_by_symbol: dict[str, int] = {}
        self.instruments = [
            ProviderInstrument("AAPL", "Apple Inc.", "US", "NASDAQ", "stock", "USD"),
            ProviderInstrument("MSFT", "Microsoft Corp.", "US", "NASDAQ", "stock", "USD"),
        ]

    def fetch_instruments(
        self,
        market: str,
        exchange: str | None = None,
    ) -> list[ProviderInstrument]:
        self.instrument_fetch_count += 1
        if exchange is None:
            return self.instruments
        return [instrument for instrument in self.instruments if instrument.exchange == exchange]

    def fetch_bars(
        self,
        symbol: str,
        timeframe: str,
        start: date,
        end: date,
    ) -> list[ProviderBar]:
        self.bar_fetch_counts_by_symbol[symbol] = (
            self.bar_fetch_counts_by_symbol.get(symbol, 0) + 1
        )
        symbol_offset = Decimal("0.00") if symbol == "AAPL" else Decimal("10.00")
        return [
            ProviderBar(
                symbol=symbol,
                timestamp=start,
                open=Decimal("100.00") + symbol_offset,
                high=Decimal("102.00") + symbol_offset,
                low=Decimal("99.00") + symbol_offset,
                close=Decimal("101.00") + symbol_offset,
                volume=Decimal("1000"),
                amount=Decimal("101000"),
            )
        ]


class TargetedBarsProvider:
    def __init__(self, bars: list[ProviderBar]) -> None:
        self.bars = bars
        self.fetch_bars_count = 0
        self.fetch_instruments_count = 0

    def fetch_instruments(
        self,
        market: str,
        exchange: str | None = None,
    ) -> list[ProviderInstrument]:
        self.fetch_instruments_count += 1
        raise AssertionError("single-symbol ingestion must not fetch provider instruments")

    def fetch_bars(
        self,
        symbol: str,
        timeframe: str,
        start: date,
        end: date,
    ) -> list[ProviderBar]:
        self.fetch_bars_count += 1
        return self.bars


class BatchBarsProvider:
    def __init__(
        self,
        bars_by_symbol: dict[str, list[ProviderBar]],
        failed_symbols: set[str] | None = None,
    ) -> None:
        self.bars_by_symbol = bars_by_symbol
        self.failed_symbols = failed_symbols or set()
        self.fetch_bars_symbols: list[str] = []
        self.fetch_instruments_count = 0

    def fetch_instruments(
        self,
        market: str,
        exchange: str | None = None,
    ) -> list[ProviderInstrument]:
        self.fetch_instruments_count += 1
        raise AssertionError("batch symbol ingestion must not fetch provider instruments")

    def fetch_bars(
        self,
        symbol: str,
        timeframe: str,
        start: date,
        end: date,
    ) -> list[ProviderBar]:
        self.fetch_bars_symbols.append(symbol)
        if symbol in self.failed_symbols:
            msg = f"provider error for {symbol}"
            raise RuntimeError(msg)
        return self.bars_by_symbol.get(symbol, [])


def _provider_bar(symbol: str, timestamp: date, close_price: Decimal) -> ProviderBar:
    return ProviderBar(
        symbol=symbol,
        timestamp=timestamp,
        open=close_price - Decimal("1.00"),
        high=close_price + Decimal("1.00"),
        low=close_price - Decimal("2.00"),
        close=close_price,
        volume=Decimal("1000"),
        amount=close_price * Decimal("1000"),
    )


def _serialized_bar(
    timestamp: object,
    close_price: float,
    volume: float = 1000.0,
) -> dict[str, object]:
    return {
        "timestamp": timestamp,
        "open": close_price - 1.0,
        "high": close_price + 1.0,
        "low": close_price - 2.0,
        "close": close_price,
        "volume": volume,
        "amount": close_price * volume,
    }


def _serialized_snapshot(bars: list[dict[str, object]]) -> dict[str, object]:
    return {
        "market": "US",
        "provider": "mock",
        "timeframe": "1d",
        "start": "2026-01-05",
        "end": "2026-01-06",
        "instrument_count": 1,
        "instruments": [
            {
                "symbol": "SYNC",
                "name": "Synchronized Corp.",
                "exchange": "NASDAQ",
                "asset_type": "stock",
                "currency": "USD",
                "bars": bars,
            }
        ],
    }


def test_ingest_market_snapshot_returns_serialized_snapshot():
    snapshot = ingest_market_snapshot(
        "US",
        date(2026, 1, 1),
        date(2026, 1, 2),
        provider_name="mock",
    )

    assert snapshot["market"] == "US"
    assert snapshot["provider"] == "mock"
    assert snapshot["instrument_count"] == 1
    assert snapshot["bar_count"] == 2
    assert snapshot["instruments"][0]["symbol"] == "AAPL"
    assert snapshot["instruments"][0]["bars"][0]["close"] == 101.0


def test_ingest_market_snapshot_includes_quality_diagnostics():
    snapshot = ingest_market_snapshot(
        "US",
        date(2026, 1, 1),
        date(2026, 1, 2),
        provider_name="mock",
    )

    quality_diagnostics = snapshot["quality_diagnostics"]
    instrument_diagnostics = quality_diagnostics["instruments"][0]

    assert quality_diagnostics["status"] == "OK"
    assert quality_diagnostics["instrument_count"] == 1
    assert instrument_diagnostics["symbol"] == "AAPL"
    assert instrument_diagnostics["status"] == "OK"
    assert instrument_diagnostics["checked_bars"] == 2
    assert instrument_diagnostics["missing_dates"] == []
    assert instrument_diagnostics["invalid_ohlc"] == []
    assert instrument_diagnostics["volume_warnings"] == []


def test_ingest_market_snapshot_reports_failed_quality_when_no_instruments(monkeypatch):
    def get_empty_market_snapshot(market, start, end, provider_name="mock"):
        return {
            "market": market,
            "provider": provider_name,
            "timeframe": "1d",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "instrument_count": 0,
            "instruments": [],
        }

    monkeypatch.setattr(ingestion_service, "get_market_snapshot", get_empty_market_snapshot)

    snapshot = ingestion_service.ingest_market_snapshot(
        "US",
        date(2026, 1, 1),
        date(2026, 1, 2),
        provider_name="mock",
    )

    quality_diagnostics = snapshot["quality_diagnostics"]

    assert quality_diagnostics["status"] == "FAIL"
    assert quality_diagnostics["instrument_count"] == 0
    assert quality_diagnostics["instruments"] == []
    assert quality_diagnostics["quality_error"] == "No instruments available for quality diagnostics."
    assert snapshot["bar_count"] == 0


def test_ingest_mock_market_snapshot_remains_compatible():
    snapshot = ingest_mock_market_snapshot(
        "US",
        date(2026, 1, 1),
        date(2026, 1, 2),
        provider_name="mock",
    )

    assert snapshot["market"] == "US"
    assert snapshot["provider"] == "mock"
    assert snapshot["status"] == "ingested"


def test_session_backed_ingestion_fetches_provider_once_per_snapshot(
    monkeypatch,
    sqlite_session: Session,
):
    provider = CountingSnapshotProvider()
    monkeypatch.setattr(market_data_service, "get_provider", lambda provider_name: provider)

    snapshot = ingest_market_snapshot(
        "US",
        date(2026, 1, 5),
        date(2026, 1, 5),
        session=sqlite_session,
        provider_name="mock",
    )

    assert provider.instrument_fetch_count == 1
    assert provider.bar_fetch_counts_by_symbol == {"AAPL": 1, "MSFT": 1}
    assert snapshot["bar_count"] == 2
    assert sqlite_session.query(DailyBar).count() == 2


def test_session_and_no_session_bar_count_come_from_serialized_snapshot(
    monkeypatch,
    sqlite_session: Session,
):
    snapshot_payload = _serialized_snapshot(
        [
            _serialized_bar("2026-01-05", 101.0),
            _serialized_bar("2026-01-06", 102.0),
        ]
    )
    monkeypatch.setattr(
        ingestion_service,
        "get_market_snapshot",
        lambda market, start, end, provider_name="mock": snapshot_payload,
    )

    no_session_snapshot = ingestion_service.ingest_market_snapshot(
        "US",
        date(2026, 1, 5),
        date(2026, 1, 6),
        provider_name="mock",
    )
    session_snapshot = ingestion_service.ingest_market_snapshot(
        "US",
        date(2026, 1, 5),
        date(2026, 1, 6),
        session=sqlite_session,
        provider_name="mock",
    )

    assert no_session_snapshot["bar_count"] == 2
    assert session_snapshot["bar_count"] == 2
    assert len(session_snapshot["instruments"][0]["bars"]) == 2
    assert session_snapshot["quality_diagnostics"]["instruments"][0]["checked_bars"] == 2


def test_session_backed_ingestion_writes_database_from_returned_snapshot(
    monkeypatch,
    sqlite_session: Session,
):
    snapshot_payload = _serialized_snapshot(
        [
            _serialized_bar("2026-01-05T00:00:00Z", 111.25),
            _serialized_bar("2026-01-06", 112.5),
        ]
    )
    monkeypatch.setattr(
        ingestion_service,
        "get_market_snapshot",
        lambda market, start, end, provider_name="mock": snapshot_payload,
    )

    returned_snapshot = ingestion_service.ingest_market_snapshot(
        "US",
        date(2026, 1, 5),
        date(2026, 1, 6),
        session=sqlite_session,
        provider_name="mock",
    )

    instrument = sqlite_session.query(Instrument).filter(Instrument.symbol == "SYNC").one()
    database_bars = (
        sqlite_session.query(DailyBar)
        .filter(DailyBar.instrument_id == instrument.id)
        .order_by(DailyBar.trade_date)
        .all()
    )
    returned_bars = returned_snapshot["instruments"][0]["bars"]
    quality_diagnostics = returned_snapshot["quality_diagnostics"]["instruments"][0]

    assert [database_bar.trade_date.isoformat() for database_bar in database_bars] == [
        "2026-01-05",
        "2026-01-06",
    ]
    assert [database_bar.close for database_bar in database_bars] == [
        Decimal("111.25"),
        Decimal("112.5"),
    ]
    assert [returned_bar["close"] for returned_bar in returned_bars] == [111.25, 112.5]
    assert quality_diagnostics["checked_bars"] == len(returned_bars)


def test_symbol_daily_bar_ingestion_fetches_bars_without_instrument_universe(
    monkeypatch,
    sqlite_session: Session,
):
    provider = TargetedBarsProvider(
        [_provider_bar("AAPL", date(2026, 1, 5), Decimal("123.45"))]
    )
    monkeypatch.setattr(ingestion_service, "get_provider", lambda provider_name: provider)

    first_result = ingest_symbol_daily_bars(
        "aapl",
        "us",
        date(2026, 1, 5),
        date(2026, 1, 5),
        session=sqlite_session,
        provider_name="mock",
    )
    second_result = ingest_symbol_daily_bars(
        "AAPL",
        "US",
        date(2026, 1, 5),
        date(2026, 1, 5),
        session=sqlite_session,
        provider_name="mock",
    )

    assert provider.fetch_bars_count == 2
    assert provider.fetch_instruments_count == 0
    assert first_result["status"] == "ingested"
    assert first_result["bar_count"] == 1
    assert second_result["bar_count"] == 1
    assert sqlite_session.query(Instrument).filter(Instrument.symbol == "AAPL").count() == 1
    assert sqlite_session.query(DailyBar).count() == 1
    database_bar = sqlite_session.query(DailyBar).one()
    assert database_bar.close == Decimal("123.45")


def test_symbol_daily_bar_ingestion_can_store_etf_asset_type(
    monkeypatch,
    sqlite_session: Session,
):
    provider = TargetedBarsProvider([_provider_bar("SPY", date(2026, 1, 5), Decimal("510.25"))])
    monkeypatch.setattr(ingestion_service, "get_provider", lambda provider_name: provider)

    result = ingest_symbol_daily_bars(
        "spy",
        "us",
        date(2026, 1, 5),
        date(2026, 1, 5),
        session=sqlite_session,
        provider_name="mock",
        asset_type="ETF",
    )

    instrument = sqlite_session.query(Instrument).filter(Instrument.symbol == "SPY").one()
    assert result["status"] == "ingested"
    assert result["instruments"][0]["asset_type"] == "etf"
    assert instrument.asset_type == "etf"


@pytest.mark.parametrize(
    ("asset_type", "symbol", "expected_source"),
    [
        ("etf", "510300", "akshare.fund_etf_hist_em"),
        ("index", "000001", "akshare.stock_zh_index_daily"),
    ],
)
def test_cn_fund_index_daily_bar_ingestion_uses_asset_specific_akshare_source(
    monkeypatch,
    asset_type,
    symbol,
    expected_source,
):
    bar = ProviderBar(
        symbol=symbol,
        timestamp=date(2026, 7, 17),
        open=Decimal("4"),
        high=Decimal("4.1"),
        low=Decimal("3.9"),
        close=Decimal("4.05"),
        volume=Decimal("1000"),
        amount=Decimal("4050"),
    )
    monkeypatch.setattr(
        "packages.providers.akshare_provider.AkShareProvider.fetch_etf_bars",
        lambda self, _symbol, _timeframe, _start, _end: [bar],
    )
    monkeypatch.setattr(
        "packages.providers.akshare_provider.AkShareProvider.fetch_index_bars",
        lambda self, _symbol, _start, _end: [bar],
    )

    result = ingest_symbol_daily_bars(
        symbol=symbol,
        market="CN",
        start=date(2026, 7, 1),
        end=date(2026, 7, 18),
        provider_name="akshare",
        asset_type=asset_type,
    )

    assert result["status"] == "ingested"
    assert result["source"] == expected_source
    assert result["instruments"][0]["asset_type"] == asset_type


def test_cn_etf_daily_bar_ingestion_uses_sina_fallback_with_raw_provenance(
    monkeypatch,
):
    bar = ProviderBar(
        symbol="510300",
        timestamp=date(2026, 7, 17),
        open=Decimal("4"),
        high=Decimal("4.1"),
        low=Decimal("3.9"),
        close=Decimal("4.05"),
        volume=Decimal("1000"),
        amount=Decimal("4050"),
    )

    def fail_eastmoney(*_args, **_kwargs):
        raise ConnectionError("primary provider unavailable")

    monkeypatch.setattr(
        "packages.providers.akshare_provider.AkShareProvider.fetch_etf_bars",
        fail_eastmoney,
    )
    monkeypatch.setattr(
        "packages.providers.akshare_provider.AkShareProvider.fetch_sina_etf_bars",
        lambda self, _symbol, _timeframe, _start, _end: [bar],
    )

    result = ingest_symbol_daily_bars(
        symbol="510300",
        market="CN",
        start=date(2026, 7, 1),
        end=date(2026, 7, 18),
        provider_name="akshare",
        asset_type="etf",
        daily_bar_policy=CN_RESILIENT_POLICY,
    )

    assert result["status"] == "ingested"
    assert result["source"] == "akshare.fund_etf_hist_sina"
    assert result["adjustment"] == "raw"
    assert result["fallback_used"] is True
    assert [attempt["source"] for attempt in result["source_attempts"]] == [
        "akshare.fund_etf_hist_em",
        "akshare.fund_etf_hist_sina",
    ]


def test_symbol_daily_bar_ingestion_rejects_unknown_asset_type(
    monkeypatch,
    sqlite_session: Session,
):
    provider = TargetedBarsProvider([_provider_bar("SPY", date(2026, 1, 5), Decimal("510.25"))])
    monkeypatch.setattr(ingestion_service, "get_provider", lambda provider_name: provider)

    with pytest.raises(ValueError, match="Unsupported asset_type"):
        ingest_symbol_daily_bars(
            "spy",
            "us",
            date(2026, 1, 5),
            date(2026, 1, 5),
            session=sqlite_session,
            provider_name="mock",
            asset_type="fund",
        )

    assert provider.fetch_bars_count == 0
    assert sqlite_session.query(Instrument).count() == 0


def test_symbol_daily_bar_ingestion_returns_no_data_without_daily_rows(
    monkeypatch,
    sqlite_session: Session,
):
    provider = TargetedBarsProvider([])
    monkeypatch.setattr(ingestion_service, "get_provider", lambda provider_name: provider)

    result = ingest_symbol_daily_bars(
        "missing",
        "us",
        date(2026, 1, 5),
        date(2026, 1, 5),
        session=sqlite_session,
        provider_name="mock",
    )

    assert result["status"] == "no_data"
    assert result["symbol"] == "MISSING"
    assert result["bar_count"] == 0
    assert result["no_data_reason"] == "Provider returned no daily bars for the requested symbol/date range."
    assert sqlite_session.query(DailyBar).count() == 0


def test_resilient_daily_bar_ingestion_persists_selected_source_provenance(
    sqlite_session: Session,
):
    coordinator = DailyBarFetchCoordinator(
        [
            DailyBarSource(
                provider="akshare",
                source="akshare.stock_zh_a_hist",
                adjustment="qfq",
                priority=0,
                fetch=lambda *_args: (_ for _ in ()).throw(ConnectionError("unavailable")),
            ),
            DailyBarSource(
                provider="akshare",
                source="akshare.stock_zh_a_daily",
                adjustment="qfq",
                priority=1,
                fetch=lambda *_args: [
                    _provider_bar("600519", date(2026, 1, 5), Decimal("123.45"))
                ],
            ),
        ]
    )

    result = ingest_symbol_daily_bars(
        "600519",
        "CN",
        date(2026, 1, 5),
        date(2026, 1, 5),
        session=sqlite_session,
        provider_name="akshare",
        daily_bar_policy=CN_RESILIENT_POLICY,
        fetch_coordinator=coordinator,
    )

    database_bar = sqlite_session.query(DailyBar).one()
    assert result["effective_provider"] == "akshare"
    assert result["source"] == "akshare.stock_zh_a_daily"
    assert result["fallback_used"] is True
    assert database_bar.provider == "akshare"
    assert database_bar.source == "akshare.stock_zh_a_daily"
    assert database_bar.adjustment == "qfq"
    assert database_bar.source_priority == 1


def test_lower_priority_daily_bar_source_cannot_overwrite_primary(
    sqlite_session: Session,
):
    primary = DailyBarFetchCoordinator(
        [
            DailyBarSource(
                provider="akshare",
                source="akshare.stock_zh_a_hist",
                adjustment="qfq",
                priority=0,
                fetch=lambda *_args: [
                    _provider_bar("600519", date(2026, 1, 5), Decimal("100"))
                ],
            )
        ]
    )
    fallback = DailyBarFetchCoordinator(
        [
            DailyBarSource(
                provider="akshare",
                source="akshare.stock_zh_a_daily",
                adjustment="qfq",
                priority=1,
                fetch=lambda *_args: [
                    _provider_bar("600519", date(2026, 1, 5), Decimal("200"))
                ],
            )
        ]
    )

    for coordinator in (primary, fallback):
        ingest_symbol_daily_bars(
            "600519",
            "CN",
            date(2026, 1, 5),
            date(2026, 1, 5),
            session=sqlite_session,
            provider_name="akshare",
            fetch_coordinator=coordinator,
        )

    database_bar = sqlite_session.query(DailyBar).one()
    assert database_bar.close == Decimal("100")
    assert database_bar.source == "akshare.stock_zh_a_hist"
    assert database_bar.source_priority == 0


def test_recovered_primary_source_replaces_fallback_daily_bar(
    sqlite_session: Session,
):
    def coordinator(source: str, priority: int, close: str) -> DailyBarFetchCoordinator:
        return DailyBarFetchCoordinator(
            [
                DailyBarSource(
                    provider="akshare",
                    source=source,
                    adjustment="qfq",
                    priority=priority,
                    fetch=lambda *_args: [
                        _provider_bar("600519", date(2026, 1, 5), Decimal(close))
                    ],
                )
            ]
        )

    for fetch_coordinator in (
        coordinator("akshare.stock_zh_a_daily", 1, "200"),
        coordinator("akshare.stock_zh_a_hist", 0, "100"),
    ):
        ingest_symbol_daily_bars(
            "600519",
            "CN",
            date(2026, 1, 5),
            date(2026, 1, 5),
            session=sqlite_session,
            provider_name="akshare",
            fetch_coordinator=fetch_coordinator,
        )

    database_bar = sqlite_session.query(DailyBar).one()
    assert database_bar.close == Decimal("100")
    assert database_bar.source == "akshare.stock_zh_a_hist"
    assert database_bar.source_priority == 0


def test_symbol_daily_bar_batch_ingestion_dedupes_and_preserves_partial_results(
    monkeypatch,
    sqlite_session: Session,
):
    provider = BatchBarsProvider(
        bars_by_symbol={"AAPL": [_provider_bar("AAPL", date(2026, 1, 5), Decimal("123.45"))]},
        failed_symbols={"MSFT"},
    )
    monkeypatch.setattr(ingestion_service, "get_provider", lambda provider_name: provider)

    result = ingest_symbol_daily_bars_batch(
        "aapl, AAPL, msft, missing",
        "us",
        date(2026, 1, 5),
        date(2026, 1, 5),
        session=sqlite_session,
        provider_name="mock",
        asset_type="ETF",
    )

    assert provider.fetch_bars_symbols == ["AAPL", "MSFT", "MISSING"]
    assert provider.fetch_instruments_count == 0
    assert result["status"] == "partial"
    assert result["symbols"] == ["AAPL", "MSFT", "MISSING"]
    assert result["symbol_count"] == 3
    assert result["succeeded_count"] == 1
    assert result["failed_count"] == 1
    assert result["no_data_count"] == 1
    assert result["total_bar_count"] == 1
    assert [item["status"] for item in result["items"]] == ["ingested", "failed", "no_data"]
    assert result["diagnostics"] == [
        {
            "symbol": "MSFT",
            "code": "SYMBOL_DAILY_BAR_INGESTION_FAILED",
            "message": "provider error for MSFT",
        }
    ]

    aapl = sqlite_session.query(Instrument).filter(Instrument.symbol == "AAPL").one()
    assert aapl.asset_type == "etf"
    assert sqlite_session.query(DailyBar).count() == 1


def test_symbol_daily_bar_batch_ingestion_requires_symbols(
    monkeypatch,
    sqlite_session: Session,
):
    provider = BatchBarsProvider({})
    monkeypatch.setattr(ingestion_service, "get_provider", lambda provider_name: provider)

    with pytest.raises(ValueError, match="At least one symbol"):
        ingest_symbol_daily_bars_batch(
            " , ,, ",
            "us",
            date(2026, 1, 5),
            date(2026, 1, 5),
            session=sqlite_session,
            provider_name="mock",
        )

    assert provider.fetch_bars_symbols == []
    assert sqlite_session.query(Instrument).count() == 0


def test_duplicate_serialized_bars_preserve_processed_count_and_last_write_wins(
    monkeypatch,
    sqlite_session: Session,
):
    snapshot_payload = _serialized_snapshot(
        [
            _serialized_bar("2026-01-05", 101.0),
            _serialized_bar("2026-01-05", 202.0),
        ]
    )
    monkeypatch.setattr(
        ingestion_service,
        "get_market_snapshot",
        lambda market, start, end, provider_name="mock": snapshot_payload,
    )

    returned_snapshot = ingestion_service.ingest_market_snapshot(
        "US",
        date(2026, 1, 5),
        date(2026, 1, 5),
        session=sqlite_session,
        provider_name="mock",
    )

    database_bar = sqlite_session.query(DailyBar).one()

    assert returned_snapshot["bar_count"] == 2
    assert sqlite_session.query(DailyBar).count() == 1
    assert database_bar.close == Decimal("202.0")


def test_session_backed_empty_instruments_do_not_fallback_to_provider(
    monkeypatch,
    sqlite_session: Session,
):
    def get_empty_market_snapshot(market, start, end, provider_name="mock"):
        return {
            "market": market,
            "provider": provider_name,
            "timeframe": "1d",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "instrument_count": 0,
            "instruments": [],
        }

    def fail_if_provider_fallback_is_used(provider_name):
        raise AssertionError("empty serialized snapshots must not trigger a provider fallback")

    monkeypatch.setattr(ingestion_service, "get_market_snapshot", get_empty_market_snapshot)
    monkeypatch.setattr(
        ingestion_service,
        "get_provider",
        fail_if_provider_fallback_is_used,
        raising=False,
    )

    snapshot = ingestion_service.ingest_market_snapshot(
        "US",
        date(2026, 1, 1),
        date(2026, 1, 2),
        session=sqlite_session,
        provider_name="mock",
    )

    assert snapshot["bar_count"] == 0
    assert snapshot["quality_diagnostics"]["status"] == "FAIL"
    assert sqlite_session.query(Instrument).count() == 0
    assert sqlite_session.query(DailyBar).count() == 0
