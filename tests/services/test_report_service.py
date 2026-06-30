from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.analytics.fundamentals import FundamentalSnapshot
from packages.services.fundamentals import upsert_fundamental_snapshot
from packages.services.indicators import calculate_and_store_daily_indicators
from packages.services.ingestion import ingest_mock_market_snapshot
from packages.services.news import ingest_mock_news
from packages.services.reports import (
    generate_and_store_daily_report,
    generate_stock_report_payload,
    get_latest_daily_report_payload,
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


def test_generate_stock_report_payload_uses_market_data_citation():
    payload = generate_stock_report_payload("AAPL", date(2026, 1, 1), date(2026, 1, 15))

    assert payload["symbol"] == "AAPL"
    assert payload["report_type"] == "stock_daily"
    assert "# AAPL AI 个股报告" in payload["content_markdown"]
    assert "PE 28.40" in payload["content_markdown"]
    assert "bars_1d:AAPL:2026-01-15" in payload["citations"]
    assert "fundamental_metrics:AAPL:2026-01-15" in payload["citations"]


def test_generate_stock_report_payload_aggregates_database_indicators_and_news():
    session = make_session()
    ingest_mock_market_snapshot("US", date(2026, 1, 1), date(2026, 1, 20), session=session)
    calculate_and_store_daily_indicators(
        "AAPL",
        date(2026, 1, 1),
        date(2026, 1, 20),
        session=session,
        ma_window=3,
    )
    ingest_mock_news("AAPL", session=session)
    upsert_fundamental_snapshot(
        FundamentalSnapshot(
            symbol="AAPL",
            as_of=date(2026, 1, 20),
            currency="USD",
            pe_ratio=30.5,
            revenue_growth=0.12,
            net_margin=0.25,
            debt_to_assets=0.29,
        ),
        session=session,
        source="test_fixture",
    )

    payload = generate_stock_report_payload(
        "AAPL",
        date(2026, 1, 1),
        date(2026, 1, 20),
        session=session,
    )

    assert payload["source"] == "database"
    assert "## 综合研判" in payload["content_markdown"]
    assert "MA 119.00" in payload["content_markdown"]
    assert "RSI 100.00" in payload["content_markdown"]
    assert "BOLL upper 121.00, middle 119.00, lower 117.00" in payload["content_markdown"]
    assert "ATR 3.00" in payload["content_markdown"]
    assert "PE 30.50" in payload["content_markdown"]
    assert "Apple reports strong growth in services revenue" in payload["content_markdown"]
    assert "情绪 positive，置信度 0.60" in payload["content_markdown"]
    assert "bars_1d:AAPL:2026-01-20" in payload["citations"]
    assert "technical_indicators:AAPL:2026-01-20T00:00:00+00:00" in payload["citations"]
    assert "fundamental_metrics:AAPL:2026-01-20" in payload["citations"]
    assert "news_articles:AAPL:https://example.com/aapl-services-growth" in payload["citations"]


def test_generate_and_store_daily_report_persists_latest_report():
    session = make_session()
    ingest_mock_market_snapshot("US", date(2026, 1, 1), date(2026, 1, 20), session=session)
    calculate_and_store_daily_indicators(
        "AAPL",
        date(2026, 1, 1),
        date(2026, 1, 20),
        session=session,
        ma_window=3,
    )
    ingest_mock_news("AAPL", session=session)

    stored = generate_and_store_daily_report(
        "AAPL",
        date(2026, 1, 1),
        date(2026, 1, 20),
        session=session,
    )
    latest = get_latest_daily_report_payload("AAPL", session=session)

    assert stored["status"] == "stored"
    assert stored["report_type"] == "stock_daily"
    assert latest["symbol"] == "AAPL"
    assert latest["report_type"] == "stock_daily"
    assert latest["as_of"] == "2026-01-20"
    assert "MA 119.00" in latest["content_markdown"]
    assert "PE 28.40" in latest["content_markdown"]
    assert "Apple reports strong growth in services revenue" in latest["content_markdown"]
    assert "fundamental_metrics:AAPL:2026-01-20" in latest["citations"]
    assert "news_articles:AAPL:https://example.com/aapl-services-growth" in latest["citations"]
