from datetime import date, datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from packages.providers.base import ProviderInstrument, ProviderInstrumentUniverseSnapshot
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
    assert progress[-1] == ("daily_bars", 2, 2)


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
