from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.routers import assistant as assistant_router
from packages.shared.database import get_session


def override_no_database_session():
    yield None


def test_market_assistant_api_returns_contextual_answer(monkeypatch):
    def answer_stub(**kwargs):
        assert kwargs["symbol"] == "AAPL"
        assert kwargs["question"] == "请总结近期走势。"
        assert kwargs["provider_name"] == "mock"
        assert kwargs["session"] is None
        return {
            "status": "degraded",
            "answer_markdown": "### 概览\n基于可用数据整理。",
            "symbol": "AAPL",
            "as_of": "2026-01-03",
            "model": {
                "provider": "deterministic",
                "name": "market-assistant-deterministic-fallback",
                "used_llm": False,
                "fallback_reason": "OpenAI-compatible LLM provider is not configured.",
            },
            "context": {
                "scope": "instrument",
                "timeframe": "1d",
                "start": "2026-01-01",
                "end": "2026-01-03",
                "latest_close": 105.0,
                "period_change_pct": 5.0,
                "bar_count": 2,
            },
            "citations": [
                {
                    "id": "bars_1d:AAPL:2026-01-03",
                    "label": "Daily bars for AAPL as of 2026-01-03",
                    "source": "bars_1d",
                    "url": None,
                    "source_type": "bars",
                    "as_of": "2026-01-03",
                    "provider": "mock",
                    "excerpt": "Daily bars from 2026-01-01 to 2026-01-03.",
                }
            ],
            "diagnostics": [
                {
                    "source": "generated_reports",
                    "status": "no_data",
                    "severity": "info",
                    "code": "SOURCE_NO_DATA",
                    "message": "No generated research reports are available.",
                }
            ],
            "safety": {
                "not_investment_advice": True,
                "no_fabricated_market_data": True,
                "disclaimer": "以下内容仅用于信息整理和投资者教育，不构成投资建议、收益承诺或买卖指令。",
            },
        }

    monkeypatch.setattr(assistant_router, "answer_market_assistant_question", answer_stub)
    app.dependency_overrides[get_session] = override_no_database_session
    try:
        client = TestClient(app)
        response = client.post(
            "/assistant/market",
            json={
                "scope": "instrument",
                "symbol": "AAPL",
                "question": "请总结近期走势。",
                "locale": "zh",
                "timeframe": "1d",
                "start": "2026-01-01",
                "end": "2026-01-03",
                "provider": "mock",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert payload["status"] == "degraded"
    assert payload["context"]["latest_close"] == 105.0
    assert payload["citations"][0]["source"] == "bars_1d"
    assert payload["citations"][0]["source_type"] == "bars"
    assert payload["diagnostics"][0]["code"] == "SOURCE_NO_DATA"
    assert payload["safety"]["not_investment_advice"] is True


def test_market_assistant_api_rejects_empty_question():
    app.dependency_overrides[get_session] = override_no_database_session
    try:
        client = TestClient(app)
        response = client.post(
            "/assistant/market",
            json={"symbol": "AAPL", "question": "", "provider": "mock"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_market_assistant_api_maps_service_validation_errors(monkeypatch):
    def failing_answer_stub(**kwargs):
        raise ValueError("Start date must be earlier than or equal to end date.")

    monkeypatch.setattr(assistant_router, "answer_market_assistant_question", failing_answer_stub)
    app.dependency_overrides[get_session] = override_no_database_session
    try:
        client = TestClient(app)
        response = client.post(
            "/assistant/market",
            json={
                "symbol": "AAPL",
                "question": "请分析走势。",
                "start": "2026-01-03",
                "end": "2026-01-01",
                "provider": "mock",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"] == "Start date must be earlier than or equal to end date."
