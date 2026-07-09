from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from packages.services.stock_selection import screen_local_stock_selection
from packages.shared.database import get_session

router = APIRouter(prefix="/stock-selection", tags=["stock-selection"])


@router.get("/screen")
def screen_stock_selection(
    symbols: str | None = Query(
        default=None,
        description="Optional comma-separated symbol list. If omitted, stored active instruments are scanned.",
    ),
    market: str | None = Query(default=None, description="Optional market code such as US, CN, or HK."),
    max_pe_ratio: float | None = Query(default=None, ge=0),
    min_revenue_growth: float | None = Query(default=None),
    min_net_margin: float | None = Query(default=None),
    min_rsi: float | None = Query(default=None, ge=0, le=100),
    max_rsi: float | None = Query(default=None, ge=0, le=100),
    require_price_above_ma: bool = Query(default=False),
    required_pattern_codes: str | None = Query(
        default=None,
        description="Optional comma-separated candlestick pattern codes that must be present.",
    ),
    min_mfi: float | None = Query(default=None, ge=0, le=100),
    max_mfi: float | None = Query(default=None, ge=0, le=100),
    min_william_r: float | None = Query(default=None, ge=-100, le=0),
    max_william_r: float | None = Query(default=None, ge=-100, le=0),
    min_chip_benefit_ratio: float | None = Query(default=None, ge=0, le=1),
    max_chip_benefit_ratio: float | None = Query(default=None, ge=0, le=1),
    min_latest_volume: float | None = Query(default=None, ge=0),
    min_traded_amount: float | None = Query(default=None, ge=0),
    min_news_article_count: int | None = Query(default=None, ge=1),
    required_news_sentiment: str | None = Query(
        default=None,
        description="Optional latest stored sentiment label, such as positive, neutral, or negative.",
    ),
    min_news_sentiment_confidence: float | None = Query(default=None, ge=0, le=1),
    watchlist_only: bool = Query(
        default=False,
        description="When true, scan only active instruments in the default watchlist.",
    ),
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    payload = screen_local_stock_selection(
        session=session,
        symbols=_parse_symbols(symbols),
        market=market,
        max_pe_ratio=max_pe_ratio,
        min_revenue_growth=min_revenue_growth,
        min_net_margin=min_net_margin,
        min_rsi=min_rsi,
        max_rsi=max_rsi,
        require_price_above_ma=require_price_above_ma,
        required_pattern_codes=_parse_csv(required_pattern_codes),
        min_mfi=min_mfi,
        max_mfi=max_mfi,
        min_william_r=min_william_r,
        max_william_r=max_william_r,
        min_chip_benefit_ratio=min_chip_benefit_ratio,
        max_chip_benefit_ratio=max_chip_benefit_ratio,
        min_latest_volume=min_latest_volume,
        min_traded_amount=min_traded_amount,
        min_news_article_count=min_news_article_count,
        required_news_sentiment=required_news_sentiment,
        min_news_sentiment_confidence=min_news_sentiment_confidence,
        watchlist_only=watchlist_only,
        limit=limit,
    )
    if payload["status"] == "invalid_request":
        raise HTTPException(status_code=400, detail=payload["diagnostics"][0]["message"])
    return payload


def _parse_symbols(value: str | None) -> list[str] | None:
    return _parse_csv(value)


def _parse_csv(value: str | None) -> list[str] | None:
    if value is None:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]
