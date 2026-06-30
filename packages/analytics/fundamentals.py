from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class FundamentalSnapshot:
    symbol: str
    as_of: date
    currency: str
    pe_ratio: float
    revenue_growth: float
    net_margin: float
    debt_to_assets: float


def format_percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def summarize_fundamentals(snapshot: FundamentalSnapshot) -> str:
    return (
        f"PE {snapshot.pe_ratio:.2f}，营收增速 {format_percent(snapshot.revenue_growth)}，"
        f"净利率 {format_percent(snapshot.net_margin)}，资产负债率 "
        f"{format_percent(snapshot.debt_to_assets)}"
    )
