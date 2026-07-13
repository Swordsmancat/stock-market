from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import httpx

from packages.providers.cninfo_disclosure_provider import normalize_a_share_symbol


CNINFO_QUERY_URL = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
CNINFO_STATIC_HOST = "static.cninfo.com.cn"
CNINFO_STATIC_PREFIX = "/finalpage/"
CNINFO_PAGE_SIZE = 30
MAX_CNINFO_QUERY_PAGES = 20
MAX_PDF_BYTES = 25 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 30.0
SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
PDF_MEDIA_TYPES = {"application/pdf", "application/x-pdf"}


class CninfoDocumentProviderError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class CninfoAttachment:
    announcement_id: str
    url: str
    media_type: str
    provider_size: int | None
    source_path: str
    metadata: dict[str, object]


@dataclass(frozen=True)
class DocumentHttpResponse:
    status_code: int
    url: str
    headers: Mapping[str, str]
    content: bytes


@dataclass(frozen=True)
class DownloadedPdf:
    url: str
    media_type: str
    content: bytes
    sha256: str
    byte_size: int
    last_modified: str | None
    retrieved_at: datetime


def discover_cninfo_attachment(
    *,
    symbol: str,
    org_id: str,
    announcement_id: str,
    published_at: datetime,
    post_json: Callable[..., object] | None = None,
) -> CninfoAttachment:
    normalized_symbol = normalize_a_share_symbol(symbol)
    normalized_org_id = _safe_id(org_id, "CNINFO org ID is invalid.")
    normalized_announcement_id = _safe_id(
        announcement_id,
        "CNINFO announcement ID is invalid.",
    )
    local_date = _ensure_aware_datetime(published_at).astimezone(ZoneInfo("Asia/Shanghai")).date()
    start_date = local_date - timedelta(days=2)
    end_date = local_date + timedelta(days=2)
    request_json = post_json or _default_post_json

    payload = {
        "pageNum": "1",
        "pageSize": str(CNINFO_PAGE_SIZE),
        "column": "szse",
        "tabName": "fulltext",
        "plate": "",
        "stock": f"{normalized_symbol},{normalized_org_id}",
        "searchkey": "",
        "secid": "",
        "category": "",
        "trade": "",
        "seDate": f"{start_date.isoformat()}~{end_date.isoformat()}",
        "sortName": "",
        "sortType": "",
        "isHLtitle": "false",
    }

    total_pages = 1
    for page_number in range(1, MAX_CNINFO_QUERY_PAGES + 1):
        if page_number > total_pages:
            break
        payload["pageNum"] = str(page_number)
        response_payload = _call_post_json(request_json, payload)
        announcements = response_payload.get("announcements")
        if not isinstance(announcements, list):
            raise CninfoDocumentProviderError(
                "CNINFO_DOCUMENT_SCHEMA_ERROR",
                "CNINFO attachment response is missing the announcements list.",
            )
        total_pages = min(
            MAX_CNINFO_QUERY_PAGES,
            max(1, math.ceil(_safe_nonnegative_int(response_payload.get("totalAnnouncement")) / CNINFO_PAGE_SIZE)),
        )
        for item in announcements:
            if not isinstance(item, dict):
                continue
            if str(item.get("announcementId") or "").strip() != normalized_announcement_id:
                continue
            if str(item.get("secCode") or "").strip() != normalized_symbol:
                raise CninfoDocumentProviderError(
                    "CNINFO_DOCUMENT_IDENTITY_MISMATCH",
                    "CNINFO attachment symbol does not match the persisted disclosure.",
                )
            return _normalize_attachment(item, normalized_announcement_id)

    raise CninfoDocumentProviderError(
        "CNINFO_DOCUMENT_NOT_FOUND",
        "CNINFO did not return an attachment for the persisted announcement ID.",
    )


