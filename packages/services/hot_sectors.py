from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol


HOT_SECTOR_TAXONOMY_VERSION = "sector-taxonomy-v1"
DEFAULT_HOT_SECTOR_PROVIDER = "static_fixture"
STATIC_FIXTURE_SOURCE = "static_sector_fixture"
STATIC_FIXTURE_REASON = "Static mock sector data; not live market data."

FLOW_DIRECTION_LABELS = {
    "inflow": "流入",
    "outflow": "流出",
    "flat": "持平",
    "unknown": "未知",
}


@dataclass(frozen=True)
class HotSectorConstituent:
    symbol: str
    name: str
    change_percent: float | None = None
    weight: float | None = None
    net_flow_amount: float | None = None
    contribution_value: float | None = None
    contribution_label: str | None = None

    def to_payload(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "change_percent": self.change_percent,
            "weight": self.weight,
            "net_flow_amount": self.net_flow_amount,
            "contribution_value": self.contribution_value,
            "contribution_label": self.contribution_label,
        }


@dataclass(frozen=True)
class HotSectorProviderItem:
    sector_id: str
    name: str
    name_en: str
    market: str
    change_percent: float | None
    flow_direction: str
    net_flow_amount: float | None
    net_flow_currency: str
    net_flow_unit: str
    flow_window: str
    flow_metric: str
    flow_definition: str
    leader: HotSectorConstituent | None = None
    top_constituents: list[HotSectorConstituent] = field(default_factory=list)
    as_of: str | None = None
    provider: str | None = None
    is_verified: bool = False
    breadth: dict[str, object] | None = None
    constituent_contribution: dict[str, object] | None = None
    taxonomy: dict[str, object] | None = None
    history: dict[str, object] | None = None
    availability: dict[str, object] = field(default_factory=dict)

    def to_payload(self, rank: int, fallback_provider: str | None) -> dict[str, object]:
        leader = self.leader or (self.top_constituents[0] if self.top_constituents else None)
        display_flow_amount = _display_amount_in_hundred_million(self.net_flow_amount, self.net_flow_unit)
        flow_direction = _normalize_flow_direction(self.flow_direction)
        provider_name = self.provider or fallback_provider
        breadth = self.breadth if self.breadth is not None else _build_breadth_payload(
            self.top_constituents,
            is_verified=self.is_verified,
        )
        constituent_contribution = (
            self.constituent_contribution
            if self.constituent_contribution is not None
            else _build_constituent_contribution_payload(
                self.top_constituents,
                is_verified=self.is_verified,
            )
        )
        taxonomy = self.taxonomy or _build_taxonomy_payload(
            provider_name=provider_name,
            sector_id=self.sector_id,
        )
        history = self.history or _build_unavailable_rotation_history_payload()
        availability = self.availability or {
            "performance": "available" if self.change_percent is not None else "no_data",
            "fund_flow": "available" if self.net_flow_amount is not None else "no_data",
            "constituents": "available" if self.top_constituents else "no_data",
        }
        availability = {
            **availability,
            "breadth": availability.get("breadth") or _availability_from_optional_payload(breadth),
            "constituent_contribution": availability.get("constituent_contribution")
            or _availability_from_optional_payload(constituent_contribution),
            "rotation_history": availability.get("rotation_history") or _availability_from_optional_payload(history),
            "taxonomy": availability.get("taxonomy") or "versioned",
        }
        return {
            "sector_id": self.sector_id,
            "name": self.name,
            "name_en": self.name_en,
            "market": self.market,
            "taxonomy_version": HOT_SECTOR_TAXONOMY_VERSION,
            "taxonomy": taxonomy,
            "rank": rank,
            "change_percent": self.change_percent,
            "change_window": "intraday",
            "fund_flow": FLOW_DIRECTION_LABELS[flow_direction],
            "fund_flow_amount": display_flow_amount,
            "flow_direction": flow_direction,
            "net_flow_amount": self.net_flow_amount,
            "net_flow_currency": self.net_flow_currency,
            "net_flow_unit": self.net_flow_unit,
            "flow_window": self.flow_window,
            "flow_metric": self.flow_metric,
            "flow_definition": self.flow_definition,
            "leader_symbol": leader.symbol if leader else None,
            "leader_name": leader.name if leader else None,
            "leader_change_percent": leader.change_percent if leader else None,
            "leader": leader.to_payload() if leader else None,
            "symbols_count": len(self.top_constituents),
            "top_constituents": [constituent.to_payload() for constituent in self.top_constituents],
            "breadth": breadth,
            "constituent_contribution": constituent_contribution,
            "history": history,
            "as_of": self.as_of,
            "provider": provider_name,
            "is_verified": self.is_verified,
            "availability": availability,
        }


