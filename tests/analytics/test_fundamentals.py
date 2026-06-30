from datetime import date

from packages.analytics.fundamentals import FundamentalSnapshot, summarize_fundamentals


def test_summarize_fundamentals_formats_core_metrics():
    snapshot = FundamentalSnapshot(
        symbol="AAPL",
        as_of=date(2026, 1, 20),
        currency="USD",
        pe_ratio=28.4,
        revenue_growth=0.08,
        net_margin=0.24,
        debt_to_assets=0.31,
    )

    summary = summarize_fundamentals(snapshot)

    assert "PE 28.40" in summary
    assert "营收增速 8.00%" in summary
    assert "净利率 24.00%" in summary
    assert "资产负债率 31.00%" in summary
