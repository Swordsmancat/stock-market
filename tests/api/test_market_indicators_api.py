import json
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from apps.api.main import app
from packages.domain.models import MarketIndicatorObservation
from packages.providers.fred_provider import FredProviderConfigurationError, FredProviderError
from packages.providers.world_bank_provider import WorldBankProviderError
from packages.services.market_indicators import (
    AkShareCnMacroRefreshResult,
    FredMacroRefreshResult,
    MarketIndicatorObservationSeed,
    WorldBankMacroRefreshResult,
    get_latest_market_indicator_payload,
    seed_market_indicators,
    upsert_market_indicator_observation,
)
from packages.shared.database import Base, get_session


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def with_test_client(session):
    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def valid_seed_content(value="4.250000"):
    return json.dumps(
        {
            "observations": [
                {
                    "code": "us_10y_yield",
                    "as_of": "2026-07-03",
                    "value": value,
                    "source": "Audited seed: FRED DGS10",
                    "components": {
                        "source_series_id": "DGS10",
                        "methodology": "Daily 10-year Treasury constant maturity rate.",
                    },
                }
            ]
        }
    )


def test_market_indicator_seed_preview_api_validates_without_writing():
    session = make_session()
    client = with_test_client(session)
    try:
        response = client.post(
            "/market-indicators/seeds/preview",
            json={
                "content": valid_seed_content(),
                "filename": "macro-seeds.json",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "valid"
    assert payload["can_import"] is True
    assert payload["summary"]["inserts"] == 1
    assert payload["rows"][0]["code"] == "us_10y_yield"
    assert payload["rows"][0]["intent"] == "insert"
    assert session.query(MarketIndicatorObservation).count() == 0


def test_market_indicator_seed_import_api_rejects_invalid_content_atomically():
    session = make_session()
    content = json.dumps(
        [
            {
                "code": "us_10y_yield",
                "as_of": "2026-07-03",
                "value": "4.250000",
                "source": "Audited seed: FRED DGS10",
                "components": {"source_series_id": "DGS10"},
            }
        ]
    )
    client = with_test_client(session)
    try:
        response = client.post(
            "/market-indicators/seeds/import",
            json={"content": content, "format": "json"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    payload = response.json()
    assert payload["detail"]["status"] == "invalid"
    assert "components must include one of" in "; ".join(payload["detail"]["errors"])
    assert session.query(MarketIndicatorObservation).count() == 0


def test_market_indicator_seed_import_api_requires_overwrite_acknowledgement(monkeypatch):
    session = make_session()
    seed_market_indicators(session=session)
    upsert_market_indicator_observation(
        MarketIndicatorObservationSeed(
            code="us_10y_yield",
            as_of=date(2026, 7, 3),
            value=Decimal("4.250000"),
            source="Audited seed: FRED DGS10",
            components={
                "source_series_id": "DGS10",
                "methodology": "Initial reviewed value.",
            },
        ),
        session=session,
    )
    client = with_test_client(session)
    try:
        response = client.post(
            "/market-indicators/seeds/import",
            json={
                "content": valid_seed_content("4.310000"),
                "filename": "macro-seeds.json",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    payload = response.json()
    assert payload["detail"]["summary"]["updates"] == 1
    assert get_latest_market_indicator_payload("us_10y_yield", session=session)["value"] == 4.25

    monkeypatch.setattr(
        "apps.api.routers.market_indicators.clear_market_overview_cache",
        lambda provider_name=None: 7,
    )
    client = with_test_client(session)
    try:
        confirmed_response = client.post(
            "/market-indicators/seeds/import",
            json={
                "content": valid_seed_content("4.310000"),
                "filename": "macro-seeds.json",
                "overwrite_acknowledged": True,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert confirmed_response.status_code == 200
    confirmed_payload = confirmed_response.json()
    assert confirmed_payload["status"] == "imported"
    assert confirmed_payload["summary"] == {"inserts": 0, "updates": 1}
    assert confirmed_payload["cache"]["market_overview_cleared"] == 7
    assert get_latest_market_indicator_payload("us_10y_yield", session=session)["value"] == 4.31


def test_official_macro_source_status_api_returns_readiness_without_secret(monkeypatch):
    session = make_session()
    monkeypatch.setattr("packages.services.market_indicators.settings.fred_api_key", "SECRET_FRED_TOKEN")
    seed_market_indicators(session=session)
    upsert_market_indicator_observation(
        MarketIndicatorObservationSeed(
            code="us_10y_yield",
            as_of=date(2026, 7, 3),
            value=Decimal("4.250000"),
            source="Audited seed: FRED DGS10",
            components={
                "source_series_id": "DGS10",
                "source_url": "https://fred.stlouisfed.org/series/DGS10",
                "methodology": "Daily 10-year Treasury constant maturity rate.",
            },
        ),
        session=session,
    )

    client = with_test_client(session)
    try:
        response = client.get("/market-indicators/official-sources/status")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    providers = {provider["provider"]: provider for provider in payload["providers"]}
    assert "SECRET_FRED_TOKEN" not in json.dumps(payload)
    assert payload["status"] == "degraded"
    assert providers["fred"]["configured"] is True
    assert providers["fred"]["credential_label"] == "FRED_API_KEY"
    assert providers["fred"]["evidence_count"] == 1
    assert providers["fred"]["latest_as_of"] == "2026-07-03"
    assert providers["world_bank"]["credential_required"] is False
    assert providers["world_bank"]["configured"] is True
    assert providers["world_bank"]["source_frequency"] == "annual_lagged"


def test_fred_official_refresh_api_dry_run_forwards_without_clearing_cache(monkeypatch):
    session = make_session()
    calls = {}

    def fake_refresh(**kwargs):
        calls.update(kwargs)
        return FredMacroRefreshResult(
            observations=1,
            fetched=2,
            skipped=1,
            dry_run=True,
            codes=("us_10y_yield",),
            latest_as_of="2026-07-01",
            diagnostics=("FRED DGS10 skipped 1 missing or invalid observations.",),
        )

    def fail_cache_clear(provider_name=None):
        raise AssertionError("dry-run refresh must not clear cache")

    monkeypatch.setattr("apps.api.routers.market_indicators.refresh_fred_macro_indicators", fake_refresh)
    monkeypatch.setattr("apps.api.routers.market_indicators.clear_market_overview_cache", fail_cache_clear)

    client = with_test_client(session)
    try:
        response = client.post(
            "/market-indicators/official-refresh/fred",
            json={
                "series": "DGS10",
                "start": "2026-07-01",
                "end": "2026-07-02",
                "latest_only": True,
                "dry_run": True,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "status": "ok",
        "provider": "fred",
        "dry_run": True,
        "observations": 1,
        "fetched": 2,
        "skipped": 1,
        "codes": ["us_10y_yield"],
        "latest_as_of": "2026-07-01",
        "diagnostics": ["FRED DGS10 skipped 1 missing or invalid observations."],
        "cache": {"market_overview_cleared": 0},
    }
    assert calls["session"] is session
    assert calls["series_group"] == "DGS10"
    assert calls["start"] == date(2026, 7, 1)
    assert calls["end"] == date(2026, 7, 2)
    assert calls["latest_only"] is True
    assert calls["dry_run"] is True


def test_fred_official_refresh_api_write_clears_cache_after_observations(monkeypatch):
    session = make_session()

    monkeypatch.setattr(
        "apps.api.routers.market_indicators.refresh_fred_macro_indicators",
        lambda **kwargs: FredMacroRefreshResult(
            observations=2,
            fetched=2,
            skipped=0,
            dry_run=False,
            codes=("us_10y_yield", "us_2y_yield"),
            latest_as_of="2026-07-02",
            diagnostics=(),
        ),
    )
    monkeypatch.setattr(
        "apps.api.routers.market_indicators.clear_market_overview_cache",
        lambda provider_name=None: 9,
    )

    client = with_test_client(session)
    try:
        response = client.post(
            "/market-indicators/official-refresh/fred",
            json={"series": "rates", "dry_run": False},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "fred"
    assert payload["dry_run"] is False
    assert payload["observations"] == 2
    assert payload["codes"] == ["us_10y_yield", "us_2y_yield"]
    assert payload["cache"]["market_overview_cleared"] == 9


def test_fred_official_refresh_api_returns_sanitized_configuration_and_provider_errors(monkeypatch):
    session = make_session()
    client = with_test_client(session)

    monkeypatch.setattr(
        "apps.api.routers.market_indicators.refresh_fred_macro_indicators",
        lambda **kwargs: (_ for _ in ()).throw(
            FredProviderConfigurationError("FRED API key is not configured.")
        ),
    )
    try:
        config_response = client.post(
            "/market-indicators/official-refresh/fred",
            json={"series": "all"},
        )
    finally:
        app.dependency_overrides.clear()

    assert config_response.status_code == 503
    assert config_response.json()["detail"] == {
        "status": "error",
        "provider": "fred",
        "message": "FRED API key is not configured.",
    }

    client = with_test_client(session)
    monkeypatch.setattr(
        "apps.api.routers.market_indicators.refresh_fred_macro_indicators",
        lambda **kwargs: (_ for _ in ()).throw(
            FredProviderError("FRED request failed with api_key=SECRET_TOKEN")
        ),
    )
    try:
        provider_response = client.post(
            "/market-indicators/official-refresh/fred",
            json={"series": "all"},
        )
    finally:
        app.dependency_overrides.clear()

    assert provider_response.status_code == 502
    message = provider_response.json()["detail"]["message"]
    assert "SECRET_TOKEN" not in message
    assert "api_key=[redacted]" in message


def test_world_bank_official_refresh_api_write_clears_cache(monkeypatch):
    session = make_session()
    calls = {}

    def fake_refresh(**kwargs):
        calls.update(kwargs)
        return WorldBankMacroRefreshResult(
            observations=3,
            fetched=6,
            skipped=0,
            dry_run=False,
            codes=("buffett_indicator_cn", "buffett_indicator_hk", "buffett_indicator_us"),
            latest_as_of="2024-12-31",
            diagnostics=(),
        )

    monkeypatch.setattr("apps.api.routers.market_indicators.refresh_world_bank_macro_indicators", fake_refresh)
    monkeypatch.setattr(
        "apps.api.routers.market_indicators.clear_market_overview_cache",
        lambda provider_name=None: 4,
    )

    client = with_test_client(session)
    try:
        response = client.post(
            "/market-indicators/official-refresh/world-bank",
            json={
                "target": "all",
                "start_year": 2020,
                "end_year": 2024,
                "latest_only": False,
                "dry_run": False,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "world_bank"
    assert payload["dry_run"] is False
    assert payload["observations"] == 3
    assert payload["fetched"] == 6
    assert payload["codes"] == [
        "buffett_indicator_cn",
        "buffett_indicator_hk",
        "buffett_indicator_us",
    ]
    assert payload["latest_as_of"] == "2024-12-31"
    assert payload["cache"]["market_overview_cleared"] == 4
    assert calls["session"] is session
    assert calls["target_group"] == "all"
    assert calls["start_year"] == 2020
    assert calls["end_year"] == 2024
    assert calls["latest_only"] is False
    assert calls["dry_run"] is False


def test_world_bank_official_refresh_api_maps_validation_and_provider_errors(monkeypatch):
    session = make_session()

    monkeypatch.setattr(
        "apps.api.routers.market_indicators.refresh_world_bank_macro_indicators",
        lambda **kwargs: (_ for _ in ()).throw(ValueError("Unsupported World Bank macro target 'bad'")),
    )
    client = with_test_client(session)
    try:
        validation_response = client.post(
            "/market-indicators/official-refresh/world-bank",
            json={"target": "bad"},
        )
    finally:
        app.dependency_overrides.clear()

    assert validation_response.status_code == 400
    assert "Unsupported World Bank macro target" in validation_response.json()["detail"]

    monkeypatch.setattr(
        "apps.api.routers.market_indicators.refresh_world_bank_macro_indicators",
        lambda **kwargs: (_ for _ in ()).throw(
            WorldBankProviderError("World Bank response for USA/CM.MKT.LCAP.GD.ZS was not a metadata/data list.")
        ),
    )
    client = with_test_client(session)
    try:
        provider_response = client.post(
            "/market-indicators/official-refresh/world-bank",
            json={"target": "USA"},
        )
    finally:
        app.dependency_overrides.clear()

    assert provider_response.status_code == 502
    assert provider_response.json()["detail"]["provider"] == "world_bank"
    assert "metadata/data list" in provider_response.json()["detail"]["message"]


def test_macro_dashboard_api_returns_grouped_stored_history_without_writing():
    session = make_session()
    seed_market_indicators(session=session)
    upsert_market_indicator_observation(
        MarketIndicatorObservationSeed(
            code="cn_cpi_yoy",
            as_of=date(2026, 6, 30),
            value=Decimal("1.000000"),
            source="AkShare macro_china_cpi",
            components={
                "source_url": "https://data.eastmoney.com/cjsj/cpi.html",
                "methodology": "China national CPI YoY.",
            },
        ),
        session=session,
    )
    before = session.query(MarketIndicatorObservation).count()

    client = with_test_client(session)
    try:
        response = client.get("/market-indicators/dashboard?history_limit=6")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total"] == 25
    assert [group["id"] for group in payload["groups"]] == [
        "rates",
        "fundamentals",
        "valuation",
        "external",
        "money",
        "fiscal",
    ]
    assert session.query(MarketIndicatorObservation).count() == before


def test_akshare_macro_refresh_api_reports_partial_success_and_clears_cache(monkeypatch):
    session = make_session()
    calls = {}

    def fake_refresh(**kwargs):
        calls.update(kwargs)
        return AkShareCnMacroRefreshResult(
            observations=4,
            fetched=20,
            skipped=1,
            dry_run=False,
            codes=("cn_cpi_yoy", "cn_ppi_yoy"),
            latest_as_of="2026-06-30",
            diagnostics=("pmi: provider_error:ConnectionError",),
            families=(
                {
                    "family": "cpi",
                    "status": "ok",
                    "fetched": 20,
                    "skipped": 1,
                    "observations": 4,
                    "codes": ["cn_cpi_yoy", "cn_ppi_yoy"],
                },
                {
                    "family": "pmi",
                    "status": "error",
                    "fetched": 0,
                    "skipped": 0,
                    "observations": 0,
                    "codes": [],
                },
            ),
        )

    monkeypatch.setattr(
        "apps.api.routers.market_indicators.refresh_akshare_cn_macro_indicators",
        fake_refresh,
    )
    monkeypatch.setattr(
        "apps.api.routers.market_indicators.clear_market_overview_cache",
        lambda provider_name=None: 5,
    )

    client = with_test_client(session)
    try:
        response = client.post(
            "/market-indicators/official-refresh/akshare-cn",
            json={"family": "all", "history_limit": 12, "dry_run": False},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["provider"] == "akshare"
    assert payload["observations"] == 4
    assert payload["cache"] == {"market_overview_cleared": 5}
    assert payload["diagnostics"] == ["pmi: provider_error:ConnectionError"]
    assert calls == {
        "session": session,
        "family": "all",
        "history_limit": 12,
        "dry_run": False,
    }
