from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from packages.domain.models import Base
from packages.providers.eastmoney_industry_rankings import IndustryDailyRecord
from packages.services.industry_rankings import (
    get_industry_ranking_payload,
    refresh_industry_rankings,
)


def test_partial_refresh_recomputes_ranks_across_the_stored_date(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    now = datetime.now(timezone.utc)
    monkeypatch.setattr(
        "packages.services.industry_rankings.get_platform_settings",
        lambda: {"eastmoney_proxy_url": "", "eastmoney_cookie": ""},
    )

    def initial_fetcher(**kwargs):
        return (
            IndustryDailyRecord("BK1", "One", date(2026, 7, 17), Decimal("1.0"), now),
            IndustryDailyRecord("BK2", "Two", date(2026, 7, 17), Decimal("2.0"), now),
        )

    def partial_fetcher(**kwargs):
        return (
            IndustryDailyRecord("BK3", "Three", date(2026, 7, 17), Decimal("3.0"), now),
        )

    with Session(engine) as session:
        refresh_industry_rankings(session=session, fetcher=initial_fetcher)
        refresh_industry_rankings(session=session, fetcher=partial_fetcher)
        payload = get_industry_ranking_payload(session=session, days=1, limit=20)

    assert [(item["code"], item["rank"]) for item in payload["items"]] == [
        ("BK3", 1),
        ("BK2", 2),
        ("BK1", 3),
    ]
