from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from apps.api.main import app
from packages.domain.models import OfficialDisclosure
from packages.providers.cninfo_disclosure_provider import CninfoDisclosureProviderError
from packages.providers.cninfo_document_provider import CninfoDocumentProviderError
from packages.services.official_disclosure_documents import (
    OfficialDisclosureDocumentNotFoundError,
    OfficialDisclosureDocumentPersistenceError,
    OfficialDisclosureDocumentStorageError,
)
from packages.shared.database import Base, get_session


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def with_test_client(session):
    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def test_official_disclosures_api_lists_metadata_only_rows():
    session = make_session()
    session.add(
        OfficialDisclosure(
            source="cninfo",
            source_document_id="1212345678",
            symbol="000001",
            company_name="平安银行",
            title="2025 年年度报告",
            category="年报",
            published_at=datetime(2026, 3, 20, 10, 30, tzinfo=timezone.utc),
            source_url="http://www.cninfo.com.cn/new/disclosure/detail?announcementId=1212345678",
            retrieved_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
            dedupe_hash="a" * 64,
            metadata_json={"content_ingested": False},
        )
    )
    session.commit()
    client = with_test_client(session)
    try:
        response = client.get("/official-disclosures?symbol=000001")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total"] == 1
    assert payload["items"][0]["citation_id"].startswith("official_disclosure:")
    assert payload["evidence_boundary"]["content_ingested"] is False


