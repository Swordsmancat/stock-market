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
        limit=limit,
    )
    if payload["status"] == "invalid_request":
        raise HTTPException(status_code=400, detail=payload["diagnostics"][0]["message"])
    return payload


def _parse_symbols(value: str | None) -> list[str] | None:
    if value is None:
        return None
    return [symbol.strip() for symbol in value.split(",") if symbol.strip()]
