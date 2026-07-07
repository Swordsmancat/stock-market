from packages.services.source_capabilities import (
    CHINA_MACRO_SOURCE_CAPABILITIES,
    get_china_macro_source_capability_payload,
    get_source_capability_by_id,
)


def _items_by_id(payload: dict[str, object]) -> dict[str, dict[str, object]]:
    return {str(item["id"]): item for item in payload["items"]}


def test_china_macro_capability_registry_covers_required_source_families() -> None:
    payload = get_china_macro_source_capability_payload()
    items = _items_by_id(payload)

    assert len(CHINA_MACRO_SOURCE_CAPABILITIES) >= 6
    assert {
        "nbs_cn_macro",
        "pboc_cn_m2",
        "world_bank_china_macro",
        "imf_china_macro",
        "trading_economics_china_macro",
        "akshare_tushare_cn_macro",
    } <= set(items)
    assert items["nbs_cn_macro"]["access_mode"] == "official_api"
    assert items["pboc_cn_m2"]["access_mode"] in {"public_page", "manual_seed"}
    assert items["world_bank_china_macro"]["adapter_status"] == "adapter_ready"
    assert items["trading_economics_china_macro"]["credential_required"] is True
    assert items["akshare_tushare_cn_macro"]["access_mode"] == "library_wrapper"


def test_china_macro_capability_payload_serializes_stable_contract() -> None:
    payload = get_china_macro_source_capability_payload()
    items = _items_by_id(payload)
    nbs = items["nbs_cn_macro"]

    assert set(payload) == {
        "status",
        "summary",
        "groups",
        "items",
        "diagnostics",
        "citation_policy",
        "recommended_next_action",
    }
    assert payload["status"] == "degraded"
    assert payload["summary"]["total"] == len(CHINA_MACRO_SOURCE_CAPABILITIES)
    assert payload["summary"]["adapter_ready"] >= 1
    assert payload["summary"]["candidate"] >= 1
    assert payload["summary"]["manual_only"] >= 1
    assert nbs["region"] == "CN"
    assert nbs["indicator_families"] == ["GDP", "CPI", "PPI", "PMI", "activity"]
    assert nbs["indicator_codes"] == ["cn_gdp", "cn_cpi_yoy", "cn_ppi_yoy", "cn_pmi"]
    assert nbs["validation"]["status"] == "not_checked"
    assert nbs["validation"]["checked_at"] is None
    assert isinstance(nbs["validation"]["diagnostics"], list)
    assert nbs["citation_policy"].startswith("Capability metadata is not evidence")
    assert nbs["is_ai_citable"] is False
    assert {group["adapter_status"] for group in payload["groups"]} >= {
        "adapter_ready",
        "candidate",
        "manual_only",
    }


def test_china_macro_capability_rows_do_not_create_citation_ids() -> None:
    payload = get_china_macro_source_capability_payload()

    for item in payload["items"]:
        assert item["is_ai_citable"] is False
        assert "citation_id" not in item
        assert "market_indicator:" not in str(item)
        assert item["citation_policy"].endswith("validated observations are stored locally.")


def test_get_source_capability_by_id_normalizes_and_rejects_unknown_ids() -> None:
    capability = get_source_capability_by_id(" NBS_CN_MACRO ")

    assert capability.id == "nbs_cn_macro"
    assert get_source_capability_by_id("not-a-source") is None
