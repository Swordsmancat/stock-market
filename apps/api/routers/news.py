from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from packages.services.news import get_news_sentiment_payload, ingest_mock_news
from packages.shared.database import get_session

router = APIRouter(prefix="/news", tags=["news"])


@router.post("/mock-ingest")
def mock_ingest_news(
    symbol: str = Query(...),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return ingest_mock_news(symbol, session=session)


@router.get("/{symbol}")
def get_news(symbol: str, session: Session = Depends(get_session)) -> dict[str, object]:
    return get_news_sentiment_payload(symbol, session=session)
