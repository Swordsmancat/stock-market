import pytest

from packages.services.stock_selection_profiles import (
    get_stock_selection_profiles_payload,
    resolve_stock_selection_profile,
)


def test_stock_selection_profiles_expose_named_visible_editable_criteria():
    payload = get_stock_selection_profiles_payload()

    assert [item["id"] for item in payload["items"]] == [
        "balanced_research",
        "quality_value",
        "trend_liquidity",
    ]
    assert all(item["criteria"] for item in payload["items"])
    assert all(item["supported_overrides"] for item in payload["items"])
    assert payload["safety"]["deterministic_ranking"] is True
    assert payload["safety"]["no_automated_trading"] is True


def test_resolve_stock_selection_profile_echoes_defaults_overrides_and_effective_criteria():
    resolved = resolve_stock_selection_profile(
        " BALANCED_RESEARCH ",
        {"max_pe_ratio": 30.0, "min_latest_volume": 2_000_000.0},
    )

    assert resolved["profile"]["id"] == "balanced_research"
    assert resolved["default_criteria"]["max_pe_ratio"] == 35.0
    assert resolved["overrides"] == {
        "max_pe_ratio": 30.0,
        "min_latest_volume": 2_000_000.0,
    }
    assert resolved["effective_criteria"]["max_pe_ratio"] == 30.0
    assert resolved["effective_criteria"]["min_revenue_growth"] == 0.05


def test_resolve_stock_selection_profile_rejects_unknown_profile():
    with pytest.raises(ValueError, match="Unknown stock-selection profile"):
        resolve_stock_selection_profile("missing")


def test_resolve_stock_selection_profile_rejects_unknown_override():
    with pytest.raises(ValueError, match="Unsupported stock-selection profile override"):
        resolve_stock_selection_profile("quality_value", {"future_return": 0.5})
