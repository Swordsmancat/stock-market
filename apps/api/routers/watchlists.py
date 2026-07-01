from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from packages.services.watchlists import (
    get_default_watchlist_payload,
    remove_watchlist_item,
    upsert_watchlist_item,
)
from packages.shared.database import get_session

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


class WatchlistItemInput(BaseModel):
    symbol: str
    market: str
    name: str | None = None
    is_active: bool = True
    alert_rules: dict[str, Any] = Field(default_factory=dict)


@router.get("")
def get_default_watchlist(session: Session = Depends(get_session)) -> dict[str, object]:
    return get_default_watchlist_payload(session=session)


@router.post("/items")
def upsert_default_watchlist_item(
    payload: WatchlistItemInput,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return upsert_watchlist_item(
        symbol=payload.symbol,
        market=payload.market,
        name=payload.name,
        is_active=payload.is_active,
        alert_rules=payload.alert_rules,
        session=session,
    )


@router.delete("/items")
def remove_default_watchlist_item(
    symbol: str,
    market: str,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return remove_watchlist_item(symbol=symbol, market=market, session=session)
