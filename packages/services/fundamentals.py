from datetime import date
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
from packages.providers.yfinance_helpers import map_symbol_to_ticker
from packages.shared.config import settings


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

    snapshot = _FUNDAMENTAL_FIXTURES.get(symbol.upper())
    if snapshot is None:
        return {"symbol": symbol, "source": "mock_fundamentals", "item": None}

    return _payload_from_snapshot(snapshot, source="mock_fundamentals", as_of=as_of)


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
