from packages.services.market_data import get_latest_bar_payload
from packages.services.portfolios import (
    create_portfolio_payload,
    get_demo_portfolio_payload,
    upsert_portfolio_position_payload,
)

def test_get_demo_portfolio_payload_uses_latest_market_data_price():
    latest = get_latest_bar_payload("AAPL", session=None, provider_name="mock")
    latest_price = float(latest["item"]["close"])
    payload = get_demo_portfolio_payload()

    assert payload["id"] == "demo"
    assert payload["positions"][0]["symbol"] == "AAPL"
    assert payload["positions"][0]["latest_price"] == latest_price
    assert payload["positions"][0]["market_value"] == latest_price * 10
    assert payload["summary"]["total_cost"] == 1000.0
    assert payload["summary"]["unrealized_pnl"] == latest_price * 10 - 1000.0
    assert payload["summary"]["unrealized_return_pct"] == (latest_price * 10 - 1000.0) / 1000.0
    assert payload["positions"][0]["weight"] == 1.0
    assert payload["recommendation"]["status"] == "simulated"


def test_create_portfolio_and_add_position_with_database_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    import packages.domain.models  # noqa: F401
    from packages.shared.database import Base

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    created = create_portfolio_payload("Tech", session=session, base_currency="USD")
    portfolio_id = created["id"]
    assert created["name"] == "Tech"
    assert created["positions"] == []

    updated = upsert_portfolio_position_payload(
        portfolio_id,
        "AAPL",
        "US",
        quantity=3,
        avg_cost=150,
        session=session,
    )
    assert updated is not None
    assert len(updated["positions"]) == 1
    assert updated["positions"][0]["symbol"] == "AAPL"
    assert updated["summary"]["total_cost"] == 450.0