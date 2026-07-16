import json
import re
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from packages.analytics.fundamentals import (
    FundamentalSnapshot as FundamentalMetricsSnapshot,
)
from packages.analytics.fundamentals import (
    summarize_fundamentals,
)
from packages.domain.models import FundamentalSnapshot as FundamentalSnapshotModel
from packages.providers.cn_market_helpers import (
    find_column,
    normalize_cn_symbol,
    safe_pct_ratio,
    tushare_ts_code,
)
from packages.providers.eastmoney_public_fundamentals import (
    EastmoneyPublicFundamentalsProviderError,
    EastmoneyPublicFundamentalsSnapshot,
    fetch_eastmoney_public_fundamentals,
)
from packages.providers.yfinance_helpers import map_symbol_to_ticker
from packages.services.platform_settings import get_platform_settings
from packages.shared.cache import redis_client
from packages.shared.config import settings


_EXACT_A_SHARE_PATTERN = re.compile(r"^\d{6}$")
_EASTMONEY_FUNDAMENTALS_CACHE_TTL_SECONDS = 1800
_EASTMONEY_FUNDAMENTALS_SOURCES = [
    "eastmoney.RPT_F10_FINANCE_MAINFINADATA",
    "eastmoney.PC_HSF10.CompanySurvey.PageAjax",
]


_FUNDAMENTAL_FIXTURES = {
    "AAPL": FundamentalMetricsSnapshot(
        symbol="AAPL",
        as_of=date(2026, 1, 20),
        currency="USD",
        pe_ratio=28.40,
        revenue_growth=0.08,
        net_margin=0.24,
        debt_to_assets=0.31,
    ),
    "0700": FundamentalMetricsSnapshot(
        symbol="0700",
        as_of=date(2026, 1, 20),
        currency="HKD",
        pe_ratio=22.10,
        revenue_growth=0.11,
        net_margin=0.19,
        debt_to_assets=0.27,
    ),
    "600519": FundamentalMetricsSnapshot(
        symbol="600519",
        as_of=date(2026, 1, 20),
        currency="CNY",
        pe_ratio=26.80,
        revenue_growth=0.10,
        net_margin=0.52,
        debt_to_assets=0.18,
    ),
}


def _snapshot_from_model(row: FundamentalSnapshotModel) -> FundamentalMetricsSnapshot:
    return FundamentalMetricsSnapshot(
        symbol=row.symbol,
        as_of=row.as_of,
        currency=row.currency,
        pe_ratio=float(row.pe_ratio),
        revenue_growth=float(row.revenue_growth),
        net_margin=float(row.net_margin),
        debt_to_assets=float(row.debt_to_assets),
    )


def _payload_from_snapshot(
    snapshot: FundamentalMetricsSnapshot,
    source: str,
    as_of: date | None = None,
) -> dict[str, object]:
    effective_as_of = as_of or snapshot.as_of
    citation = f"fundamental_metrics:{snapshot.symbol}:{effective_as_of.isoformat()}"
    return {
        "symbol": snapshot.symbol,
        "source": source,
        "as_of": effective_as_of.isoformat(),
        "item": {
            "currency": snapshot.currency,
            "pe_ratio": snapshot.pe_ratio,
            "revenue_growth": snapshot.revenue_growth,
            "net_margin": snapshot.net_margin,
            "debt_to_assets": snapshot.debt_to_assets,
            "summary": summarize_fundamentals(snapshot),
        },
        "citation": citation,
    }


def _latest_fundamental_snapshot(
    symbol: str,
    as_of: date | None,
    session: Session,
) -> FundamentalSnapshotModel | None:
    query = session.query(FundamentalSnapshotModel).filter(FundamentalSnapshotModel.symbol == symbol.upper())
    if as_of is not None:
        query = query.filter(FundamentalSnapshotModel.as_of <= as_of)
    return query.order_by(FundamentalSnapshotModel.as_of.desc()).first()


