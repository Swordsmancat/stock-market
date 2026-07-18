from unittest.mock import patch

from packages.ai.report_builder import ReportContext, build_stock_report, resolve_combined_summary


def test_resolve_combined_summary_uses_mock_template_when_llm_disabled():
    context = ReportContext(
        symbol="AAPL",
        as_of="2026-01-20",
        price_summary="Close 101",
        indicator_summary="MA 100",
        fundamental_summary="PE 20",
        news_summary="Positive",
        citations=[],
        combined_summary="模板综合研判",
    )
    with patch(
        "packages.services.platform_settings.get_platform_settings",
        return_value={"llm_provider": "mock", "llm_api_key": ""},
    ):
        assert resolve_combined_summary(context) == "模板综合研判"


def test_resolve_combined_summary_uses_llm_when_openai_configured():
    context = ReportContext(
        symbol="AAPL",
        as_of="2026-01-20",
        price_summary="Close 101",
        indicator_summary="MA 100",
        fundamental_summary="PE 20",
        news_summary="Positive",
        citations=[],
        combined_summary="模板综合研判",
    )

    class FakeLLM:
        def generate(self, prompt: str) -> str:
            assert "AAPL" in prompt
            return "LLM 综合研判内容"

    with patch(
        "packages.services.platform_settings.get_platform_settings",
        return_value={"llm_provider": "openai", "llm_api_key": "sk-test"},
    ):
        with patch("packages.ai.llm_factory.get_llm_provider", return_value=FakeLLM()):
            assert resolve_combined_summary(context) == "LLM 综合研判内容"


def test_build_stock_report_uses_llm_summary_when_configured():
    context = ReportContext(
        symbol="AAPL",
        as_of="2026-01-20",
        price_summary="Close 101",
        indicator_summary="MA 100",
        fundamental_summary="PE 20",
        news_summary="Positive",
        citations=["bars_1d:AAPL:2026-01-20"],
        combined_summary="模板综合研判",
    )
    with patch(
        "packages.ai.report_builder.resolve_combined_summary",
        return_value="LLM 输出综合研判",
    ):
        report = build_stock_report(context)
    assert "LLM 输出综合研判" in report
    assert "bars_1d:AAPL:2026-01-20" in report
