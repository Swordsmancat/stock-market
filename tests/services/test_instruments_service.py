import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.domain.models import Instrument, Market
from packages.services.instruments import list_instruments_payload
from packages.shared.database import Base


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def seed_database_instruments(session) -> None:
    us_market = Market(
        code="US",
        name="United States",
        timezone="America/New_York",
        currency="USD",
    )
    cn_market = Market(
        code="CN",
        name="China",
        timezone="Asia/Shanghai",
        currency="CNY",
    )
    session.add_all([us_market, cn_market])
    session.flush()
    session.add_all(
        [
            Instrument(
                symbol="AAPL",
                name="Apple Inc.",
                market_id=us_market.id,
                asset_type="stock",
                currency="USD",
            ),
            Instrument(
                symbol="AMZN",
                name="Amazon.com Inc.",
                market_id=us_market.id,
                asset_type="stock",
                currency="USD",
            ),
            Instrument(
                symbol="MSFT",
                name="Microsoft Corp.",
                market_id=us_market.id,
                asset_type="stock",
                currency="USD",
            ),
            Instrument(
                symbol="600000",
                name="Shanghai Pudong Development Bank",
                market_id=cn_market.id,
                asset_type="stock",
                currency="CNY",
            ),
        ]
    )
    session.commit()


def test_database_filters_and_counts_before_sql_pagination():
    session = make_session()
    seed_database_instruments(session)

    payload = list_instruments_payload(
        session=session,
        query="a",
        market="US",
        limit=1,
        offset=1,
    )

    assert payload == {
        "source": "database",
        "items": [
            {
                "symbol": "AMZN",
                "name": "Amazon.com Inc.",
                "market": "US",
                "exchange": "",
                "asset_type": "stock",
                "currency": "USD",
                "source": "database",
            }
        ],
        "total": 2,
        "limit": 1,
        "offset": 1,
        "has_more": False,
    }


def test_seed_fallback_supports_pages_and_legacy_complete_list():
    legacy_payload = list_instruments_payload(session=None)
    first_page = list_instruments_payload(session=None, limit=1, offset=0)
    middle_page = list_instruments_payload(session=None, limit=1, offset=1)
    last_page = list_instruments_payload(session=None, limit=1, offset=2)

    assert [item["symbol"] for item in legacy_payload["items"]] == [
        "600519",
        "0700",
        "AAPL",
    ]
    assert legacy_payload["source"] == "seed"
    assert legacy_payload["total"] == 3
    assert legacy_payload["limit"] is None
    assert legacy_payload["offset"] == 0
    assert legacy_payload["has_more"] is False

    assert [item["symbol"] for item in first_page["items"]] == ["600519"]
    assert first_page["has_more"] is True
    assert [item["symbol"] for item in middle_page["items"]] == ["0700"]
    assert middle_page["has_more"] is True
    assert [item["symbol"] for item in last_page["items"]] == ["AAPL"]
    assert last_page["total"] == 3
    assert last_page["limit"] == 1
    assert last_page["offset"] == 2
    assert last_page["has_more"] is False


@pytest.mark.parametrize(
    ("limit", "offset"),
    [(0, 0), (101, 0), (1, -1)],
)
def test_service_rejects_invalid_pagination_bounds(limit: int, offset: int):
    with pytest.raises(ValueError):
        list_instruments_payload(session=None, limit=limit, offset=offset)