@dataclass(frozen=True)
class HotSectorProviderResult:
    status: str
    data_mode: str
    source: str
    provider: str | None
    as_of: str | None
    is_realtime: bool
    is_delayed: bool
    delay_minutes: int | None
    market: str
    message: str
    flow_definition: dict[str, object]
    availability: dict[str, object]
    items: list[HotSectorProviderItem]
    requested_provider: str | None = None
    effective_provider: str | None = None
    provider_capabilities: dict[str, object] = field(default_factory=dict)


class HotSectorFundFlowProvider(Protocol):
    provider_name: str

    def fetch_hot_sectors(self, limit: int) -> HotSectorProviderResult:
        ...


class StaticHotSectorFixtureProvider:
    provider_name = DEFAULT_HOT_SECTOR_PROVIDER

    def fetch_hot_sectors(self, limit: int) -> HotSectorProviderResult:
        return HotSectorProviderResult(
            status="degraded",
            data_mode="mock",
            source=STATIC_FIXTURE_SOURCE,
            provider=self.provider_name,
            requested_provider=self.provider_name,
            effective_provider=self.provider_name,
            as_of=None,
            is_realtime=False,
            is_delayed=False,
            delay_minutes=None,
            market="mixed_global",
            message=STATIC_FIXTURE_REASON,
            flow_definition={
                "metric": "static_fixture_demo_value",
                "window": "unknown",
                "currency": "N/A",
                "unit": "hundred_million",
                "methodology": "Static fixture values for UI demonstration only; not real fund-flow data.",
            },
            availability={
                "status": "mock",
                "reason": STATIC_FIXTURE_REASON,
                "performance": "mock",
                "fund_flow": "mock",
                "constituents": "mock",
            },
            items=_build_static_fixture_items(),
        )


class AkshareHotSectorFundFlowProvider:
    provider_name = "akshare"

    def fetch_hot_sectors(self, limit: int) -> HotSectorProviderResult:
        import akshare as ak

        sector_frame = ak.stock_sector_fund_flow_rank(indicator="今日")
        columns = [str(column) for column in getattr(sector_frame, "columns", [])]
        as_of = datetime.now(timezone.utc).isoformat()
        items: list[HotSectorProviderItem] = []
        for _, row in sector_frame.head(limit).iterrows():
            sector_name = str(_row_value(row, columns, "名称") or "Unknown sector")
            change_percent = _safe_float(_row_value(row, columns, "涨跌幅"))
            net_flow_amount = _safe_float(_row_value(row, columns, "主力净流入", "净额"))
            leader_name = _row_value(row, columns, "最大股") or _row_value(row, columns, "领涨股票")
            leader = None
            if leader_name is not None:
                leader = HotSectorConstituent(
                    symbol=str(leader_name),
                    name=str(leader_name),
                    change_percent=None,
                    net_flow_amount=None,
                )
            items.append(
                HotSectorProviderItem(
                    sector_id=_slugify_sector_name(sector_name),
                    name=sector_name,
                    name_en=sector_name,
                    market="CN",
                    change_percent=change_percent,
                    flow_direction=_direction_from_amount(net_flow_amount),
                    net_flow_amount=net_flow_amount,
                    net_flow_currency="CNY",
                    net_flow_unit="yuan",
                    flow_window="intraday",
                    flow_metric="provider_reported_main_net_inflow",
                    flow_definition="AkShare/Eastmoney provider-reported main net inflow for the sector.",
                    leader=leader,
                    top_constituents=[leader] if leader else [],
                    as_of=as_of,
                    provider=self.provider_name,
                    is_verified=True,
                    availability={
                        "performance": "available" if change_percent is not None else "no_data",
                        "fund_flow": "available" if net_flow_amount is not None else "no_data",
                        "constituents": "available" if leader else "no_data",
                    },
                )
            )

        return HotSectorProviderResult(
            status="ok" if items else "degraded",
            data_mode="delayed",
            source="akshare_sector_fund_flow_rank",
            provider=self.provider_name,
            requested_provider=self.provider_name,
            effective_provider=self.provider_name,
            as_of=as_of if items else None,
            is_realtime=False,
            is_delayed=True,
            delay_minutes=15,
            market="CN",
            message="AkShare sector fund-flow data. Field definitions follow the provider's Eastmoney source.",
            flow_definition={
                "metric": "provider_reported_main_net_inflow",
                "window": "intraday",
                "currency": "CNY",
                "unit": "yuan",
                "methodology": "Provider-reported main net inflow by sector from AkShare/Eastmoney.",
            },
            availability={
                "status": "delayed" if items else "no_data",
                "reason": None if items else "AkShare returned no sector fund-flow rows.",
                "performance": "available" if items else "no_data",
                "fund_flow": "available" if items else "no_data",
                "constituents": "available" if items else "no_data",
            },
            items=items,
        )


