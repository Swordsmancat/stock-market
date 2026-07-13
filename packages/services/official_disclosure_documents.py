from __future__ import annotations

import hashlib
import os
import tempfile
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from uuid import UUID as PythonUUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from packages.analytics.disclosure_documents import (
    DEFAULT_MAX_SECTIONS,
    DisclosureExtractionResult,
    ExtractedDisclosureSection,
    extract_disclosure_pdf_sections,
)
from packages.domain.models import (
    OfficialDisclosure,
    OfficialDisclosureDocument,
    OfficialDisclosureSection,
)
from packages.providers.cninfo_disclosure_provider import normalize_a_share_symbol
from packages.providers.cninfo_document_provider import (
    CninfoAttachment,
    DownloadedPdf,
    discover_cninfo_attachment,
    download_cninfo_pdf,
)
from packages.shared.config import settings


OFFICIAL_DISCLOSURE_SECTION_CITATION_PREFIX = "official_disclosure_section:"
DEFAULT_SECTION_LIMIT = 100
MAX_SECTION_LIMIT = 200
MAX_AI_SECTION_EXCERPT_CHARS = 700


class OfficialDisclosureDocumentNotFoundError(LookupError):
    pass


class OfficialDisclosureDocumentPersistenceError(RuntimeError):
    pass


class OfficialDisclosureDocumentStorageError(RuntimeError):
    pass


def ingest_official_disclosure_document(
    disclosure_id: str,
    *,
    session: Session,
    storage_root: str | Path | None = None,
    attachment_discoverer: Callable[..., CninfoAttachment] = discover_cninfo_attachment,
    pdf_downloader: Callable[..., DownloadedPdf] = download_cninfo_pdf,
    extractor: Callable[[bytes], DisclosureExtractionResult] = extract_disclosure_pdf_sections,
) -> dict[str, object]:
    disclosure = _get_disclosure(disclosure_id, session=session)
    org_id = _disclosure_org_id(disclosure)
    attachment = attachment_discoverer(
        symbol=disclosure.symbol,
        org_id=org_id,
        announcement_id=disclosure.source_document_id,
        published_at=_ensure_aware_datetime(disclosure.published_at),
    )
    downloaded = pdf_downloader(attachment.url)
    root = _storage_root(storage_root)
    storage_path, file_action = _store_versioned_pdf(
        root=root,
        disclosure_id=str(disclosure.id),
        downloaded=downloaded,
    )

    existing = (
        session.query(OfficialDisclosureDocument)
        .filter(
            OfficialDisclosureDocument.official_disclosure_id == disclosure.id,
            OfficialDisclosureDocument.sha256 == downloaded.sha256,
        )
        .one_or_none()
    )
    if existing is not None:
        existing_sections = _document_sections(existing.id, session=session, limit=DEFAULT_MAX_SECTIONS)
        return _ingestion_payload(
            status="ok" if existing.extraction_status == "extracted" else existing.extraction_status,
            action="restored" if file_action == "written" else "unchanged",
            disclosure=disclosure,
            document=existing,
            sections=existing_sections,
            diagnostics=_document_diagnostics(existing),
        )

    extraction = extractor(downloaded.content)
    document = OfficialDisclosureDocument(
        official_disclosure_id=disclosure.id,
        attachment_url=downloaded.url,
        media_type=downloaded.media_type,
        provider_size=attachment.provider_size,
        byte_size=downloaded.byte_size,
        sha256=downloaded.sha256,
        storage_path=storage_path,
        retrieved_at=downloaded.retrieved_at,
        last_modified=downloaded.last_modified,
        page_count=extraction.page_count,
        extraction_status=extraction.status,
        extraction_method=extraction.extraction_method,
        metadata_json={
            "source_path": attachment.source_path,
            "attachment": attachment.metadata,
            "diagnostics": extraction.diagnostics,
            "content_addressed": True,
        },
    )
    new_sections: list[OfficialDisclosureSection] = []
    try:
        session.add(document)
        session.flush()
        for extracted in extraction.sections:
            section = _section_model(document.id, extracted)
            session.add(section)
            new_sections.append(section)
        session.commit()
    except SQLAlchemyError as error:
        session.rollback()
        raise OfficialDisclosureDocumentPersistenceError(
            "Official disclosure document evidence could not be persisted."
        ) from error

    return _ingestion_payload(
        status="ok" if extraction.status == "extracted" else extraction.status,
        action="created",
        disclosure=disclosure,
        document=document,
        sections=new_sections,
        diagnostics=extraction.diagnostics,
    )


