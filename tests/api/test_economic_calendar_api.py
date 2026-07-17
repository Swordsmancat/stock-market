from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.main import app
from packages.domain.models import Base
from packages.shared.database import get_session


def test_get_is_database_only_and_validates_range():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    app.dependency_overrides[get_session] = lambda: session
    try:
        client = TestClient(app)
        response = client.get("/economic-calendar/events?start=2026-07-01&end=2026-07-31")
        assert response.status_code == 200
        assert response.json()["items"] == []
        invalid = client.get("/economic-calendar/events?start=2026-01-01&end=2026-07-31")
        assert invalid.status_code == 400
    finally:
        app.dependency_overrides.clear()
        session.close()
