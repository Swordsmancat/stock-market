from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from apps.api.main import app
from packages.domain.models import (
    DailyBar,
    FundamentalSnapshot,
    Instrument,
    Market,
    NewsArticle,
    SentimentSignal,
    TechnicalIndicator,
)
from packages.shared.database import Base, get_session


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def seed_selection_fixture(session) -> None:
    market = Market(code="US", name="US Stock", timezone="America/New_York", currency="USD")
    session.add(market)
    session.flush()
    instrument = Instrument(
        symbol="AAPL",
        name="Apple Inc.",
        market=market,
        asset_type="stock",
        currency="USD",
    )
    session.add(instrument)
    session.flush()
    session.add(
        DailyBar(
            instrument_id=instrument.id,
            trade_date=date(2026, 1, 20),
            open=Decimal("100"),
            high=Decimal("112"),
            low=Decimal("99"),
            close=Decimal("110"),
            volume=Decimal("1000000"),
        )
    )
    session.add_all(
        [
            TechnicalIndicator(
                instrument_id=instrument.id,
                timeframe="1d",
                as_of=datetime(2026, 1, 20, tzinfo=timezone.utc),
                indicator_code="ma",
                params={"window": 20},
                value_json={"value": 100.0},
            ),
            TechnicalIndicator(
                instrument_id=instrument.id,
                timeframe="1d",
                as_of=datetime(2026, 1, 20, tzinfo=timezone.utc),
                indicator_code="rsi",
                params={"window": 14},
                value_json={"value": 55.0},
            ),
            TechnicalIndicator(
                instrument_id=instrument.id,
                timeframe="1d",
                as_of=datetime(2026, 1, 20, tzinfo=timezone.utc),
                indicator_code="mfi",
                params={"window": 14},
                value_json={"value": 62.0},
            ),
            TechnicalIndicator(
                instrument_id=instrument.id,
                timeframe="1d",
                as_of=datetime(2026, 1, 20, tzinfo=timezone.utc),
                indicator_code="william_r",
                params={"window": 14},
                value_json={"value": -24.0},
            ),
            TechnicalIndicator(
                instrument_id=instrument.id,
                timeframe="1d",
                as_of=datetime(2026, 1, 20, tzinfo=timezone.utc),
                indicator_code="candlestick_patterns",
                params={"rule_set": "candlestick_patterns_v1", "research_signal_only": True},
                value_json={
                    "value": {
                        "rule_set": "candlestick_patterns_v1",
                        "integration_source": "instock_inspired_rules",
                        "status": "evaluated",
                        "research_signal_only": True,
                        "pattern_count": 1,
                        "patterns": [
                            {
                                "code": "hammer",
                                "label": "Hammer",
                                "market_bias": "bullish",
                                "lookback_bars": 1,
                                "rule_set": "candlestick_patterns_v1",
                            }
                        ],
                    }
                },
            ),
            TechnicalIndicator(
                instrument_id=instrument.id,
                timeframe="1d",
                as_of=datetime(2026, 1, 20, tzinfo=timezone.utc),
                indicator_code="chip_distribution",
                params={
                    "rule_set": "chip_distribution_v1",
                    "research_signal_only": True,
                    "approximation": "volume_weighted_without_float_shares",
                },
                value_json={
                    "value": {
                        "rule_set": "chip_distribution_v1",
                        "research_signal_only": True,
                        "approximation": "volume_weighted_without_float_shares",
                        "status": "evaluated",
                        "benefit_ratio": 0.72,
                    }
                },
            ),
        ]
    )
    session.add(
        FundamentalSnapshot(
            symbol="AAPL",
            as_of=date(2026, 1, 19),
            currency="USD",
            pe_ratio=Decimal("25"),
            revenue_growth=Decimal("0.12"),
            net_margin=Decimal("0.24"),
            debt_to_assets=Decimal("0.30"),
            source="test_fixture",
        )
    )
    session.commit()


def seed_news_sentiment(session, symbol: str, sentiment: str, confidence: float) -> NewsArticle:
    article = NewsArticle(
        symbol=symbol,
        title=f"{symbol} stored news",
        url=f"https://example.com/{symbol.lower()}-stored-news",
        source="test_news",
        published_at=datetime(2026, 1, 21, tzinfo=timezone.utc),
        summary=f"{symbol} stored news summary",
        dedupe_hash=f"{symbol.lower()}-{sentiment}-api-news",
    )
    session.add(article)
    session.flush()
    session.add(
        SentimentSignal(
            article_id=article.id,
            symbol=symbol,
            sentiment=sentiment,
            confidence=Decimal(str(confidence)),
            reason="test fixture",
        )
    )
    session.commit()
    return article