def list_official_disclosure_sections(
    disclosure_id: str,
    *,
    session: Session,
    document_id: str | None = None,
    limit: int = DEFAULT_SECTION_LIMIT,
) -> dict[str, object]:
    disclosure = _get_disclosure(disclosure_id, session=session)
    bounded_limit = max(1, min(limit, MAX_SECTION_LIMIT))
    versions = (
        session.query(OfficialDisclosureDocument)
        .filter(OfficialDisclosureDocument.official_disclosure_id == disclosure.id)
        .order_by(
            OfficialDisclosureDocument.retrieved_at.desc(),
            OfficialDisclosureDocument.created_at.desc(),
        )
        .all()
    )
    selected = _select_document_version(versions, document_id)
    if selected is None:
        return {
            "status": "no_data",
            "disclosure": _serialize_disclosure_identity(disclosure),
            "document": None,
            "versions": [],
            "items": [],
            "summary": {"version_count": 0, "total": 0, "returned": 0},
            "evidence_boundary": _document_section_boundary(content_ingested=False),
        }
    sections_query = session.query(OfficialDisclosureSection).filter(
        OfficialDisclosureSection.document_id == selected.id
    )
    total = sections_query.count()
    sections = (
        sections_query.order_by(OfficialDisclosureSection.section_index.asc())
        .limit(bounded_limit)
        .all()
    )
    return {
        "status": "ok" if selected.extraction_status == "extracted" else selected.extraction_status,
        "disclosure": _serialize_disclosure_identity(disclosure),
        "document": serialize_official_disclosure_document(selected),
        "versions": [serialize_official_disclosure_document(version) for version in versions],
        "items": [serialize_official_disclosure_section(item, include_content=True) for item in sections],
        "summary": {
            "version_count": len(versions),
            "total": total,
            "returned": len(sections),
        },
        "diagnostics": _document_diagnostics(selected),
        "evidence_boundary": _document_section_boundary(
            content_ingested=selected.extraction_status == "extracted"
        ),
    }


def list_citable_official_disclosure_section_citations(
    *,
    session: Session,
    symbols: list[str],
    limit: int = 4,
) -> list[dict[str, object]]:
    normalized_symbols = sorted({normalize_a_share_symbol(symbol) for symbol in symbols})
    if not normalized_symbols:
        return []
    bounded_limit = max(1, min(limit, 20))
    rows = (
        session.query(OfficialDisclosureSection, OfficialDisclosureDocument, OfficialDisclosure)
        .join(
            OfficialDisclosureDocument,
            OfficialDisclosureSection.document_id == OfficialDisclosureDocument.id,
        )
        .join(
            OfficialDisclosure,
            OfficialDisclosureDocument.official_disclosure_id == OfficialDisclosure.id,
        )
        .filter(
            OfficialDisclosure.symbol.in_(normalized_symbols),
            OfficialDisclosureDocument.extraction_status == "extracted",
        )
        .order_by(
            OfficialDisclosure.published_at.desc(),
            OfficialDisclosureDocument.retrieved_at.desc(),
            OfficialDisclosureDocument.created_at.desc(),
            OfficialDisclosureSection.section_index.asc(),
        )
        .limit(max(200, bounded_limit * 50))
        .all()
    )
    selected_documents: dict[PythonUUID, PythonUUID] = {}
    citations: list[dict[str, object]] = []
    for section, document, disclosure in rows:
        selected_document_id = selected_documents.setdefault(disclosure.id, document.id)
        if document.id != selected_document_id:
            continue
        citations.append(build_official_disclosure_section_citation(section, document, disclosure))
        if len(citations) >= bounded_limit:
            break
    return citations


