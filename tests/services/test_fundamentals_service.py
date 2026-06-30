from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.analytics.fundamentals import FundamentalSnapshot
from packages.services.fundamentals import get_fundamental_payload, upsert_fundamental_snapshot
from packages.shared.database import Base


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_get_fundamental_payload_returns_mock_metrics_with_citation():
    payload = get_fundamental_payload("AAPL", as_of=date(2026, 1, 20))

    assert payload["symbol"] == "AAPL"
    assert payload["source"] == "mock_fundamentals"
    assert payload["citation"] == "fundamental_metrics:AAPL:2026-01-20"
    assert payload["item"]["pe_ratio"] == 28.4
    assert "PE 28.40" in payload["item"]["summary"]


def test_get_fundamental_payload_prefers_database_snapshot():
    session = make_session()
    upsert_fundamental_snapshot(
        FundamentalSnapshot(
            symbol="AAPL",
            as_of=date(2026, 1, 19),
            currency="USD",
            pe_ratio=30.5,
            revenue_growth=0.12,
            net_margin=0.25,
            debt_to_assets=0.29,
        ),
        session=session,
        source="test_fixture",
    )

    payload = get_fundamental_payload("AAPL", as_of=date(2026, 1, 20), session=session)

    assert payload["symbol"] == "AAPL"
    assert payload["source"] == "database"
    assert payload["as_of"] == "2026-01-19"
    assert payload["citation"] == "fundamental_metrics:AAPL:2026-01-19"
    assert payload["item"]["pe_ratio"] == 30.5
    assert "PE 30.50" in payload["item"]["summary"]
