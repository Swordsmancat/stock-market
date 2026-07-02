from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from packages.services.fundamentals import ingest_fundamentals
from packages.services.indicators import calculate_and_store_daily_indicators
from packages.services.ingestion import ingest_market_snapshot
from packages.services.news import ingest_news
from packages.services.reports import generate_and_store_daily_report


def refresh_stock_analysis(
    symbol: str,
    market: str,
    start: date,
    end: date,
    session: Session,
    ma_window: int = 20,
    provider_name: str = "mock",
    task_run_id: UUID | str | None = None,
) -> dict[str, object]:
    ingestion = ingest_market_snapshot(
        market,
        start,
        end,
        session=session,
        provider_name=provider_name,
    )
    indicators = calculate_and_store_daily_indicators(
        symbol,
        start,
        end,
        session=session,
        ma_window=ma_window,
    )
    news = ingest_news(symbol, session=session, provider_name=provider_name)
    fundamentals = ingest_fundamentals(
        symbol,
        session=session,
        provider_name=provider_name,
        as_of=end,
    )
    report = generate_and_store_daily_report(
        symbol,
        start,
        end,
        session=session,
        task_run_id=task_run_id,
        provider_name=provider_name,
    )

    return {
        "symbol": symbol,
        "market": market,
        "status": "refreshed",
        "ingestion": ingestion,
        "indicators": indicators,
        "news": news,
        "fundamentals": fundamentals,
        "report": report,
    }