def build_official_disclosure_section_citation(
    section: OfficialDisclosureSection,
    document: OfficialDisclosureDocument,
    disclosure: OfficialDisclosure,
) -> dict[str, object]:
    excerpt = _clip(section.content_text, MAX_AI_SECTION_EXCERPT_CHARS)
    return {
        "id": f"{OFFICIAL_DISCLOSURE_SECTION_CITATION_PREFIX}{section.id}",
        "label": f"{disclosure.title} — {section.heading}",
        "source": "official_disclosure_sections",
        "source_type": "official_disclosure_section",
        "url": document.attachment_url,
        "as_of": _datetime_to_iso(disclosure.published_at),
        "provider": disclosure.source,
        "retrieved_at": _datetime_to_iso(document.retrieved_at),
        "excerpt": excerpt,
        "metadata": {
            "symbol": disclosure.symbol,
            "announcement_id": disclosure.source_document_id,
            "document_id": str(document.id),
            "document_sha256": document.sha256,
            "page_number": section.page_number,
            "section_index": section.section_index,
            "heading": section.heading,
            "topic": section.topic,
            "content_hash": section.content_hash,
            **_document_section_boundary(content_ingested=True),
        },
    }


def serialize_official_disclosure_document(
    document: OfficialDisclosureDocument,
) -> dict[str, object]:
    return {
        "id": str(document.id),
        "attachment_url": document.attachment_url,
        "media_type": document.media_type,
        "provider_size": document.provider_size,
        "byte_size": document.byte_size,
        "sha256": document.sha256,
        "retrieved_at": _datetime_to_iso(document.retrieved_at),
        "last_modified": document.last_modified,
        "page_count": document.page_count,
        "extraction_status": document.extraction_status,
        "extraction_method": document.extraction_method,
        "stored": True,
        "metadata": _public_document_metadata(document.metadata_json),
        "created_at": _datetime_to_iso(document.created_at),
    }


def serialize_official_disclosure_section(
    section: OfficialDisclosureSection,
    *,
    include_content: bool,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": str(section.id),
        "citation_id": f"{OFFICIAL_DISCLOSURE_SECTION_CITATION_PREFIX}{section.id}",
        "section_index": section.section_index,
        "page_number": section.page_number,
        "heading": section.heading,
        "topic": section.topic,
        "content_hash": section.content_hash,
        "created_at": _datetime_to_iso(section.created_at),
        "evidence_boundary": _document_section_boundary(content_ingested=True),
    }
    if include_content:
        payload["content_text"] = section.content_text
    else:
        payload["excerpt"] = _clip(section.content_text, MAX_AI_SECTION_EXCERPT_CHARS)
    return payload


def _get_disclosure(disclosure_id: str, *, session: Session) -> OfficialDisclosure:
    try:
        parsed_id = PythonUUID(str(disclosure_id))
    except ValueError as error:
        raise ValueError("disclosure_id must be a valid UUID.") from error
    disclosure = session.get(OfficialDisclosure, parsed_id)
    if disclosure is None:
        raise OfficialDisclosureDocumentNotFoundError("Official disclosure not found.")
    return disclosure


def _disclosure_org_id(disclosure: OfficialDisclosure) -> str:
    metadata = disclosure.metadata_json if isinstance(disclosure.metadata_json, dict) else {}
    org_id = _optional_text(metadata.get("org_id"))
    if not org_id:
        org_id = _optional_text((parse_qs(urlparse(disclosure.source_url).query).get("orgId") or [None])[0])
    if not org_id:
        raise ValueError("Persisted disclosure is missing the CNINFO org ID required for attachment discovery.")
    return org_id


def _storage_root(storage_root: str | Path | None) -> Path:
    configured = storage_root or settings.disclosure_document_storage_dir
    try:
        root = Path(configured).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise OfficialDisclosureDocumentStorageError(
            "Official disclosure storage root is not available."
        ) from error
    return root


