from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from packages.services.instrument_universe import get_instrument_universe_status
from packages.services.research_evidence_backfill import get_evidence_coverage
from packages.services.stock_discovery import discover_local_stocks
from packages.services.stock_selection import screen_local_stock_selection
from packages.services.stock_selection_profiles import get_stock_selection_profiles_payload
from packages.shared.database import get_session

router = APIRouter(prefix="/stock-selection", tags=["stock-selection"])


class StockSelectionOverrides(BaseModel):
    max_pe_ratio: float | None = Field(default=None, ge=0)
    min_revenue_growth: float | None = None
    min_net_margin: float | None = None
    min_rsi: float | None = Field(default=None, ge=0, le=100)
    max_rsi: float | None = Field(default=None, ge=0, le=100)
    require_price_above_ma: bool | None = None
    required_pattern_codes: list[str] | None = None
    min_mfi: float | None = Field(default=None, ge=0, le=100)
    max_mfi: float | None = Field(default=None, ge=0, le=100)
    min_william_r: float | None = Field(default=None, ge=-100, le=0)
    max_william_r: float | None = Field(default=None, ge=-100, le=0)
    min_chip_benefit_ratio: float | None = Field(default=None, ge=0, le=1)
    max_chip_benefit_ratio: float | None = Field(default=None, ge=0, le=1)
    min_latest_volume: float | None = Field(default=None, ge=0)
    min_traded_amount: float | None = Field(default=None, ge=0)
    min_news_article_count: int | None = Field(default=None, ge=1)
    required_news_sentiment: str | None = Field(default=None, max_length=32)
    min_news_sentiment_confidence: float | None = Field(default=None, ge=0, le=1)


class StockDiscoveryRequest(BaseModel):
    profile_id: str = Field(default="balanced_research", min_length=1, max_length=64)
    overrides: StockSelectionOverrides = Field(default_factory=StockSelectionOverrides)
    market: str = Field(default="CN", min_length=1, max_length=32)
    asset_type: str = Field(default="stock", min_length=1, max_length=32)
    watchlist_only: bool = False
    shortlist_limit: int = Field(default=10, ge=1, le=20)
    locale: Literal["zh", "en"] = "zh"
    use_llm: bool = True


@router.get("/profiles")
def get_stock_selection_profiles() -> dict[str, object]:
    return get_stock_selection_profiles_payload()


@router.get("/evidence-coverage")
def get_stock_selection_evidence_coverage(
    market: str = Query(default="CN"),
    provider: str = Query(default="akshare"),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    try:
        return get_evidence_coverage(
            session=session,
            market=market,
            provider=provider,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/universe-status")
def get_stock_selection_universe_status(
    market: str = Query(default="CN"),
    provider: str = Query(default="akshare"),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    try:
        return get_instrument_universe_status(
            session=session,
            market=market,
            provider_name=provider,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/discover")
def discover_stock_selection(
    request: StockDiscoveryRequest,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    try:
        return discover_local_stocks(
            session=session,
            profile_id=request.profile_id,
            overrides=request.overrides.model_dump(exclude_none=True),
            market=request.market,
            asset_type=request.asset_type,
            watchlist_only=request.watchlist_only,
            shortlist_limit=request.shortlist_limit,
            locale=request.locale,
            use_llm=request.use_llm,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/screen")
def screen_stock_selection(
    symbols: str | None = Query(
        default=None,
        description="Optional comma-separated symbol list. If omitted, stored active instruments are scanned.",
    ),
    market: str | None = Query(default=None, description="Optional market code such as US, CN, or HK."),
    asset_type: str | None = Query(default=None, description="Optional stored instrument asset type."),
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
        asset_type=asset_type,
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