def get_hot_sectors_payload(
    limit: int = 5,
    provider_name: str | None = None,
    provider: HotSectorFundFlowProvider | None = None,
) -> dict[str, object]:
    requested_provider = _normalize_requested_provider(provider_name)
    if provider is not None:
        return _fetch_and_normalize_provider(provider, limit, requested_provider)

    if requested_provider in {DEFAULT_HOT_SECTOR_PROVIDER, "mock", "static"}:
        return _fetch_and_normalize_provider(StaticHotSectorFixtureProvider(), limit, requested_provider)
    if requested_provider == "akshare":
        return _fetch_and_normalize_provider(AkshareHotSectorFundFlowProvider(), limit, requested_provider)

    return build_unavailable_hot_sectors_payload(
        message=f"Hot-sector fund-flow provider '{requested_provider}' is not configured or verified.",
        requested_provider=requested_provider,
        effective_provider=requested_provider,
    )


def build_unavailable_hot_sectors_payload(
    *,
    message: str,
    requested_provider: str | None = None,
    effective_provider: str | None = None,
    source: str = "none",
) -> dict[str, object]:
    return {
        "status": "unavailable",
        "data_mode": "none",
        "source": source,
        "provider": effective_provider,
        "requested_provider": requested_provider or DEFAULT_HOT_SECTOR_PROVIDER,
        "effective_provider": effective_provider or "none",
        "as_of": None,
        "generated_at": _utc_now_isoformat(),
        "is_realtime": False,
        "is_delayed": False,
        "delay_minutes": None,
        "market": "unknown",
        "taxonomy_version": HOT_SECTOR_TAXONOMY_VERSION,
        "flow_definition": {
            "metric": "unavailable",
            "window": "unknown",
            "currency": "N/A",
            "unit": "unknown",
            "methodology": "No verified sector fund-flow data is available.",
        },
        "availability": {
            "status": "unavailable",
            "reason": message,
            "performance": "unavailable",
            "fund_flow": "unavailable",
            "constituents": "unavailable",
            "breadth": "unavailable",
            "constituent_contribution": "unavailable",
            "rotation_history": "unavailable",
            "taxonomy": "unavailable",
        },
        "provider_capabilities": _build_unavailable_provider_capabilities(message),
        "message": message,
        "count": 0,
        "items": [],
    }

def _fetch_and_normalize_provider(
    provider: HotSectorFundFlowProvider,
    limit: int,
    requested_provider: str,
) -> dict[str, object]:
    try:
        provider_result = provider.fetch_hot_sectors(limit=limit)
    except Exception as error:
        return build_unavailable_hot_sectors_payload(
            message=f"Hot-sector provider '{provider.provider_name}' failed: {error.__class__.__name__}.",
            requested_provider=requested_provider,
            effective_provider=provider.provider_name,
            source="provider_error",
        )

    return _normalize_provider_result(provider_result, limit, requested_provider)


