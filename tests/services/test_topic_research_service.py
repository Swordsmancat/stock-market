from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from packages.domain.models import (
    Base,
    FundamentalSnapshot,
    IndustryDailyRanking,
    Instrument,
    Market,
    NewsArticle,
)
from packages.services.topic_research import get_topic_research_payload
import packages.services.topic_research as topic_research


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def _seed(session):
    market = Market(code="CN", name="China", timezone="Asia/Shanghai", currency="CNY")
    session.add(market)
    session.flush()
    session.add(
        Instrument(
            symbol="600519",
            name="Kweichow Moutai",
            market_id=market.id,
            asset_type="stock",
            currency="CNY",
            is_active=True,
        )
    )
    session.add_all(
        [
            NewsArticle(
                symbol="600519",
                title="消费复苏推动白酒零售回暖",
                url="https://example.com/consumer",
                source="stored-news",
                published_at=datetime(2026, 7, 16, 8, tzinfo=timezone.utc),
                summary="白酒渠道库存改善。",
                dedupe_hash="consumer-news",
            ),
            NewsArticle(
                symbol="000001",
                title="Unrelated bank update",
                url="https://example.com/bank",
                source="stored-news",
                published_at=datetime(2026, 7, 17, 8, tzinfo=timezone.utc),
                summary=None,
                dedupe_hash="bank-news",
            ),
        ]
    )
    session.add_all(
        [
            IndustryDailyRanking(
                provider="eastmoney",
                taxonomy="industry",
                industry_code="BK0001",
                industry_name="食品饮料",
                trade_date=date(2026, 7, 17),
                change_percent=Decimal("1.25"),
                rank=3,
                source_url="https://quote.eastmoney.com/",
                retrieved_at=datetime(2026, 7, 17, 9, tzinfo=timezone.utc),
            ),
            IndustryDailyRanking(
                provider="eastmoney",
                taxonomy="industry",
                industry_code="BK0001",
                industry_name="食品饮料",
                trade_date=date(2026, 7, 16),
                change_percent=Decimal("-0.50"),
                rank=8,
                source_url="https://quote.eastmoney.com/",
                retrieved_at=datetime(2026, 7, 16, 9, tzinfo=timezone.utc),
            ),
        ]
    )
    session.add_all(
        [
            FundamentalSnapshot(
                symbol="600519",
                as_of=date(2026, 6, 30),
                currency="CNY",
                source="eastmoney_public",
                company_json={},
            ),
            FundamentalSnapshot(
                symbol="600519",
                as_of=date(2026, 3, 31),
                currency="CNY",
                source="eastmoney_public",
                company_json={
                    "name": "贵州茅台",
                    "industry": "白酒消费",
                    "business_scope": "白酒生产与销售",
                    "profile": "消费品公司",
                },
            ),
            FundamentalSnapshot(
                symbol="600519",
                as_of=date(2025, 12, 31),
                currency="CNY",
                source="eastmoney_public",
                company_json={"name": "旧记录", "industry": "白酒消费"},
            ),
            FundamentalSnapshot(
                symbol="688382",
                as_of=date(2026, 3, 31),
                currency="CNY",
                source="eastmoney_public",
                company_json={
                    "name": "医药公司",
                    "industry": "医药制造业",
                    "business_scope": "药品生产、批发及零售",
                },
            ),
        ]
    )
    session.commit()


def test_topic_projection_matches_stored_evidence_with_reasons(session):
    _seed(session)

    payload = get_topic_research_payload(
        session=session,
        topic="consumption",
        window="90d",
        as_of=date(2026, 7, 18),
    )

    assert payload["status"] == "ready"
    assert payload["source"] == "database"
    assert payload["taxonomy_version"] == "focused-topic-v1"
    assert payload["period"] == {"start": "2026-04-20", "end": "2026-07-18"}
    assert payload["evidence_count"] == 4
    assert payload["latest_evidence_date"] == "2026-07-17"
    assert payload["sections"]["news"]["total"] == 1
    assert payload["sections"]["companies"]["total"] == 1
    assert payload["sections"]["news"]["items"][0]["matched_on"] == {
        "field": "title",
        "keyword": "消费",
    }
    assert [item["date"] for item in payload["sections"]["industry_rankings"]["items"]] == [
        "2026-07-17",
        "2026-07-16",
    ]
    company = payload["sections"]["companies"]["items"][0]
    assert company["name"] == "贵州茅台"
    assert company["market"] == "CN"
    assert company["as_of"] == "2026-03-31"


def test_topic_projection_returns_truthful_empty_sections(session):
    payload = get_topic_research_payload(
        session=session,
        topic="real_estate",
        window="30d",
        as_of=date(2026, 7, 18),
    )

    assert payload["status"] == "empty"
    assert payload["evidence_count"] == 0
    assert payload["latest_evidence_date"] is None
    assert all(section["status"] == "empty" for section in payload["sections"].values())
    assert payload["safety"] == {"research_only": True, "trading_enabled": False}


def test_topic_projection_validates_topic_and_window(session):
    with pytest.raises(ValueError, match="Unsupported topic"):
        get_topic_research_payload(session=session, topic="fx")
    with pytest.raises(ValueError, match="Unsupported topic window"):
        get_topic_research_payload(session=session, window="365d")


def test_topic_projection_uses_shanghai_date_by_default(session, monkeypatch):
    monkeypatch.setattr(topic_research, "_shanghai_today", lambda: date(2026, 7, 18))

    payload = get_topic_research_payload(session=session, window="30d")

    assert payload["period"] == {"start": "2026-06-19", "end": "2026-07-18"}
