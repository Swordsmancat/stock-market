from datetime import date, datetime, timezone
from unittest.mock import patch

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.providers.eastmoney_public_news import EastmoneyPublicNewsItem
from packages.domain.models import FundamentalSnapshot as FundamentalSnapshotModel
from packages.services.fundamentals import ingest_akshare_fundamentals, ingest_fundamentals
from packages.services.news import ingest_akshare_news, ingest_news
from packages.shared.database import Base


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_ingest_fundamentals_routes_to_akshare(monkeypatch):
    session = make_session()

    def fake_akshare_ingest(symbol, session, as_of=None):
        return {"symbol": symbol, "status": "ingested", "source": "akshare"}

    monkeypatch.setattr(
        "packages.services.fundamentals.ingest_akshare_fundamentals",
        fake_akshare_ingest,
    )

    result = ingest_fundamentals("600519", session=session, provider_name="akshare", as_of=date(2026, 1, 20))

    assert result["status"] == "ingested"
    assert result["source"] == "akshare"


def test_ingest_akshare_fundamentals_persists_snapshot():
    session = make_session()
    frame = pd.DataFrame(
        [
            {
                "日期": "2026-03-31",
                "主营业务收入增长(%)": 10.5,
                "销售净利率(%)": 52.2,
                "资产负债率(%)": 12.1,
            }
        ]
    )

    with patch("akshare.stock_financial_analysis_indicator", return_value=frame):
        result = ingest_akshare_fundamentals("600519", session=session, as_of=date(2026, 3, 31))

    assert result["status"] == "ingested"
    assert result["source"] == "akshare"
    assert result["item"]["pe_ratio"] is None
    assert result["item"]["revenue_growth"] == 0.105
    stored = session.query(FundamentalSnapshotModel).one()
    assert float(stored.pe_ratio) == 0.0


def test_ingest_news_keeps_akshare_name_as_eastmoney_public_compatibility_route(
    monkeypatch,
):
    session = make_session()

    def fake_akshare_news(symbol, session):
        return {
            "symbol": symbol,
            "status": "ingested",
            "source": "eastmoney_public",
            "article_count": 1,
        }

    monkeypatch.setattr("packages.services.news.ingest_akshare_news", fake_akshare_news)

    result = ingest_news("600519", session=session, provider_name="akshare")

    assert result["status"] == "ingested"
    assert result["source"] == "eastmoney_public"
    assert result["article_count"] == 1


def test_ingest_akshare_news_compatibility_path_uses_eastmoney_public(monkeypatch):
    session = make_session()
    item = EastmoneyPublicNewsItem(
        symbol="600519",
        title="Moutai revenue grows",
        url="https://finance.eastmoney.com/a/202606293806093223.html",
        publisher="Eastmoney",
        summary="Moutai revenue grows strongly in the quarter.",
        published_at=datetime(2026, 6, 29, 14, 13, 41, tzinfo=timezone.utc),
    )
    monkeypatch.setattr(
        "packages.services.news.fetch_eastmoney_public_news",
        lambda symbol, **kwargs: (item,),
    )
    monkeypatch.setattr(
        "packages.services.news.get_platform_settings",
        lambda: {
            "akshare_enabled": True,
            "news_search_timeout_seconds": 3,
            "news_search_max_results": 10,
        },
    )

    result = ingest_akshare_news("600519", session=session)

    assert result["status"] == "ingested"
    assert result["source"] == "eastmoney_public"
    assert result["article_count"] == 1
    assert result["sentiment_count"] == 1
