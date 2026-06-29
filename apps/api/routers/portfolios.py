from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from packages.services.portfolios import get_demo_portfolio_payload
from packages.shared.database import get_session

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.get("/demo")
def get_demo_portfolio(session: Session = Depends(get_session)) -> dict[str, object]:
    return get_demo_portfolio_payload(session=session)
