from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from packages.domain.models import DailyBar, Exchange, Instrument, Market
from packages.providers.base import ProviderInstrument, ProviderInstrumentUniverseSnapshot
from packages.services import cn_fund_index_pipeline as pipeline_service
from packages.services.cn_fund_index_pipeline import (
    CnFundIndexPipelineError,
    sync_cn_fund_index_data,
)
from packages.shared.database import Base


class FundIndexProvider:
    def fetch_instrument_universe(self, market: str, asset_type: str):
        assert market == "CN"
        symbol, name, exchange = {
            "etf": ("510300", "CSI 300 ETF", "SSE"),
            "index": ("000001", "SSE Composite", "SSE"),
        }[asset_type]
        return ProviderInstrumentUniverseSnapshot(
            provider="akshare",
            source=f"akshare.fixture.{asset_type}",
            as_of=datetime(2026, 7, 19, tzinfo=timezone.utc),
            status="ok",
            items=[
                ProviderInstrument(
                    symbol=symbol,
                    name=name,
                    market="CN",
                    exchange=exchange,
                    asset_type=asset_type,
                    currency="CNY",
                )
            ],
            is_complete=True,
            availability={"status": "ok", "row_count": 1},
        )


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    value = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    try:
        yield value
    finally:
        value.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _seed_daily_bar(
    session,
    *,
    asset_type: str,
    symbol: str,
    trade_date: date,
    source: str,
    adjustment: str,
) -> None:
    market = session.query(Market).filter(Market.code == "CN").one_or_none()
    if market is None:
        market = Market(
            code="CN",
            name="China",
            timezone="Asia/Shanghai",
            currency="CNY",
        )
        session.add(market)
        session.flush()
    exchange = session.query(Exchange).filter(Exchange.code == "SSE").one_or_none()
    if exchange is None:
        exchange = Exchange(market=market, code="SSE", name="Shanghai")
        session.add(exchange)
        session.flush()
    instrument = Instrument(
        symbol=symbol,
        name=symbol,
        market=market,
        exchange=exchange,
        asset_type=asset_type,
        currency="CNY",
        is_active=True,
    )
    session.add(instrument)
    session.flush()
    session.add(
        DailyBar(
            instrument_id=instrument.id,
            trade_date=trade_date,
            open=Decimal("1"),
            high=Decimal("1"),
            low=Decimal("1"),
            close=Decimal("1"),
            volume=Decimal("1"),
            provider="akshare",
            source=source,
            adjustment=adjustment,
            source_priority=1 if source.endswith("sina") else 0,
        )
    )
    session.commit()


def test_pipeline_syncs_catalogs_then_ingests_asset_specific_bars_sequentially(session):
    calls: list[tuple[str, str, str]] = []
    progress: list[tuple[str, int, int]] = []

    def ingest(**kwargs):
        calls.append(
            (
                kwargs["asset_type"],
                kwargs["symbol"],
                kwargs["daily_bar_policy"],
            )
        )
        return {
            "status": "ingested",
            "bar_count": 2,
            "source": f"akshare.{kwargs['asset_type']}.fixture",
        }

    result = sync_cn_fund_index_data(
        session=session,
        start=date(2026, 7, 1),
        end=date(2026, 7, 19),
        max_symbols_per_type=10,
        request_delay_seconds=0,
        provider=FundIndexProvider(),
        bar_ingestor=ingest,
        progress_callback=lambda phase, current, total, _message: progress.append(
            (phase, current, total)
        ),
    )

    assert calls == [
        ("etf", "510300", "cn_resilient"),
        ("index", "000001", "cn_resilient"),
    ]
    assert result["status"] == "ok"
    assert result["assets"]["etf"]["bar_count"] == 2
    assert result["assets"]["index"]["source_counts"] == {
        "akshare.index.fixture": 1
    }
    assert result["assets"]["etf"]["window_counts"] == {
        "full_seed": 1,
        "full_refresh": 0,
        "incremental": 0,
        "current": 0,
    }
    assert result["assets"]["etf"]["overlap_days"] == 7
    assert progress[-1] == ("daily_bars", 2, 2)


