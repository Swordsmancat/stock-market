from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from apps.api.main import app
from packages.domain.models import OfficialDisclosure
from packages.providers.cninfo_disclosure_provider import CninfoDisclosureProviderError
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
