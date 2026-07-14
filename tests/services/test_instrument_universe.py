from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from packages.domain.models import Exchange, Instrument, InstrumentUniverseSync, Market
from packages.providers.base import ProviderInstrument, ProviderInstrumentUniverseSnapshot
from packages.services.instrument_universe import (
    get_instrument_universe_status,
    sync_instrument_universe,
)
from packages.shared.database import Base


@pytest.fixture
def sqlite_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


class UniverseProvider:
    def __init__(self, snapshot: ProviderInstrumentUniverseSnapshot) -> None:
        self.snapshot = snapshot

    def fetch_instrument_universe(self, market: str) -> ProviderInstrumentUniverseSnapshot:
        assert market == "CN"
        return self.snapshot


class FailingUniverseProvider:
    def fetch_instrument_universe(self, market: str) -> ProviderInstrumentUniverseSnapshot:
        assert market == "CN"
        raise RuntimeError("credential=secret-value")


def _instrument(symbol: str, name: str, exchange: str) -> ProviderInstrument:
    return ProviderInstrument(
        symbol=symbol,
        name=name,
        market="CN",
        exchange=exchange,
        asset_type="stock",
        currency="CNY",
    )


def _snapshot(
    items: list[ProviderInstrument],
    *,
    complete: bool = True,
    status: str = "ok",
) -> ProviderInstrumentUniverseSnapshot:
    return ProviderInstrumentUniverseSnapshot(
        provider="akshare",
        source="akshare.fixture",
        as_of=datetime(2026, 7, 10, 1, 2, tzinfo=timezone.utc),
        status=status,
        items=items,
        is_complete=complete,
        availability={"status": status, "row_count": len(items)},
    )


def _seed_manual_instrument(session: Session, *, symbol: str = "900001") -> Instrument:
    market = Market(
        code="CN",
        name="China",
        timezone="Asia/Shanghai",
        currency="CNY",
        trading_calendar_code="XSHG",
    )
    exchange = Exchange(code="SSE", name="Shanghai Stock Exchange", market=market)
    instrument = Instrument(
        symbol=symbol,
        name="Manual Instrument",
        market=market,
        exchange=exchange,
        asset_type="stock",
        currency="CNY",
        is_active=True,
    )
    session.add(instrument)
    session.commit()
    return instrument


def test_sync_inserts_multi_exchange_a_share_universe(sqlite_session: Session):
    result = sync_instrument_universe(
        session=sqlite_session,
        provider=UniverseProvider(
            _snapshot(
                [
                    _instrument("600519", "Kweichow Moutai", "SSE"),
                    _instrument("000001", "Ping An Bank", "SZSE"),
                    _instrument("430047", "Novogene", "BSE"),
                ]
            )
        ),
    )

    assert result["counts"] == {
        "total_count": 3,
        "inserted_count": 3,
        "updated_count": 0,
        "unchanged_count": 0,
        "reactivated_count": 0,
        "deactivated_count": 0,
        "skipped_count": 0,
    }
    rows = sqlite_session.query(Instrument).order_by(Instrument.symbol).all()
    assert [(row.symbol, row.exchange.code, row.universe_provider) for row in rows] == [
        ("000001", "SZSE", "akshare"),
        ("430047", "BSE", "akshare"),
        ("600519", "SSE", "akshare"),
    ]


def test_sync_repairs_legacy_cn_stock_metadata_in_place(sqlite_session: Session):
    market = Market(
        code="CN",
        name="China",
        timezone="Asia/Shanghai",
        currency="CNY",
        trading_calendar_code="XSHG",
    )
    legacy = Instrument(
        symbol="600519",
        name="Legacy Stock",
        market=market,
        asset_type="stock",
        currency="CNY",
        is_active=True,
    )
    sqlite_session.add(legacy)
    sqlite_session.commit()
    legacy_id = legacy.id

    result = sync_instrument_universe(
        session=sqlite_session,
        provider=UniverseProvider(
            _snapshot([_instrument("600519", "Kweichow Moutai", "SSE")])
        ),
    )

    repaired = sqlite_session.query(Instrument).filter_by(symbol="600519").one()
    assert repaired.id == legacy_id
    assert repaired.name == "Kweichow Moutai"
    assert repaired.exchange.code == "SSE"
    assert repaired.universe_provider == "akshare"
    assert result["counts"]["inserted_count"] == 0
    assert result["counts"]["updated_count"] == 1


