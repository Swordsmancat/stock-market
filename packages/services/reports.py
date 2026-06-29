from datetime import date

from packages.ai.report_builder import ReportContext, build_stock_report
from packages.services.market_data import get_bars_payload


def generate_stock_report_payload(symbol: str, start: date, end: date) -> dict[str, object]:
    bars_payload = get_bars_payload(symbol, "1d", start, end)
    items = bars_payload["items"]
    first_bar = items[0]
    latest_bar = items[-1]
    change_pct = ((latest_bar["close"] - first_bar["close"]) / first_bar["close"]) * 100
    citation = f"bars_1d:{symbol}:{latest_bar['timestamp']}"
    context = ReportContext(
        symbol=symbol,
        as_of=str(latest_bar["timestamp"]),
        price_summary=f"Close {latest_bar['close']:.2f}, period change {change_pct:.2f}%",
        indicator_summary="Mock provider data is available for MA and RSI analysis.",
        news_summary="No external news source is connected in the MVP skeleton.",
        citations=[citation],
    )
    return {
        "symbol": symbol,
        "report_type": "stock_daily",
        "as_of": context.as_of,
        "content_markdown": build_stock_report(context),
        "citations": context.citations,
    }
