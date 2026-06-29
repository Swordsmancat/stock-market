from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from apps.worker.tasks.ingestion import ingest_mock_market_data
from apps.worker.tasks import reports as report_tasks
from packages.services.reports import get_latest_daily_report_payload
from packages.shared.database import Base


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_ingest_mock_market_data_returns_summary():
    result = ingest_mock_market_data("US")
    assert result["market"] == "US"
    assert result["instrument_count"] >= 1
    assert result["bar_count"] >= 1


def test_refresh_daily_stock_analysis_task_stores_latest_daily_report(monkeypatch):
    session = make_session()
    monkeypatch.setattr(report_tasks, "SessionLocal", lambda: session)

    result = report_tasks.refresh_daily_stock_analysis(
        symbol="AAPL",
        market="US",
        start="2026-01-01",
        end="2026-01-20",
        ma_window=3,
    )
    latest = get_latest_daily_report_payload("AAPL", session=session)

    assert result["symbol"] == "AAPL"
    assert result["status"] == "refreshed"
    assert result["report"]["status"] == "stored"
    assert latest["as_of"] == date(2026, 1, 20).isoformat()
    assert "Apple reports strong growth in services revenue" in latest["content_markdown"]