def test_stock_selection_api_screens_local_composite_criteria():
    session = make_session()
    seed_selection_fixture(session)

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        response = client.get(
            "/stock-selection/screen",
            params={
                "symbols": "aapl,AAPL",
                "market": "US",
                "asset_type": "stock",
                "max_pe_ratio": 30,
                "min_revenue_growth": 0.1,
                "min_rsi": 40,
                "max_rsi": 70,
                "require_price_above_ma": True,
                "required_pattern_codes": "hammer",
                "min_mfi": 50,
                "max_mfi": 70,
                "min_william_r": -50,
                "max_william_r": -10,
                "min_chip_benefit_ratio": 0.6,
                "min_latest_volume": 1_000_000,
                "min_traded_amount": 100_000_000,
                "watchlist_only": True,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["research_signal_only"] is True
    assert payload["candidate_scope"]["asset_type"] == "stock"
    assert payload["candidate_scope"]["watchlist_only"] is True
    assert payload["count"] == 1
    assert payload["items"][0]["symbol"] == "AAPL"
    assert payload["items"][0]["research_signal_only"] is True
    assert payload["items"][0]["technical_indicators"]["mfi"] == 62.0
    assert payload["items"][0]["technical_indicators"]["william_r"] == -24.0
    assert payload["items"][0]["technical_indicators"]["chip_distribution"]["benefit_ratio"] == 0.72
    assert payload["items"][0]["latest_bar"]["traded_amount"] == 110_000_000.0
    assert {rule["code"] for rule in payload["items"][0]["matched_rules"]} >= {
        "min_latest_volume",
        "min_traded_amount",
        "required_pattern_codes",
        "min_mfi",
        "max_mfi",
        "min_william_r",
        "max_william_r",
        "min_chip_benefit_ratio",
    }
    assert "buy" not in payload["disclaimer"].lower()
    assert payload["items"][0]["evidence_citations"] == [
        "bars_1d:AAPL:2026-01-20",
        "technical_indicators:AAPL:2026-01-20T00:00:00+00:00",
        "fundamental_metrics:AAPL:2026-01-19",
    ]


def test_stock_selection_api_screens_stored_news_sentiment_criteria():
    session = make_session()
    seed_selection_fixture(session)
    article = seed_news_sentiment(session, "AAPL", "positive", 0.82)

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        response = client.get(
            "/stock-selection/screen",
            params={
                "symbols": "AAPL",
                "min_news_article_count": 1,
                "required_news_sentiment": "positive",
                "min_news_sentiment_confidence": 0.75,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["count"] == 1
    item = payload["items"][0]
    assert item["symbol"] == "AAPL"
    assert item["news_sentiment"]["latest_sentiment"] == "positive"
    assert item["news_sentiment"]["latest_confidence"] == 0.82
    assert f"news:AAPL:{article.id}" in item["evidence_citations"]
    assert {rule["code"] for rule in item["matched_rules"]} == {
        "min_news_article_count",
        "required_news_sentiment",
        "min_news_sentiment_confidence",
    }


def test_stock_selection_api_rejects_empty_criteria():
    session = make_session()
    seed_selection_fixture(session)

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        response = client.get("/stock-selection/screen", params={"symbols": "AAPL"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "At least one fundamental, technical, market-data, or news selection criterion is required."
    )


def test_stock_selection_profiles_api_lists_transparent_named_profiles():
    client = TestClient(app)

    response = client.get("/stock-selection/profiles")

    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload["items"]] == [
        "balanced_research",
        "quality_value",
        "trend_liquidity",
    ]
    assert payload["items"][0]["criteria"]["max_pe_ratio"] == 35.0
    assert payload["safety"]["parameters_visible_and_editable"] is True


def test_stock_discovery_api_returns_deterministic_profile_shortlist():
    session = make_session()
    seed_selection_fixture(session)

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        response = client.post(
            "/stock-selection/discover",
            json={
                "profile_id": "balanced_research",
                "market": "US",
                "locale": "en",
                "use_llm": False,
                "shortlist_limit": 5,
                "overrides": {"max_pe_ratio": 30},
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["profile"]["id"] == "balanced_research"
    assert payload["effective_criteria"]["max_pe_ratio"] == 30.0
    assert payload["shortlist_count"] == 1
    assert payload["shortlist"][0]["symbol"] == "AAPL"
    assert payload["model"]["used_llm"] is False
    assert payload["safety"]["deterministic_shortlist"] is True
