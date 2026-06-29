from fastapi import APIRouter

from packages.services.portfolios import get_demo_portfolio_payload

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.get("/demo")
def get_demo_portfolio() -> dict[str, object]:
    return get_demo_portfolio_payload()
