from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


AccessMode = Literal[
    "official_api",
    "public_page",
    "manual_seed",
    "vendor_api",
    "library_wrapper",
    "unsupported",
]
AdapterStatus = Literal[
    "implemented",
    "adapter_ready",
    "candidate",
    "manual_only",
    "blocked",
    "future",
]
ValidationStatus = Literal["not_checked", "ok", "warning", "failed", "skipped"]

CAPABILITY_CITATION_POLICY = (
    "Capability metadata is not evidence; AI may cite macro data only after "
    "validated observations are stored locally."
)


@dataclass(frozen=True)
class SourceCapabilityLink:
    label: str
    url: str
    source_type: str

    def to_payload(self) -> dict[str, object]:
        return {
            "label": self.label,
            "url": self.url,
            "source_type": self.source_type,
        }


@dataclass(frozen=True)
class SourceCapabilityValidation:
    status: ValidationStatus = "not_checked"
    checked_at: str | None = None
    summary: str = "Static candidate record; live validation has not been run."
    diagnostics: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, object]:
        return {
            "status": self.status,
            "checked_at": self.checked_at,
            "summary": self.summary,
            "diagnostics": list(self.diagnostics),
        }


@dataclass(frozen=True)
class SourceCapability:
    id: str
    label: str
    authority: str
    region: str
    indicator_families: tuple[str, ...]
    indicator_codes: tuple[str, ...]
    access_mode: AccessMode
    adapter_status: AdapterStatus
    credential_required: bool
    license_note: str
    freshness_policy: str
    collection_links: tuple[SourceCapabilityLink, ...]
    recommended_next_action: str
    validation: SourceCapabilityValidation = SourceCapabilityValidation()
    citation_policy: str = CAPABILITY_CITATION_POLICY
    live_probe_url: str | None = None
    live_probe_markers: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "authority": self.authority,
            "region": self.region,
            "indicator_families": list(self.indicator_families),
            "indicator_codes": list(self.indicator_codes),
            "access_mode": self.access_mode,
            "adapter_status": self.adapter_status,
            "credential_required": self.credential_required,
            "license_note": self.license_note,
            "freshness_policy": self.freshness_policy,
            "collection_links": [link.to_payload() for link in self.collection_links],
            "validation": self.validation.to_payload(),
            "citation_policy": self.citation_policy,
            "recommended_next_action": self.recommended_next_action,
            "probe_url": self.live_probe_url,
            "is_ai_citable": False,
        }


