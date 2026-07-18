from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

import httpx

UNIVERSE_URL = "https://push2.eastmoney.com/api/qt/clist/get"
UNIVERSE_FALLBACK_URL = "https://push2delay.eastmoney.com/api/qt/clist/get"
HISTORY_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
HISTORY_FALLBACK_URL = "https://push2delay.eastmoney.com/api/qt/stock/kline/get"
SOURCE_URL = "https://quote.eastmoney.com/center/gridlist.html#industry_board_1"
INDUSTRY_UNIVERSE_FILTER = "m:90 s:4"
QUOTE_CENTER_UT = "8dec03ba335b81bf4ebdf7b29ec27d15"
MAX_INDUSTRIES = 200
MAX_DAYS = 20


class EastmoneyIndustryRankingError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class IndustryDailyRecord:
    industry_code: str
    industry_name: str
    trade_date: date
    change_percent: Decimal
    retrieved_at: datetime


Requester = Callable[..., object]


def fetch_eastmoney_industry_history(
    *, days: int = 12, proxy_url: str = "", cookie: str = "", requester: Requester | None = None
) -> tuple[IndustryDailyRecord, ...]:
    if not 1 <= days <= MAX_DAYS:
        raise ValueError("days must be between 1 and 20.")
    request = requester or _request
    headers = {
        "accept": "application/json,text/plain,*/*",
        "referer": SOURCE_URL,
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
    }
    if cookie.strip():
        headers["cookie"] = cookie.strip()
    universe = _get_json(
        request,
        UNIVERSE_URL,
        params={"pn": "1", "pz": str(MAX_INDUSTRIES), "po": "1", "np": "1", "fltt": "2", "invt": "2", "fid": "f3", "fs": INDUSTRY_UNIVERSE_FILTER, "fields": "f12,f14,f3", "ut": QUOTE_CENTER_UT},
        headers=headers,
        proxy_url=proxy_url,
        fallback_url=UNIVERSE_FALLBACK_URL,
        validator=_has_industry_universe,
    )
    diff = _mapping(_mapping(universe).get("data")).get("diff")
    if not isinstance(diff, list) or not diff:
        raise EastmoneyIndustryRankingError("EASTMONEY_INDUSTRY_SCHEMA_REJECTED", "Eastmoney industry universe response did not match the expected schema.")
    industries: dict[str, str] = {}
    for row in diff:
        mapped = _mapping(row)
        code, name = str(mapped.get("f12") or "").strip(), str(mapped.get("f14") or "").strip()
        if code.startswith("BK") and code not in industries and name:
            industries[code] = name[:128]
    if not industries or len(industries) > MAX_INDUSTRIES:
        raise EastmoneyIndustryRankingError("EASTMONEY_INDUSTRY_SCHEMA_REJECTED", "Eastmoney industry universe response did not match the expected schema.")
    retrieved_at = datetime.now(timezone.utc)
    records: list[IndustryDailyRecord] = []
    for code, name in industries.items():
        payload = _get_json(
            request,
            HISTORY_URL,
            params={"secid": f"90.{code}", "klt": "101", "fqt": "1", "lmt": str(days), "end": "20500101", "iscca": "1", "fields1": "f1,f2,f3,f4,f5,f6", "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"},
            headers=headers,
            proxy_url=proxy_url,
            fallback_url=HISTORY_FALLBACK_URL,
            validator=_has_history_rows,
            return_last_rejected=True,
        )
        klines = _mapping(_mapping(payload).get("data")).get("klines")
        if not isinstance(klines, list):
            raise EastmoneyIndustryRankingError("EASTMONEY_INDUSTRY_SCHEMA_REJECTED", "Eastmoney industry history response did not match the expected schema.")
        for line in klines[-days:]:
            parts = str(line).split(",")
            try:
                day = date.fromisoformat(parts[0])
                change = Decimal(parts[8])
            except (IndexError, ValueError, InvalidOperation):
                raise EastmoneyIndustryRankingError("EASTMONEY_INDUSTRY_ROW_REJECTED", "Eastmoney industry history contained an invalid row.") from None
            if not change.is_finite():
                raise EastmoneyIndustryRankingError("EASTMONEY_INDUSTRY_ROW_REJECTED", "Eastmoney industry history contained an invalid row.")
            records.append(IndustryDailyRecord(code, name, day, change, retrieved_at))
    if not records:
        raise EastmoneyIndustryRankingError(
            "EASTMONEY_INDUSTRY_SCHEMA_REJECTED",
            "Eastmoney industry history response contained no usable rows.",
        )
    return tuple(records)


def _mapping(value: object) -> Mapping[object, object]:
    return value if isinstance(value, Mapping) else {}


def _has_industry_universe(value: object) -> bool:
    diff = _mapping(_mapping(value).get("data")).get("diff")
    if not isinstance(diff, list) or not diff:
        return False
    return any(
        str(_mapping(row).get("f12") or "").strip().startswith("BK")
        and bool(str(_mapping(row).get("f14") or "").strip())
        for row in diff
    )


def _has_history_rows(value: object) -> bool:
    klines = _mapping(_mapping(value).get("data")).get("klines")
    return isinstance(klines, list) and bool(klines)


def _get_json(
    request: Requester,
    url: str,
    *,
    params: dict[str, str],
    headers: dict[str, str],
    proxy_url: str,
    fallback_url: str | None = None,
    validator: Callable[[object], bool] | None = None,
    return_last_rejected: bool = False,
) -> object:
    urls = (url,) if fallback_url is None else (url, fallback_url)
    proxies = (None,) + ((proxy_url.strip(),) if proxy_url.strip() else ())
    last_code = "EASTMONEY_INDUSTRY_REQUEST_FAILED"
    last_rejected: object | None = None
    for proxy in proxies:
        for candidate_url in urls:
            try:
                response = request(
                    candidate_url,
                    params=params,
                    headers=headers,
                    timeout=12.0,
                    proxy=proxy,
                )
                if getattr(response, "status_code", None) != 200:
                    last_code = "EASTMONEY_INDUSTRY_HTTP_STATUS"
                    continue
                payload = response.json()
                if validator is not None and not validator(payload):
                    last_code = "EASTMONEY_INDUSTRY_SCHEMA_REJECTED"
                    last_rejected = payload
                    continue
                return payload
            except (httpx.TimeoutException, TimeoutError):
                last_code = "EASTMONEY_INDUSTRY_TIMEOUT"
            except Exception:
                last_code = "EASTMONEY_INDUSTRY_REQUEST_FAILED"
    if return_last_rejected and last_rejected is not None:
        return last_rejected
    raise EastmoneyIndustryRankingError(last_code, "Eastmoney industry data request failed.")


def _request(url: str, **kwargs: object) -> httpx.Response:
    proxy = kwargs.pop("proxy", None)
    with httpx.Client(proxy=proxy or None, follow_redirects=False) as client:
        return client.get(url, **kwargs)
