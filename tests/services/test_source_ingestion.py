import json

from packages.services.source_ingestion import (
    SourceIngestionExtractionInput,
    extract_source_ingestion_payload,
)


def test_source_ingestion_uses_deterministic_fallback_without_llm(monkeypatch):
    monkeypatch.setattr(
        "packages.services.source_ingestion.get_platform_settings",
        lambda: {"llm_provider": "mock", "llm_api_key": ""},
    )

    payload = extract_source_ingestion_payload(
        SourceIngestionExtractionInput(
            content=(
                "World Bank market capitalization and GDP data for Buffett Indicator review.\n"
                "Calculation: market capitalization divided by GDP for 2026-07-07.\n"
                "Source URL: https://data.worldbank.org/indicator/CM.MKT.LCAP.GD.ZS"
            ),
            filename="buffett-source.md",
            source_id="buffett_manual_valuation_components",
            source_label="Buffett Indicator manual valuation components",
            source_category="valuation",
            target_indicator_codes=["buffett_indicator_us"],
            component_role="gdp",
            locale="en",
        )
    )

    assert payload["status"] == "fallback"
    assert payload["model"] == {
        "provider": "deterministic",
        "name": "source-ingestion-deterministic-fallback",
        "used_llm": False,
        "fallback_reason": "OpenAI-compatible LLM provider is not configured.",
    }
    assert "World Bank market capitalization" in payload["summary"]
    assert {
        "label": "Buffett Indicator",
        "code": "buffett_indicator_us",
        "reason": "Matched buffett, market cap, market capitalization.",
    } in payload["key_indicators"]
    assert payload["suggested_fields"]["target_indicator_codes"] == ["buffett_indicator_us"]
    assert "valuation" in payload["suggested_fields"]["tags"]
    assert payload["suggested_fields"]["ai_follow_up"]
    assert payload["safety"]["drafts_are_not_citations"] is True
    diagnostic = payload["diagnostics"][0]
    assert diagnostic["code"] == "SOURCE_INGESTION_FALLBACK_USED"
    assert diagnostic["details"]["reason"] == "OpenAI-compatible LLM provider is not configured."


def test_source_ingestion_uses_llm_when_configured(monkeypatch):
    monkeypatch.setattr(
        "packages.services.source_ingestion.get_platform_settings",
        lambda: {"llm_provider": "openai", "llm_api_key": "sk-test"},
    )

    class FakeLLM:
        def generate(self, prompt: str) -> str:
            assert "Return JSON only" in prompt
            assert "Draft uploads and extracted suggestions are collection notes only" in prompt
            return json.dumps(
                {
                    "summary": "Reviewed Buffett Indicator source context.",
                    "key_indicators": [
                        {
                            "label": "Buffett Indicator",
                            "code": "buffett_indicator_us",
                            "reason": "The source discusses market cap and GDP.",
                        }
                    ],
                    "citation_clues": [
                        {"kind": "date", "label": "As-of date", "value": "2026-07-07"}
                    ],
                    "follow_up_questions": [
                        "Confirm market-cap and GDP component timing before import."
                    ],
                    "suggested_fields": {
                        "title": "Buffett Indicator source review",
                        "source_name": "World Bank",
                        "source_type": "valuation",
                        "tags": ["macro", "valuation"],
                        "target_indicator_codes": ["buffett_indicator_us"],
                        "methodology_note": "Review ratio calculation.",
                        "license_note": "Confirm public-source usage.",
                        "ai_follow_up": "Confirm component timing before import.",
                    },
                }
            )

    monkeypatch.setattr("packages.services.source_ingestion.get_llm_provider", lambda: FakeLLM())

    payload = extract_source_ingestion_payload(
        SourceIngestionExtractionInput(
            content="Buffett Indicator source review for market cap divided by GDP.",
            source_label="Buffett Indicator manual valuation components",
            source_category="valuation",
        )
    )

    assert payload["status"] == "ok"
    assert payload["model"] == {
        "provider": "openai",
        "name": "gpt-4o-mini",
        "used_llm": True,
        "fallback_reason": None,
    }
    assert payload["summary"] == "Reviewed Buffett Indicator source context."
    assert payload["suggested_fields"]["source_name"] == "World Bank"
    assert payload["diagnostics"] == []


def test_source_ingestion_falls_back_on_invalid_llm_output(monkeypatch):
    monkeypatch.setattr(
        "packages.services.source_ingestion.get_platform_settings",
        lambda: {"llm_provider": "openai", "llm_api_key": "sk-test"},
    )

    class FakeLLM:
        def generate(self, prompt: str) -> str:
            return "not json"

    monkeypatch.setattr("packages.services.source_ingestion.get_llm_provider", lambda: FakeLLM())

    payload = extract_source_ingestion_payload(
        SourceIngestionExtractionInput(
            content="PBOC China M2 monetary statistics source note for liquidity review.",
            source_id="pboc_cn_m2_public_manual",
            source_label="PBOC China M2 public/manual source",
            source_category="macro",
            target_indicator_codes=["cn_m2_yoy"],
        )
    )

    assert payload["status"] == "fallback"
    assert payload["model"]["fallback_reason"] == "LLM extraction returned invalid JSON."
    assert payload["suggested_fields"]["target_indicator_codes"] == ["cn_m2_yoy"]
    assert any(item["code"] == "SOURCE_INGESTION_FALLBACK_USED" for item in payload["diagnostics"])


def test_source_ingestion_returns_invalid_input_payload():
    payload = extract_source_ingestion_payload(SourceIngestionExtractionInput(content=" "))

    assert payload["status"] == "invalid_input"
    assert payload["summary"] == ""
    assert payload["key_indicators"] == []
    assert payload["model"]["used_llm"] is False
    assert payload["diagnostics"][0]["code"] == "SOURCE_INGESTION_CONTENT_REQUIRED"
