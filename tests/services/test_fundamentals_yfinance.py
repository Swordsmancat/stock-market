from datetime import date
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.services.fundamentals import ingest_fundamentals
from packages.shared.database import Base


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_ingest_fundamentals_uses_yfinance_path(monkeypatch):
    session = make_session()

    def fake_yfinance_ingest(symbol, session, as_of=None):
        return {"symbol": symbol, "status": "ingested", "source": "yfinance"}

    monkeypatch.setattr(
        "packages.services.fundamentals.ingest_yfinance_fundamentals",
        fake_yfinance_ingest,
    )

    result = ingest_fundamentals("AAPL", session=session, provider_name="yfinance", as_of=date(2026, 1, 20))

    assert result["status"] == "ingested"
    assert result["source"] == "yfinance"
