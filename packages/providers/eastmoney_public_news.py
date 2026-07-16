from __future__ import annotations

import json
import math
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from types import MappingProxyType
from zoneinfo import ZoneInfo

import httpx


EASTMONEY_NEWS_ENDPOINT = "https://search-api-web.eastmoney.com/search/jsonp"
EASTMONEY_NEWS_CALLBACK = "jQuery35101792940631092459_1764599530165"
EASTMONEY_NEWS_CACHE_BUSTER = "1764599530176"
EASTMONEY_NEWS_DEFAULT_MAX_ROWS = 10
EASTMONEY_NEWS_MAX_ROWS = 20
EASTMONEY_NEWS_MAX_RESPONSE_BYTES = 256 * 1024
EASTMONEY_NEWS_DEFAULT_TIMEOUT_SECONDS = 8.0
EASTMONEY_NEWS_MEDIA_TYPE = "text/javascript"
EASTMONEY_NEWS_HEADERS: Mapping[str, str] = MappingProxyType(
    {
        "Accept": "text/javascript, application/javascript, */*;q=0.1",
        "User-Agent": "stock-analysis-platform/0.1",
        "Referer": "https://so.eastmoney.com/",
    }
)

_ARTICLE_CODE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_CN_SYMBOL_PATTERN = re.compile(r"^\d{6}$")
_IGNORED_TAGS = frozenset({"noscript", "script", "style", "template"})
_BLOCK_TAGS = frozenset(
    {
        "address",
        "article",
        "aside",
        "blockquote",
        "br",
        "dd",
        "div",
        "dl",
        "dt",
        "figcaption",
        "figure",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hr",
        "li",
        "main",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "td",
        "th",
        "tr",
        "ul",
    }
)


