from datetime import date

from sqlalchemy.orm import Session

from packages.services.indicators import calculate_and_store_daily_indicators
from packages.services.ingestion import ingest_mock_market_snapshot
from packages.services.news import ingest_mock_news
from packages.services.reports import generate_stock_report_payload


def refresh_stock_analysis(
    symbol: str,
    market: str,
    start: date,
    end: date,
    session: Session,
    ma_window: int = 20,
) -> dict[str, object]:
    ingestion = ingest_mock_market_snapshot(market, start, end, session=session)
    indicators = calculate_and_store_daily_indicators(
        symbol,
        start,
        end,
        session=session,
        ma_window=ma_window,
    )
    news = ingest_mock_news(symbol, session=session)
    report = generate_stock_report_payload(symbol, start, end, session=session)

    return {
        "symbol": symbol,
        "market": market,
        "status": "refreshed",
        "ingestion": ingestion,
        "indicators": indicators,
        "news": news,
        "report": report,
    }
