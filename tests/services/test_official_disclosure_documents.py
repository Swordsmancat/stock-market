import hashlib
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.domain.models import (
    OfficialDisclosure,
    OfficialDisclosureDocument,
    OfficialDisclosureSection,
)
from packages.providers.cninfo_document_provider import CninfoAttachment, DownloadedPdf
from packages.services.official_disclosure_documents import (
    ingest_official_disclosure_document,
    list_citable_official_disclosure_section_citations,
    list_official_disclosure_sections,
)
from packages.shared.database import Base
from tests.helpers.pdf_factory import make_pdf


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def seed_disclosure(session):
    disclosure = OfficialDisclosure(
        source="cninfo",
        source_document_id="1225022887",
        symbol="000001",
        company_name="Ping An Bank",
        title="2025 annual report",
        category="annual_report",
        published_at=datetime(2026, 3, 20, 16, tzinfo=timezone.utc),
        source_url=(
            "https://www.cninfo.com.cn/new/disclosure/detail?stockCode=000001&"
            "announcementId=1225022887&orgId=gssz0000001"
        ),
        retrieved_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
        dedupe_hash="a" * 64,
        metadata_json={"org_id": "gssz0000001"},
    )
    session.add(disclosure)
    session.commit()
    session.refresh(disclosure)
    return disclosure


def attachment():
    return CninfoAttachment(
        announcement_id="1225022887",
        url="https://static.cninfo.com.cn/finalpage/2026-03-21/1225022887.PDF",
        media_type="application/pdf",
        provider_size=1930,
        source_path="finalpage/2026-03-21/1225022887.PDF",
        metadata={"provider": "cninfo"},
    )


def downloaded(content):
    return DownloadedPdf(
        url=attachment().url,
        media_type="application/pdf",
        content=content,
        sha256=hashlib.sha256(content).hexdigest(),
        byte_size=len(content),
        last_modified="Fri, 20 Mar 2026 12:18:17 GMT",
        retrieved_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
    )


def ingest(session, disclosure, content, tmp_path):
    return ingest_official_disclosure_document(
        str(disclosure.id),
        session=session,
        storage_root=tmp_path,
        attachment_discoverer=lambda **kwargs: attachment(),
        pdf_downloader=lambda url: downloaded(content),
    )


def test_ingest_document_is_idempotent_and_builds_page_hash_citations(tmp_path):
    session = make_session()
    disclosure = seed_disclosure(session)
    content = make_pdf(["1. Risk Factors Material customer concentration risk."])

    first = ingest(session, disclosure, content, tmp_path)
    second = ingest(session, disclosure, content, tmp_path)
    citations = list_citable_official_disclosure_section_citations(
        session=session,
        symbols=["000001.SZ"],
    )

    assert first["action"] == "created"
    assert second["action"] == "unchanged"
    assert first["citations"][0]["id"] == second["citations"][0]["id"]
    assert session.query(OfficialDisclosureDocument).count() == 1
    assert session.query(OfficialDisclosureSection).count() == 1
    assert len(list(tmp_path.rglob("*.pdf"))) == 1
    assert "storage_path" not in first["document"]
    assert citations[0]["metadata"]["document_sha256"] == hashlib.sha256(content).hexdigest()
    assert citations[0]["metadata"]["page_number"] == 1
    assert citations[0]["metadata"]["topic"] == "risks"
    assert citations[0]["metadata"]["content_ingested"] is True


def test_changed_document_creates_new_version_and_keeps_old_version_queryable(tmp_path):
    session = make_session()
    disclosure = seed_disclosure(session)
    first = ingest(session, disclosure, make_pdf(["1. Risk Factors First version."]), tmp_path)
    second = ingest(session, disclosure, make_pdf(["1. Risk Factors Corrected version."]), tmp_path)

    old_payload = list_official_disclosure_sections(
        str(disclosure.id),
        session=session,
        document_id=first["document"]["id"],
    )
    latest_payload = list_official_disclosure_sections(str(disclosure.id), session=session)
    latest_citations = list_citable_official_disclosure_section_citations(
        session=session,
        symbols=["000001"],
    )

    assert first["document"]["id"] != second["document"]["id"]
    assert session.query(OfficialDisclosureDocument).count() == 2
    assert len(list(tmp_path.rglob("*.pdf"))) == 2
    assert "First version" in old_payload["items"][0]["content_text"]
    assert "Corrected version" in latest_payload["items"][0]["content_text"]
    assert latest_payload["summary"]["version_count"] == 2
    assert "Corrected version" in latest_citations[0]["excerpt"]
    assert all("First version" not in citation["excerpt"] for citation in latest_citations)


def test_image_only_pdf_is_stored_but_never_becomes_citable(tmp_path):
    session = make_session()
    disclosure = seed_disclosure(session)

    payload = ingest(session, disclosure, make_pdf([""]), tmp_path)
    citations = list_citable_official_disclosure_section_citations(
        session=session,
        symbols=["000001"],
    )

    assert payload["status"] == "no_text"
    assert payload["summary"]["section_count"] == 0
    assert payload["citations"] == []
    assert payload["diagnostics"][0]["code"] == "PDF_NO_EXTRACTABLE_TEXT"
    assert payload["evidence_boundary"]["content_ingested"] is False
    assert session.query(OfficialDisclosureDocument).one().extraction_status == "no_text"
    assert session.query(OfficialDisclosureSection).count() == 0
    assert citations == []


def test_missing_storage_file_is_restored_without_changing_document_identity(tmp_path):
    session = make_session()
    disclosure = seed_disclosure(session)
    content = make_pdf(["2. Financial Statements Revenue information."])
    first = ingest(session, disclosure, content, tmp_path)
    stored_file = next(tmp_path.rglob("*.pdf"))
    stored_file.unlink()

    restored = ingest(session, disclosure, content, tmp_path)

    assert restored["action"] == "restored"
    assert restored["document"]["id"] == first["document"]["id"]
    assert next(tmp_path.rglob("*.pdf")).exists()
