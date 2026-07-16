from __future__ import annotations

import json
import math
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timezone
from types import MappingProxyType
from typing import TypedDict

import httpx


EASTMONEY_FINANCIAL_ENDPOINT = (
    "https://datacenter.eastmoney.com/securities/api/data/get"
)
EASTMONEY_COMPANY_ENDPOINT = (
    "https://emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/PageAjax"
)
EASTMONEY_FUNDAMENTALS_DEFAULT_TIMEOUT_SECONDS = 8.0
EASTMONEY_FINANCIAL_MAX_RESPONSE_BYTES = 256 * 1024
EASTMONEY_COMPANY_MAX_RESPONSE_BYTES = 256 * 1024
EASTMONEY_FINANCIAL_MAX_ROWS = 20
EASTMONEY_COMPANY_PROFILE_MAX_CHARS = 2000
EASTMONEY_FUNDAMENTALS_HEADERS: Mapping[str, str] = MappingProxyType(
    {
        "Accept": "application/json, text/plain, */*;q=0.1",
        "User-Agent": "stock-analysis-platform/0.1",
        "Referer": "https://emweb.securities.eastmoney.com/",
    }
)

_CN_SYMBOL_PATTERN = re.compile(r"^\d{6}$")
_FINANCIAL_MEDIA_TYPES = frozenset({"application/json", "text/plain"})
_COMPANY_MEDIA_TYPES = frozenset({"application/json", "text/json"})


