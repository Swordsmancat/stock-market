from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.routers import topic_research as topic_research_router


def test_topic_research_api_delegates_query(monkeypatch):
    captured: dict[str, object] = {}

    def stub(**kwargs):
        captured.update(kwargs)
        return {"status": "ready", "source": "database"}

    monkeypatch.setattr(topic_research_router, "get_topic_research_payload", stub)
    response = TestClient(app).get(
        "/topic-research",
        params={"topic": "nonferrous", "window": "180d"},
    )

    assert response.status_code == 200
    assert captured["topic"] == "nonferrous"
    assert captured["window"] == "180d"
    assert captured["session"] is not None


def test_topic_research_api_rejects_unknown_topic_and_window():
    client = TestClient(app)

    assert client.get("/topic-research", params={"topic": "fx"}).status_code == 422
    assert client.get("/topic-research", params={"window": "365d"}).status_code == 422
