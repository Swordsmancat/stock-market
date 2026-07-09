"""API router for provider-backed daily market context."""

from fastapi import APIRouter, Query

from packages.services.market_daily_data import (
    get_block_trades_payload,
    get_dragon_tiger_list_payload,
    get_limit_up_reasons_payload,
    get_stock_fund_flow_payload,
)


router = APIRouter()


@router.get("/market-daily-data/fund-flow/stocks")
async def get_stock_fund_flow(
    market: str = Query("CN", description="Market code. Phase 1 supports CN."),
    window: str = Query("today", description="Fund-flow window: today, 3d, 5d, or 10d"),
    limit: int = Query(20, ge=1, le=100, description="Number of stock rows to return"),
    provider: str | None = Query(default=None, description="Optional market daily-data provider"),
) -> dict[str, object]:
    """Get A-share individual stock fund-flow ranking."""
    return get_stock_fund_flow_payload(
        market=market,
        window=window,
        limit=limit,
        provider_name=provider,
    )


@router.get("/market-daily-data/limit-up-reasons")
async def get_limit_up_reasons(
    trade_date: str | None = Query(
        default=None,
        alias="date",
        description="Trade date as YYYY-MM-DD or YYYYMMDD. Defaults to today.",
    ),
    market: str = Query("CN", description="Market code. Phase 1 supports CN."),
    limit: int = Query(50, ge=1, le=100, description="Number of rows to return"),
    provider: str | None = Query(default=None, description="Optional market daily-data provider"),
) -> dict[str, object]:
    """Get A-share limit-up reason context when the provider exposes it."""
    return get_limit_up_reasons_payload(
        trade_date=trade_date,
        market=market,
        limit=limit,
        provider_name=provider,
    )


@router.get("/market-daily-data/dragon-tiger-list")
async def get_dragon_tiger_list(
    trade_date: str | None = Query(
        default=None,
        alias="date",
        description="Trade date as YYYY-MM-DD or YYYYMMDD. Defaults to today.",
    ),
    market: str = Query("CN", description="Market code. Phase 1 supports CN."),
    limit: int = Query(50, ge=1, le=100, description="Number of rows to return"),
    provider: str | None = Query(default=None, description="Optional market daily-data provider"),
) -> dict[str, object]:
    """Get A-share Dragon Tiger List context."""
    return get_dragon_tiger_list_payload(
        trade_date=trade_date,
        market=market,
        limit=limit,
        provider_name=provider,
    )


@router.get("/market-daily-data/block-trades")
async def get_block_trades(
    trade_date: str | None = Query(
        default=None,
        alias="date",
        description="Trade date as YYYY-MM-DD or YYYYMMDD. Defaults to today.",
    ),
    market: str = Query("CN", description="Market code. Phase 1 supports CN."),
    limit: int = Query(50, ge=1, le=100, description="Number of rows to return"),
    provider: str | None = Query(default=None, description="Optional market daily-data provider"),
) -> dict[str, object]:
    """Get A-share block-trade context."""
    return get_block_trades_payload(
        trade_date=trade_date,
        market=market,
        limit=limit,
        provider_name=provider,
    )
