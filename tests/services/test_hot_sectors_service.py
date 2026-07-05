from packages.services.hot_sectors import (
    HotSectorConstituent,
    HotSectorProviderItem,
    HotSectorProviderResult,
    get_hot_sectors_payload,
)


class FakeLiveHotSectorProvider:
    provider_name = "fake_live"

    def fetch_hot_sectors(self, limit: int) -> HotSectorProviderResult:
        return HotSectorProviderResult(
            status="ok",
            data_mode="live",
            source="fake_provider_sector_flow",
            provider=self.provider_name,
            as_of="2026-07-04T09:30:00+00:00",
            is_realtime=True,
            is_delayed=False,
            delay_minutes=None,
            market="CN",
            message="Verified fake provider data for tests.",
            flow_definition={
                "metric": "provider_reported_net_inflow",
                "window": "intraday",
                "currency": "CNY",
                "unit": "yuan",
                "methodology": "Provider-reported sector net inflow.",
            },
            availability={
                "status": "available",
                "reason": None,
                "performance": "available",
                "fund_flow": "available",
                "constituents": "available",
            },
            items=[
                HotSectorProviderItem(
                    sector_id="cn_ai",
                    name="人工智能",
                    name_en="Artificial Intelligence",
                    market="CN",
                    change_percent=3.25,
                    flow_direction="inflow",
                    net_flow_amount=520_000_000,
                    net_flow_currency="CNY",
                    net_flow_unit="yuan",
                    flow_window="intraday",
                    flow_metric="provider_reported_net_inflow",
                    flow_definition="Provider-reported sector net inflow.",
                    leader=HotSectorConstituent("300001.SZ", "测试龙头", 6.5),
                    top_constituents=[HotSectorConstituent("300001.SZ", "测试龙头", 6.5)],
                    as_of="2026-07-04T09:30:00+00:00",
                    provider=self.provider_name,
                    is_verified=True,
                )
            ],
        )


class FakeDelayedHotSectorProvider(FakeLiveHotSectorProvider):
    provider_name = "fake_delayed"

    def fetch_hot_sectors(self, limit: int) -> HotSectorProviderResult:
        result = super().fetch_hot_sectors(limit)
        return HotSectorProviderResult(
            status="ok",
            data_mode="delayed",
            source=result.source,
            provider=self.provider_name,
            as_of=result.as_of,
            is_realtime=False,
            is_delayed=True,
            delay_minutes=15,
            market=result.market,
            message="Delayed fake provider data for tests.",
            flow_definition=result.flow_definition,
            availability={**result.availability, "status": "delayed"},
            items=result.items,
        )


class EmptyHotSectorProvider:
    provider_name = "empty_provider"

    def fetch_hot_sectors(self, limit: int) -> HotSectorProviderResult:
        return HotSectorProviderResult(
            status="degraded",
            data_mode="none",
            source="empty_provider",
            provider=self.provider_name,
            as_of=None,
            is_realtime=False,
            is_delayed=False,
            delay_minutes=None,
            market="CN",
            message="Provider returned no hot-sector rows.",
            flow_definition={
                "metric": "provider_reported_net_inflow",
                "window": "intraday",
                "currency": "CNY",
                "unit": "yuan",
                "methodology": "Provider-reported sector net inflow.",
            },
            availability={
                "status": "no_data",
                "reason": "Provider returned no hot-sector rows.",
                "performance": "no_data",
                "fund_flow": "no_data",
                "constituents": "no_data",
            },
            items=[],
        )


class FailingHotSectorProvider:
    provider_name = "failing_provider"

    def fetch_hot_sectors(self, limit: int) -> HotSectorProviderResult:
        raise RuntimeError("provider failed token=secret123")


def test_static_fixture_fallback_is_degraded_mock_with_metadata():
    payload = get_hot_sectors_payload(limit=1)

    assert payload["status"] == "degraded"
    assert payload["data_mode"] == "mock"
    assert payload["source"] == "static_sector_fixture"
    assert payload["provider"] == "static_fixture"
    assert payload["availability"]["status"] == "mock"
    assert payload["flow_definition"]["metric"] == "static_fixture_demo_value"
    assert payload["count"] == 1
    item = payload["items"][0]
    assert item["sector_id"] == "ev_new_energy"
    assert item["flow_direction"] == "inflow"
    assert item["is_verified"] is False
    assert item["top_constituents"]
    assert item["breadth"]["status"] == "mock"
    assert item["constituent_contribution"]["status"] == "mock"
    assert item["history"]["status"] == "unavailable"
    assert item["taxonomy"]["taxonomy_version"] == "sector-taxonomy-v1"
    assert payload["provider_capabilities"]["sector_ranking"]["status"] == "mock"