def _normalize_provider_result(
    provider_result: HotSectorProviderResult,
    limit: int,
    requested_provider: str,
) -> dict[str, object]:
    effective_provider = provider_result.effective_provider or provider_result.provider or DEFAULT_HOT_SECTOR_PROVIDER
    if not provider_result.items:
        message = provider_result.message or "No verified hot-sector rows are available."
        return {
            "status": "degraded",
            "data_mode": "none",
            "source": provider_result.source,
            "provider": provider_result.provider,
            "requested_provider": requested_provider,
            "effective_provider": effective_provider,
            "as_of": None,
            "generated_at": _utc_now_isoformat(),
            "is_realtime": False,
            "is_delayed": provider_result.is_delayed,
            "delay_minutes": provider_result.delay_minutes,
            "market": provider_result.market,
            "taxonomy_version": HOT_SECTOR_TAXONOMY_VERSION,
            "flow_definition": provider_result.flow_definition,
            "availability": {
                **provider_result.availability,
                "status": "no_data",
                "reason": message,
                "breadth": provider_result.availability.get("breadth") or "unavailable",
                "constituent_contribution": provider_result.availability.get("constituent_contribution")
                or "unavailable",
                "rotation_history": provider_result.availability.get("rotation_history") or "unavailable",
                "taxonomy": provider_result.availability.get("taxonomy") or "versioned",
            },
            "provider_capabilities": _build_provider_capabilities_payload(provider_result, has_items=False),
            "message": message,
            "count": 0,
            "items": [],
        }

    sorted_items = sorted(provider_result.items, key=_sector_sort_key, reverse=True)[:limit]
    serialized_items = [
        item.to_payload(rank=index + 1, fallback_provider=effective_provider)
        for index, item in enumerate(sorted_items)
    ]
    return {
        "status": provider_result.status,
        "data_mode": provider_result.data_mode,
        "source": provider_result.source,
        "provider": provider_result.provider,
        "requested_provider": requested_provider,
        "effective_provider": effective_provider,
        "as_of": provider_result.as_of,
        "generated_at": _utc_now_isoformat(),
        "is_realtime": provider_result.is_realtime,
        "is_delayed": provider_result.is_delayed,
        "delay_minutes": provider_result.delay_minutes,
        "market": provider_result.market,
        "taxonomy_version": HOT_SECTOR_TAXONOMY_VERSION,
        "flow_definition": provider_result.flow_definition,
        "availability": provider_result.availability,
        "provider_capabilities": _build_provider_capabilities_payload(provider_result, has_items=True),
        "message": provider_result.message,
        "count": len(serialized_items),
        "items": serialized_items,
    }


def _build_static_fixture_items() -> list[HotSectorProviderItem]:
    return [
        _static_item(
            sector_id="ev_new_energy",
            name="新能源汽车",
            name_en="EV & New Energy",
            change_percent=5.2,
            net_flow_amount=1_250_000_000,
            constituents=[
                HotSectorConstituent("TSLA", "特斯拉", 6.8),
                HotSectorConstituent("NIO", "蔚来", 4.1),
                HotSectorConstituent("XPEV", "小鹏汽车", 3.2),
                HotSectorConstituent("LI", "理想汽车", 2.9),
            ],
        ),
        _static_item(
            sector_id="artificial_intelligence",
            name="人工智能",
            name_en="Artificial Intelligence",
            change_percent=3.8,
            net_flow_amount=830_000_000,
            constituents=[
                HotSectorConstituent("NVDA", "英伟达", 5.2),
                HotSectorConstituent("AMD", "超威半导体", 3.4),
                HotSectorConstituent("GOOGL", "谷歌", 1.7),
                HotSectorConstituent("MSFT", "微软", 1.2),
            ],
        ),
        _static_item(
            sector_id="semiconductor",
            name="半导体",
            name_en="Semiconductor",
            change_percent=2.1,
            net_flow_amount=-320_000_000,
            constituents=[
                HotSectorConstituent("TSM", "台积电", 3.1),
                HotSectorConstituent("ASML", "阿斯麦", 2.6),
                HotSectorConstituent("INTC", "英特尔", -0.5),
                HotSectorConstituent("QCOM", "高通", 0.8),
            ],
        ),
        _static_item(
            sector_id="biotech_pharma",
            name="生物医药",
            name_en="Biotech & Pharma",
            change_percent=-1.5,
            net_flow_amount=-510_000_000,
            constituents=[
                HotSectorConstituent("PFE", "辉瑞", -0.8),
                HotSectorConstituent("MRNA", "Moderna", -2.7),
                HotSectorConstituent("JNJ", "强生", -0.3),
                HotSectorConstituent("ABBV", "艾伯维", 0.2),
            ],
        ),
        _static_item(
            sector_id="consumer_electronics",
            name="消费电子",
            name_en="Consumer Electronics",
            change_percent=0.8,
            net_flow_amount=210_000_000,
            constituents=[
                HotSectorConstituent("AAPL", "苹果", 1.2),
                HotSectorConstituent("SONY", "索尼", 0.6),
                HotSectorConstituent("SAMSUNG", "三星", 0.4),
            ],
        ),
    ]