def upsert_fundamental_snapshot(
    snapshot: FundamentalMetricsSnapshot,
    session: Session,
    source: str = "manual",
) -> dict[str, object]:
    row = (
        session.query(FundamentalSnapshotModel)
        .filter(FundamentalSnapshotModel.symbol == snapshot.symbol.upper())
        .filter(FundamentalSnapshotModel.as_of == snapshot.as_of)
        .first()
    )
    values = {
        "symbol": snapshot.symbol.upper(),
        "as_of": snapshot.as_of,
        "currency": snapshot.currency,
        "pe_ratio": Decimal(str(snapshot.pe_ratio)),
        "revenue_growth": Decimal(str(snapshot.revenue_growth)),
        "net_margin": Decimal(str(snapshot.net_margin)),
        "debt_to_assets": Decimal(str(snapshot.debt_to_assets)),
        "source": source,
    }
    if row is None:
        row = FundamentalSnapshotModel(**values)
        session.add(row)
    else:
        for key, value in values.items():
            setattr(row, key, value)
    session.commit()

    return _payload_from_snapshot(_snapshot_from_model(row), source="database")


def get_fundamental_payload(
    symbol: str,
    as_of: date | None = None,
    session: Session | None = None,
) -> dict[str, object]:
    if session is not None:
        try:
            row = _latest_fundamental_snapshot(symbol, as_of, session)
        except SQLAlchemyError:
            session.rollback()
        else:
            if row is not None:
                return _payload_from_snapshot(_snapshot_from_model(row), source="database")

    normalized_symbol = str(symbol).strip().upper()
    if _is_eastmoney_public_eligible(normalized_symbol):
        return _get_eastmoney_public_payload(
            normalized_symbol,
            as_of=as_of or date.today(),
        )

    snapshot = _FUNDAMENTAL_FIXTURES.get(normalized_symbol)
    if snapshot is None:
        return {"symbol": symbol, "source": "mock_fundamentals", "item": None}

    return _payload_from_snapshot(snapshot, source="mock_fundamentals", as_of=as_of)


def _is_eastmoney_public_eligible(symbol: str) -> bool:
    if not _EXACT_A_SHARE_PATTERN.fullmatch(symbol):
        return False
    try:
        return bool(get_platform_settings().get("akshare_enabled", False))
    except Exception:
        return False


def _get_eastmoney_public_payload(symbol: str, *, as_of: date) -> dict[str, object]:
    cache_key = f"fundamentals:eastmoney-public:{symbol}:{as_of.isoformat()}"
    cached = _read_eastmoney_public_cache(cache_key, symbol=symbol)
    if cached is not None:
        return cached

    try:
        snapshot = fetch_eastmoney_public_fundamentals(symbol, as_of=as_of)
    except EastmoneyPublicFundamentalsProviderError as error:
        return _eastmoney_unavailable_payload(symbol, as_of=as_of, code=error.code)
    except Exception:
        return _eastmoney_unavailable_payload(
            symbol,
            as_of=as_of,
            code="EASTMONEY_FUNDAMENTALS_REQUEST_FAILED",
        )

    if snapshot is None:
        payload = _eastmoney_no_data_payload(symbol, as_of=as_of)
    else:
        payload = _payload_from_eastmoney_snapshot(snapshot)
    _write_eastmoney_public_cache(cache_key, payload)
    return payload


def _payload_from_eastmoney_snapshot(
    snapshot: EastmoneyPublicFundamentalsSnapshot,
) -> dict[str, object]:
    company = snapshot.company
    metrics = {
        "pe_ratio": snapshot.pe_ratio,
        "revenue_growth": snapshot.revenue_growth,
        "net_margin": snapshot.net_margin,
        "debt_to_assets": snapshot.debt_to_assets,
    }
    return {
        "symbol": snapshot.symbol,
        "source": snapshot.provider,
        "provider": snapshot.provider,
        "status": snapshot.status,
        "as_of": snapshot.as_of.isoformat(),
        "retrieved_at": snapshot.retrieved_at.isoformat(),
        "upstream_sources": list(snapshot.upstream_sources),
        "diagnostics": list(snapshot.diagnostics),
        "item": {
            "currency": snapshot.currency,
            **metrics,
            "company": (
                {
                    "name": company.name,
                    "industry": company.industry,
                    "business_scope": company.business_scope,
                    "profile": company.profile,
                }
                if company is not None
                else None
            ),
            "summary": None,
        },
        "citation": (
            f"fundamental_metrics:{snapshot.symbol}:{snapshot.as_of.isoformat()}"
        ),
    }


