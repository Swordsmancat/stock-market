from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.services.ingestion import ingest_mock_market_snapshot
from packages.services.market_data import get_bars_payload
from packages.shared.database import Base


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_ingestion_writes_bars_and_market_data_reads_database_first():
    session = make_session()
    ingest_mock_market_snapshot("US", date(2026, 1, 1), date(2026, 1, 2), session=session)

    payload = get_bars_payload("AAPL", "1d", date(2026, 1, 1), date(2026, 1, 2), session=session)

    assert payload["source"] == "database"
    assert payload["symbol"] == "AAPL"
    assert len(payload["items"]) == 2
    assert payload["items"][1]["close"] == 102.0
