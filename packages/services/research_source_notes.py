from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from sqlalchemy.orm import Session

from packages.domain.models import ResearchSourceNote


RESEARCH_SOURCE_NOTE_CITATION_PREFIX = "research_source_note:"
VALID_REVIEW_STATUSES = {"draft", "reviewed", "archived"}
DEFAULT_NOTE_LIMIT = 50
MAX_EXCERPT_CHARS = 12000
MAX_NOTE_CHARS = 8000
MAX_AI_EXCERPT_CHARS = 420


class ResearchSourceNoteValidationError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


@dataclass(frozen=True)
class ResearchSourceNoteInput:
    title: str
    source_name: str
    source_type: str
    source_url: str | None = None
    symbols: list[str] | None = None
    tags: list[str] | None = None
    published_at: datetime | None = None
    as_of: date | None = None
    retrieved_at: datetime | None = None
    excerpt: str | None = None
    note: str | None = None
    ai_follow_up: str | None = None
    review_status: str = "draft"
    is_citable: bool = False
    metadata: dict[str, object] | None = None


def create_research_source_note(payload: ResearchSourceNoteInput, *, session: Session) -> dict[str, object]:
    normalized = _normalize_payload(payload)
    note = ResearchSourceNote(
        title=normalized.title,
        source_url=normalized.source_url,
        source_name=normalized.source_name,
        source_type=normalized.source_type,
        symbols_json=normalized.symbols or [],
        tags_json=normalized.tags or [],
        published_at=normalized.published_at,
        as_of=normalized.as_of,
        retrieved_at=normalized.retrieved_at or datetime.now(timezone.utc),
        excerpt=normalized.excerpt,
        note=normalized.note,
        ai_follow_up=normalized.ai_follow_up,
        review_status=normalized.review_status,
        is_citable=normalized.is_citable,
        metadata_json=normalized.metadata or {},
    )
    session.add(note)
    session.commit()
    session.refresh(note)
    return serialize_research_source_note(note)


def list_research_source_notes(
    *,
    session: Session,
    limit: int = DEFAULT_NOTE_LIMIT,
    review_status: str | None = None,
    source_type: str | None = None,
    citable_only: bool = False,
) -> dict[str, object]:
    bounded_limit = max(1, min(limit, 200))
    query = session.query(ResearchSourceNote)
    if review_status:
        query = query.filter(ResearchSourceNote.review_status == review_status.strip())
    if source_type:
        query = query.filter(ResearchSourceNote.source_type == source_type.strip())
    if citable_only:
        query = query.filter(ResearchSourceNote.is_citable.is_(True), ResearchSourceNote.review_status == "reviewed")
    items = query.order_by(ResearchSourceNote.created_at.desc()).limit(bounded_limit).all()
    total = query.count()
    return {
        "items": [serialize_research_source_note(item) for item in items],
        "summary": {
            "total": total,
            "returned": len(items),
            "citable": sum(1 for item in items if item.is_citable and item.review_status == "reviewed"),
        },
    }


def list_citable_research_source_note_citations(
    *,
    session: Session,
    symbols: list[str] | None = None,
    limit: int = 6,
) -> list[dict[str, object]]:
    payload = list_research_source_notes(session=session, citable_only=True, limit=limit * 4)
    requested_symbols = {symbol.strip().upper() for symbol in symbols or [] if symbol.strip()}
    citations: list[dict[str, object]] = []
    for item in payload["items"]:
        if not isinstance(item, dict):
            continue
        item_symbols = {str(symbol).upper() for symbol in item.get("symbols", []) if str(symbol).strip()}
        if requested_symbols and item_symbols and not requested_symbols.intersection(item_symbols):
            continue
        citations.append(build_research_source_note_citation(item))
        if len(citations) >= limit:
            break
    return citations


def build_research_source_note_citation(item: dict[str, object]) -> dict[str, object]:
    excerpt = _clip_text(str(item.get("excerpt") or item.get("note") or ""), MAX_AI_EXCERPT_CHARS)
    return {
        "id": f"{RESEARCH_SOURCE_NOTE_CITATION_PREFIX}{item['id']}",
        "label": str(item.get("title") or "Research source note"),
        "source": "research_source_notes",
        "source_type": "research_source_note",
        "url": item.get("source_url"),
        "as_of": item.get("as_of") or item.get("published_at") or item.get("retrieved_at"),
        "provider": item.get("source_name"),
        "retrieved_at": item.get("retrieved_at"),
        "excerpt": excerpt,
        "metadata": {
            "source_name": item.get("source_name"),
            "source_type": item.get("source_type"),
            "symbols": item.get("symbols") or [],
            "tags": item.get("tags") or [],
            "review_status": item.get("review_status"),
        },
    }