def download_cninfo_pdf(
    attachment_url: str,
    *,
    http_get: Callable[..., DocumentHttpResponse] | None = None,
    max_bytes: int = MAX_PDF_BYTES,
    retrieved_at: datetime | None = None,
) -> DownloadedPdf:
    normalized_url = validate_cninfo_attachment_url(attachment_url)
    getter = http_get or _default_http_get
    try:
        response = getter(normalized_url, max_bytes=max_bytes)
    except CninfoDocumentProviderError:
        raise
    except Exception as error:
        raise CninfoDocumentProviderError(
            "CNINFO_DOCUMENT_DOWNLOAD_ERROR",
            f"CNINFO document download failed: {error.__class__.__name__}.",
        ) from error

    if 300 <= response.status_code < 400:
        raise CninfoDocumentProviderError(
            "CNINFO_DOCUMENT_REDIRECT_REJECTED",
            "CNINFO document download returned a redirect.",
        )
    if response.status_code != 200:
        raise CninfoDocumentProviderError(
            "CNINFO_DOCUMENT_HTTP_ERROR",
            f"CNINFO document download returned HTTP {response.status_code}.",
        )
    final_url = validate_cninfo_attachment_url(response.url)
    if final_url != normalized_url:
        raise CninfoDocumentProviderError(
            "CNINFO_DOCUMENT_URL_MISMATCH",
            "CNINFO document response URL does not match the requested attachment.",
        )
    headers = {str(key).lower(): str(value).strip() for key, value in response.headers.items()}
    media_type = headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if media_type not in PDF_MEDIA_TYPES:
        raise CninfoDocumentProviderError(
            "CNINFO_DOCUMENT_MEDIA_TYPE_REJECTED",
            "CNINFO document response is not an allowed PDF media type.",
        )
    content_length = _optional_nonnegative_int(headers.get("content-length"))
    if content_length is not None and content_length > max_bytes:
        raise CninfoDocumentProviderError(
            "CNINFO_DOCUMENT_TOO_LARGE",
            f"CNINFO document exceeds the {max_bytes}-byte download limit.",
        )
    content = bytes(response.content)
    if len(content) > max_bytes:
        raise CninfoDocumentProviderError(
            "CNINFO_DOCUMENT_TOO_LARGE",
            f"CNINFO document exceeds the {max_bytes}-byte download limit.",
        )
    if not content.startswith(b"%PDF-"):
        raise CninfoDocumentProviderError(
            "CNINFO_DOCUMENT_SIGNATURE_REJECTED",
            "CNINFO document does not have a valid PDF signature.",
        )
    effective_retrieved_at = _ensure_aware_datetime(retrieved_at or datetime.now(timezone.utc))
    return DownloadedPdf(
        url=final_url,
        media_type=media_type,
        content=content,
        sha256=hashlib.sha256(content).hexdigest(),
        byte_size=len(content),
        last_modified=_optional_text(headers.get("last-modified")),
        retrieved_at=effective_retrieved_at,
    )


def validate_cninfo_attachment_url(value: str) -> str:
    normalized = str(value).strip()
    parsed = urlparse(normalized)
    path = parsed.path
    try:
        port = parsed.port
    except ValueError as error:
        raise CninfoDocumentProviderError(
            "CNINFO_DOCUMENT_URL_REJECTED",
            "CNINFO attachment URL is outside the allowed official PDF boundary.",
        ) from error
    if (
        parsed.scheme != "https"
        or parsed.hostname != CNINFO_STATIC_HOST
        or port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or not path.startswith(CNINFO_STATIC_PREFIX)
        or not path.lower().endswith(".pdf")
        or ".." in PurePosixPath(path).parts
    ):
        raise CninfoDocumentProviderError(
            "CNINFO_DOCUMENT_URL_REJECTED",
            "CNINFO attachment URL is outside the allowed official PDF boundary.",
        )
    return normalized


def _normalize_attachment(item: dict[str, object], announcement_id: str) -> CninfoAttachment:
    adjunct_type = _required_text(item.get("adjunctType"), "CNINFO attachment type is missing.")
    if adjunct_type.upper() != "PDF":
        raise CninfoDocumentProviderError(
            "CNINFO_DOCUMENT_TYPE_REJECTED",
            "CNINFO attachment is not a PDF.",
        )
    source_path = _required_text(item.get("adjunctUrl"), "CNINFO attachment path is missing.")
    if (
        "://" in source_path
        or source_path.startswith("//")
        or "\\" in source_path
        or ".." in PurePosixPath(source_path).parts
    ):
        raise CninfoDocumentProviderError(
            "CNINFO_DOCUMENT_PATH_REJECTED",
            "CNINFO attachment path is outside the allowed relative path boundary.",
        )
    normalized_path = f"/{source_path.lstrip('/')}"
    if PurePosixPath(normalized_path).stem != announcement_id:
        raise CninfoDocumentProviderError(
            "CNINFO_DOCUMENT_IDENTITY_MISMATCH",
            "CNINFO attachment filename does not match the announcement ID.",
        )
    url = validate_cninfo_attachment_url(f"https://{CNINFO_STATIC_HOST}{normalized_path}")
    return CninfoAttachment(
        announcement_id=announcement_id,
        url=url,
        media_type="application/pdf",
        provider_size=_optional_nonnegative_int(item.get("adjunctSize")),
        source_path=source_path,
        metadata={
            "provider": "cninfo",
            "adjunct_type": adjunct_type,
            "announcement_type": _optional_text(item.get("announcementTypeName")),
        },
    )


