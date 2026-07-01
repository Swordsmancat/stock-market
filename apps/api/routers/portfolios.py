from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from packages.services.portfolios import (
    create_portfolio_payload,
    delete_portfolio_payload,
    get_demo_portfolio_payload,
    get_portfolio_payload,
    list_portfolios_payload,
    remove_portfolio_position_payload,
    update_portfolio_payload,
    upsert_portfolio_position_payload,
)
from packages.shared.database import get_session

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


class PortfolioInput(BaseModel):
    name: str
    base_currency: str = "USD"
    risk_profile: str | None = None


class PortfolioUpdateInput(BaseModel):
    name: str | None = None
    base_currency: str | None = None
    risk_profile: str | None = None


class PortfolioPositionInput(BaseModel):
    symbol: str
    market: str
    quantity: float = Field(gt=0)
    avg_cost: float = Field(gt=0)
    name: str | None = None


@router.get("")
def list_portfolios(session: Session = Depends(get_session)) -> dict[str, object]:
    return list_portfolios_payload(session=session)


@router.get("/demo")
def get_demo_portfolio(session: Session = Depends(get_session)) -> dict[str, object]:
    return get_demo_portfolio_payload(session=session)


@router.get("/{portfolio_id}")
def get_portfolio(portfolio_id: str, session: Session = Depends(get_session)) -> dict[str, object]:
    payload = get_portfolio_payload(portfolio_id, session=session)
    if payload is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return payload


@router.post("")
def create_portfolio(payload: PortfolioInput, session: Session = Depends(get_session)) -> dict[str, object]:
    return create_portfolio_payload(
        name=payload.name,
        base_currency=payload.base_currency,
        risk_profile=payload.risk_profile,
        session=session,
    )


@router.patch("/{portfolio_id}")
def update_portfolio(
    portfolio_id: str,
    payload: PortfolioUpdateInput,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    result = update_portfolio_payload(
        portfolio_id,
        session=session,
        name=payload.name,
        base_currency=payload.base_currency,
        risk_profile=payload.risk_profile,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Portfolio not found or cannot be updated")
    return result


@router.delete("/{portfolio_id}")
def delete_portfolio(portfolio_id: str, session: Session = Depends(get_session)) -> dict[str, object]:
    result = delete_portfolio_payload(portfolio_id, session=session)
    if result is None:
        raise HTTPException(status_code=404, detail="Portfolio not found or cannot be deleted")
    return result


@router.post("/{portfolio_id}/positions")
def upsert_portfolio_position(
    portfolio_id: str,
    payload: PortfolioPositionInput,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    result = upsert_portfolio_position_payload(
        portfolio_id,
        payload.symbol,
        payload.market,
        payload.quantity,
        payload.avg_cost,
        session=session,
        name=payload.name,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return result


@router.delete("/{portfolio_id}/positions")
def remove_portfolio_position(
    portfolio_id: str,
    symbol: str = Query(...),
    market: str = Query(...),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    result = remove_portfolio_position_payload(portfolio_id, symbol, market, session=session)
    if result is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return result
