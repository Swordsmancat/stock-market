from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.domain.models import (
    OfficialDisclosure,
    OfficialDisclosureDocument,
    OfficialDisclosureSection,
)
from packages.providers.cninfo_document_provider import CninfoDocumentProviderError
from packages.services.official_disclosure_operations import (
    WATCHLIST_DISCLOSURE_TASK_NAME,
    enqueue_watchlist_official_disclosure_ingestion,
    ingest_watchlist_official_disclosures,
    list_watchlist_official_disclosure_evidence,
)
from packages.services.task_runs import start_task_run
from packages.services.watchlists import upsert_watchlist_item
from packages.shared.database import Base


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def add_disclosure(session, *, symbol="000001", announcement_id="1225022887"):
    disclosure = OfficialDisclosure(
        source="cninfo",
        source_document_id=announcement_id,
        symbol=symbol,
        company_name="平安银行",
        title="2025 年年度报告",
        category="年报",
        published_at=datetime(2026, 3, 21, tzinfo=timezone.utc),
        source_url=f"https://www.cninfo.com.cn/new/disclosure/detail?announcementId={announcement_id}",
        retrieved_at=datetime(2026, 3, 22, tzinfo=timezone.utc),
        dedupe_hash=announcement_id[-1] * 64,
        metadata_json={"org_id": "gssz0000001"},
    )
    session.add(disclosure)
    session.commit()
    return disclosure


def test_watchlist_coverage_filters_non_cn_and_never_exposes_storage_path():
    session = make_session()
    upsert_watchlist_item("000001", "CN", session=session)
    upsert_watchlist_item("AAPL", "US", session=session)
    disclosure = add_disclosure(session)
    document = OfficialDisclosureDocument(
        official_disclosure_id=disclosure.id,
        attachment_url="https://static.cninfo.com.cn/finalpage/2026-03-21/1225022887.PDF",
        media_type="application/pdf",
        byte_size=100,
        sha256="a" * 64,
        storage_path="secret/absolute-looking/path.pdf",
        retrieved_at=datetime(2026, 3, 22, tzinfo=timezone.utc),
        page_count=1,
        extraction_status="extracted",
        extraction_method="pypdf",
        metadata_json={},
    )
    session.add(document)
    session.flush()
    session.add(
        OfficialDisclosureSection(
            document_id=document.id,
            section_index=0,
            page_number=1,
            heading="主要财务数据",
            topic="financials",
            content_text="营业收入增长。",
            content_hash="b" * 64,
        )
    )
    session.commit()

    payload = list_watchlist_official_disclosure_evidence(session=session)

    assert payload["symbols"] == ["000001"]
    assert payload["summary"]["metadata_disclosure_count"] == 1
    assert payload["summary"]["citable_section_count"] == 1
    assert payload["items"][0]["status"] == "extracted"
    assert payload["items"][0]["content_citable"] is True
    assert "storage_path" not in str(payload)


def test_watchlist_batch_is_sequential_bounded_and_skips_extracted_documents():
    session = make_session()
    upsert_watchlist_item("000001", "CN", session=session)
    upsert_watchlist_item("600519", "CN", session=session)
    calls = []
    sleeps = []

    def refresh(payload, *, session):
        calls.append(("metadata", payload.symbol))
        add_disclosure(
            session,
            symbol=payload.symbol,
            announcement_id="1225022887" if payload.symbol == "000001" else "1225022888",
        )
        return {"status": "ok", "counts": {"created": 1}}

    def ingest(disclosure_id, *, session):
        disclosure = session.get(OfficialDisclosure, UUID(disclosure_id))
        calls.append(("document", disclosure.symbol))
        return {"status": "ok", "action": "created", "document": {"sha256": "a" * 64}}

    progress = []
    result = ingest_watchlist_official_disclosures(
        session=session,
        lookback_days=30,
        max_documents=1,
        request_delay_seconds=0.5,
        metadata_refresher=refresh,
        document_ingester=ingest,
        sleep_func=sleeps.append,
        progress_callback=lambda *values: progress.append(values),
        today=date(2026, 3, 31),
    )

    assert calls == [("metadata", "000001"), ("metadata", "600519"), ("document", "000001")]
    assert sleeps == [0.5, 0.5]
    assert result["summary"]["candidate_document_count"] == 1
    assert result["summary"]["processed_document_count"] == 1
    assert result["safety"]["sequential_requests"] is True
    assert progress[-1][0] == "documents"


def test_watchlist_batch_preserves_success_when_one_document_fails():
    session = make_session()
    upsert_watchlist_item("000001", "CN", session=session)
    first = add_disclosure(session, announcement_id="1225022887")
    add_disclosure(session, announcement_id="1225022888")

    def ingest(disclosure_id, *, session):
        if disclosure_id == str(first.id):
            raise CninfoDocumentProviderError("CNINFO_DOCUMENT_HTTP_ERROR", "CNINFO unavailable.")
        return {"status": "ok", "action": "created", "document": {"sha256": "a" * 64}}

    result = ingest_watchlist_official_disclosures(
        session=session,
        lookback_days=30,
        max_documents=2,
        request_delay_seconds=0,
        metadata_refresher=lambda *args, **kwargs: {"status": "no_data", "counts": {}},
        document_ingester=ingest,
        today=date(2026, 3, 31),
    )

    assert result["status"] == "partial"
    assert result["summary"]["created"] == 1
    assert result["summary"]["failed"] == 1
    assert result["diagnostics"][0]["code"] == "CNINFO_DOCUMENT_HTTP_ERROR"
    assert "unavailable" in result["diagnostics"][0]["message"].lower()


def test_watchlist_batch_empty_scope_is_no_data_without_universe_fallback():
    session = make_session()
    result = ingest_watchlist_official_disclosures(
        session=session,
        request_delay_seconds=0,
        metadata_refresher=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError()),
        document_ingester=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError()),
    )
    assert result["status"] == "no_data"
    assert result["symbols"] == []
    assert result["summary"]["processed_document_count"] == 0


def test_watchlist_batch_enqueue_reuses_active_task_run():
    session = make_session()
    active = start_task_run(WATCHLIST_DISCLOSURE_TASK_NAME, {}, session=session)

    payload = enqueue_watchlist_official_disclosure_ingestion(session=session)

    assert payload["status"] == "already_running"
    assert payload["task_run"]["id"] == str(active.id)
