from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class FundamentalSnapshot:
    symbol: str
    as_of: date
    currency: str
    pe_ratio: float | None
    revenue_growth: float | None
    net_margin: float | None
    debt_to_assets: float | None


def format_percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def summarize_fundamentals(snapshot: FundamentalSnapshot) -> str | None:
    if any(
        value is None
        for value in (
            snapshot.pe_ratio,
            snapshot.revenue_growth,
            snapshot.net_margin,
            snapshot.debt_to_assets,
        )
    ):
        return None
    assert snapshot.pe_ratio is not None
    assert snapshot.revenue_growth is not None
    assert snapshot.net_margin is not None
    assert snapshot.debt_to_assets is not None
    return (
        f"PE {snapshot.pe_ratio:.2f}，营收增速 {format_percent(snapshot.revenue_growth)}，"
        f"净利率 {format_percent(snapshot.net_margin)}，资产负债率 "
        f"{format_percent(snapshot.debt_to_assets)}"
    )
