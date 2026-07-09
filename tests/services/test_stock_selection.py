from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.domain.models import (
    DailyBar,
    FundamentalSnapshot,
    Instrument,
    Market,
    NewsArticle,
    SentimentSignal,
    TechnicalIndicator,
)
from packages.services.stock_selection import screen_local_stock_selection
from packages.services.watchlists import upsert_watchlist_item
from packages.shared.database import Base


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def seed_instrument(
    session,
    symbol: str,
    *,
    close: float,
    ma: float,
    rsi: float,
    mfi: float | None = 55.0,
    william_r: float | None = -30.0,
    pattern_codes: list[str] | None = None,
    chip_benefit_ratio: float | None = 0.65,
    pe_ratio: float = 25.0,
    revenue_growth: float = 0.12,
    net_margin: float = 0.24,
) -> None:
    market = session.query(Market).filter(Market.code == "US").one_or_none()
    if market is None:
        market = Market(code="US", name="US Stock", timezone="America/New_York", currency="USD")
        session.add(market)
        session.flush()
    instrument = Instrument(
        symbol=symbol,
        name=symbol,
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
            high=Decimal(str(close + 1)),
            low=Decimal("99"),
            close=Decimal(str(close)),
            volume=Decimal("1000000"),
        )
    )
    indicator_as_of = datetime(2026, 1, 20, tzinfo=timezone.utc)
    indicator_rows = [
        TechnicalIndicator(
            instrument_id=instrument.id,
            timeframe="1d",
            as_of=indicator_as_of,
            indicator_code="ma",
            params={"window": 20},
            value_json={"value": ma},
        ),
        TechnicalIndicator(
            instrument_id=instrument.id,
            timeframe="1d",
            as_of=indicator_as_of,
            indicator_code="rsi",
            params={"window": 14},
            value_json={"value": rsi},
        ),
        TechnicalIndicator(
            instrument_id=instrument.id,
            timeframe="1d",
            as_of=indicator_as_of,
            indicator_code="candlestick_patterns",
            params={"rule_set": "candlestick_patterns_v1", "research_signal_only": True},
            value_json={"value": _candlestick_payload(pattern_codes or [])},
        ),
    ]
    if mfi is not None:
        indicator_rows.append(
            TechnicalIndicator(
                instrument_id=instrument.id,
                timeframe="1d",
                as_of=indicator_as_of,
                indicator_code="mfi",
                params={"window": 14},
                value_json={"value": mfi},
            )
        )
    if william_r is not None:
        indicator_rows.append(
            TechnicalIndicator(
                instrument_id=instrument.id,
                timeframe="1d",
                as_of=indicator_as_of,
                indicator_code="william_r",
                params={"window": 14},
                value_json={"value": william_r},
            )
        )
    if chip_benefit_ratio is not None:
        indicator_rows.append(
            TechnicalIndicator(
                instrument_id=instrument.id,
                timeframe="1d",
                as_of=indicator_as_of,
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
                        "benefit_ratio": chip_benefit_ratio,
                    }
                },
            )
        )
    session.add_all(indicator_rows)
    session.add(
        FundamentalSnapshot(
            symbol=symbol,
            as_of=date(2026, 1, 19),
            currency="USD",
            pe_ratio=Decimal(str(pe_ratio)),
            revenue_growth=Decimal(str(revenue_growth)),
            net_margin=Decimal(str(net_margin)),
            debt_to_assets=Decimal("0.30"),
            source="test_fixture",
        )
    )
    session.commit()