def _call_post_json(
    post_json: Callable[..., object],
    payload: dict[str, str],
) -> dict[str, object]:
    try:
        value = post_json(
            CNINFO_QUERY_URL,
            data=dict(payload),
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
    except CninfoDocumentProviderError:
        raise
    except Exception as error:
        raise CninfoDocumentProviderError(
            "CNINFO_DOCUMENT_PROVIDER_ERROR",
            f"CNINFO attachment discovery failed: {error.__class__.__name__}.",
        ) from error
    if not isinstance(value, dict):
        raise CninfoDocumentProviderError(
            "CNINFO_DOCUMENT_SCHEMA_ERROR",
            "CNINFO attachment response is not a JSON object.",
        )
    return value


def _default_post_json(url: str, *, data: dict[str, str], timeout: float) -> object:
    response = httpx.post(
        url,
        data=data,
        timeout=timeout,
        follow_redirects=False,
        headers={
            "User-Agent": "stock-analysis-platform/0.1",
            "Referer": "https://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search",
        },
    )
    if response.status_code != 200:
        raise CninfoDocumentProviderError(
            "CNINFO_DOCUMENT_HTTP_ERROR",
            f"CNINFO attachment discovery returned HTTP {response.status_code}.",
        )
    try:
        return response.json()
    except ValueError as error:
        raise CninfoDocumentProviderError(
            "CNINFO_DOCUMENT_SCHEMA_ERROR",
            "CNINFO attachment discovery did not return valid JSON.",
        ) from error


def _default_http_get(url: str, *, max_bytes: int) -> DocumentHttpResponse:
    try:
        with httpx.stream(
            "GET",
            url,
            timeout=DEFAULT_TIMEOUT_SECONDS,
            follow_redirects=False,
            headers={
                "User-Agent": "stock-analysis-platform/0.1",
                "Referer": "https://www.cninfo.com.cn/",
            },
        ) as response:
            content_length = _optional_nonnegative_int(response.headers.get("content-length"))
            if content_length is not None and content_length > max_bytes:
                raise CninfoDocumentProviderError(
                    "CNINFO_DOCUMENT_TOO_LARGE",
                    f"CNINFO document exceeds the {max_bytes}-byte download limit.",
                )
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > max_bytes:
                    raise CninfoDocumentProviderError(
                        "CNINFO_DOCUMENT_TOO_LARGE",
                        f"CNINFO document exceeds the {max_bytes}-byte download limit.",
                    )
                chunks.append(chunk)
            return DocumentHttpResponse(
                status_code=response.status_code,
                url=str(response.url),
                headers=dict(response.headers),
                content=b"".join(chunks),
            )
    except CninfoDocumentProviderError:
        raise
    except Exception as error:
        raise CninfoDocumentProviderError(
            "CNINFO_DOCUMENT_DOWNLOAD_ERROR",
            f"CNINFO document download failed: {error.__class__.__name__}.",
        ) from error


def _safe_id(value: object, message: str) -> str:
    normalized = _required_text(value, message)
    if not SAFE_ID_PATTERN.fullmatch(normalized):
        raise ValueError(message)
    return normalized


def _required_text(value: object, message: str) -> str:
    normalized = _optional_text(value)
    if not normalized:
        raise CninfoDocumentProviderError("CNINFO_DOCUMENT_SCHEMA_ERROR", message)
    return normalized


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _safe_nonnegative_int(value: object) -> int:
    parsed = _optional_nonnegative_int(value)
    return parsed or 0


def _optional_nonnegative_int(value: object) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        parsed = int(float(str(value)))
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _ensure_aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
