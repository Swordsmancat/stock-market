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
from packages.services.reports import generate_and_store_daily_report
from packages.services.task_runs import finish_task_run, start_task_run
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
    assert "PE 28.40" in payload["content_markdown"]
    assert "bars_1d:AAPL:2026-01-15" in payload["citations"]
    assert "fundamental_metrics:AAPL:2026-01-15" in payload["citations"]
    assert "本报告仅基于平台内可验证数据生成" in payload["content_markdown"]


def test_generate_stock_report_returns_actionable_no_data_error():
    app.dependency_overrides[get_session] = override_no_database_session
    try:
        client = TestClient(app)
        response = client.get(
            "/reports/AAPL/stock",
            params={"start": "2026-01-02", "end": "2026-01-01", "provider": "mock"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    payload = response.json()
    assert payload["detail"]["category"] == "no_market_data"
    assert payload["detail"]["symbol"] == "AAPL"
    assert payload["detail"]["provider"] == "mock"
    assert payload["detail"]["no_data_reason"] == "No daily bars were available for the requested symbol/date range."


def test_daily_report_generate_returns_actionable_no_data_error():
    session = make_session()

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        response = client.post(
            "/reports/AAPL/daily/generate",
            params={"start": "2026-01-02", "end": "2026-01-01", "provider": "mock"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    payload = response.json()
    assert payload["detail"]["category"] == "no_market_data"
    assert payload["detail"]["symbol"] == "AAPL"
    assert payload["detail"]["provider"] == "mock"


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
    assert generated["task_run_id"] is None
    assert generated["source_summary"]["source"] == "database"
    assert generated["source_summary"]["price_source"] == "database"
    assert generated["source_summary"]["provider"] == "mock"
    assert generated["source_summary"]["task_run_id"] is None

    assert latest_response.status_code == 200
    latest = latest_response.json()
    assert latest["symbol"] == "AAPL"
    assert latest["as_of"] == "2026-01-20"
    assert latest["task_run_id"] is None
    assert latest["source_summary"]["provider"] == "mock"
    assert "MA 119.00" in latest["content_markdown"]
    assert "PE 28.40" in latest["content_markdown"]
    assert "Apple reports strong growth in services revenue" in latest["content_markdown"]
    assert "fundamental_metrics:AAPL:2026-01-20" in latest["citations"]
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
    assert payload["items"][0]["task_run_id"] is None
    assert payload["items"][0]["source_summary"]["provider"] == "mock"
    assert "Apple reports strong growth in services revenue" in payload["items"][0][
        "content_markdown"
    ]


def test_reports_list_filters_and_detail_returns_persisted_report():
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
            params={"start": "2026-01-01", "end": "2026-01-20"},
        )
        list_response = client.get(
            "/reports",
            params={
                "symbol": "AAPL",
                "report_type": "stock_daily",
                "q": "Apple",
                "as_of_start": "2026-01-20",
                "as_of_end": "2026-01-20",
                "limit": 10,
                "offset": 0,
            },
        )
        report_id = list_response.json()["items"][0]["id"]
        detail_response = client.get(f"/reports/items/{report_id}")
    finally:
        app.dependency_overrides.clear()

    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["source"] == "database"
    assert payload["total"] == 1
    assert payload["limit"] == 10
    assert payload["offset"] == 0
    assert payload["items"][0]["symbol"] == "AAPL"
    assert payload["items"][0]["report_type"] == "stock_daily"

    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["id"] == report_id
    assert "Apple reports strong growth in services revenue" in detail["content_markdown"]


def test_reports_list_and_detail_include_task_run_id_lineage():
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
    task_run = start_task_run(
        "reports.refresh_daily_stock_analysis",
        {"symbol": "AAPL", "market": "US"},
        session=session,
    )
    generated = generate_and_store_daily_report(
        "AAPL",
        date(2026, 1, 1),
        date(2026, 1, 20),
        session=session,
        task_run_id=task_run.id,
    )
    finish_task_run(task_run, {"report": {"id": generated["id"]}}, session=session)

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        list_response = client.get("/reports", params={"symbol": "AAPL", "limit": 10, "offset": 0})
        detail_response = client.get(f"/reports/items/{generated['id']}")
        latest_response = client.get("/reports/AAPL/daily/latest")
        history_response = client.get("/reports/AAPL/daily/history", params={"limit": 1})
    finally:
        app.dependency_overrides.clear()

    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["items"][0]["id"] == generated["id"]
    assert list_payload["items"][0]["task_run_id"] == str(task_run.id)
    assert list_payload["items"][0]["source_summary"]["source"] == "database"
    assert list_payload["items"][0]["source_summary"]["price_source"] == "database"
    assert list_payload["items"][0]["source_summary"]["provider"] == "mock"
    assert list_payload["items"][0]["source_summary"]["task_run_id"] == str(task_run.id)

    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["id"] == generated["id"]
    assert detail["task_run_id"] == str(task_run.id)
    assert detail["source_summary"] == list_payload["items"][0]["source_summary"]

    assert latest_response.status_code == 200
    latest = latest_response.json()
    assert latest["task_run_id"] == str(task_run.id)
    assert latest["source_summary"]["task_run_id"] == str(task_run.id)

    assert history_response.status_code == 200
    history = history_response.json()
    assert history["items"][0]["task_run_id"] == str(task_run.id)
    assert history["items"][0]["source_summary"]["task_run_id"] == str(task_run.id)
