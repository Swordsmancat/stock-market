from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo


CNINFO_SOURCE = "cninfo"
CNINFO_SOURCE_NAME = "CNINFO"
CNINFO_HOSTS = {"cninfo.com.cn", "www.cninfo.com.cn"}
CNINFO_REQUIRED_COLUMNS = {"代码", "简称", "公告标题", "公告时间", "公告链接"}
A_SHARE_SYMBOL_PATTERN = re.compile(r"^\d{6}$")
MAX_CNINFO_DATE_RANGE_DAYS = 366


class CninfoDisclosureProviderError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class OfficialDisclosureCandidate:
    source: str
    source_document_id: str
    symbol: str
    company_name: str | None
    title: str
    category: str | None
    published_at: datetime
    source_url: str
    retrieved_at: datetime
    metadata: dict[str, object]


@dataclass(frozen=True)
class DisclosureCandidateRejection:
    row_index: int
    code: str
    message: str


@dataclass(frozen=True)
class CninfoDisclosureFetchResult:
    items: list[OfficialDisclosureCandidate]
    rejections: list[DisclosureCandidateRejection]


def fetch_cninfo_disclosures(
    *,
    symbol: str,
    start_date: date,
    end_date: date,
    category: str | None = None,
    fetcher: Callable[..., Any] | None = None,
    retrieved_at: datetime | None = None,
) -> CninfoDisclosureFetchResult:
    normalized_symbol = normalize_a_share_symbol(symbol)
    if start_date > end_date:
        raise ValueError("start_date must be earlier than or equal to end_date.")
    if (end_date - start_date).days > MAX_CNINFO_DATE_RANGE_DAYS:
        raise ValueError(f"date range must not exceed {MAX_CNINFO_DATE_RANGE_DAYS} days.")

    provider_fetcher = fetcher or _load_akshare_fetcher()
    try:
        frame = provider_fetcher(
            symbol=normalized_symbol,
            market="沪深京",
            keyword="",
            category=(category or "").strip(),
            start_date=start_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d"),
        )
    except (ValueError, KeyError) as error:
        raise CninfoDisclosureProviderError(
            "CNINFO_REQUEST_REJECTED",
            f"CNINFO rejected the disclosure metadata request: {error.__class__.__name__}.",
        ) from error
    except Exception as error:
        raise CninfoDisclosureProviderError(
            "CNINFO_PROVIDER_ERROR",
            f"CNINFO disclosure metadata could not be loaded: {error.__class__.__name__}.",
        ) from error

    columns = {str(column) for column in getattr(frame, "columns", [])}
    missing_columns = sorted(CNINFO_REQUIRED_COLUMNS - columns)
    if missing_columns:
        raise CninfoDisclosureProviderError(
            "CNINFO_SCHEMA_ERROR",
            "CNINFO disclosure metadata response is missing required fields.",
        )

    effective_retrieved_at = _ensure_aware_datetime(retrieved_at or datetime.now(timezone.utc))
    items: list[OfficialDisclosureCandidate] = []
    rejections: list[DisclosureCandidateRejection] = []
    for row_index, row in enumerate(frame.to_dict(orient="records")):
        try:
            items.append(
                _normalize_candidate(
                    row,
                    requested_symbol=normalized_symbol,
                    category=category,
                    retrieved_at=effective_retrieved_at,
                )
            )
        except ValueError as error:
            rejections.append(
                DisclosureCandidateRejection(
                    row_index=row_index,
                    code="CNINFO_ROW_REJECTED",
                    message=str(error),
                )
            )
    return CninfoDisclosureFetchResult(items=items, rejections=rejections)


def normalize_a_share_symbol(symbol: str) -> str:
    normalized = str(symbol).strip().upper()
    for suffix in (".SH", ".SZ", ".BJ"):
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)]
            break
    if not A_SHARE_SYMBOL_PATTERN.fullmatch(normalized):
        raise ValueError("symbol must be a six-digit A-share code.")
    return normalized


def _load_akshare_fetcher() -> Callable[..., Any]:
    try:
        import akshare as ak  # type: ignore[import-untyped]
    except ImportError as error:
        raise CninfoDisclosureProviderError(
            "CNINFO_PROVIDER_UNAVAILABLE",
            "AkShare is not installed; install the cn-market dependency extra.",
        ) from error
    return ak.stock_zh_a_disclosure_report_cninfo


def _normalize_candidate(
    row: dict[str, object],
    *,
    requested_symbol: str,
    category: str | None,
    retrieved_at: datetime,
) -> OfficialDisclosureCandidate:
    symbol = normalize_a_share_symbol(_required_text(row.get("代码"), "Disclosure symbol is missing."))
    if symbol != requested_symbol:
        raise ValueError("Disclosure symbol does not match the requested symbol.")
    title = _bounded_text(
        _required_text(row.get("公告标题"), "Disclosure title is missing."),
        1024,
        "Disclosure title is too long.",
    )
    source_url = _bounded_text(
        _required_text(row.get("公告链接"), "Disclosure URL is missing."),
        2048,
        "Disclosure URL is too long.",
    )
    parsed_url = urlparse(source_url)
    if (
        parsed_url.scheme not in {"http", "https"}
        or parsed_url.hostname not in CNINFO_HOSTS
        or parsed_url.path != "/new/disclosure/detail"
    ):
        raise ValueError("Disclosure URL is not an allowed CNINFO detail URL.")
    document_ids = parse_qs(parsed_url.query).get("announcementId", [])
    source_document_id = _required_text(
        document_ids[0] if document_ids else None,
        "Disclosure URL is missing announcementId.",
    )
    source_document_id = _bounded_text(
        source_document_id,
        128,
        "Disclosure announcementId is too long.",
    )
    published_at = _parse_published_at(row.get("公告时间"))
    query = parse_qs(parsed_url.query)
    metadata: dict[str, object] = {
        "provider": "akshare",
        "authority": CNINFO_SOURCE_NAME,
        "market": "沪深京",
        "org_id": _optional_text((query.get("orgId") or [""])[0]),
        "evidence_scope": "metadata_only",
        "content_ingested": False,
    }
    return OfficialDisclosureCandidate(
        source=CNINFO_SOURCE,
        source_document_id=source_document_id,
        symbol=symbol,
        company_name=_bounded_optional_text(
            row.get("简称"),
            256,
            "Disclosure company name is too long.",
        ),
        title=title,
        category=_bounded_optional_text(
            category,
            128,
            "Disclosure category is too long.",
        ),
        published_at=published_at,
        source_url=source_url,
        retrieved_at=retrieved_at,
        metadata=metadata,
    )


def _parse_published_at(value: object) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = _required_text(value, "Disclosure publication time is missing.")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as error:
            raise ValueError("Disclosure publication time is invalid.") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
    return parsed.astimezone(timezone.utc)


def _ensure_aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _required_text(value: object, message: str) -> str:
    text = _optional_text(value)
    if not text:
        raise ValueError(message)
    return text


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in {"nan", "nat", "<na>"}:
        return None
    return text or None


def _bounded_text(value: str, limit: int, message: str) -> str:
    if len(value) > limit:
        raise ValueError(message)
    return value


def _bounded_optional_text(value: object, limit: int, message: str) -> str | None:
    text = _optional_text(value)
    return _bounded_text(text, limit, message) if text else None
