from datetime import date

from packages.analytics.fundamentals import FundamentalSnapshot, summarize_fundamentals


_FUNDAMENTAL_FIXTURES = {
    "AAPL": FundamentalSnapshot(
        symbol="AAPL",
        as_of=date(2026, 1, 20),
        currency="USD",
        pe_ratio=28.40,
        revenue_growth=0.08,
        net_margin=0.24,
        debt_to_assets=0.31,
    ),
    "0700": FundamentalSnapshot(
        symbol="0700",
        as_of=date(2026, 1, 20),
        currency="HKD",
        pe_ratio=22.10,
        revenue_growth=0.11,
        net_margin=0.19,
        debt_to_assets=0.27,
    ),
    "600519": FundamentalSnapshot(
        symbol="600519",
        as_of=date(2026, 1, 20),
        currency="CNY",
        pe_ratio=26.80,
        revenue_growth=0.10,
        net_margin=0.52,
        debt_to_assets=0.18,
    ),
}


def get_fundamental_payload(symbol: str, as_of: date | None = None) -> dict[str, object]:
    snapshot = _FUNDAMENTAL_FIXTURES.get(symbol.upper())
    if snapshot is None:
        return {"symbol": symbol, "source": "mock_fundamentals", "item": None}

    effective_as_of = as_of or snapshot.as_of
    citation = f"fundamental_metrics:{snapshot.symbol}:{effective_as_of.isoformat()}"
    return {
        "symbol": snapshot.symbol,
        "source": "mock_fundamentals",
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