class EastmoneyPublicNewsProviderError(RuntimeError):
    """Sanitized, stable failure from the public Eastmoney news boundary."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class EastmoneyPublicNewsHttpResponse:
    status_code: int
    headers: Mapping[str, str]
    content: bytes


@dataclass(frozen=True)
class EastmoneyPublicNewsItem:
    symbol: str
    title: str
    url: str
    publisher: str
    summary: str | None
    published_at: datetime


HttpGetter = Callable[..., EastmoneyPublicNewsHttpResponse]


def fetch_eastmoney_public_news(
    symbol: str,
    *,
    timeout: float = EASTMONEY_NEWS_DEFAULT_TIMEOUT_SECONDS,
    max_rows: int = EASTMONEY_NEWS_DEFAULT_MAX_ROWS,
    http_get: HttpGetter | None = None,
) -> tuple[EastmoneyPublicNewsItem, ...]:
    normalized_symbol = _normalize_symbol(symbol)
    normalized_timeout = _normalize_timeout(timeout)
    normalized_max_rows = _normalize_max_rows(max_rows)
    params = _build_request_params(normalized_symbol, max_rows=normalized_max_rows)
    getter = http_get or _default_http_get

    try:
        response = getter(
            EASTMONEY_NEWS_ENDPOINT,
            params=params,
            headers=EASTMONEY_NEWS_HEADERS,
            timeout=normalized_timeout,
            follow_redirects=False,
            trust_env=False,
            max_bytes=EASTMONEY_NEWS_MAX_RESPONSE_BYTES,
        )
    except EastmoneyPublicNewsProviderError:
        raise
    except (TimeoutError, httpx.TimeoutException):
        raise EastmoneyPublicNewsProviderError(
            "EASTMONEY_NEWS_TIMEOUT",
            "Eastmoney public news request timed out.",
        ) from None
    except Exception:
        raise EastmoneyPublicNewsProviderError(
            "EASTMONEY_NEWS_REQUEST_FAILED",
            "Eastmoney public news request failed.",
        ) from None

    return _parse_response(
        response,
        symbol=normalized_symbol,
        max_rows=normalized_max_rows,
    )


def _build_request_params(symbol: str, *, max_rows: int) -> dict[str, str]:
    query = {
        "uid": "",
        "keyword": symbol,
        "type": ["cmsArticleWebOld"],
        "client": "web",
        "clientType": "web",
        "clientVersion": "curr",
        "param": {
            "cmsArticleWebOld": {
                "searchScope": "default",
                "sort": "default",
                "pageIndex": 1,
                "pageSize": max_rows,
                "preTag": "<em>",
                "postTag": "</em>",
            }
        },
    }
    return {
        "cb": EASTMONEY_NEWS_CALLBACK,
        "param": json.dumps(query, ensure_ascii=False, separators=(",", ":")),
        "_": EASTMONEY_NEWS_CACHE_BUSTER,
    }


def _parse_response(
    response: EastmoneyPublicNewsHttpResponse,
    *,
    symbol: str,
    max_rows: int,
) -> tuple[EastmoneyPublicNewsItem, ...]:
    if not isinstance(response, EastmoneyPublicNewsHttpResponse):
        raise EastmoneyPublicNewsProviderError(
            "EASTMONEY_NEWS_RESPONSE_REJECTED",
            "Eastmoney public news response has an unsupported transport shape.",
        )
    if 300 <= response.status_code < 400:
        raise EastmoneyPublicNewsProviderError(
            "EASTMONEY_NEWS_REDIRECT_REJECTED",
            "Eastmoney public news response redirected unexpectedly.",
        )
    if response.status_code != 200:
        raise EastmoneyPublicNewsProviderError(
            "EASTMONEY_NEWS_HTTP_STATUS",
            "Eastmoney public news response returned an unexpected status.",
        )

    headers = {
        str(name).strip().lower(): str(value).strip()
        for name, value in response.headers.items()
    }
    media_type = headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if media_type != EASTMONEY_NEWS_MEDIA_TYPE:
        raise EastmoneyPublicNewsProviderError(
            "EASTMONEY_NEWS_MEDIA_TYPE_REJECTED",
            "Eastmoney public news response returned an unexpected media type.",
        )

    content_length = _optional_content_length(headers.get("content-length"))
    if (
        content_length is not None
        and content_length > EASTMONEY_NEWS_MAX_RESPONSE_BYTES
    ):
        raise EastmoneyPublicNewsProviderError(
            "EASTMONEY_NEWS_RESPONSE_TOO_LARGE",
            "Eastmoney public news response exceeded the fixed size limit.",
        )
    if not isinstance(response.content, bytes):
        raise EastmoneyPublicNewsProviderError(
            "EASTMONEY_NEWS_RESPONSE_REJECTED",
            "Eastmoney public news response content has an unsupported shape.",
        )
    if len(response.content) > EASTMONEY_NEWS_MAX_RESPONSE_BYTES:
        raise EastmoneyPublicNewsProviderError(
            "EASTMONEY_NEWS_RESPONSE_TOO_LARGE",
            "Eastmoney public news response exceeded the fixed size limit.",
        )

    try:
        response_text = response.content.decode("utf-8")
    except UnicodeDecodeError:
        raise EastmoneyPublicNewsProviderError(
            "EASTMONEY_NEWS_ENCODING_REJECTED",
            "Eastmoney public news response was not valid UTF-8.",
        ) from None

    callback_prefix = f"{EASTMONEY_NEWS_CALLBACK}("
    if not response_text.startswith(callback_prefix) or not response_text.endswith(")"):
        raise EastmoneyPublicNewsProviderError(
            "EASTMONEY_NEWS_CALLBACK_REJECTED",
            "Eastmoney public news response did not match the fixed JSONP callback.",
        )
    payload_text = response_text[len(callback_prefix) : -1]
    try:
        payload = json.loads(payload_text, parse_constant=_reject_json_constant)
    except (json.JSONDecodeError, ValueError):
        raise EastmoneyPublicNewsProviderError(
            "EASTMONEY_NEWS_SCHEMA_REJECTED",
            "Eastmoney public news response did not contain valid JSON.",
        ) from None

    rows = _extract_rows(payload, max_rows=max_rows)
    return tuple(_normalize_row(row, symbol=symbol) for row in rows)


def _extract_rows(payload: object, *, max_rows: int) -> list[object]:
    if not isinstance(payload, Mapping):
        raise _schema_error()
    code = payload.get("code")
    if type(code) is not int or code != 0 or payload.get("msg") != "OK":
        raise EastmoneyPublicNewsProviderError(
            "EASTMONEY_NEWS_RESULT_REJECTED",
            "Eastmoney public news response reported an unsuccessful result.",
        )
    result = payload.get("result")
    if not isinstance(result, Mapping):
        raise _schema_error()
    rows = result.get("cmsArticleWebOld")
    if not isinstance(rows, list):
        raise _schema_error()
    if len(rows) > EASTMONEY_NEWS_MAX_ROWS:
        raise EastmoneyPublicNewsProviderError(
            "EASTMONEY_NEWS_ROW_COUNT_REJECTED",
            "Eastmoney public news response exceeded the fixed row limit.",
        )
    return rows[:max_rows]


def _normalize_row(row: object, *, symbol: str) -> EastmoneyPublicNewsItem:
    try:
        if not isinstance(row, Mapping):
            raise ValueError
        article_code = _required_string(row.get("code"))
        if not _ARTICLE_CODE_PATTERN.fullmatch(article_code):
            raise ValueError
        title = _plain_text(_required_string(row.get("title")))
        publisher = _plain_text(_required_string(row.get("mediaName")))
        content = row.get("content")
        if not isinstance(content, str):
            raise ValueError
        summary = _plain_text(content) or None
        published_at = datetime.strptime(
            _required_string(row.get("date")),
            "%Y-%m-%d %H:%M:%S",
        ).replace(tzinfo=ZoneInfo("Asia/Shanghai"))
        if not title or len(title) > 512 or not publisher or len(publisher) > 128:
            raise ValueError
    except (TypeError, ValueError, OverflowError):
        raise EastmoneyPublicNewsProviderError(
            "EASTMONEY_NEWS_ROW_REJECTED",
            "Eastmoney public news response contained an invalid row.",
        ) from None

    return EastmoneyPublicNewsItem(
        symbol=symbol,
        title=title,
        url=f"https://finance.eastmoney.com/a/{article_code}.html",
        publisher=publisher,
        summary=summary[:1000].rstrip() if summary else None,
        published_at=published_at,
    )


class _PlainTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self._parts: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        del attrs
        normalized_tag = tag.lower()
        if normalized_tag in _IGNORED_TAGS:
            self._ignored_depth += 1
        elif self._ignored_depth == 0 and normalized_tag in _BLOCK_TAGS:
            self._parts.append(" ")

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        del attrs
        if self._ignored_depth == 0 and tag.lower() in _BLOCK_TAGS:
            self._parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()
        if normalized_tag in _IGNORED_TAGS:
            self._ignored_depth = max(0, self._ignored_depth - 1)
        elif self._ignored_depth == 0 and normalized_tag in _BLOCK_TAGS:
            self._parts.append(" ")

    def handle_data(self, data: str) -> None:
        if self._ignored_depth == 0:
            self._parts.append(data)

    def normalized_text(self) -> str:
        return " ".join("".join(self._parts).split())


def _plain_text(value: str) -> str:
    parser = _PlainTextParser()
    parser.feed(value)
    parser.close()
    return parser.normalized_text()


def _normalize_symbol(value: str) -> str:
    normalized = str(value).strip().upper()
    for suffix in (".SH", ".SZ", ".BJ"):
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)]
            break
    if not _CN_SYMBOL_PATTERN.fullmatch(normalized):
        raise ValueError("symbol must be a six-digit A-share code.")
    return normalized


def _normalize_timeout(value: float) -> float:
    if isinstance(value, bool):
        raise ValueError("timeout must be a finite positive number.")
    try:
        normalized = float(value)
    except (TypeError, ValueError):
        raise ValueError("timeout must be a finite positive number.") from None
    if not math.isfinite(normalized) or normalized <= 0:
        raise ValueError("timeout must be a finite positive number.")
    return normalized


def _normalize_max_rows(value: int) -> int:
    if type(value) is not int or not 1 <= value <= EASTMONEY_NEWS_MAX_ROWS:
        raise ValueError(
            f"max_rows must be between 1 and {EASTMONEY_NEWS_MAX_ROWS}."
        )
    return value


def _required_string(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError
    normalized = value.strip()
    if not normalized:
        raise ValueError
    return normalized


def _optional_content_length(value: str | None) -> int | None:
    if value is None or not value.isdigit():
        return None
    return int(value)


def _reject_json_constant(_value: str) -> None:
    raise ValueError


def _schema_error() -> EastmoneyPublicNewsProviderError:
    return EastmoneyPublicNewsProviderError(
        "EASTMONEY_NEWS_SCHEMA_REJECTED",
        "Eastmoney public news response did not match the expected schema.",
    )


def _default_http_get(
    url: str,
    *,
    params: Mapping[str, str],
    headers: Mapping[str, str],
    timeout: float,
    follow_redirects: bool,
    trust_env: bool,
    max_bytes: int,
) -> EastmoneyPublicNewsHttpResponse:
    with httpx.Client(
        timeout=timeout,
        follow_redirects=follow_redirects,
        trust_env=trust_env,
        headers=dict(headers),
    ) as client:
        with client.stream("GET", url, params=dict(params)) as response:
            content_length = _optional_content_length(response.headers.get("content-length"))
            if content_length is not None and content_length > max_bytes:
                raise EastmoneyPublicNewsProviderError(
                    "EASTMONEY_NEWS_RESPONSE_TOO_LARGE",
                    "Eastmoney public news response exceeded the fixed size limit.",
                )
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > max_bytes:
                    raise EastmoneyPublicNewsProviderError(
                        "EASTMONEY_NEWS_RESPONSE_TOO_LARGE",
                        "Eastmoney public news response exceeded the fixed size limit.",
                    )
                chunks.append(chunk)
            return EastmoneyPublicNewsHttpResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                content=b"".join(chunks),
            )