def _static_item(
    *,
    sector_id: str,
    name: str,
    name_en: str,
    change_percent: float,
    net_flow_amount: float,
    constituents: list[HotSectorConstituent],
) -> HotSectorProviderItem:
    return HotSectorProviderItem(
        sector_id=sector_id,
        name=name,
        name_en=name_en,
        market="mixed_global",
        change_percent=change_percent,
        flow_direction=_direction_from_amount(net_flow_amount),
        net_flow_amount=net_flow_amount,
        net_flow_currency="N/A",
        net_flow_unit="yuan",
        flow_window="unknown",
        flow_metric="static_fixture_demo_value",
        flow_definition="Static fixture value for UI demonstration only; not real sector fund-flow data.",
        leader=constituents[0] if constituents else None,
        top_constituents=constituents,
        as_of=None,
        provider=DEFAULT_HOT_SECTOR_PROVIDER,
        is_verified=False,
        availability={
            "performance": "mock",
            "fund_flow": "mock",
            "constituents": "mock",
            "reason": STATIC_FIXTURE_REASON,
        },
    )


def _normalize_requested_provider(provider_name: str | None) -> str:
    normalized_provider = (provider_name or DEFAULT_HOT_SECTOR_PROVIDER).strip().lower()
    return normalized_provider or DEFAULT_HOT_SECTOR_PROVIDER


def _direction_from_amount(amount: float | None) -> str:
    if amount is None:
        return "unknown"
    if amount > 0:
        return "inflow"
    if amount < 0:
        return "outflow"
    return "flat"


def _normalize_flow_direction(flow_direction: str | None) -> str:
    normalized_direction = (flow_direction or "unknown").strip().lower()
    if normalized_direction in FLOW_DIRECTION_LABELS:
        return normalized_direction
    return "unknown"


def _display_amount_in_hundred_million(amount: float | None, unit: str) -> float | None:
    if amount is None:
        return None
    if unit == "hundred_million":
        return amount
    return amount / 100_000_000


def _sector_sort_key(item: HotSectorProviderItem) -> float:
    if item.change_percent is None:
        return float("-inf")
    return item.change_percent


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        parsed_value = float(value)
    except (TypeError, ValueError):
        return None
    if parsed_value != parsed_value:
        return None
    return parsed_value


def _row_value(row: object, columns: list[str], *substrings: str) -> object | None:
    column = _find_column(columns, *substrings)
    if column is None:
        return None
    try:
        return row[column]
    except Exception:
        return None


def _find_column(columns: list[str], *substrings: str) -> str | None:
    for column in columns:
        if all(substring in column for substring in substrings):
            return column
    return None


def _slugify_sector_name(sector_name: str) -> str:
    normalized_characters = [character.lower() if character.isalnum() else "_" for character in sector_name]
    return "".join(normalized_characters).strip("_") or "unknown_sector"


def _utc_now_isoformat() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_breadth_payload(
    constituents: list[HotSectorConstituent],
    *,
    is_verified: bool,
) -> dict[str, object]:
    if not constituents:
        return {
            "status": "unavailable",
            "reason": "No constituent performance data is available for breadth calculation.",
        }

    parsed_changes = [
        _safe_float(constituent.change_percent)
        for constituent in constituents
    ]
    advancers = sum(1 for change_percent in parsed_changes if change_percent is not None and change_percent > 0)
    decliners = sum(1 for change_percent in parsed_changes if change_percent is not None and change_percent < 0)
    unchanged = sum(1 for change_percent in parsed_changes if change_percent == 0)
    total = len(constituents)
    advance_decline_ratio = None if decliners == 0 else advancers / decliners
    return {
        "status": "derived_from_constituents" if is_verified else "mock",
        "advancers": advancers,
        "decliners": decliners,
        "unchanged": unchanged,
        "total": total,
        "advance_decline_ratio": advance_decline_ratio,
        "source": "verified_constituents" if is_verified else "mock_constituents",
    }


