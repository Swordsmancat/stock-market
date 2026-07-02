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
