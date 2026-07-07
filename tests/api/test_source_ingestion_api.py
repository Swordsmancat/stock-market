from fastapi.testclient import TestClient

from apps.api.main import app


def test_source_ingestion_api_extracts_with_fallback(monkeypatch):
    monkeypatch.setattr(
        "packages.services.source_ingestion.get_platform_settings",
        lambda: {"llm_provider": "mock", "llm_api_key": ""},
    )
    client = TestClient(app)

    response = client.post(
        "/source-ingestion/extract",
        json={
            "content": "World Bank GDP and market capitalization source for Buffett Indicator.",
            "filename": "buffett-note.md",
            "source_id": "buffett_manual_valuation_components",
            "source_label": "Buffett Indicator manual valuation components",
            "source_category": "valuation",
            "target_indicator_codes": ["buffett_indicator_us"],
            "component_role": "gdp",
            "locale": "en",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "fallback"
    assert payload["suggested_fields"]["target_indicator_codes"] == ["buffett_indicator_us"]
    assert payload["model"]["used_llm"] is False
    assert payload["safety"]["not_investment_advice"] is True


def test_source_ingestion_api_returns_invalid_input_payload():
    client = TestClient(app)

    response = client.post("/source-ingestion/extract", json={"content": ""})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "invalid_input"
    assert payload["diagnostics"][0]["code"] == "SOURCE_INGESTION_CONTENT_REQUIRED"
