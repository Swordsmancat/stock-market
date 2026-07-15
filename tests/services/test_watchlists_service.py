from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.domain.models import AlertTrigger, Watchlist, WatchlistItem
from packages.services.watchlists import (
    get_active_watchlist_entries,
    get_default_watchlist_payload,
    get_watchlist_item_membership,
    remove_watchlist_item,
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
    assert len(payload["items"]) == 1
    item = payload["items"][0]
    assert item["symbol"] == "AAPL"
    assert item["market"] == "US"
    assert item["name"] == "Apple Inc."
    assert item["is_active"] is True
    assert item["alert_rules"] == {}
    assert "latest_price" in item
    assert "alert_status" in item


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


def test_remove_watchlist_item_marks_item_inactive():
    session = make_session()
    upsert_watchlist_item("AAPL", "US", session=session, name="Apple Inc.")

    result = remove_watchlist_item("AAPL", "US", session=session)
    entries = get_active_watchlist_entries(session=session)

    assert result["status"] == "removed"
    assert result["item"]["is_active"] is False
    assert entries == []


def test_reactivating_item_without_alert_rules_preserves_existing_rules():
    session = make_session()
    upsert_watchlist_item(
        "AAPL",
        "US",
        session=session,
        name="Apple Inc.",
        alert_rules={"price_above": 250},
    )
    remove_watchlist_item("AAPL", "US", session=session)

    result = upsert_watchlist_item(
        "AAPL",
        "US",
        session=session,
        name="Apple Inc.",
    )

    assert result["item"]["is_active"] is True
    assert result["item"]["alert_rules"] == {"price_above": 250}


def test_membership_read_does_not_create_or_seed_default_watchlist():
    session = make_session()

    result = get_watchlist_item_membership("AAPL", "US", session=session)

    assert result == {
        "source": "database",
        "status": "not_watched",
        "symbol": "AAPL",
        "market": "US",
        "item": None,
    }
    assert session.query(Watchlist).count() == 0
    assert session.query(WatchlistItem).count() == 0
    assert session.query(AlertTrigger).count() == 0


def test_membership_read_uses_exact_active_symbol_and_market_without_writes():
    session = make_session()
    upsert_watchlist_item(
        "0700",
        "HK",
        session=session,
        name="Tencent Holdings",
        alert_rules={"price_above": 400},
    )

    watched = get_watchlist_item_membership("0700", "hk", session=session)
    other_market = get_watchlist_item_membership("0700", "US", session=session)

    assert watched["status"] == "watched"
    assert watched["item"]["alert_rules"] == {"price_above": 400}
    assert other_market["status"] == "not_watched"
    assert session.query(AlertTrigger).count() == 0


def test_membership_read_treats_soft_removed_item_as_not_watched():
    session = make_session()
    upsert_watchlist_item("AAPL", "US", session=session, name="Apple Inc.")
    remove_watchlist_item("AAPL", "US", session=session)

    result = get_watchlist_item_membership("AAPL", "US", session=session)

    assert result["status"] == "not_watched"
    assert result["item"] is None