class EastmoneyPublicFundamentalsProviderError(RuntimeError):
    """Sanitized failure from the public Eastmoney fundamentals boundary."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class EastmoneyPublicFundamentalsHttpResponse:
    status_code: int
    headers: Mapping[str, str]
    content: bytes


@dataclass(frozen=True)
class EastmoneyPublicCompany:
    name: str | None
    industry: str | None
    business_scope: str | None
    profile: str | None


@dataclass(frozen=True)
class EastmoneyPublicFundamentalsSnapshot:
    symbol: str
    as_of: date
    currency: str
    pe_ratio: None
    revenue_growth: float | None
    net_margin: float | None
    debt_to_assets: float | None
    company: EastmoneyPublicCompany | None
    status: str
    provider: str
    upstream_sources: tuple[str, ...]
    retrieved_at: datetime
    diagnostics: tuple[str, ...]


HttpGetter = Callable[..., EastmoneyPublicFundamentalsHttpResponse]


class _NormalizedFinancialRow(TypedDict):
    as_of: date
    currency: str
    revenue_growth: float | None
    net_margin: float | None
    debt_to_assets: float | None


def fetch_eastmoney_public_fundamentals(
    symbol: str,
    *,
    as_of: date,
    timeout: float = EASTMONEY_FUNDAMENTALS_DEFAULT_TIMEOUT_SECONDS,
    http_get: HttpGetter | None = None,
) -> EastmoneyPublicFundamentalsSnapshot | None:
    normalized_symbol = _normalize_symbol(symbol)
    normalized_as_of = _normalize_as_of(as_of)
    normalized_timeout = _normalize_timeout(timeout)
    exchange = _exchange_for_symbol(normalized_symbol)
    getter = http_get or _default_http_get

    financial_response = _request(
        getter,
        EASTMONEY_FINANCIAL_ENDPOINT,
        params=_financial_params(normalized_symbol, exchange),
        timeout=normalized_timeout,
        max_bytes=EASTMONEY_FINANCIAL_MAX_RESPONSE_BYTES,
    )
    financial_payload = _parse_json_response(
        financial_response,
        allowed_media_types=_FINANCIAL_MEDIA_TYPES,
        max_bytes=EASTMONEY_FINANCIAL_MAX_RESPONSE_BYTES,
    )
    selected = _select_financial_row(
        financial_payload,
        symbol=normalized_symbol,
        exchange=exchange,
        as_of=normalized_as_of,
    )
    if selected is None:
        return None

    company: EastmoneyPublicCompany | None = None
    diagnostics: tuple[str, ...] = ()
    try:
        company_response = _request(
            getter,
            EASTMONEY_COMPANY_ENDPOINT,
            params={"code": f"{exchange}{normalized_symbol}"},
            timeout=normalized_timeout,
            max_bytes=EASTMONEY_COMPANY_MAX_RESPONSE_BYTES,
        )
        company_payload = _parse_json_response(
            company_response,
            allowed_media_types=_COMPANY_MEDIA_TYPES,
            max_bytes=EASTMONEY_COMPANY_MAX_RESPONSE_BYTES,
        )
        company = _parse_company(
            company_payload,
            symbol=normalized_symbol,
            exchange=exchange,
        )
    except EastmoneyPublicFundamentalsProviderError as error:
        diagnostics = (error.code,)

    return EastmoneyPublicFundamentalsSnapshot(
        symbol=normalized_symbol,
        as_of=selected["as_of"],
        currency=selected["currency"],
        pe_ratio=None,
        revenue_growth=selected["revenue_growth"],
        net_margin=selected["net_margin"],
        debt_to_assets=selected["debt_to_assets"],
        company=company,
        status="degraded" if diagnostics else "ok",
        provider="eastmoney_public",
        upstream_sources=(
            "eastmoney.RPT_F10_FINANCE_MAINFINADATA",
            "eastmoney.PC_HSF10.CompanySurvey.PageAjax",
        ),
        retrieved_at=datetime.now(timezone.utc),
        diagnostics=diagnostics,
    )


def _financial_params(symbol: str, exchange: str) -> dict[str, str]:
    return {
        "type": "RPT_F10_FINANCE_MAINFINADATA",
        "sty": "APP_F10_MAINFINADATA",
        "quoteColumns": "",
        "filter": f'(SECUCODE="{symbol}.{exchange}")',
        "p": "1",
        "ps": "20",
        "sr": "-1",
        "st": "REPORT_DATE",
        "source": "HSF10",
        "client": "PC",
    }


def _request(
    getter: HttpGetter,
    url: str,
    *,
    params: Mapping[str, str],
    timeout: float,
    max_bytes: int,
) -> EastmoneyPublicFundamentalsHttpResponse:
    try:
        return getter(
            url,
            params=params,
            headers=EASTMONEY_FUNDAMENTALS_HEADERS,
            timeout=timeout,
            follow_redirects=False,
            trust_env=False,
            max_bytes=max_bytes,
        )
    except EastmoneyPublicFundamentalsProviderError:
        raise
    except (TimeoutError, httpx.TimeoutException):
        raise EastmoneyPublicFundamentalsProviderError(
            "EASTMONEY_FUNDAMENTALS_TIMEOUT",
            "Eastmoney public fundamentals request timed out.",
        ) from None
    except Exception:
        raise EastmoneyPublicFundamentalsProviderError(
            "EASTMONEY_FUNDAMENTALS_REQUEST_FAILED",
            "Eastmoney public fundamentals request failed.",
        ) from None


def _parse_json_response(
    response: EastmoneyPublicFundamentalsHttpResponse,
    *,
    allowed_media_types: frozenset[str],
    max_bytes: int,
) -> object:
    if not isinstance(response, EastmoneyPublicFundamentalsHttpResponse):
        raise _response_error()
    if response.status_code != 200:
        raise _response_error()
    headers = {
        str(name).strip().lower(): str(value).strip()
        for name, value in response.headers.items()
    }
    media_type = headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if media_type not in allowed_media_types:
        raise _response_error()
    content_length = _optional_content_length(headers.get("content-length"))
    if content_length is not None and content_length > max_bytes:
        raise EastmoneyPublicFundamentalsProviderError(
            "EASTMONEY_FUNDAMENTALS_RESPONSE_TOO_LARGE",
            "Eastmoney public fundamentals response exceeded the size limit.",
        )
    if not isinstance(response.content, bytes):
        raise _response_error()
    if len(response.content) > max_bytes:
        raise EastmoneyPublicFundamentalsProviderError(
            "EASTMONEY_FUNDAMENTALS_RESPONSE_TOO_LARGE",
            "Eastmoney public fundamentals response exceeded the size limit.",
        )
    try:
        return json.loads(
            response.content.decode("utf-8"),
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        raise _schema_error() from None


def _select_financial_row(
    payload: object,
    *,
    symbol: str,
    exchange: str,
    as_of: date,
) -> _NormalizedFinancialRow | None:
    if not isinstance(payload, Mapping) or payload.get("success") is not True:
        raise _schema_error()
    result = payload.get("result")
    if not isinstance(result, Mapping):
        raise _schema_error()
    rows = result.get("data")
    if not isinstance(rows, list):
        raise _schema_error()
    if len(rows) > EASTMONEY_FINANCIAL_MAX_ROWS:
        raise _schema_error()

    normalized_rows = [
        _normalize_financial_row(row, symbol=symbol, exchange=exchange)
        for row in rows
    ]
    eligible = [row for row in normalized_rows if row["as_of"] <= as_of]
    if not eligible:
        return None
    return max(eligible, key=lambda row: row["as_of"])


def _normalize_financial_row(
    row: object,
    *,
    symbol: str,
    exchange: str,
) -> _NormalizedFinancialRow:
    if not isinstance(row, Mapping):
        raise _schema_error()
    if row.get("SECURITY_CODE") != symbol or row.get("SECUCODE") != f"{symbol}.{exchange}":
        raise EastmoneyPublicFundamentalsProviderError(
            "EASTMONEY_FUNDAMENTALS_IDENTITY_REJECTED",
            "Eastmoney public fundamentals response identity did not match.",
        )
    try:
        report_date = datetime.strptime(
            _required_string(row.get("REPORT_DATE"))[:10],
            "%Y-%m-%d",
        ).date()
        currency = _required_string(row.get("CURRENCY"))
        revenue_growth = _optional_ratio(row.get("TOTALOPERATEREVETZ"))
        net_margin = _optional_ratio(row.get("XSJLL"))
        debt_to_assets = _optional_ratio(row.get("ZCFZL"))
    except (TypeError, ValueError, OverflowError):
        raise _schema_error() from None
    return {
        "as_of": report_date,
        "currency": currency,
        "revenue_growth": revenue_growth,
        "net_margin": net_margin,
        "debt_to_assets": debt_to_assets,
    }


def _parse_company(
    payload: object,
    *,
    symbol: str,
    exchange: str,
) -> EastmoneyPublicCompany | None:
    if not isinstance(payload, Mapping):
        raise _schema_error()
    rows = payload.get("jbzl")
    if not isinstance(rows, list) or len(rows) > 1:
        raise _schema_error()
    if not rows:
        return None
    row = rows[0]
    if not isinstance(row, Mapping):
        raise _schema_error()
    if row.get("SECURITY_CODE") != symbol or row.get("SECUCODE") != f"{symbol}.{exchange}":
        raise EastmoneyPublicFundamentalsProviderError(
            "EASTMONEY_FUNDAMENTALS_IDENTITY_REJECTED",
            "Eastmoney public company identity did not match.",
        )
    return EastmoneyPublicCompany(
        name=_optional_text(row.get("ORG_NAME"), max_chars=256),
        industry=_optional_text(row.get("INDUSTRYCSRC1"), max_chars=256),
        business_scope=_optional_text(row.get("BUSINESS_SCOPE"), max_chars=2000),
        profile=_optional_text(
            row.get("ORG_PROFILE"),
            max_chars=EASTMONEY_COMPANY_PROFILE_MAX_CHARS,
        ),
    )


def _normalize_symbol(value: str) -> str:
    normalized = str(value).strip().upper()
    for suffix in (".SH", ".SZ", ".BJ"):
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)]
            break
    if not _CN_SYMBOL_PATTERN.fullmatch(normalized):
        raise ValueError("symbol must be a six-digit A-share code.")
    return normalized


def _exchange_for_symbol(symbol: str) -> str:
    if symbol.startswith(("4", "8")):
        return "BJ"
    if symbol.startswith(("5", "6", "9")):
        return "SH"
    return "SZ"


def _normalize_as_of(value: date) -> date:
    if isinstance(value, datetime) or not isinstance(value, date):
        raise ValueError("as_of must be a date.")
    return value


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


def _optional_ratio(value: object) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, str | int | float):
        raise ValueError
    normalized = float(value)
    if not math.isfinite(normalized):
        raise ValueError
    return normalized / 100.0


def _required_string(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError
    normalized = value.strip()
    if not normalized:
        raise ValueError
    return normalized


def _optional_text(value: object, *, max_chars: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise _schema_error()
    normalized = " ".join(value.split())
    return normalized[:max_chars] or None


def _optional_content_length(value: str | None) -> int | None:
    if value is None or not value.isdigit():
        return None
    return int(value)


def _reject_json_constant(_value: str) -> None:
    raise ValueError


def _response_error() -> EastmoneyPublicFundamentalsProviderError:
    return EastmoneyPublicFundamentalsProviderError(
        "EASTMONEY_FUNDAMENTALS_RESPONSE_REJECTED",
        "Eastmoney public fundamentals response was rejected.",
    )


def _schema_error() -> EastmoneyPublicFundamentalsProviderError:
    return EastmoneyPublicFundamentalsProviderError(
        "EASTMONEY_FUNDAMENTALS_SCHEMA_REJECTED",
        "Eastmoney public fundamentals response did not match the expected schema.",
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
) -> EastmoneyPublicFundamentalsHttpResponse:
    with httpx.Client(
        timeout=timeout,
        follow_redirects=follow_redirects,
        trust_env=trust_env,
        headers=dict(headers),
    ) as client:
        with client.stream("GET", url, params=dict(params)) as response:
            content_length = _optional_content_length(
                response.headers.get("content-length")
            )
            if content_length is not None and content_length > max_bytes:
                raise EastmoneyPublicFundamentalsProviderError(
                    "EASTMONEY_FUNDAMENTALS_RESPONSE_TOO_LARGE",
                    "Eastmoney public fundamentals response exceeded the size limit.",
                )
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > max_bytes:
                    raise EastmoneyPublicFundamentalsProviderError(
                        "EASTMONEY_FUNDAMENTALS_RESPONSE_TOO_LARGE",
                        "Eastmoney public fundamentals response exceeded the size limit.",
                    )
                chunks.append(chunk)
            return EastmoneyPublicFundamentalsHttpResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                content=b"".join(chunks),
            )
