from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.domain.models import (
    FundamentalSnapshot,
    ResearchShortlistCandidate,
    ResearchShortlistRun,
    Watchlist,
    WatchlistItem,
)
from packages.providers.eastmoney_public_fundamentals import (
    EastmoneyPublicCompany,
    EastmoneyPublicFundamentalsSnapshot,
)
from packages.services.eastmoney_automation import (
    refresh_eastmoney_calendar_batch,
    refresh_eastmoney_fundamentals_batch,
    refresh_eastmoney_news_batch,
    resolve_eastmoney_research_symbols,
)
import packages.services.eastmoney_automation as eastmoney_automation
from packages.shared.database import Base


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_research_symbols_prioritize_latest_shortlist_then_watchlist():
    session = make_session()
    watchlist = Watchlist(name="default", is_default=True)
    session.add(watchlist)
    session.flush()
    session.add_all(
        [
            WatchlistItem(
                watchlist_id=watchlist.id,
                symbol="600519",
                market="CN",
                name="Kweichow Moutai",
                is_active=True,
            ),
            WatchlistItem(
                watchlist_id=watchlist.id,
                symbol="AAPL",
                market="US",
                name="Apple",
                is_active=True,
            ),
        ]
    )
    run = ResearchShortlistRun(
        generation_key="key",
        status="committed",
        decision_date=date(2026, 7, 17),
        market="CN",
        asset_type="stock",
        profile_id="balanced_research",
        rule_set="rules",
        scoring_model="score",
        locale="zh",
        shortlist_limit=10,
        explanation_markdown="",
    )
    session.add(run)
    session.flush()
    session.add(
        ResearchShortlistCandidate(
            run_id=run.id,
            instrument_id=uuid4(),
            symbol="000001",
            name="Ping An Bank",
            market="CN",
            asset_type="stock",
            rank=1,
            total_score=Decimal("1"),
            minimum_rule_buffer=Decimal("0"),
            entry_trade_date=date(2026, 7, 17),
            entry_close=Decimal("10"),
            entry_provider="akshare",
            entry_source="database",
            entry_adjustment="qfq",
            entry_source_priority=1,
            entry_ingested_at=datetime.now(timezone.utc),
        )
    )
    session.commit()

    assert resolve_eastmoney_research_symbols(session, limit=10) == (
        "000001",
        "600519",
    )


def test_automation_defaults_to_shanghai_date(monkeypatch):
    session = make_session()
    observed = {}

    monkeypatch.setattr(
        eastmoney_automation,
        "_shanghai_today",
        lambda: date(2026, 7, 18),
    )

    class Result:
        inserted = 1
        updated = 0

    def fake_refresh(*, session, start, end):
        observed.update(start=start, end=end)
        return Result()

    monkeypatch.setattr(eastmoney_automation, "refresh_economic_calendar", fake_refresh)

    result = refresh_eastmoney_calendar_batch(session=session)

    assert result["start"] == "2026-07-11"
    assert result["end"] == "2026-09-10"
    assert observed == {"start": date(2026, 7, 11), "end": date(2026, 9, 10)}


def test_news_batch_counts_deduplicated_items_as_skipped(monkeypatch):
    session = make_session()
    monkeypatch.setattr(
        eastmoney_automation,
        "resolve_eastmoney_research_symbols",
        lambda session, *, limit: ("600519",),
    )
    monkeypatch.setattr(
        eastmoney_automation,
        "ingest_akshare_news",
        lambda symbol, *, session: {
            "symbol": symbol,
            "status": "skipped",
            "article_count": 0,
        },
    )

    result = refresh_eastmoney_news_batch(
        session=session,
        limit=10,
        request_delay_seconds=0,
    )

    assert result["status"] == "ok"
    assert result["counts"] == {
        "ingested": 0,
        "empty": 0,
        "skipped": 1,
        "provider_error": 0,
    }


def test_fundamental_batch_persists_coherent_company_snapshot():
    session = make_session()
    watchlist = Watchlist(name="default", is_default=True)
    session.add(watchlist)
    session.flush()
    session.add(
        WatchlistItem(
            watchlist_id=watchlist.id,
            symbol="600519",
            market="CN",
            name="Kweichow Moutai",
            is_active=True,
        )
    )
    session.commit()
    progress = []

    def fetcher(symbol, *, as_of):
        assert symbol == "600519"
        assert as_of == date(2026, 7, 17)
        return EastmoneyPublicFundamentalsSnapshot(
            symbol=symbol,
            as_of=date(2026, 6, 30),
            currency="CNY",
            pe_ratio=None,
            revenue_growth=0.1,
            net_margin=0.5,
            debt_to_assets=0.2,
            company=EastmoneyPublicCompany(
                name="Kweichow Moutai",
                industry="Beverages",
                business_scope="Production",
                profile="Profile",
            ),
            status="ok",
            provider="eastmoney_public",
            upstream_sources=("financial", "company"),
            retrieved_at=datetime.now(timezone.utc),
            diagnostics=(),
        )

    result = refresh_eastmoney_fundamentals_batch(
        session=session,
        limit=10,
        as_of=date(2026, 7, 17),
        request_delay_seconds=0,
        fetcher=fetcher,
        progress_callback=lambda *args: progress.append(args),
    )

    row = session.query(FundamentalSnapshot).one()
    assert result["counts"] == {"ingested": 1, "empty": 0, "provider_error": 0}
    assert row.source == "eastmoney_public"
    assert row.pe_ratio is None
    assert row.company_json["industry"] == "Beverages"
    assert progress[-1][:3] == ("fundamentals", 1, 1)


def test_fundamental_batch_preserves_more_complete_existing_snapshot():
    session = make_session()
    watchlist = Watchlist(name="default", is_default=True)
    session.add(watchlist)
    session.flush()
    session.add(
        WatchlistItem(
            watchlist_id=watchlist.id,
            symbol="600519",
            market="CN",
            name="Kweichow Moutai",
            is_active=True,
        )
    )
    session.add(
        FundamentalSnapshot(
            symbol="600519",
            as_of=date(2026, 6, 30),
            currency="CNY",
            pe_ratio=Decimal("20"),
            revenue_growth=Decimal("0.1"),
            net_margin=Decimal("0.5"),
            debt_to_assets=Decimal("0.2"),
            source="akshare",
        )
    )
    session.commit()

    def fetcher(symbol, *, as_of):
        return EastmoneyPublicFundamentalsSnapshot(
            symbol=symbol,
            as_of=date(2026, 6, 30),
            currency="CNY",
            pe_ratio=None,
            revenue_growth=0.11,
            net_margin=0.51,
            debt_to_assets=0.21,
            company=EastmoneyPublicCompany("Moutai", "Beverages", None, None),
            status="ok",
            provider="eastmoney_public",
            upstream_sources=("financial", "company"),
            retrieved_at=datetime.now(timezone.utc),
            diagnostics=(),
        )

    refresh_eastmoney_fundamentals_batch(
        session=session,
        limit=10,
        as_of=date(2026, 7, 17),
        request_delay_seconds=0,
        fetcher=fetcher,
    )

    row = session.query(FundamentalSnapshot).one()
    assert row.source == "akshare"
    assert row.pe_ratio == Decimal("20.000000")
    assert row.revenue_growth == Decimal("0.100000")
    assert row.company_json["industry"] == "Beverages"