def _eastmoney_no_data_payload(symbol: str, *, as_of: date) -> dict[str, object]:
    return {
        "symbol": symbol,
        "source": "eastmoney_public",
        "provider": "eastmoney_public",
        "status": "no_data",
        "as_of": as_of.isoformat(),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "upstream_sources": list(_EASTMONEY_FUNDAMENTALS_SOURCES),
        "diagnostics": ["EASTMONEY_FUNDAMENTALS_NO_DATA"],
        "item": None,
    }


def _eastmoney_unavailable_payload(
    symbol: str,
    *,
    as_of: date,
    code: str,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "source": "eastmoney_public",
        "provider": "eastmoney_public",
        "status": "unavailable",
        "as_of": as_of.isoformat(),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "upstream_sources": list(_EASTMONEY_FUNDAMENTALS_SOURCES),
        "diagnostics": [code],
        "item": None,
    }


def _read_eastmoney_public_cache(
    cache_key: str,
    *,
    symbol: str,
) -> dict[str, object] | None:
    try:
        cached = redis_client.get(cache_key)
        payload = json.loads(cached) if cached else None
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("symbol") != symbol or payload.get("source") != "eastmoney_public":
        return None
    if payload.get("status") not in {"ok", "degraded", "no_data"}:
        return None
    return payload


def _write_eastmoney_public_cache(
    cache_key: str,
    payload: dict[str, object],
) -> None:
    try:
        redis_client.set(
            cache_key,
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            ex=_EASTMONEY_FUNDAMENTALS_CACHE_TTL_SECONDS,
        )
    except Exception:
        pass


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed != parsed:  # NaN
        return None
    return parsed


def ingest_fundamentals(
    symbol: str,
    session: Session,
    provider_name: str | None = None,
    as_of: date | None = None,
) -> dict[str, object]:
    provider = (provider_name or settings.market_data_provider).lower()
    if provider == "yfinance":
        return ingest_yfinance_fundamentals(symbol, session=session, as_of=as_of)
    if provider == "akshare":
        return ingest_akshare_fundamentals(symbol, session=session, as_of=as_of)
    if provider == "tushare":
        return ingest_tushare_fundamentals(symbol, session=session, as_of=as_of)
    return {"symbol": symbol, "status": "skipped", "source": provider}


def ingest_yfinance_fundamentals(
    symbol: str,
    session: Session,
    as_of: date | None = None,
) -> dict[str, object]:
    import yfinance as yf

    effective_as_of = as_of or date.today()
    info = yf.Ticker(map_symbol_to_ticker(symbol)).info or {}
    pe_ratio = _safe_float(info.get("trailingPE") or info.get("forwardPE"))
    revenue_growth = _safe_float(info.get("revenueGrowth"))
    net_margin = _safe_float(info.get("profitMargins"))
    debt_to_equity = _safe_float(info.get("debtToEquity"))
    if debt_to_equity is not None:
        debt_to_equity = debt_to_equity / 100.0

    if all(value is None for value in (pe_ratio, revenue_growth, net_margin, debt_to_equity)):
        return {"symbol": symbol, "status": "empty", "source": "yfinance"}

    snapshot = FundamentalMetricsSnapshot(
        symbol=symbol.upper(),
        as_of=effective_as_of,
        currency=str(info.get("currency") or "USD"),
        pe_ratio=pe_ratio or 0.0,
        revenue_growth=revenue_growth or 0.0,
        net_margin=net_margin or 0.0,
        debt_to_assets=debt_to_equity or 0.0,
    )
    payload = upsert_fundamental_snapshot(snapshot, session=session, source="yfinance")
    return {"symbol": symbol, "status": "ingested", "source": "yfinance", "item": payload.get("item")}


def _row_value(row, columns: list[str], *substrings: str) -> object | None:
    column = find_column(columns, *substrings)
    if column is None:
        return None
    return row[column]


