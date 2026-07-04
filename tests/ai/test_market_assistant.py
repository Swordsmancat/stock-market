from datetime import date

from packages.ai.market_assistant import (
    MarketAssistantPromptContext,
    build_deterministic_market_answer,
)
from packages.services import market_assistant as market_assistant_service


def test_deterministic_answer_refuses_direct_trading_instruction():
    context = MarketAssistantPromptContext(
        symbol="AAPL",
        locale="zh",
        question="AAPL 现在能不能买入？",
        timeframe="1d",
        start="2026-01-01",
        end="2026-01-03",
        as_of="2026-01-03",
        latest_close=103.0,
        period_change_pct=1.98,
        bar_count=3,
        price_summary="Daily bars are available.",
        indicator_summary="MA=102",
        fundamental_summary="PE=28.4",
        news_summary="No stored news sentiment is available.",
    )

    answer = build_deterministic_market_answer(context)

    assert "不能给出直接买入、卖出、持有、仓位或目标价指令" in answer
    assert "不构成投资建议" in answer
    assert "AAPL" in answer


def test_market_assistant_returns_traceable_fallback_answer(monkeypatch):
    monkeypatch.setattr(
        market_assistant_service,
        "get_bars_payload",
        lambda *args, **kwargs: {
            "symbol": "AAPL",
            "timeframe": "1d",
            "source": "mock",
            "provider": "mock",
            "requested_provider": "mock",
            "effective_provider": "mock",
            "items": [
                {"timestamp": "2026-01-01", "close": 100.0},
                {"timestamp": "2026-01-03", "close": 105.0},
            ],
        },
    )
    monkeypatch.setattr(
        market_assistant_service,
        "get_platform_settings",
        lambda: {"llm_provider": "mock", "llm_api_key": "", "llm_api_base": ""},
    )

    payload = market_assistant_service.answer_market_assistant_question(
        symbol="aapl",
        question="请总结近期走势和风险。",
        start=date(2026, 1, 1),
        end=date(2026, 1, 3),
        provider_name="mock",
        session=None,
    )

    assert payload["status"] == "degraded"
    assert payload["symbol"] == "AAPL"
    assert payload["model"]["used_llm"] is False
    assert payload["context"]["latest_close"] == 105.0
    assert payload["context"]["period_change_pct"] == 5.0
    assert payload["citations"][0]["id"] == "bars_1d:AAPL:2026-01-03"
    assert payload["safety"]["not_investment_advice"] is True
    assert "不构成投资建议" in payload["answer_markdown"]


def test_market_assistant_returns_no_data_without_llm(monkeypatch):
    class UnexpectedProvider:
        def generate(self, prompt: str) -> str:
            raise AssertionError("LLM should not be called when no verified bars exist.")

    monkeypatch.setattr(
        market_assistant_service,
        "get_bars_payload",
        lambda *args, **kwargs: {
            "symbol": "AAPL",
            "timeframe": "1d",
            "source": "mock",
            "provider": "mock",
            "requested_provider": "mock",
            "effective_provider": "mock",
            "items": [],
        },
    )
    monkeypatch.setattr(
        market_assistant_service,
        "get_platform_settings",
        lambda: {"llm_provider": "openai", "llm_api_key": "configured", "llm_api_base": ""},
    )
    monkeypatch.setattr(market_assistant_service, "get_llm_provider", lambda: UnexpectedProvider())

    payload = market_assistant_service.answer_market_assistant_question(
        symbol="AAPL",
        question="请分析走势。",
        start=date(2026, 1, 1),
        end=date(2026, 1, 2),
        provider_name="mock",
        session=None,
    )

    assert payload["status"] == "no_data"
    assert payload["model"]["used_llm"] is False
    assert payload["context"]["bar_count"] == 0
    assert payload["citations"] == []
    assert payload["diagnostics"][0]["source"] == "bars_1d"
    assert "没有获取到" in payload["answer_markdown"]


def test_market_assistant_falls_back_when_llm_generation_fails(monkeypatch):
    class FailingProvider:
        def generate(self, prompt: str) -> str:
            raise RuntimeError("upstream unavailable token=secret")

    monkeypatch.setattr(
        market_assistant_service,
        "get_bars_payload",
        lambda *args, **kwargs: {
            "symbol": "AAPL",
            "timeframe": "1d",
            "source": "mock",
            "provider": "mock",
            "requested_provider": "mock",
            "effective_provider": "mock",
            "items": [
                {"timestamp": "2026-01-01", "close": 100.0},
                {"timestamp": "2026-01-02", "close": 99.0},
            ],
        },
    )
    monkeypatch.setattr(
        market_assistant_service,
        "get_platform_settings",
        lambda: {"llm_provider": "openai", "llm_api_key": "configured", "llm_api_base": ""},
    )
    monkeypatch.setattr(market_assistant_service, "get_llm_provider", lambda: FailingProvider())

    payload = market_assistant_service.answer_market_assistant_question(
        symbol="AAPL",
        question="What changed recently?",
        locale="en",
        start=date(2026, 1, 1),
        end=date(2026, 1, 2),
        provider_name="mock",
        session=None,
    )

    assert payload["status"] == "degraded"
    assert payload["model"]["used_llm"] is False
    assert payload["model"]["fallback_reason"] == "LLM generation failed: RuntimeError."
    assert "secret" not in payload["model"]["fallback_reason"]
    assert "not investment advice" in payload["answer_markdown"]