def test_official_disclosures_refresh_maps_provider_errors(monkeypatch):
    session = make_session()

    def fail_refresh(*args, **kwargs):
        raise CninfoDisclosureProviderError("CNINFO_PROVIDER_ERROR", "CNINFO unavailable.")

    monkeypatch.setattr(
        "apps.api.routers.official_disclosures.refresh_official_disclosures",
        fail_refresh,
    )
    client = with_test_client(session)
    try:
        response = client.post(
            "/official-disclosures/refresh",
            json={
                "symbol": "000001",
                "start_date": "2026-03-01",
                "end_date": "2026-03-31",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json()["detail"] == {
        "source": "cninfo",
        "code": "CNINFO_PROVIDER_ERROR",
        "message": "CNINFO unavailable.",
    }


def test_official_disclosures_refresh_delegates_validated_request(monkeypatch):
    session = make_session()
    captured = {}

    def fake_refresh(payload, *, session):
        captured.update(
            {
                "symbol": payload.symbol,
                "start_date": payload.start_date.isoformat(),
                "end_date": payload.end_date.isoformat(),
                "category": payload.category,
            }
        )
        return {
            "status": "ok",
            "counts": {"received": 1, "created": 1, "updated": 0, "unchanged": 0, "rejected": 0},
            "diagnostics": [{"code": "CNINFO_METADATA_REFRESHED"}],
        }

    monkeypatch.setattr(
        "apps.api.routers.official_disclosures.refresh_official_disclosures",
        fake_refresh,
    )
    client = with_test_client(session)
    try:
        response = client.post(
            "/official-disclosures/refresh",
            json={
                "symbol": "000001",
                "start_date": "2026-03-01",
                "end_date": "2026-03-31",
                "category": "年报",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured == {
        "symbol": "000001",
        "start_date": "2026-03-01",
        "end_date": "2026-03-31",
        "category": "年报",
    }
    assert response.json()["diagnostics"][0]["code"] == "CNINFO_METADATA_REFRESHED"


def test_official_disclosures_api_rejects_invalid_symbol():
    session = make_session()
    client = with_test_client(session)
    try:
        response = client.get("/official-disclosures?symbol=AAPL")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert "six-digit" in response.json()["detail"]


def test_official_disclosure_document_ingest_api_delegates(monkeypatch):
    session = make_session()
    captured = {}

    def fake_ingest(disclosure_id, *, session):
        captured["disclosure_id"] = disclosure_id
        return {
            "status": "ok",
            "action": "created",
            "summary": {"section_count": 2, "citable_section_count": 2},
            "citations": [{"id": "official_disclosure_section:section-1"}],
        }

    monkeypatch.setattr(
        "apps.api.routers.official_disclosures.ingest_official_disclosure_document",
        fake_ingest,
    )
    client = with_test_client(session)
    try:
        response = client.post(
            "/official-disclosures/11111111-2222-3333-4444-555555555555/ingest-document"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured["disclosure_id"] == "11111111-2222-3333-4444-555555555555"
    assert response.json()["citations"][0]["id"].startswith("official_disclosure_section:")


def test_official_disclosure_document_ingest_api_maps_provider_error(monkeypatch):
    session = make_session()

    def failing_ingest(disclosure_id, *, session):
        raise CninfoDocumentProviderError("CNINFO_DOCUMENT_DOWNLOAD_ERROR", "Download failed.")

    monkeypatch.setattr(
        "apps.api.routers.official_disclosures.ingest_official_disclosure_document",
        failing_ingest,
    )
    client = with_test_client(session)
    try:
        response = client.post(
            "/official-disclosures/11111111-2222-3333-4444-555555555555/ingest-document"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json()["detail"] == {
        "source": "cninfo",
        "code": "CNINFO_DOCUMENT_DOWNLOAD_ERROR",
        "message": "Download failed.",
    }


def test_official_disclosure_document_ingest_api_maps_invalid_uuid():
    session = make_session()
    client = with_test_client(session)
    try:
        response = client.post("/official-disclosures/not-a-uuid/ingest-document")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"] == "disclosure_id must be a valid UUID."


def test_official_disclosure_document_ingest_api_maps_storage_error(monkeypatch):
    session = make_session()

    def failing_ingest(disclosure_id, *, session):
        raise OfficialDisclosureDocumentStorageError("Official disclosure storage root is not available.")

    monkeypatch.setattr(
        "apps.api.routers.official_disclosures.ingest_official_disclosure_document",
        failing_ingest,
    )
    client = with_test_client(session)
    try:
        response = client.post(
            "/official-disclosures/11111111-2222-3333-4444-555555555555/ingest-document"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json()["detail"] == "Official disclosure storage root is not available."


def test_official_disclosure_document_ingest_api_maps_persistence_error(monkeypatch):
    session = make_session()

    def failing_ingest(disclosure_id, *, session):
        raise OfficialDisclosureDocumentPersistenceError(
            "Official disclosure document evidence could not be persisted."
        )

    monkeypatch.setattr(
        "apps.api.routers.official_disclosures.ingest_official_disclosure_document",
        failing_ingest,
    )
    client = with_test_client(session)
    try:
        response = client.post(
            "/official-disclosures/11111111-2222-3333-4444-555555555555/ingest-document"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Official disclosure document evidence could not be persisted."
    )


def test_official_disclosure_sections_api_maps_missing_document(monkeypatch):
    session = make_session()

    def missing_sections(*args, **kwargs):
        raise OfficialDisclosureDocumentNotFoundError("Official disclosure document version not found.")

    monkeypatch.setattr(
        "apps.api.routers.official_disclosures.list_official_disclosure_sections",
        missing_sections,
    )
    client = with_test_client(session)
    try:
        response = client.get(
            "/official-disclosures/11111111-2222-3333-4444-555555555555/sections"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Official disclosure document version not found."


def test_official_disclosure_evidence_status_api_delegates(monkeypatch):
    session = make_session()
    monkeypatch.setattr(
        "apps.api.routers.official_disclosures.list_watchlist_official_disclosure_evidence",
        lambda *, session, limit: {
            "status": "ok",
            "scope": "watchlist",
            "summary": {"eligible_symbol_count": 2, "returned": limit},
            "items": [],
        },
    )
    client = with_test_client(session)
    try:
        response = client.get("/official-disclosures/evidence-status?limit=12")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["summary"] == {"eligible_symbol_count": 2, "returned": 12}


def test_official_disclosure_watchlist_ingest_api_enqueues_bounded_task(monkeypatch):
    session = make_session()
    captured = {}

    def enqueue(*, session, lookback_days, max_documents):
        captured.update(lookback_days=lookback_days, max_documents=max_documents)
        return {"status": "dispatched", "task_run": {"id": "task-1"}}

    monkeypatch.setattr(
        "apps.api.routers.official_disclosures.enqueue_watchlist_official_disclosure_ingestion",
        enqueue,
    )
    client = with_test_client(session)
    try:
        response = client.post(
            "/official-disclosures/watchlist/ingest",
            json={"lookback_days": 45, "max_documents": 12},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured == {"lookback_days": 45, "max_documents": 12}
    assert response.json()["task_run"]["id"] == "task-1"


def test_official_disclosure_watchlist_monitor_api_enqueues_incremental_task(monkeypatch):
    session = make_session()
    captured = {}

    def enqueue(*, session, lookback_days, max_documents, mode):
        captured.update(
            lookback_days=lookback_days,
            max_documents=max_documents,
            mode=mode,
        )
        return {"status": "dispatched", "task_run": {"id": "task-monitor"}}

    monkeypatch.setattr(
        "apps.api.routers.official_disclosures.enqueue_watchlist_official_disclosure_ingestion",
        enqueue,
    )
    client = with_test_client(session)
    try:
        response = client.post(
            "/official-disclosures/watchlist/monitor",
            json={"lookback_days": 30, "max_documents": 20},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured == {
        "lookback_days": 30,
        "max_documents": 20,
        "mode": "incremental",
    }
    assert response.json()["task_run"]["id"] == "task-monitor"
