from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.services.watchlists import (
    get_active_watchlist_entries,
    get_default_watchlist_payload,
    upsert_watchlist_item,
)
from packages.shared.database import Base


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_get_default_watchlist_seeds_from_settings_when_empty():
    session = make_session()

    payload = get_default_watchlist_payload(session=session)

    assert payload["source"] == "database"
    assert payload["name"] == "default"
    assert payload["items"] == [
        {
            "symbol": "AAPL",
            "market": "US",
            "name": "Apple Inc.",
            "is_active": True,
            "alert_rules": {},
        }
    ]


def test_upsert_watchlist_item_persists_alert_rules():
    session = make_session()

    result = upsert_watchlist_item(
        "0700",
        "HK",
        session=session,
        name="Tencent Holdings",
        alert_rules={"price_above": 400, "rsi_below": 30},
    )
    entries = get_active_watchlist_entries(session=session)

    assert result["source"] == "database"
    assert result["item"]["symbol"] == "0700"
    assert result["item"]["market"] == "HK"
    assert result["item"]["alert_rules"] == {"price_above": 400, "rsi_below": 30}
    assert entries == [("0700", "HK")]
