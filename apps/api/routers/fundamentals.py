from datetime import date

from fastapi import APIRouter, Query

from packages.services.fundamentals import get_fundamental_payload

router = APIRouter(prefix="/fundamentals", tags=["fundamentals"])


@router.get("/{symbol}")
def get_fundamentals(
    symbol: str,
    as_of: date | None = Query(default=None),
) -> dict[str, object]:
    return get_fundamental_payload(symbol, as_of=as_of)