def _store_versioned_pdf(
    *,
    root: Path,
    disclosure_id: str,
    downloaded: DownloadedPdf,
) -> tuple[str, str]:
    relative = Path(disclosure_id) / f"{downloaded.sha256}.pdf"
    final_path = (root / relative).resolve()
    if root != final_path and root not in final_path.parents:
        raise OfficialDisclosureDocumentStorageError(
            "Official disclosure storage path escaped the configured root."
        )
    try:
        final_path.parent.mkdir(parents=True, exist_ok=True)
        if final_path.exists() and _file_sha256(final_path) == downloaded.sha256:
            return relative.as_posix(), "unchanged"
    except OSError as error:
        raise OfficialDisclosureDocumentStorageError(
            "Official disclosure storage path is not available."
        ) from error

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=".document-",
            suffix=".tmp",
            dir=final_path.parent,
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(downloaded.content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, final_path)
    except OSError as error:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise OfficialDisclosureDocumentStorageError(
            "Official disclosure PDF could not be stored atomically."
        ) from error
    return relative.as_posix(), "written"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _section_model(
    document_id: PythonUUID,
    extracted: ExtractedDisclosureSection,
) -> OfficialDisclosureSection:
    return OfficialDisclosureSection(
        document_id=document_id,
        section_index=extracted.section_index,
        page_number=extracted.page_number,
        heading=extracted.heading,
        topic=extracted.topic,
        content_text=extracted.content_text,
        content_hash=extracted.content_hash,
    )


def _document_sections(
    document_id: PythonUUID,
    *,
    session: Session,
    limit: int,
) -> list[OfficialDisclosureSection]:
    return (
        session.query(OfficialDisclosureSection)
        .filter(OfficialDisclosureSection.document_id == document_id)
        .order_by(OfficialDisclosureSection.section_index.asc())
        .limit(limit)
        .all()
    )


def _select_document_version(
    versions: list[OfficialDisclosureDocument],
    document_id: str | None,
) -> OfficialDisclosureDocument | None:
    if not versions:
        if document_id:
            raise OfficialDisclosureDocumentNotFoundError("Official disclosure document version not found.")
        return None
    if not document_id:
        return versions[0]
    try:
        parsed_id = PythonUUID(str(document_id))
    except ValueError as error:
        raise ValueError("document_id must be a valid UUID.") from error
    for version in versions:
        if version.id == parsed_id:
            return version
    raise OfficialDisclosureDocumentNotFoundError("Official disclosure document version not found.")


def _ingestion_payload(
    *,
    status: str,
    action: str,
    disclosure: OfficialDisclosure,
    document: OfficialDisclosureDocument,
    sections: list[OfficialDisclosureSection],
    diagnostics: list[dict[str, object]],
) -> dict[str, object]:
    citations = [
        build_official_disclosure_section_citation(section, document, disclosure)
        for section in sections[:10]
    ]
    return {
        "status": status,
        "action": action,
        "disclosure": _serialize_disclosure_identity(disclosure),
        "document": serialize_official_disclosure_document(document),
        "summary": {
            "section_count": len(sections),
            "citable_section_count": len(sections) if document.extraction_status == "extracted" else 0,
        },
        "citations": citations,
        "diagnostics": diagnostics,
        "evidence_boundary": _document_section_boundary(
            content_ingested=document.extraction_status == "extracted"
        ),
    }


def _serialize_disclosure_identity(disclosure: OfficialDisclosure) -> dict[str, object]:
    return {
        "id": str(disclosure.id),
        "source": disclosure.source,
        "source_document_id": disclosure.source_document_id,
        "symbol": disclosure.symbol,
        "title": disclosure.title,
        "published_at": _datetime_to_iso(disclosure.published_at),
        "metadata_citation_id": f"official_disclosure:{disclosure.id}",
    }


def _document_diagnostics(document: OfficialDisclosureDocument) -> list[dict[str, object]]:
    metadata = document.metadata_json if isinstance(document.metadata_json, dict) else {}
    diagnostics = metadata.get("diagnostics")
    if not isinstance(diagnostics, list):
        return []
    return [item for item in diagnostics if isinstance(item, dict)]


def _public_document_metadata(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    return {
        key: item
        for key, item in value.items()
        if key in {"attachment", "content_addressed", "diagnostics"}
    }


def _document_section_boundary(*, content_ingested: bool) -> dict[str, object]:
    return {
        "evidence_scope": "document_section",
        "content_ingested": content_ingested,
        "ocr_used": False,
        "allowed_claims": (
            ["verbatim_extracted_text", "document_context"] if content_ingested else []
        ),
    }


def _datetime_to_iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _ensure_aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _clip(value: str, limit: int) -> str:
    normalized = value.strip()
    return normalized if len(normalized) <= limit else normalized[:limit].rstrip()
