from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from apps.api.main import app
from packages.services.indicators import calculate_and_store_daily_indicators
from packages.services.ingestion import ingest_mock_market_snapshot
from packages.services.news import ingest_mock_news
from packages.shared.database import Base, get_session


def override_no_database_session():
    yield None


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_generate_stock_report_returns_markdown_with_citations():
    app.dependency_overrides[get_session] = override_no_database_session
    try:
        client = TestClient(app)
        response = client.get(
            "/reports/AAPL/stock",
            params={"start": "2026-01-01", "end": "2026-01-15"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert payload["report_type"] == "stock_daily"
    assert "# AAPL AI 个股报告" in payload["content_markdown"]
    assert "bars_1d:AAPL:2026-01-15" in payload["citations"]
    assert "本报告仅基于平台内可验证数据生成" in payload["content_markdown"]


def test_daily_report_generate_then_latest_returns_persisted_report():
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

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        generated_response = client.post(
            "/reports/AAPL/daily/generate",
            params={"start": "2026-01-01", "end": "2026-01-20"},
        )
        latest_response = client.get("/reports/AAPL/daily/latest")
    finally:
        app.dependency_overrides.clear()

    assert generated_response.status_code == 200
    generated = generated_response.json()
    assert generated["status"] == "stored"
    assert generated["report_type"] == "stock_daily"

    assert latest_response.status_code == 200
    latest = latest_response.json()
    assert latest["symbol"] == "AAPL"
    assert latest["as_of"] == "2026-01-20"
    assert "MA 119.00" in latest["content_markdown"]
    assert "Apple reports strong growth in services revenue" in latest["content_markdown"]
    assert "news_articles:AAPL:https://example.com/aapl-services-growth" in latest["citations"]


def test_daily_report_history_returns_persisted_reports_in_descending_order():
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

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        client.post(
            "/reports/AAPL/daily/generate",
            params={"start": "2026-01-01", "end": "2026-01-19"},
        )
        client.post(
            "/reports/AAPL/daily/generate",
            params={"start": "2026-01-01", "end": "2026-01-20"},
        )
        response = client.get("/reports/AAPL/daily/history", params={"limit": 2})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert [item["as_of"] for item in payload["items"]] == ["2026-01-20", "2026-01-19"]
    assert payload["items"][0]["report_type"] == "stock_daily"
    assert "Apple reports strong growth in services revenue" in payload["items"][0][
        "content_markdown"
    ]