def ingest_akshare_fundamentals(
    symbol: str,
    session: Session,
    as_of: date | None = None,
) -> dict[str, object]:
    try:
        import akshare as ak
    except ImportError:
        return {"symbol": symbol, "status": "skipped", "source": "akshare", "reason": "akshare not installed"}

    code = normalize_cn_symbol(symbol)
    effective_as_of = as_of or date.today()
    try:
        df = ak.stock_financial_analysis_indicator(symbol=code, start_year=str(effective_as_of.year - 1))
    except Exception:
        return {"symbol": symbol, "status": "empty", "source": "akshare"}

    if df is None or df.empty:
        return {"symbol": symbol, "status": "empty", "source": "akshare"}

    columns = [str(column) for column in df.columns]
    row = df.iloc[-1]
    date_col = find_column(columns, "日期")
    if date_col is not None:
        raw_date = row[date_col]
        if hasattr(raw_date, "date"):
            effective_as_of = raw_date.date()

    revenue_growth = safe_pct_ratio(_row_value(row, columns, "主营业务", "增长"))
    net_margin = safe_pct_ratio(_row_value(row, columns, "销售", "净利率"))
    debt_to_assets = safe_pct_ratio(_row_value(row, columns, "资产负债率"))

    if all(value is None for value in (revenue_growth, net_margin, debt_to_assets)):
        return {"symbol": symbol, "status": "empty", "source": "akshare"}

    snapshot = FundamentalMetricsSnapshot(
        symbol=code,
        as_of=effective_as_of,
        currency="CNY",
        pe_ratio=0.0,
        revenue_growth=revenue_growth or 0.0,
        net_margin=net_margin or 0.0,
        debt_to_assets=debt_to_assets or 0.0,
    )
    payload = upsert_fundamental_snapshot(snapshot, session=session, source="akshare")
    return {"symbol": symbol, "status": "ingested", "source": "akshare", "item": payload.get("item")}


def ingest_tushare_fundamentals(
    symbol: str,
    session: Session,
    as_of: date | None = None,
) -> dict[str, object]:
    try:
        import tushare as ts
    except ImportError:
        return {"symbol": symbol, "status": "skipped", "source": "tushare", "reason": "tushare not installed"}

    from packages.services.platform_settings import get_platform_settings

    token = str(get_platform_settings().get("tushare_token", "") or "").strip()
    if not token:
        return {"symbol": symbol, "status": "skipped", "source": "tushare", "reason": "missing token"}

    effective_as_of = as_of or date.today()
    ts_code = tushare_ts_code(symbol)
    try:
        ts.set_token(token)
        pro = ts.pro_api()
        basic = pro.daily_basic(ts_code=ts_code, trade_date=effective_as_of.strftime("%Y%m%d"))
        if basic is None or basic.empty:
            basic = pro.daily_basic(ts_code=ts_code, limit=1)
        fina = pro.fina_indicator(ts_code=ts_code, limit=1)
    except Exception:
        return {"symbol": symbol, "status": "empty", "source": "tushare"}

    pe_ratio = _safe_float(basic.iloc[-1].get("pe_ttm")) if basic is not None and not basic.empty else None
    revenue_growth = None
    net_margin = None
    debt_to_assets = None
    if fina is not None and not fina.empty:
        fina_row = fina.iloc[-1]
        revenue_growth = _safe_float(fina_row.get("tr_yoy"))
        net_margin = _safe_float(fina_row.get("netprofit_margin"))
        debt_to_assets = _safe_float(fina_row.get("debt_to_assets"))
        if revenue_growth is not None:
            revenue_growth = revenue_growth / 100.0
        if net_margin is not None:
            net_margin = net_margin / 100.0
        if debt_to_assets is not None:
            debt_to_assets = debt_to_assets / 100.0

    if all(value is None for value in (pe_ratio, revenue_growth, net_margin, debt_to_assets)):
        return {"symbol": symbol, "status": "empty", "source": "tushare"}

    snapshot = FundamentalMetricsSnapshot(
        symbol=normalize_cn_symbol(symbol),
        as_of=effective_as_of,
        currency="CNY",
        pe_ratio=pe_ratio or 0.0,
        revenue_growth=revenue_growth or 0.0,
        net_margin=net_margin or 0.0,
        debt_to_assets=debt_to_assets or 0.0,
    )
    payload = upsert_fundamental_snapshot(snapshot, session=session, source="tushare")
    return {"symbol": symbol, "status": "ingested", "source": "tushare", "item": payload.get("item")}
