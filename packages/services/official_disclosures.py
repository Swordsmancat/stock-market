from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from packages.domain.models import OfficialDisclosure
from packages.providers.cninfo_disclosure_provider import (
    CNINFO_SOURCE,
    MAX_CNINFO_DATE_RANGE_DAYS,
    CninfoDisclosureFetchResult,
    OfficialDisclosureCandidate,
    fetch_cninfo_disclosures,
    normalize_a_share_symbol,
)


OFFICIAL_DISCLOSURE_CITATION_PREFIX = "official_disclosure:"
DEFAULT_DISCLOSURE_LIMIT = 20
MAX_DISCLOSURE_LIMIT = 200
MAX_CITATION_TITLE_CHARS = 320


class OfficialDisclosurePersistenceError(RuntimeError):
    pass


@dataclass(frozen=True)
class OfficialDisclosureRefreshInput:
    symbol: str
    start_date: date
    end_date: date
    category: str | None = None


def refresh_official_disclosures(
    payload: OfficialDisclosureRefreshInput,
    *,
    session: Session,
    provider_fetcher=fetch_cninfo_disclosures,
) -> dict[str, object]:
    symbol = normalize_a_share_symbol(payload.symbol)
    if payload.start_date > payload.end_date:
        raise ValueError("start_date must be earlier than or equal to end_date.")
    if (payload.end_date - payload.start_date).days > MAX_CNINFO_DATE_RANGE_DAYS:
        raise ValueError(f"date range must not exceed {MAX_CNINFO_DATE_RANGE_DAYS} days.")

    result: CninfoDisclosureFetchResult = provider_fetcher(
        symbol=symbol,
        start_date=payload.start_date,
        end_date=payload.end_date,
        category=payload.category,
    )
    counts = {
        "received": len(result.items) + len(result.rejections),
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "rejected": len(result.rejections),
    }
    persisted: list[OfficialDisclosure] = []
    try:
        for candidate in result.items:
            disclosure, action = _upsert_candidate(candidate, session=session)
            counts[action] += 1
            persisted.append(disclosure)
        session.commit()
    except SQLAlchemyError as error:
        session.rollback()
        raise OfficialDisclosurePersistenceError(
            "Official disclosure metadata could not be persisted."
        ) from error

    diagnostics: list[dict[str, object]] = [
        {
            "source": CNINFO_SOURCE,
            "status": "ok" if result.items else "no_data",
            "severity": "info",
            "code": "CNINFO_METADATA_REFRESHED" if result.items else "CNINFO_METADATA_EMPTY",
            "message": (
                f"CNINFO returned {len(result.items)} valid disclosure metadata records."
                if result.items
                else "CNINFO returned no valid disclosure metadata records for the requested range."
            ),
        }
    ]
    diagnostics.extend(
        {
            "source": CNINFO_SOURCE,
            "status": "rejected",
            "severity": "warning",
            "code": rejection.code,
            "message": rejection.message,
            "details": {"row_index": rejection.row_index},
        }
        for rejection in result.rejections
    )
    return {
        "status": "ok" if result.items else "no_data",
        "source": CNINFO_SOURCE,
        "symbol": symbol,
        "date_range": {
            "start": payload.start_date.isoformat(),
            "end": payload.end_date.isoformat(),
        },
        "category": _clean(payload.category),
        "counts": counts,
        "items": [serialize_official_disclosure(item) for item in persisted],
        "diagnostics": diagnostics,
        "evidence_boundary": _metadata_only_boundary(),
    }


def list_official_disclosures(
    *,
    session: Session,
    symbol: str,
    limit: int = DEFAULT_DISCLOSURE_LIMIT,
) -> dict[str, object]:
    normalized_symbol = normalize_a_share_symbol(symbol)
    bounded_limit = max(1, min(limit, MAX_DISCLOSURE_LIMIT))
    query = session.query(OfficialDisclosure).filter(OfficialDisclosure.symbol == normalized_symbol)
    total = query.count()
    items = (
        query.order_by(OfficialDisclosure.published_at.desc(), OfficialDisclosure.id.desc())
        .limit(bounded_limit)
        .all()
    )
    return {
        "items": [serialize_official_disclosure(item) for item in items],
        "summary": {"total": total, "returned": len(items), "symbol": normalized_symbol},
        "evidence_boundary": _metadata_only_boundary(),
    }