CHINA_MACRO_SOURCE_CAPABILITIES: tuple[SourceCapability, ...] = (
    SourceCapability(
        id="nbs_cn_macro",
        label="NBS China macro statistics",
        authority="National Bureau of Statistics of China",
        region="CN",
        indicator_families=("GDP", "CPI", "PPI", "PMI", "activity"),
        indicator_codes=("cn_gdp", "cn_cpi_yoy", "cn_ppi_yoy", "cn_pmi"),
        access_mode="official_api",
        adapter_status="candidate",
        credential_required=False,
        license_note=(
            "Official public statistics candidate; automated access pattern, "
            "schema stability, and usage terms must be validated before an adapter."
        ),
        freshness_policy=(
            "Monthly and quarterly public macro releases; release cadence depends "
            "on the indicator family."
        ),
        collection_links=(
            SourceCapabilityLink(
                label="NBS National Data",
                url="https://data.stats.gov.cn/english/",
                source_type="official_database",
            ),
            SourceCapabilityLink(
                label="NBS official site",
                url="https://www.stats.gov.cn/english/",
                source_type="official_site",
            ),
        ),
        recommended_next_action=(
            "Run an opt-in live probe against NBS National Data and verify schema, "
            "language, rate limits, and usage terms before proposing an adapter."
        ),
        live_probe_url="https://data.stats.gov.cn/english/easyquery.htm",
        live_probe_markers=("National Data",),
    ),
    SourceCapability(
        id="pboc_cn_m2",
        label="PBOC China M2 monetary statistics",
        authority="People's Bank of China",
        region="CN",
        indicator_families=("M2", "liquidity", "monetary_policy"),
        indicator_codes=("cn_m2_yoy",),
        access_mode="public_page",
        adapter_status="manual_only",
        credential_required=False,
        license_note=(
            "Official public monetary-statistics page is usable for manual review; "
            "a stable machine-readable endpoint has not been validated in this MVP."
        ),
        freshness_policy=(
            "Monthly public monetary-statistics release; local evidence still "
            "requires reviewed source and calculation metadata."
        ),
        collection_links=(
            SourceCapabilityLink(
                label="PBOC statistics",
                url="https://www.pbc.gov.cn/en/3688006/index.html",
                source_type="official_page",
            ),
        ),
        recommended_next_action=(
            "Keep China M2 as manual seed evidence until a stable PBOC machine "
            "readable source is validated."
        ),
        live_probe_url="https://www.pbc.gov.cn/en/3688006/index.html",
        live_probe_markers=("M2",),
    ),
    SourceCapability(
        id="world_bank_china_macro",
        label="World Bank China annual macro fallback",
        authority="World Bank public indicators API",
        region="CN",
        indicator_families=("GDP", "annual_macro", "valuation_context"),
        indicator_codes=("buffett_indicator_cn", "cn_gdp_context"),
        access_mode="official_api",
        adapter_status="adapter_ready",
        credential_required=False,
        license_note=(
            "Public World Bank API is already used by the Buffett Indicator "
            "refresh path; additional China annual context can reuse the same "
            "audited observation boundary in a follow-up adapter."
        ),
        freshness_policy=(
            "Annual macro data is often lagged; missing current-year values are "
            "normal reporting lag, not a market signal."
        ),
        collection_links=(
            SourceCapabilityLink(
                label="World Bank China GDP",
                url="https://api.worldbank.org/v2/country/CHN/indicator/NY.GDP.MKTP.CD?format=json",
                source_type="public_api",
            ),
            SourceCapabilityLink(
                label="World Bank market cap / GDP",
                url="https://data.worldbank.org/indicator/CM.MKT.LCAP.GD.ZS?locations=CN",
                source_type="public_dataset",
            ),
        ),
        recommended_next_action=(
            "Use World Bank as the safest follow-up for low-frequency China GDP "
            "context; do not use it for monthly CPI/PPI/PMI/M2 freshness gaps."
        ),
        live_probe_url=(
            "https://api.worldbank.org/v2/country/CHN/indicator/"
            "NY.GDP.MKTP.CD?format=json&per_page=1"
        ),
        live_probe_markers=("countryiso3code", "CHN"),
    ),
    SourceCapability(
        id="imf_china_macro",
        label="IMF China macro fallback",
        authority="International Monetary Fund",
        region="CN",
        indicator_families=("GDP", "CPI", "forecast_context"),
        indicator_codes=("cn_gdp_context", "cn_cpi_context"),
        access_mode="official_api",
        adapter_status="candidate",
        credential_required=False,
        license_note=(
            "Official IMF API candidate; indicator mapping and redistribution "
            "terms require validation before local evidence import."
        ),
        freshness_policy=(
            "Monthly, quarterly, or annual depending on IMF dataset and indicator; "
            "forecast values must be labeled separately from observations."
        ),
        collection_links=(
            SourceCapabilityLink(
                label="IMF Data API",
                url="https://www.imf.org/external/datamapper/api/v1/",
                source_type="official_api",
            ),
        ),
        recommended_next_action=(
            "Validate IMF endpoint shape and observation-vs-forecast semantics "
            "before considering it for China macro context."
        ),
        live_probe_url="https://www.imf.org/external/datamapper/api/v1/NGDP_RPCH/CHN",
        live_probe_markers=("values", "CHN"),
    ),
    SourceCapability(
        id="trading_economics_china_macro",
        label="Trading Economics China macro vendor API",
        authority="Trading Economics",
        region="CN",
        indicator_families=("GDP", "CPI", "PPI", "PMI", "calendar"),
        indicator_codes=("cn_gdp", "cn_cpi_yoy", "cn_ppi_yoy", "cn_pmi"),
        access_mode="vendor_api",
        adapter_status="candidate",
        credential_required=True,
        license_note=(
            "Vendor API candidate; credential, quota, redistribution, and paid "
            "license terms must be reviewed before use."
        ),
        freshness_policy=(
            "Release cadence follows provider calendar and subscription tier; "
            "do not assume realtime or unrestricted redistribution."
        ),
        collection_links=(
            SourceCapabilityLink(
                label="Trading Economics API documentation",
                url="https://docs.tradingeconomics.com/",
                source_type="vendor_api_docs",
            ),
        ),
        recommended_next_action=(
            "Treat as a paid/vendor candidate only after license, credential, "
            "and citation boundaries are accepted."
        ),
        live_probe_url=None,
    ),
    SourceCapability(
        id="akshare_tushare_cn_macro",
        label="AkShare / Tushare China macro wrappers",
        authority="AkShare and Tushare project/vendor APIs",
        region="CN",
        indicator_families=("A_share_market", "macro_wrappers", "liquidity"),
        indicator_codes=("cn_m2_yoy", "cn_cpi_yoy", "cn_ppi_yoy"),
        access_mode="library_wrapper",
        adapter_status="candidate",
        credential_required=True,
        license_note=(
            "Library-wrapper candidate; AkShare/Tushare can simplify access but "
            "the upstream source, token requirements, and license chain must be "
            "recorded before values become audited evidence."
        ),
        freshness_policy=(
            "Freshness depends on wrapper implementation and upstream source; "
            "schema drift must be monitored before production use."
        ),
        collection_links=(
            SourceCapabilityLink(
                label="AkShare documentation",
                url="https://akshare.akfamily.xyz/",
                source_type="library_docs",
            ),
            SourceCapabilityLink(
                label="Tushare Pro documentation",
                url="https://tushare.pro/document/2",
                source_type="vendor_api_docs",
            ),
        ),
        recommended_next_action=(
            "Use only as a convenience candidate after explicit dependency, "
            "token, upstream-source, and schema validation."
        ),
        live_probe_url=None,
    ),
)


