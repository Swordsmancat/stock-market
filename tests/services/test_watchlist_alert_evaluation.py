from packages.services.alerts import evaluate_alert_rules
from packages.services.watchlist_alerts import evaluate_all_watchlist_alerts
from packages.services.watchlists import upsert_watchlist_item
from packages.shared.database import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_evaluate_all_watchlist_alerts_skips_when_no_rules():
    session = make_session()

    result = evaluate_all_watchlist_alerts(session=session, provider_name="mock")

    assert result["status"] == "skipped"
    assert result["reason"] == "no_alert_rules"
    assert result["item_count"] == 0


def test_evaluate_all_watchlist_alerts_evaluates_items_with_rules(monkeypatch):
    session = make_session()
    upsert_watchlist_item(
        "AAPL",
        "US",
        session=session,
        alert_rules={"price_above": 100},
    )

    def fake_enrich(items, session, provider_name=None):
        return [
            {
                **items[0],
                "latest_price": 120.0,
                "rsi": 50.0,
                "alert_status": evaluate_alert_rules(items[0]["alert_rules"], 120.0, 50.0),
            }
        ]

    monkeypatch.setattr("packages.services.watchlist_alerts.enrich_watchlist_items", fake_enrich)

    result = evaluate_all_watchlist_alerts(session=session, provider_name="mock")

    assert result["status"] == "evaluated"
    assert result["item_count"] == 1
    assert result["triggered_count"] == 1
    assert result["items"][0]["symbol"] == "AAPL"