def test_pipeline_uses_overlap_and_locks_existing_source(monkeypatch, session):
    _seed_daily_bar(
        session,
        asset_type="etf",
        symbol="510300",
        trade_date=date(2026, 7, 17),
        source="akshare.fund_etf_hist_sina",
        adjustment="raw",
    )
    _seed_daily_bar(
        session,
        asset_type="index",
        symbol="000001",
        trade_date=date(2026, 7, 17),
        source="akshare.stock_zh_index_daily",
        adjustment="raw",
    )
    coordinator_calls: list[tuple[str, str | None]] = []
    ingest_calls: list[tuple[str, date]] = []

    def build_coordinator(_provider, asset_type, *, exact_source=None):
        coordinator_calls.append((asset_type, exact_source))
        return object()

    def ingest(**kwargs):
        ingest_calls.append((kwargs["asset_type"], kwargs["start"]))
        return {
            "status": "ingested",
            "bar_count": 2,
            "source": coordinator_calls[-1][1],
        }

    monkeypatch.setattr(
        pipeline_service,
        "build_daily_bar_fetch_coordinator",
        build_coordinator,
    )
    result = sync_cn_fund_index_data(
        session=session,
        start=date(2026, 3, 21),
        end=date(2026, 7, 19),
        max_symbols_per_type=10,
        request_delay_seconds=0,
        provider=FundIndexProvider(),
        bar_ingestor=ingest,
    )

    assert ingest_calls == [
        ("etf", date(2026, 7, 10)),
        ("index", date(2026, 7, 10)),
    ]
    assert coordinator_calls == [
        ("etf", "akshare.fund_etf_hist_sina"),
        ("index", "akshare.stock_zh_index_daily"),
    ]
    assert result["assets"]["etf"]["window_counts"]["incremental"] == 1
    assert result["assets"]["index"]["window_counts"]["incremental"] == 1


def test_pipeline_manual_mode_preserves_full_requested_window(monkeypatch, session):
    _seed_daily_bar(
        session,
        asset_type="etf",
        symbol="510300",
        trade_date=date(2026, 7, 17),
        source="akshare.fund_etf_hist_sina",
        adjustment="raw",
    )
    _seed_daily_bar(
        session,
        asset_type="index",
        symbol="000001",
        trade_date=date(2026, 7, 17),
        source="akshare.stock_zh_index_daily",
        adjustment="raw",
    )
    starts: list[date] = []
    monkeypatch.setattr(
        pipeline_service,
        "build_daily_bar_fetch_coordinator",
        lambda *_args, **_kwargs: object(),
    )

    def ingest(**kwargs):
        starts.append(kwargs["start"])
        return {"status": "ingested", "bar_count": 2, "source": "fixture"}

    result = sync_cn_fund_index_data(
        session=session,
        start=date(2026, 3, 21),
        end=date(2026, 7, 19),
        max_symbols_per_type=10,
        request_delay_seconds=0,
        incremental=False,
        provider=FundIndexProvider(),
        bar_ingestor=ingest,
    )

    assert starts == [date(2026, 3, 21), date(2026, 3, 21)]
    assert result["refresh_mode"] == "full"
    assert result["assets"]["etf"]["window_counts"]["full_refresh"] == 1
    assert result["assets"]["index"]["window_counts"]["full_refresh"] == 1


def test_pipeline_skips_provider_calls_when_every_instrument_is_current(session):
    for asset_type, symbol, source in (
        ("etf", "510300", "akshare.fund_etf_hist_sina"),
        ("index", "000001", "akshare.stock_zh_index_daily"),
    ):
        _seed_daily_bar(
            session,
            asset_type=asset_type,
            symbol=symbol,
            trade_date=date(2026, 7, 19),
            source=source,
            adjustment="raw",
        )

    result = sync_cn_fund_index_data(
        session=session,
        start=date(2026, 3, 21),
        end=date(2026, 7, 19),
        max_symbols_per_type=10,
        request_delay_seconds=0,
        provider=FundIndexProvider(),
        bar_ingestor=lambda **_kwargs: pytest.fail("current bars must not be fetched"),
    )

    assert result["status"] == "ok"
    assert result["assets"]["etf"]["counts"]["current"] == 1
    assert result["assets"]["index"]["counts"]["current"] == 1
    assert result["assets"]["etf"]["bar_count"] == 0


def test_pipeline_rejects_unknown_existing_provenance_without_leaking_it(session):
    _seed_daily_bar(
        session,
        asset_type="etf",
        symbol="510300",
        trade_date=date(2026, 7, 17),
        source="credential=unsupported-source",
        adjustment="raw",
    )

    with pytest.raises(CnFundIndexPipelineError) as exc_info:
        sync_cn_fund_index_data(
            session=session,
            start=date(2026, 3, 21),
            end=date(2026, 7, 19),
            max_symbols_per_type=10,
            request_delay_seconds=0,
            provider=FundIndexProvider(),
            bar_ingestor=lambda **_kwargs: pytest.fail("invalid source must not fetch"),
        )

    assert exc_info.value.code == "CN_ETF_DAILY_BARS_PROVIDER_WIDE_FAILURE"
    assert "credential" not in str(exc_info.value)


def test_pipeline_raises_sanitized_provider_wide_bar_failure_after_catalog_checkpoint(
    session,
):
    def fail(**_kwargs):
        raise RuntimeError("credential=must-not-be-stored")

    with pytest.raises(CnFundIndexPipelineError) as exc_info:
        sync_cn_fund_index_data(
            session=session,
            start=date(2026, 7, 1),
            end=date(2026, 7, 19),
            max_symbols_per_type=10,
            request_delay_seconds=0,
            provider=FundIndexProvider(),
            bar_ingestor=fail,
        )

    assert exc_info.value.code == "CN_ETF_DAILY_BARS_PROVIDER_WIDE_FAILURE"
    assert "must-not-be-stored" not in str(exc_info.value)