def get_source_capability_by_id(source_id: str) -> SourceCapability | None:
    normalized_source_id = source_id.strip().lower()
    for capability in CHINA_MACRO_SOURCE_CAPABILITIES:
        if capability.id == normalized_source_id:
            return capability
    return None


def get_china_macro_source_capability_payload() -> dict[str, object]:
    items = [capability.to_payload() for capability in CHINA_MACRO_SOURCE_CAPABILITIES]
    return {
        "status": _overall_status(CHINA_MACRO_SOURCE_CAPABILITIES),
        "summary": _build_summary(CHINA_MACRO_SOURCE_CAPABILITIES),
        "groups": _build_groups(items),
        "items": items,
        "diagnostics": _build_diagnostics(CHINA_MACRO_SOURCE_CAPABILITIES),
        "citation_policy": CAPABILITY_CITATION_POLICY,
        "recommended_next_action": _recommended_next_action(CHINA_MACRO_SOURCE_CAPABILITIES),
    }


def _overall_status(capabilities: tuple[SourceCapability, ...]) -> str:
    if any(capability.adapter_status in {"candidate", "manual_only", "blocked"} for capability in capabilities):
        return "degraded"
    return "ok"


def _build_summary(capabilities: tuple[SourceCapability, ...]) -> dict[str, object]:
    statuses: tuple[AdapterStatus, ...] = (
        "implemented",
        "adapter_ready",
        "candidate",
        "manual_only",
        "blocked",
        "future",
    )
    by_status = {
        status: sum(1 for capability in capabilities if capability.adapter_status == status)
        for status in statuses
    }
    return {
        "total": len(capabilities),
        **by_status,
        "needs_validation": sum(
            by_status[status] for status in ("candidate", "manual_only", "blocked")
        ),
        "by_adapter_status": by_status,
    }


def _build_groups(items: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped_items: dict[str, list[dict[str, object]]] = {}
    for item in items:
        adapter_status = str(item["adapter_status"])
        grouped_items.setdefault(adapter_status, []).append(item)

    return [
        {
            "adapter_status": adapter_status,
            "label": adapter_status.replace("_", " ").title(),
            "items": grouped_items[adapter_status],
        }
        for adapter_status in sorted(grouped_items)
    ]


def _build_diagnostics(capabilities: tuple[SourceCapability, ...]) -> list[dict[str, object]]:
    diagnostics: list[dict[str, object]] = []
    for capability in capabilities:
        if capability.adapter_status in {"implemented", "adapter_ready"}:
            severity = "info"
        elif capability.adapter_status == "blocked":
            severity = "warning"
        else:
            severity = "warning"

        diagnostics.append(
            {
                "code": f"{capability.id.upper()}_{capability.adapter_status.upper()}",
                "severity": severity,
                "item_id": capability.id,
                "message": (
                    f"{capability.label} is {capability.adapter_status.replace('_', ' ')}. "
                    f"Next action: {capability.recommended_next_action}"
                ),
            }
        )
    return diagnostics


def _recommended_next_action(capabilities: tuple[SourceCapability, ...]) -> str:
    adapter_ready = [
        capability
        for capability in capabilities
        if capability.adapter_status in {"implemented", "adapter_ready"}
    ]
    if adapter_ready:
        labels = ", ".join(capability.label for capability in adapter_ready)
        return (
            f"Use {labels} for the next low-risk adapter slice, while keeping "
            "monthly China macro sources in validation/manual mode."
        )
    return "Run opt-in live validation before selecting a production China macro adapter."


__all__ = [
    "CAPABILITY_CITATION_POLICY",
    "CHINA_MACRO_SOURCE_CAPABILITIES",
    "SourceCapability",
    "SourceCapabilityLink",
    "SourceCapabilityValidation",
    "get_china_macro_source_capability_payload",
    "get_source_capability_by_id",
]
