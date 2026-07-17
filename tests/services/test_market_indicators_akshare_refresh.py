from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.domain.models import MarketIndicator, MarketIndicatorObservation
from packages.providers.akshare_macro_provider import (
    AkShareMacroFamilyResult,
    AkShareMacroObservation,
)
from packages.services.market_indicators import (
    get_macro_dashboard_payload,
    refresh_akshare_cn_macro_indicators,
)
from packages.shared.database import Base


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


class FakeProvider:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def fetch(self, **kwargs):
        self.calls.append(kwargs)
        return self.results


def observation(code, as_of, value):
    return AkShareMacroObservation(
        code=code,
        as_of=as_of,
        value=Decimal(value),
        source="AkShare fixture",
        components={
            "provider": "akshare",
            "source_url": "https://example.test/macro",
            "methodology": "Verified fixture method.",
        },
    )


def test_akshare_macro_refresh_persists_successful_family_and_reports_partial_failure():
    session = make_session()
    provider = FakeProvider(
        (
            AkShareMacroFamilyResult(
                family="cpi",
                status="ok",
                fetched=2,
                skipped=0,
                observations=(
                    observation("cn_cpi_yoy", date(2026, 5, 31), "1.2"),
                    observation("cn_cpi_yoy", date(2026, 6, 30), "1.0"),
                ),
                diagnostics=(),
            ),
            AkShareMacroFamilyResult(
                family="pmi",
                status="error",
                fetched=0,
                skipped=0,
                observations=(),
                diagnostics=("pmi: provider_error:ConnectionError",),
            ),
        )
    )

    result = refresh_akshare_cn_macro_indicators(
        session=session,
        provider=provider,
        retrieved_at=datetime(2026, 7, 17, tzinfo=timezone.utc),
    )

    assert result.observations == 2
    assert result.codes == ("cn_cpi_yoy",)
    assert result.latest_as_of == "2026-06-30"
    assert result.diagnostics == ("pmi: provider_error:ConnectionError",)
    assert session.query(MarketIndicatorObservation).count() == 2
    assert provider.calls == [{"family": "all", "history_limit": 24, "retrieved_at": datetime(2026, 7, 17, tzinfo=timezone.utc)}]


def test_akshare_macro_refresh_dry_run_rolls_back_definitions_and_observations():
    session = make_session()
    provider = FakeProvider(
        (
            AkShareMacroFamilyResult(
                family="cpi",
                status="ok",
                fetched=1,
                skipped=0,
                observations=(observation("cn_cpi_yoy", date(2026, 6, 30), "1.0"),),
                diagnostics=(),
            ),
        )
    )

    result = refresh_akshare_cn_macro_indicators(
        session=session,
        dry_run=True,
        provider=provider,
    )

    assert result.dry_run is True
    assert session.query(MarketIndicator).count() == 0
    assert session.query(MarketIndicatorObservation).count() == 0


def test_macro_dashboard_projection_is_read_only_grouped_and_chronological():
    session = make_session()
    provider = FakeProvider(
        (
            AkShareMacroFamilyResult(
                family="cpi",
                status="ok",
                fetched=3,
                skipped=0,
                observations=(
                    observation("cn_cpi_yoy", date(2026, 4, 30), "0.8"),
                    observation("cn_cpi_yoy", date(2026, 5, 31), "1.2"),
                    observation("cn_cpi_yoy", date(2026, 6, 30), "1.0"),
                ),
                diagnostics=(),
            ),
        )
    )
    refresh_akshare_cn_macro_indicators(session=session, provider=provider)
    before = session.query(MarketIndicatorObservation).count()

    payload = get_macro_dashboard_payload(
        session=session,
        history_limit=2,
        today=date(2026, 7, 17),
    )

    after = session.query(MarketIndicatorObservation).count()
    items = {
        item["code"]: item
        for group in payload["groups"]
        for item in group["items"]
    }
    assert before == after == 3
    assert payload["summary"]["total"] == 23
    assert [group["id"] for group in payload["groups"]] == [
        "rates",
        "fundamentals",
        "valuation",
        "external",
        "money",
        "fiscal",
    ]
    assert items["cn_cpi_yoy"]["value"] == 1.0
    assert items["cn_cpi_yoy"]["previous_value"] == 1.2
    assert items["cn_cpi_yoy"]["direction"] == "down"
    assert items["cn_cpi_yoy"]["history"] == [
        {"as_of": "2026-05-31", "value": 1.2},
        {"as_of": "2026-06-30", "value": 1.0},
    ]
    assert items["cn_ppi_yoy"]["no_data_reason"] == "no_stored_observation"