def test_complete_sync_updates_reactivates_and_deactivates_only_managed_rows(
    sqlite_session: Session,
):
    manual = _seed_manual_instrument(sqlite_session)
    first_items = [
        _instrument("600519", "Old Name", "SSE"),
        _instrument("000001", "Ping An Bank", "SZSE"),
        _instrument("430047", "Novogene", "BSE"),
    ]
    sync_instrument_universe(
        session=sqlite_session,
        provider=UniverseProvider(_snapshot(first_items)),
    )
    reactivated = (
        sqlite_session.query(Instrument).filter(Instrument.symbol == "000001").one()
    )
    reactivated.is_active = False
    sqlite_session.commit()

    result = sync_instrument_universe(
        session=sqlite_session,
        provider=UniverseProvider(
            _snapshot(
                [
                    _instrument("600519", "Kweichow Moutai", "SSE"),
                    _instrument("000001", "Ping An Bank", "SZSE"),
                ]
            )
        ),
    )

    assert result["counts"]["updated_count"] == 1
    assert result["counts"]["reactivated_count"] == 1
    assert result["counts"]["deactivated_count"] == 1
    sqlite_session.refresh(manual)
    assert manual.is_active is True
    assert manual.universe_provider is None
    removed = sqlite_session.query(Instrument).filter(Instrument.symbol == "430047").one()
    assert removed.is_active is False


def test_incomplete_sync_never_deactivates_missing_managed_rows(sqlite_session: Session):
    sync_instrument_universe(
        session=sqlite_session,
        provider=UniverseProvider(
            _snapshot(
                [
                    _instrument("600519", "Kweichow Moutai", "SSE"),
                    _instrument("000001", "Ping An Bank", "SZSE"),
                ]
            )
        ),
    )

    result = sync_instrument_universe(
        session=sqlite_session,
        provider=UniverseProvider(
            _snapshot(
                [_instrument("600519", "Kweichow Moutai", "SSE")],
                complete=False,
                status="degraded",
            )
        ),
    )

    assert result["counts"]["deactivated_count"] == 0
    missing = sqlite_session.query(Instrument).filter(Instrument.symbol == "000001").one()
    assert missing.is_active is True


def test_provider_failure_preserves_last_good_universe_and_sanitizes_diagnostics(
    sqlite_session: Session,
):
    sync_instrument_universe(
        session=sqlite_session,
        provider=UniverseProvider(
            _snapshot([_instrument("600519", "Kweichow Moutai", "SSE")])
        ),
    )

    result = sync_instrument_universe(
        session=sqlite_session,
        provider=FailingUniverseProvider(),
    )

    assert result["status"] == "failed"
    assert result["counts"]["deactivated_count"] == 0
    active = sqlite_session.query(Instrument).filter(Instrument.symbol == "600519").one()
    assert active.is_active is True
    assert "secret-value" not in str(result)
    assert sqlite_session.query(InstrumentUniverseSync).count() == 2


def test_universe_status_reports_current_coverage(sqlite_session: Session):
    _seed_manual_instrument(sqlite_session)
    sync_instrument_universe(
        session=sqlite_session,
        provider=UniverseProvider(
            _snapshot([_instrument("600519", "Kweichow Moutai", "SSE")])
        ),
    )

    status = get_instrument_universe_status(session=sqlite_session)

    assert status["status"] == "ok"
    assert status["active_instrument_count"] == 2
    assert status["managed_instrument_count"] == 1
    assert status["latest_sync"]["total_count"] == 1
    assert status["safety"]["failed_refresh_preserves_last_good_universe"] is True
