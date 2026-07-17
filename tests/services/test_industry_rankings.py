from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from packages.domain.models import Base, IndustryDailyRanking
from packages.providers.eastmoney_industry_rankings import IndustryDailyRecord
from packages.services.industry_rankings import get_industry_ranking_payload, refresh_industry_rankings


def test_refresh_ranks_upserts_and_get_is_database_only(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    now = datetime.now(timezone.utc)
    state = {"bank": Decimal("1.2")}
    def fetcher(**kwargs):
        return (IndustryDailyRecord("BK1", "银行", date(2026, 7, 17), state["bank"], now), IndustryDailyRecord("BK2", "保险", date(2026, 7, 17), Decimal("2.4"), now))
    monkeypatch.setattr("packages.services.industry_rankings.get_platform_settings", lambda: {"eastmoney_proxy_url": "", "eastmoney_cookie": ""})
    with Session(engine) as session:
        first = refresh_industry_rankings(session=session, fetcher=fetcher)
        assert first["inserted"] == 2
        state["bank"] = Decimal("3.1")
        second = refresh_industry_rankings(session=session, fetcher=fetcher)
        assert second["updated"] == 2
        assert session.query(IndustryDailyRanking).count() == 2
        payload = get_industry_ranking_payload(session=session, days=12, limit=20)
        assert [(item["name"], item["rank"]) for item in payload["items"]] == [("银行", 1), ("保险", 2)]
