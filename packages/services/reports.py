from datetime import date

from sqlalchemy.orm import Session

from packages.ai.report_builder import ReportContext, build_stock_report
from packages.services.indicators import get_stored_indicators_payload
from packages.services.market_data import get_bars_payload
from packages.services.news import get_news_sentiment_payload


def _indicator_summary_and_citation(symbol: str, session: Session | None) -> tuple[str, str | None]:
    if session is None:
        return "No stored technical indicators are available in the MVP skeleton.", None

    indicator_payload = get_stored_indicators_payload(symbol, session=session)
    indicators = indicator_payload["indicators"]
    if not indicators:
        return "No stored technical indicators are available yet.", None

    ma = indicators.get("ma")
    rsi = indicators.get("rsi")
    parts = []
    if ma is not None:
        parts.append(f"MA {ma:.2f}")
    if rsi is not None:
        parts.append(f"RSI {rsi:.2f}")
    citation = f"technical_indicators:{symbol}:{indicator_payload['as_of']}"
    return ", ".join(parts), citation


def _news_summary_and_citation(symbol: str, session: Session | None) -> tuple[str, str | None]:
    if session is None:
        return "No external news source is connected in the MVP skeleton.", None

    news_payload = get_news_sentiment_payload(symbol, session=session)
    items = news_payload["items"]
    if not items:
        return "No stored news sentiment is available yet.", None

    latest_news = items[0]
    summary = (
        f"{latest_news['title']}，情绪 {latest_news['sentiment']}，"
        f"置信度 {latest_news['confidence']:.2f}"
    )
    citation = f"news_articles:{symbol}:{latest_news['url']}"
    return summary, citation


def generate_stock_report_payload(
    symbol: str,
    start: date,
    end: date,
    session: Session | None = None,
) -> dict[str, object]:
    bars_payload = get_bars_payload(symbol, "1d", start, end, session=session)
    items = bars_payload["items"]
    first_bar = items[0]
    latest_bar = items[-1]
    change_pct = ((latest_bar["close"] - first_bar["close"]) / first_bar["close"]) * 100
    citations = [f"bars_1d:{symbol}:{latest_bar['timestamp']}"]
    indicator_summary, indicator_citation = _indicator_summary_and_citation(symbol, session)
    if indicator_citation is not None:
        citations.append(indicator_citation)
    news_summary, news_citation = _news_summary_and_citation(symbol, session)
    if news_citation is not None:
        citations.append(news_citation)
    context = ReportContext(
        symbol=symbol,
        as_of=str(latest_bar["timestamp"]),
        price_summary=f"Close {latest_bar['close']:.2f}, period change {change_pct:.2f}%",
        indicator_summary=indicator_summary,
        news_summary=news_summary,
        citations=citations,
    )
    return {
        "symbol": symbol,
        "report_type": "stock_daily",
        "as_of": context.as_of,
        "source": bars_payload["source"],
        "content_markdown": build_stock_report(context),
        "citations": context.citations,
    }
