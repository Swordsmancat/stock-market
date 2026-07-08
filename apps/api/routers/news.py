from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from packages.services.news import get_news_sentiment_payload, ingest_mock_news
from packages.services.news_search import (
    search_and_ingest_news_candidates,
    search_news_candidates,
)
from packages.shared.database import get_session

router = APIRouter(prefix="/news", tags=["news"])


@router.post("/mock-ingest")
def mock_ingest_news(
    symbol: str = Query(...),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return ingest_mock_news(symbol, session=session)


@router.get("/search")
def search_news(
    symbol: str = Query(...),
    query: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return search_news_candidates(symbol, query=query, session=session)


@router.post("/search-ingest")
def search_ingest_news(
    symbol: str = Query(...),
    query: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return search_and_ingest_news_candidates(symbol, query=query, session=session)


@router.get("/{symbol}")
def get_news(symbol: str, session: Session = Depends(get_session)) -> dict[str, object]:
    return get_news_sentiment_payload(symbol, session=session)