def test_provider_backed_live_payload_is_normalized():
    payload = get_hot_sectors_payload(
        limit=5,
        provider_name="fake_live",
        provider=FakeLiveHotSectorProvider(),
    )

    assert payload["status"] == "ok"
    assert payload["data_mode"] == "live"
    assert payload["provider"] == "fake_live"
    assert payload["requested_provider"] == "fake_live"
    assert payload["effective_provider"] == "fake_live"
    assert payload["is_realtime"] is True
    assert payload["is_delayed"] is False
    assert payload["count"] == 1
    item = payload["items"][0]
    assert item["is_verified"] is True
    assert item["fund_flow"] == "流入"
    assert item["fund_flow_amount"] == 5.2
    assert item["leader_symbol"] == "300001.SZ"
    assert item["breadth"] == {
        "status": "derived_from_constituents",
        "advancers": 1,
        "decliners": 0,
        "unchanged": 0,
        "total": 1,
        "advance_decline_ratio": None,
        "source": "verified_constituents",
    }
    assert item["constituent_contribution"]["status"] == "derived_from_constituents"
    assert item["constituent_contribution"]["top_positive"][0]["symbol"] == "300001.SZ"
    assert item["history"]["status"] == "unavailable"
    assert item["taxonomy"] == {
        "status": "versioned",
        "provider_taxonomy": "fake_live",
        "taxonomy_version": "sector-taxonomy-v1",
        "normalized_sector_id": "cn_ai",
    }
    assert item["availability"]["breadth"] == "derived_from_constituents"
    assert item["availability"]["rotation_history"] == "unavailable"
    assert payload["provider_capabilities"]["sector_ranking"]["status"] == "verified"
    assert payload["provider_capabilities"]["rotation_history"]["status"] == "unavailable"


def test_provider_backed_delayed_payload_keeps_delay_metadata():
    payload = get_hot_sectors_payload(
        limit=5,
        provider_name="fake_delayed",
        provider=FakeDelayedHotSectorProvider(),
    )

    assert payload["status"] == "ok"
    assert payload["data_mode"] == "delayed"
    assert payload["is_realtime"] is False
    assert payload["is_delayed"] is True
    assert payload["delay_minutes"] == 15
    assert payload["availability"]["status"] == "delayed"


def test_empty_provider_payload_returns_no_data_without_fabricated_rows():
    payload = get_hot_sectors_payload(
        limit=5,
        provider_name="empty_provider",
        provider=EmptyHotSectorProvider(),
    )

    assert payload["status"] == "degraded"
    assert payload["data_mode"] == "none"
    assert payload["availability"]["status"] == "no_data"
    assert payload["availability"]["breadth"] == "unavailable"
    assert payload["provider_capabilities"]["breadth"]["status"] == "unavailable"
    assert payload["count"] == 0
    assert payload["items"] == []


def test_unknown_provider_returns_unavailable_payload():
    payload = get_hot_sectors_payload(limit=5, provider_name="unknown_provider")

    assert payload["status"] == "unavailable"
    assert payload["data_mode"] == "none"
    assert payload["requested_provider"] == "unknown_provider"
    assert payload["availability"]["breadth"] == "unavailable"
    assert payload["provider_capabilities"]["sector_fund_flow"]["status"] == "unavailable"
    assert payload["count"] == 0
    assert payload["items"] == []


def test_provider_failure_returns_unavailable_payload_without_secret_leak():
    payload = get_hot_sectors_payload(
        limit=5,
        provider_name="failing_provider",
        provider=FailingHotSectorProvider(),
    )

    assert payload["status"] == "unavailable"
    assert payload["data_mode"] == "none"
    assert payload["source"] == "provider_error"
    assert "RuntimeError" in payload["message"]
    assert "secret123" not in payload["message"]