def seed_news_sentiment(
    session,
    symbol: str,
    *,
    sentiment: str,
    confidence: float,
    published_at: datetime | None = None,
) -> NewsArticle:
    article = NewsArticle(
        symbol=symbol,
        title=f"{symbol} stored news",
        url=f"https://example.com/{symbol.lower()}-stored-news",
        source="test_news",
        published_at=published_at or datetime(2026, 1, 21, tzinfo=timezone.utc),
        summary=f"{symbol} stored news summary",
        dedupe_hash=f"{symbol.lower()}-{sentiment}-stored-news",
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


def _candlestick_payload(pattern_codes: list[str]) -> dict[str, object]:
    return {
        "rule_set": "candlestick_patterns_v1",
        "integration_source": "instock_inspired_rules",
        "status": "evaluated",
        "research_signal_only": True,
        "pattern_count": len(pattern_codes),
        "patterns": [
            {
                "code": pattern_code,
                "label": pattern_code.replace("_", " ").title(),
                "market_bias": "neutral",
                "lookback_bars": 1,
                "rule_set": "candlestick_patterns_v1",
            }
            for pattern_code in pattern_codes
        ],
    }


def test_stock_selection_matches_local_fundamental_and_technical_criteria():
    session = make_session()
    seed_instrument(session, "AAPL", close=110.0, ma=100.0, rsi=55.0)
    seed_instrument(session, "MSFT", close=90.0, ma=100.0, rsi=72.0, pe_ratio=42.0)

    payload = screen_local_stock_selection(
        session=session,
        symbols=["aapl", "MSFT", "AAPL"],
        max_pe_ratio=30.0,
        min_revenue_growth=0.10,
        min_net_margin=0.20,
        min_rsi=40.0,
        max_rsi=70.0,
        require_price_above_ma=True,
    )

    assert payload["status"] == "ok"
    assert payload["rule_set"] == "instock_composite_selection_v1"
    assert payload["research_signal_only"] is True
    assert payload["count"] == 1
    item = payload["items"][0]
    assert item["symbol"] == "AAPL"
    assert item["score"] == 1.0
    assert item["latest_bar"]["close"] == 110.0
    assert item["fundamentals"]["pe_ratio"] == 25.0
    assert item["technical_indicators"]["rsi"] == 55.0
    assert {rule["code"] for rule in item["matched_rules"]} == {
        "max_pe_ratio",
        "min_revenue_growth",
        "min_net_margin",
        "min_rsi",
        "max_rsi",
        "require_price_above_ma",
    }
    assert item["evidence_citations"] == [
        "bars_1d:AAPL:2026-01-20",
        "technical_indicators:AAPL:2026-01-20T00:00:00+00:00",
        "fundamental_metrics:AAPL:2026-01-19",
    ]
    assert any(
        diagnostic["symbol"] == "MSFT" and diagnostic["rule"] == "max_pe_ratio"
        for diagnostic in payload["diagnostics"]
    )


def test_stock_selection_matches_stored_technical_evidence_criteria():
    session = make_session()
    seed_instrument(
        session,
        "AAPL",
        close=110.0,
        ma=100.0,
        rsi=55.0,
        mfi=62.0,
        william_r=-24.0,
        pattern_codes=["hammer", "doji"],
        chip_benefit_ratio=0.72,
    )
    seed_instrument(
        session,
        "MSFT",
        close=108.0,
        ma=100.0,
        rsi=57.0,
        mfi=82.0,
        william_r=-7.0,
        pattern_codes=["doji"],
        chip_benefit_ratio=0.42,
    )

    payload = screen_local_stock_selection(
        session=session,
        symbols=["AAPL", "MSFT"],
        required_pattern_codes=["HAMMER", "hammer"],
        min_mfi=50.0,
        max_mfi=70.0,
        min_william_r=-50.0,
        max_william_r=-10.0,
        min_chip_benefit_ratio=0.60,
        max_chip_benefit_ratio=0.80,
    )

    assert payload["status"] == "ok"
    assert payload["criteria"]["required_pattern_codes"] == ["hammer"]
    assert payload["count"] == 1
    item = payload["items"][0]
    assert item["symbol"] == "AAPL"
    assert item["score"] == 1.0
    assert item["technical_indicators"]["mfi"] == 62.0
    assert item["technical_indicators"]["william_r"] == -24.0
    assert item["technical_indicators"]["chip_distribution"]["benefit_ratio"] == 0.72
    assert item["technical_indicators"]["candlestick_patterns"]["patterns"][0]["code"] == "hammer"
    assert {rule["code"] for rule in item["matched_rules"]} == {
        "required_pattern_codes",
        "min_mfi",
        "max_mfi",
        "min_william_r",
        "max_william_r",
        "min_chip_benefit_ratio",
        "max_chip_benefit_ratio",
    }
    assert any(
        diagnostic["symbol"] == "MSFT"
        and diagnostic["rule"] == "required_pattern_codes"
        and diagnostic["details"]["missing_pattern_codes"] == ["hammer"]
        for diagnostic in payload["diagnostics"]
    )


def test_stock_selection_matches_stored_news_sentiment_criteria():
    session = make_session()
    seed_instrument(session, "AAPL", close=110.0, ma=100.0, rsi=55.0)
    seed_instrument(session, "MSFT", close=112.0, ma=100.0, rsi=58.0)
    aapl_news = seed_news_sentiment(session, "AAPL", sentiment="positive", confidence=0.82)
    seed_news_sentiment(session, "MSFT", sentiment="negative", confidence=0.91)

    payload = screen_local_stock_selection(
        session=session,
        symbols=["AAPL", "MSFT"],
        min_news_article_count=1,
        required_news_sentiment="Positive",
        min_news_sentiment_confidence=0.75,
    )

    assert payload["status"] == "ok"
    assert payload["criteria"]["required_news_sentiment"] == "positive"
    assert payload["count"] == 1
    item = payload["items"][0]
    assert item["symbol"] == "AAPL"
    assert item["news_sentiment"]["article_count"] == 1
    assert item["news_sentiment"]["latest_sentiment"] == "positive"
    assert item["news_sentiment"]["latest_confidence"] == 0.82
    assert item["news_sentiment"]["citation_id"] == f"news:AAPL:{aapl_news.id}"
    assert f"news:AAPL:{aapl_news.id}" in item["evidence_citations"]
    assert {rule["code"] for rule in item["matched_rules"]} == {
        "min_news_article_count",
        "required_news_sentiment",
        "min_news_sentiment_confidence",
    }
    assert any(
        diagnostic["symbol"] == "MSFT"
        and diagnostic["rule"] == "required_news_sentiment"
        and diagnostic["details"]["actual"] == "negative"
        for diagnostic in payload["diagnostics"]
    )


def test_stock_selection_reports_missing_news_without_fabricating_match():
    session = make_session()
    seed_instrument(session, "AAPL", close=110.0, ma=100.0, rsi=55.0)

    payload = screen_local_stock_selection(
        session=session,
        symbols=["AAPL"],
        min_news_article_count=1,
    )

    assert payload["status"] == "ok"
    assert payload["items"] == []
    assert payload["diagnostics"] == [
        {
            "symbol": "AAPL",
            "code": "SELECTION_RULE_NOT_MATCHED",
            "rule": "min_news_article_count",
            "message": "A requested stock-selection criterion was not matched.",
            "details": {
                "code": "min_news_article_count",
                "field": "news.article_count",
                "status": "not_matched",
                "actual": 0.0,
                "threshold": 1.0,
            },
        }
    ]


def test_stock_selection_reports_missing_technical_evidence_without_fabricating_match():
    session = make_session()
    seed_instrument(session, "AAPL", close=110.0, ma=100.0, rsi=55.0, mfi=None)

    payload = screen_local_stock_selection(
        session=session,
        symbols=["AAPL"],
        min_mfi=50.0,
    )

    assert payload["status"] == "ok"
    assert payload["items"] == []
    assert payload["diagnostics"] == [
        {
            "symbol": "AAPL",
            "code": "SELECTION_RULE_NOT_MATCHED",
            "rule": "min_mfi",
            "message": "A requested stock-selection criterion was not matched.",
            "details": {
                "code": "min_mfi",
                "field": "mfi",
                "status": "missing_value",
                "actual": None,
                "threshold": 50.0,
            },
        }
    ]


def test_stock_selection_can_scope_candidates_to_active_watchlist_items():
    session = make_session()
    seed_instrument(session, "AAPL", close=110.0, ma=100.0, rsi=55.0)
    seed_instrument(session, "MSFT", close=112.0, ma=100.0, rsi=56.0)
    upsert_watchlist_item("AAPL", "US", session=session, name="Apple Inc.")

    payload = screen_local_stock_selection(
        session=session,
        watchlist_only=True,
        min_rsi=40.0,
        max_rsi=70.0,
    )

    assert payload["status"] == "ok"
    assert payload["candidate_scope"] == {
        "symbols": [],
        "market": None,
        "watchlist_only": True,
    }
    assert payload["count"] == 1
    assert payload["items"][0]["symbol"] == "AAPL"


def test_stock_selection_requires_at_least_one_criterion():
    session = make_session()
    seed_instrument(session, "AAPL", close=110.0, ma=100.0, rsi=55.0)

    payload = screen_local_stock_selection(session=session, symbols=["AAPL"])

    assert payload["status"] == "invalid_request"
    assert payload["items"] == []
    assert payload["diagnostics"][0]["code"] == "NO_SELECTION_CRITERIA"
    assert payload["diagnostics"][0]["message"] == (
        "At least one fundamental, technical, or news selection criterion is required."
    )


def test_stock_selection_reports_missing_fundamentals_without_fabricating_match():
    session = make_session()
    seed_instrument(session, "AAPL", close=110.0, ma=100.0, rsi=55.0)
    session.query(FundamentalSnapshot).delete()
    session.commit()

    payload = screen_local_stock_selection(
        session=session,
        symbols=["AAPL"],
        max_pe_ratio=30.0,
    )

    assert payload["status"] == "ok"
    assert payload["items"] == []
    assert payload["diagnostics"] == [
        {
            "symbol": "AAPL",
            "code": "MISSING_FUNDAMENTALS",
            "message": "Fundamental criteria were requested but no stored snapshot is available.",
        }
    ]