def list_citable_official_disclosure_citations(
    *,
    session: Session,
    symbols: list[str],
    limit: int = 3,
) -> list[dict[str, object]]:
    normalized_symbols = sorted({normalize_a_share_symbol(symbol) for symbol in symbols})
    if not normalized_symbols:
        return []
    rows = (
        session.query(OfficialDisclosure)
        .filter(OfficialDisclosure.symbol.in_(normalized_symbols))
        .order_by(OfficialDisclosure.published_at.desc(), OfficialDisclosure.id.desc())
        .limit(max(1, min(limit, 20)))
        .all()
    )
    return [build_official_disclosure_citation(row) for row in rows]


def build_official_disclosure_citation(disclosure: OfficialDisclosure) -> dict[str, object]:
    title = _clip(disclosure.title, MAX_CITATION_TITLE_CHARS)
    boundary = _metadata_only_boundary()
    return {
        "id": f"{OFFICIAL_DISCLOSURE_CITATION_PREFIX}{disclosure.id}",
        "label": title,
        "source": "official_disclosures",
        "source_type": "official_disclosure",
        "url": disclosure.source_url,
        "as_of": _datetime_to_iso(disclosure.published_at),
        "provider": disclosure.source,
        "retrieved_at": _datetime_to_iso(disclosure.retrieved_at),
        "excerpt": (
            f"CNINFO published disclosure metadata for {disclosure.symbol}: "
            f"{title}. Document body has not been ingested."
        ),
        "metadata": {
            "symbol": disclosure.symbol,
            "company_name": disclosure.company_name,
            "category": disclosure.category,
            "source_document_id": disclosure.source_document_id,
            **boundary,
        },
    }


def serialize_official_disclosure(disclosure: OfficialDisclosure) -> dict[str, object]:
    return {
        "id": str(disclosure.id),
        "citation_id": f"{OFFICIAL_DISCLOSURE_CITATION_PREFIX}{disclosure.id}",
        "source": disclosure.source,
        "source_document_id": disclosure.source_document_id,
        "symbol": disclosure.symbol,
        "company_name": disclosure.company_name,
        "title": disclosure.title,
        "category": disclosure.category,
        "published_at": _datetime_to_iso(disclosure.published_at),
        "source_url": disclosure.source_url,
        "retrieved_at": _datetime_to_iso(disclosure.retrieved_at),
        "metadata": disclosure.metadata_json or {},
        "evidence_boundary": _metadata_only_boundary(),
        "created_at": _datetime_to_iso(disclosure.created_at),
        "updated_at": _datetime_to_iso(disclosure.updated_at),
    }


def _upsert_candidate(
    candidate: OfficialDisclosureCandidate,
    *,
    session: Session,
) -> tuple[OfficialDisclosure, str]:
    dedupe_hash = _candidate_hash(candidate)
    existing = (
        session.query(OfficialDisclosure)
        .filter(
            OfficialDisclosure.source == candidate.source,
            OfficialDisclosure.source_document_id == candidate.source_document_id,
        )
        .one_or_none()
    )
    if existing is None:
        disclosure = OfficialDisclosure(
            source=candidate.source,
            source_document_id=candidate.source_document_id,
            symbol=candidate.symbol,
            company_name=candidate.company_name,
            title=candidate.title,
            category=candidate.category,
            published_at=candidate.published_at,
            source_url=candidate.source_url,
            retrieved_at=candidate.retrieved_at,
            dedupe_hash=dedupe_hash,
            metadata_json=candidate.metadata,
        )
        session.add(disclosure)
        session.flush()
        return disclosure, "created"
    if existing.dedupe_hash == dedupe_hash:
        return existing, "unchanged"
    existing.symbol = candidate.symbol
    existing.company_name = candidate.company_name
    existing.title = candidate.title
    existing.category = candidate.category
    existing.published_at = candidate.published_at
    existing.source_url = candidate.source_url
    existing.retrieved_at = candidate.retrieved_at
    existing.dedupe_hash = dedupe_hash
    existing.metadata_json = candidate.metadata
    existing.updated_at = datetime.now(timezone.utc)
    session.flush()
    return existing, "updated"


def _candidate_hash(candidate: OfficialDisclosureCandidate) -> str:
    payload = {
        "source": candidate.source,
        "source_document_id": candidate.source_document_id,
        "symbol": candidate.symbol,
        "company_name": candidate.company_name,
        "title": candidate.title,
        "category": candidate.category,
        "published_at": candidate.published_at.isoformat(),
        "source_url": candidate.source_url,
        "metadata": candidate.metadata,
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _metadata_only_boundary() -> dict[str, object]:
    return {
        "evidence_scope": "metadata_only",
        "content_ingested": False,
        "allowed_claims": ["document_identity", "title", "publication_time", "category"],
    }


def _datetime_to_iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _clean(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _clip(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[:limit].rstrip()