def _build_constituent_contribution_payload(
    constituents: list[HotSectorConstituent],
    *,
    is_verified: bool,
) -> dict[str, object]:
    ranked_constituents = [
        constituent
        for constituent in constituents
        if _contribution_sort_value(constituent) is not None
    ]
    if not ranked_constituents:
        return {
            "status": "unavailable",
            "reason": "No constituent contribution inputs are available from the provider.",
        }

    sorted_by_contribution = sorted(
        ranked_constituents,
        key=lambda constituent: _contribution_sort_value(constituent) or 0,
        reverse=True,
    )
    return {
        "status": "derived_from_constituents" if is_verified else "mock",
        "metric": "contribution_value_or_change_percent",
        "top_positive": [
            _constituent_contribution_payload(constituent)
            for constituent in sorted_by_contribution
            if (_contribution_sort_value(constituent) or 0) > 0
        ][:3],
        "top_negative": [
            _constituent_contribution_payload(constituent)
            for constituent in reversed(sorted_by_contribution)
            if (_contribution_sort_value(constituent) or 0) < 0
        ][:3],
    }


def _constituent_contribution_payload(constituent: HotSectorConstituent) -> dict[str, object]:
    return {
        "symbol": constituent.symbol,
        "name": constituent.name,
        "value": _contribution_sort_value(constituent),
        "label": constituent.contribution_label or "change_percent",
    }


def _contribution_sort_value(constituent: HotSectorConstituent) -> float | None:
    if constituent.contribution_value is not None:
        return constituent.contribution_value
    if constituent.net_flow_amount is not None:
        return constituent.net_flow_amount
    return constituent.change_percent


def _build_taxonomy_payload(provider_name: str | None, sector_id: str) -> dict[str, object]:
    return {
        "status": "versioned",
        "provider_taxonomy": provider_name or "unknown",
        "taxonomy_version": HOT_SECTOR_TAXONOMY_VERSION,
        "normalized_sector_id": sector_id,
    }


def _build_unavailable_rotation_history_payload() -> dict[str, object]:
    return {
        "status": "unavailable",
        "reason": "Rotation history snapshots are not stored for this provider yet.",
        "snapshot_count": 0,
        "items": [],
    }


def _availability_from_optional_payload(payload: dict[str, object] | None) -> str:
    if not payload:
        return "unavailable"
    status = str(payload.get("status") or "available")
    if status in {"available", "derived_from_constituents", "mock", "versioned"}:
        return status
    return status


def _build_unavailable_provider_capabilities(reason: str) -> dict[str, object]:
    return {
        "sector_ranking": {"status": "unavailable", "reason": reason},
        "sector_fund_flow": {"status": "unavailable", "reason": reason},
        "constituents": {"status": "unavailable", "reason": reason},
        "breadth": {"status": "unavailable", "reason": reason},
        "constituent_contribution": {"status": "unavailable", "reason": reason},
        "rotation_history": {"status": "unavailable", "reason": reason},
        "taxonomy": {"status": "unavailable", "reason": reason},
    }


def _build_provider_capabilities_payload(
    provider_result: HotSectorProviderResult,
    *,
    has_items: bool,
) -> dict[str, object]:
    if provider_result.provider_capabilities:
        return provider_result.provider_capabilities

    if provider_result.data_mode == "mock":
        capability_status = "mock"
    elif has_items and provider_result.status == "ok":
        capability_status = "verified" if provider_result.is_realtime else "delayed"
    elif has_items:
        capability_status = "partial"
    else:
        capability_status = "unavailable"

    reason = provider_result.availability.get("reason") if isinstance(provider_result.availability, dict) else None
    return {
        "sector_ranking": {
            "status": capability_status,
            "source": provider_result.source,
            "reason": reason,
        },
        "sector_fund_flow": {
            "status": capability_status,
            "metric": provider_result.flow_definition.get("metric"),
            "reason": reason,
        },
        "constituents": {
            "status": provider_result.availability.get("constituents", capability_status),
            "reason": reason,
        },
        "breadth": {
            "status": provider_result.availability.get("breadth", "derived_from_constituents" if has_items else "unavailable"),
            "reason": reason,
        },
        "constituent_contribution": {
            "status": provider_result.availability.get(
                "constituent_contribution",
                "derived_from_constituents" if has_items else "unavailable",
            ),
            "reason": reason,
        },
        "rotation_history": {
            "status": provider_result.availability.get("rotation_history", "unavailable"),
            "reason": "Rotation history is not persisted yet.",
        },
        "taxonomy": {
            "status": provider_result.availability.get("taxonomy", "versioned"),
            "taxonomy_version": HOT_SECTOR_TAXONOMY_VERSION,
        },
    }
