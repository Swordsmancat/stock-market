from datetime import date, datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.domain.models import OfficialDisclosure
from packages.providers.cninfo_disclosure_provider import (
    CninfoDisclosureProviderError,
    CninfoDisclosureFetchResult,
    DisclosureCandidateRejection,
    OfficialDisclosureCandidate,
)
from packages.services.official_disclosures import (
    OfficialDisclosureRefreshInput,
    list_citable_official_disclosure_citations,
    list_official_disclosures,
    refresh_official_disclosures,
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


def candidate(*, title="2025 年年度报告", category="年报", source_url=None):
    return OfficialDisclosureCandidate(
        source="cninfo",
        source_document_id="1212345678",
        symbol="000001",
        company_name="平安银行",
        title=title,
        category=category,
        published_at=datetime(2026, 3, 20, 10, 30, tzinfo=timezone.utc),
        source_url=source_url
        or "http://www.cninfo.com.cn/new/disclosure/detail?announcementId=1212345678",
        retrieved_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
        metadata={
            "provider": "akshare",
            "authority": "CNINFO",
            "evidence_scope": "metadata_only",
            "content_ingested": False,
        },
    )


def refresh(session, disclosure_candidate):
    return refresh_official_disclosures(
        OfficialDisclosureRefreshInput(
            symbol="000001",
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 31),
            category=disclosure_candidate.category,
        ),
        session=session,
        provider_fetcher=lambda **kwargs: CninfoDisclosureFetchResult(
            items=[disclosure_candidate], rejections=[]
        ),
    )


def test_refresh_is_idempotent_and_builds_metadata_only_citations():
    session = make_session()

    first = refresh(session, candidate())
    second = refresh(session, candidate())
    listed = list_official_disclosures(session=session, symbol="000001.SZ")
    citations = list_citable_official_disclosure_citations(
        session=session, symbols=["000001"], limit=3
    )

    assert first["counts"] == {
        "received": 1,
        "created": 1,
        "updated": 0,
        "unchanged": 0,
        "rejected": 0,
    }
    assert second["counts"]["unchanged"] == 1
    assert session.query(OfficialDisclosure).count() == 1
    assert listed["summary"] == {"total": 1, "returned": 1, "symbol": "000001"}
    assert first["items"][0]["citation_id"] == second["items"][0]["citation_id"]
    assert citations[0]["id"] == first["items"][0]["citation_id"]
    assert citations[0]["metadata"]["evidence_scope"] == "metadata_only"
    assert citations[0]["metadata"]["content_ingested"] is False
    assert "Document body has not been ingested" in citations[0]["excerpt"]


def test_refresh_updates_metadata_without_changing_identity():
    session = make_session()
    original = refresh(session, candidate())

    changed = refresh(
        session,
        candidate(
            title="2025 年年度报告（更新后）",
            category="补充更正",
            source_url="https://www.cninfo.com.cn/new/disclosure/detail?announcementId=1212345678",
        ),
    )

    assert changed["counts"]["updated"] == 1
    assert original["items"][0]["citation_id"] == changed["items"][0]["citation_id"]
    assert changed["items"][0]["title"].endswith("（更新后）")


def test_refresh_reports_rejected_rows_without_deleting_existing_data():
    session = make_session()
    refresh(session, candidate())

    payload = refresh_official_disclosures(
        OfficialDisclosureRefreshInput(
            symbol="000001",
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 31),
        ),
        session=session,
        provider_fetcher=lambda **kwargs: CninfoDisclosureFetchResult(
            items=[],
            rejections=[
                DisclosureCandidateRejection(
                    row_index=0,
                    code="CNINFO_ROW_REJECTED",
                    message="Disclosure URL is missing announcementId.",
                )
            ],
        ),
    )

    assert payload["status"] == "no_data"
    assert payload["counts"]["rejected"] == 1
    assert session.query(OfficialDisclosure).count() == 1
    assert "announcementId" in payload["diagnostics"][1]["message"]


def test_provider_failure_leaves_previously_stored_metadata_intact():
    session = make_session()
    refresh(session, candidate())

    def failing_provider(**kwargs):
        raise CninfoDisclosureProviderError("CNINFO_PROVIDER_ERROR", "CNINFO unavailable.")

    try:
        refresh_official_disclosures(
            OfficialDisclosureRefreshInput(
                symbol="000001",
                start_date=date(2026, 3, 1),
                end_date=date(2026, 3, 31),
            ),
            session=session,
            provider_fetcher=failing_provider,
        )
    except CninfoDisclosureProviderError:
        pass
    else:
        raise AssertionError("Expected provider failure")

    assert session.query(OfficialDisclosure).count() == 1
