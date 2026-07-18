from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.main import app
from packages.domain.models import Base
from packages.shared.database import get_session


def test_get_investment_calendar_is_database_only_and_bounded():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    app.dependency_overrides[get_session] = lambda: session
    try:
        client = TestClient(app)
        response = client.get("/investment-calendar?start=2026-07-01&end=2026-07-31&kind=economic")
        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "start": "2026-07-01",
            "end": "2026-07-31",
            "kind": "economic",
            "count": 0,
            "truncated": False,
            "days": [],
        }

        invalid = client.get("/investment-calendar?start=2026-01-01&end=2026-07-31&kind=economic")
        assert invalid.status_code == 400
        assert "42 days" in invalid.json()["detail"]

        invalid_kind = client.get(
            "/investment-calendar?start=2026-07-01&end=2026-07-31&kind=unknown"
        )
        assert invalid_kind.status_code == 422
    finally:
        app.dependency_overrides.clear()
        session.close()