def serialize_research_source_note(note: ResearchSourceNote) -> dict[str, object]:
    return {
        "id": str(note.id),
        "title": note.title,
        "source_url": note.source_url,
        "source_name": note.source_name,
        "source_type": note.source_type,
        "symbols": _normalize_list(note.symbols_json),
        "tags": _normalize_list(note.tags_json),
        "published_at": _datetime_to_iso(note.published_at),
        "as_of": note.as_of.isoformat() if note.as_of else None,
        "retrieved_at": note.retrieved_at.isoformat(),
        "excerpt": note.excerpt,
        "note": note.note,
        "ai_follow_up": note.ai_follow_up,
        "review_status": note.review_status,
        "is_citable": note.is_citable,
        "citation_id": f"{RESEARCH_SOURCE_NOTE_CITATION_PREFIX}{note.id}" if note.is_citable else None,
        "metadata": note.metadata_json or {},
        "created_at": note.created_at.isoformat(),
        "updated_at": note.updated_at.isoformat(),
    }


def _normalize_payload(payload: ResearchSourceNoteInput) -> ResearchSourceNoteInput:
    title = _clean_required(payload.title, "title")
    source_name = _clean_required(payload.source_name, "source_name")
    source_type = _clean_required(payload.source_type, "source_type")
    source_url = _clean_optional(payload.source_url)
    excerpt = _clip_text(_clean_optional(payload.excerpt), MAX_EXCERPT_CHARS)
    note = _clip_text(_clean_optional(payload.note), MAX_NOTE_CHARS)
    ai_follow_up = _clip_text(_clean_optional(payload.ai_follow_up), MAX_NOTE_CHARS)
    review_status = _clean_optional(payload.review_status) or "draft"
    symbols = _normalize_symbols(payload.symbols)
    tags = _normalize_list(payload.tags)
    metadata = payload.metadata if isinstance(payload.metadata, dict) else {}

    errors: list[str] = []
    if review_status not in VALID_REVIEW_STATUSES:
        errors.append("review_status must be one of draft, reviewed, or archived.")
    if not source_url and not excerpt:
        errors.append("Either source_url or excerpt is required.")
    if payload.is_citable:
        if review_status != "reviewed":
            errors.append("Citable notes must have review_status=reviewed.")
        if not excerpt:
            errors.append("Citable notes require a reviewed excerpt.")
        if not source_url and not (source_name and (payload.as_of or payload.published_at)):
            errors.append("Citable notes require source_url or source name plus date metadata.")
    if errors:
        raise ResearchSourceNoteValidationError(errors)

    return ResearchSourceNoteInput(
        title=title,
        source_name=source_name,
        source_type=source_type,
        source_url=source_url,
        symbols=symbols,
        tags=tags,
        published_at=payload.published_at,
        as_of=payload.as_of,
        retrieved_at=payload.retrieved_at,
        excerpt=excerpt,
        note=note,
        ai_follow_up=ai_follow_up,
        review_status=review_status,
        is_citable=payload.is_citable,
        metadata=metadata,
    )


def _clean_required(value: str, field_name: str) -> str:
    cleaned = _clean_optional(value)
    if not cleaned:
        raise ResearchSourceNoteValidationError([f"{field_name} is required."])
    return cleaned


def _clean_optional(value: object) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _clip_text(value: str | None, limit: int) -> str | None:
    if value is None or len(value) <= limit:
        return value
    return value[:limit].rstrip()


def _normalize_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized: list[str] = []
    for value in values:
        cleaned = _clean_optional(value)
        if not cleaned:
            continue
        if cleaned not in normalized:
            normalized.append(cleaned)
    return normalized


def _normalize_symbols(values: object) -> list[str]:
    return [symbol.upper() for symbol in _normalize_list(values)]


def _datetime_to_iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
