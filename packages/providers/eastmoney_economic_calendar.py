from __future__ import annotations

import hashlib
import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

import httpx

ENDPOINT = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
REPORT = "RPT_INFO_SCHEDULENEWSNEW"
SOURCE_URL = "https://data.eastmoney.com/cjrl/"
PAGE_SIZE = 100
MAX_PAGES = 100
MAX_DAYS = 62
SHANGHAI = ZoneInfo("Asia/Shanghai")


class EastmoneyEconomicCalendarError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class EconomicCalendarRecord:
    external_event_id: str
    indicator_id: str | None
    country: str
    name: str
    reference_period: str | None
    importance: int
    scheduled_at: datetime
    previous_value: Decimal | None
    forecast_value: Decimal | None
    actual_value: Decimal | None
    unit: str | None
    retrieved_at: datetime


HttpGetter = Callable[..., object]


def fetch_eastmoney_economic_calendar(
    start: date, end: date, *, http_get: HttpGetter | None = None
) -> tuple[EconomicCalendarRecord, ...]:
    if end < start or (end - start).days + 1 > MAX_DAYS:
        raise ValueError("date range must contain between 1 and 62 days.")
    getter = http_get or httpx.get
    retrieved_at = datetime.now(timezone.utc)
    records: list[EconomicCalendarRecord] = []
    page = 1
    pages = 1
    while page <= pages:
        if page > MAX_PAGES:
            raise EastmoneyEconomicCalendarError(
                "EASTMONEY_CALENDAR_PAGE_LIMIT",
                "Eastmoney economic calendar exceeded the page limit.",
            )
        params = {
            "reportName": REPORT,
            "columns": "ALL",
            "filter": f"(PUBLISH_DATE>='{start.isoformat()}')(PUBLISH_DATE<='{end.isoformat()}')",
            "pageNumber": str(page),
            "pageSize": str(PAGE_SIZE),
            "sortColumns": "PUBLISH_DATEH",
            "sortTypes": "1",
            "source": "WEB",
            "client": "WEB",
        }
        try:
            response = getter(ENDPOINT, params=params, timeout=12.0, follow_redirects=False)
            if getattr(response, "status_code", None) != 200:
                raise EastmoneyEconomicCalendarError(
                    "EASTMONEY_CALENDAR_HTTP_STATUS",
                    "Eastmoney economic calendar returned an unexpected status.",
                )
            payload = response.json()
        except EastmoneyEconomicCalendarError:
            raise
        except (httpx.TimeoutException, TimeoutError):
            raise EastmoneyEconomicCalendarError(
                "EASTMONEY_CALENDAR_TIMEOUT", "Eastmoney economic calendar request timed out."
            ) from None
        except Exception:
            raise EastmoneyEconomicCalendarError(
                "EASTMONEY_CALENDAR_REQUEST_FAILED", "Eastmoney economic calendar request failed."
            ) from None
        if (
            not isinstance(payload, Mapping)
            or payload.get("success") is not True
            or not isinstance(payload.get("result"), Mapping)
        ):
            raise EastmoneyEconomicCalendarError(
                "EASTMONEY_CALENDAR_SCHEMA_REJECTED",
                "Eastmoney economic calendar response did not match the expected schema.",
            )
        result = payload["result"]
        rows = result.get("data")
        if not isinstance(rows, list):
            raise EastmoneyEconomicCalendarError(
                "EASTMONEY_CALENDAR_SCHEMA_REJECTED",
                "Eastmoney economic calendar response did not match the expected schema.",
            )
        try:
            pages = int(result.get("pages") or 1)
        except (TypeError, ValueError):
            raise EastmoneyEconomicCalendarError(
                "EASTMONEY_CALENDAR_SCHEMA_REJECTED",
                "Eastmoney economic calendar response did not match the expected schema.",
            ) from None
        if pages < 1 or pages > MAX_PAGES:
            raise EastmoneyEconomicCalendarError(
                "EASTMONEY_CALENDAR_PAGE_LIMIT",
                "Eastmoney economic calendar exceeded the page limit.",
            )
        records.extend(_normalize(row, retrieved_at) for row in rows)
        page += 1
    return tuple({record.external_event_id: record for record in records}.values())


def _normalize(row: object, retrieved_at: datetime) -> EconomicCalendarRecord:
    if not isinstance(row, Mapping):
        raise EastmoneyEconomicCalendarError(
            "EASTMONEY_CALENDAR_ROW_REJECTED",
            "Eastmoney economic calendar contained an invalid row.",
        )
    try:
        name = _required(row.get("INDICATOR_NAME_NEW") or row.get("STR_INDEXNAME"), 512)
        country = _required(row.get("STR_COUNTRY"), 64)
        indicator_id = _optional(row.get("INDICATOR_ID"), 64)
        scheduled_at = _parse_time(row)
        external_id = _optional(row.get("MXID"), 128)
        if not external_id:
            seed = f"{indicator_id or ''}|{scheduled_at.isoformat()}|{name}".encode()
            external_id = hashlib.sha256(seed).hexdigest()
        importance = int(row.get("STAR") or 0)
        if not 0 <= importance <= 5:
            raise ValueError
        return EconomicCalendarRecord(
            external_event_id=external_id,
            indicator_id=indicator_id,
            country=country,
            name=name,
            reference_period=_optional(row.get("DAT_PREDICT_DATE"), 64),
            importance=importance,
            scheduled_at=scheduled_at,
            previous_value=_decimal(row.get("DEC_LINDEXVALUE")),
            forecast_value=_decimal(row.get("DEC_FOREVALUE")),
            actual_value=_decimal(row.get("DEC_INDEXVALUE")),
            unit=_optional(row.get("UNIT"), 64),
            retrieved_at=retrieved_at,
        )
    except (TypeError, ValueError, OverflowError):
        raise EastmoneyEconomicCalendarError(
            "EASTMONEY_CALENDAR_ROW_REJECTED",
            "Eastmoney economic calendar contained an invalid row.",
        ) from None


def _parse_time(row: Mapping[object, object]) -> datetime:
    primary = _optional(row.get("PUBLISH_DATEH"), 32)
    if primary:
        parsed = _try_parse_time(primary)
        if parsed is not None:
            return parsed
    day = _optional(row.get("PUBLISH_DATEH_Z"), 32)
    clock = _optional(row.get("PUBLISH_DATETME"), 16)
    if day and clock:
        parsed = _try_parse_time(f"{day[:10]} {clock}")
        if parsed is not None:
            return parsed
    raise ValueError


def _try_parse_time(value: str) -> datetime | None:
    cleaned = value.replace("T", " ").split(".", 1)[0]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(cleaned, fmt).replace(tzinfo=SHANGHAI).astimezone(timezone.utc)
        except ValueError:
            pass
    return None


def _required(value: object, limit: int) -> str:
    result = _optional(value, limit)
    if not result:
        raise ValueError
    return result


def _optional(value: object, limit: int) -> str | None:
    if value is None:
        return None
    result = str(value).strip()
    if not result:
        return None
    if len(result) > limit:
        raise ValueError
    return result


def _decimal(value: object) -> Decimal | None:
    if value is None or str(value).strip() in {"", "--", "-"}:
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError from None
    if not result.is_finite() or not math.isfinite(float(result)):
        raise ValueError
    return result
