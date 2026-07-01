from __future__ import annotations

import math
from datetime import datetime, timezone


def normalize_cn_symbol(symbol: str) -> str:
    return symbol.upper().split(".")[0]


def tushare_ts_code(symbol: str) -> str:
    code = normalize_cn_symbol(symbol)
    suffix = "SH" if code.startswith("6") else "SZ"
    return f"{code}.{suffix}"


def find_column(columns: list[str], *substrings: str) -> str | None:
    for col in columns:
        if all(part in col for part in substrings):
            return col
    for col in columns:
        if any(part in col for part in substrings):
            return col
    return None


def safe_pct_ratio(value: object) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(parsed):
        return None
    return parsed / 100.0


def parse_cn_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return datetime.now(timezone.utc)
