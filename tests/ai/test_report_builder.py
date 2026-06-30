from packages.ai.report_builder import ReportContext, build_stock_report


def test_build_stock_report_includes_citations_and_cutoff():
    context = ReportContext(
        symbol="AAPL",
        as_of="2026-06-29",
        price_summary="Close 101.00, up 1.0%",
        indicator_summary="MA20 above MA60",
        fundamental_summary="PE 28.40, revenue growth 8.00%",
        news_summary="Positive earnings news",
        citations=["news_articles:1", "bars_1d:AAPL:2026-06-29"],
    )
    report = build_stock_report(context)
    assert "AAPL" in report
    assert "2026-06-29" in report
    assert "PE 28.40" in report
    assert "news_articles:1" in report
