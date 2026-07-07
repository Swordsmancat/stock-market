from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from sqlalchemy.orm import Session

from packages.domain.models import (
    GeneratedReport,
    MarketIndicator,
    MarketIndicatorObservation,
    NewsArticle,
)
from packages.services.market_indicators import MACRO_INDICATOR_CODES


SourceStatus = Literal[
    "configured",
    "needs_adapter",
    "needs_manual_seed",
    "no_data",
    "future",
]
EvidenceKind = Literal[
    "macro_observations",
    "generated_reports",
    "news_articles",
    "static",
]


@dataclass(frozen=True)
class SourceCollectionLink:
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
class SourceSeedTemplateChecklistItem:
    id: str
    label: str
    required: bool
    why: str

    def to_payload(self) -> dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "required": self.required,
            "why": self.why,
        }


@dataclass(frozen=True)
class SourceSeedTemplate:
    label: str
    description: str
    target_indicator_codes: tuple[str, ...]
    required_fields: tuple[str, ...]
    json_template: dict[str, object]
    csv_header: tuple[str, ...]
    csv_example_rows: tuple[str, ...]
    review_checklist: tuple[SourceSeedTemplateChecklistItem, ...]
    warnings: tuple[str, ...]
    import_command: str
    citation_boundary: str

    def to_payload(self) -> dict[str, object]:
        return {
            "label": self.label,
            "description": self.description,
            "target_indicator_codes": list(self.target_indicator_codes),
            "required_fields": list(self.required_fields),
            "json_template": self.json_template,
            "csv_header": list(self.csv_header),
            "csv_example_rows": list(self.csv_example_rows),
            "review_checklist": [item.to_payload() for item in self.review_checklist],
            "warnings": list(self.warnings),
            "import_command": self.import_command,
            "citation_boundary": self.citation_boundary,
        }


@dataclass(frozen=True)
class SourceDefinition:
    id: str
    label: str
    category: str
    authority: str
    default_status: SourceStatus
    freshness_policy: str
    ai_usage: str
    next_action: str
    coverage: tuple[str, ...]
    collection_note: str
    citation_policy: str
    seed_template: SourceSeedTemplate | None = None
    collection_links: tuple[SourceCollectionLink, ...] = ()
    evidence_kind: EvidenceKind = "static"
    indicator_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceEvidence:
    count: int
    latest_as_of: str | None


FRED_US_RATES_CODES = ("us_10y_yield", "us_2y_yield", "us_10y_2y_spread")
FRED_US_INFLATION_CODES = ("us_cpi_yoy",)
FRED_US_LIQUIDITY_CODES = ("us_m2_yoy",)
PBOC_CN_M2_CODES = ("cn_m2_yoy",)
BUFFETT_INDICATOR_CODES = (
    "buffett_indicator_cn",
    "buffett_indicator_hk",
    "buffett_indicator_us",
)

SEED_TEMPLATE_REQUIRED_FIELDS = ("code", "as_of", "value", "source", "components")
SEED_TEMPLATE_CSV_HEADER = ("code", "as_of", "value", "source", "components_json")
SEED_TEMPLATE_IMPORT_COMMAND = (
    "python scripts/import_market_indicator_seeds.py path/to/macro-seeds.json"
)
SEED_TEMPLATE_CITATION_BOUNDARY = (
    "This template is not evidence; imported observations become citeable only "
    "after validation stores reviewed source and methodology metadata locally."
)
DEFAULT_SEED_TEMPLATE_WARNINGS = (
    "Replace every placeholder before import; template values are not market data.",
    "Do not treat source links or template rows as AI citations.",
)
DEFAULT_SEED_TEMPLATE_CHECKLIST = (
    SourceSeedTemplateChecklistItem(
        id="replace_placeholders",
        label="Replace every placeholder date and value before import.",
        required=True,
        why="The template is not an observation until reviewed values are supplied.",
    ),
    SourceSeedTemplateChecklistItem(
        id="preserve_source_reference",
        label=(
            "Keep at least one source_url, source_series_id, source_document, "
            "or source_name in components."
        ),
        required=True,
        why="The seed importer requires source metadata for auditability.",
    ),
    SourceSeedTemplateChecklistItem(
        id="record_method",
        label=(
            "Record methodology, calculation, notes, or review_note in "
            "components."
        ),
        required=True,
        why="AI summaries can cite only reviewed observations with method metadata.",
    ),
)

CATEGORY_LABELS = {
    "macro": "Macro sources",
    "valuation": "Valuation sources",
    "reports": "Generated reports",
    "news": "Stored news",
    "documents": "Documents",
    "manual_seed": "Manual seed files",
}

ACTIONABLE_STATUSES = {"needs_adapter", "needs_manual_seed", "no_data"}


def _seed_observation_template(
    *,
    code: str,
    source: str,
    components: dict[str, object],
) -> dict[str, object]:
    return {
        "code": code,
        "as_of": "YYYY-MM-DD",
        "value": "<reviewed decimal>",
        "source": source,
        "components": components,
    }


def _csv_components_json(components: dict[str, object]) -> str:
    encoded = json.dumps(components, sort_keys=True)
    return f'"{encoded.replace('"', '""')}"'


def _csv_seed_row(
    *,
    code: str,
    source: str,
    components: dict[str, object],
) -> str:
    return ",".join(
        (
            code,
            "YYYY-MM-DD",
            "<reviewed decimal>",
            source,
            _csv_components_json(components),
        )
    )


def _source_seed_template(
    *,
    label: str,
    description: str,
    observations: tuple[dict[str, object], ...],
    target_indicator_codes: tuple[str, ...],
    review_checklist: tuple[SourceSeedTemplateChecklistItem, ...] = DEFAULT_SEED_TEMPLATE_CHECKLIST,
) -> SourceSeedTemplate:
    return SourceSeedTemplate(
        label=label,
        description=description,
        target_indicator_codes=target_indicator_codes,
        required_fields=SEED_TEMPLATE_REQUIRED_FIELDS,
        json_template={"observations": [dict(observation) for observation in observations]},
        csv_header=SEED_TEMPLATE_CSV_HEADER,
        csv_example_rows=tuple(
            _csv_seed_row(
                code=str(observation["code"]),
                source=str(observation["source"]),
                components=dict(observation["components"]),
            )
            for observation in observations
        ),
        review_checklist=review_checklist,
        warnings=DEFAULT_SEED_TEMPLATE_WARNINGS,
        import_command=SEED_TEMPLATE_IMPORT_COMMAND,
        citation_boundary=SEED_TEMPLATE_CITATION_BOUNDARY,
    )


FRED_RATES_SEED_TEMPLATE = _source_seed_template(
    label="FRED rates seed template",
    description=(
        "Prepare reviewed daily Treasury observations before importing rates "
        "and yield-curve context."
    ),
    target_indicator_codes=FRED_US_RATES_CODES,
    observations=(
        _seed_observation_template(
            code="us_10y_yield",
            source="Audited seed: FRED DGS10",
            components={
                "source_series_id": "DGS10",
                "source_url": "https://fred.stlouisfed.org/series/DGS10",
                "methodology": "<operator review note>",
            },
        ),
        _seed_observation_template(
            code="us_2y_yield",
            source="Audited seed: FRED DGS2",
            components={
                "source_series_id": "DGS2",
                "source_url": "https://fred.stlouisfed.org/series/DGS2",
                "methodology": "<operator review note>",
            },
        ),
        _seed_observation_template(
            code="us_10y_2y_spread",
            source="Audited seed: FRED T10Y2Y",
            components={
                "source_series_id": "T10Y2Y",
                "source_url": "https://fred.stlouisfed.org/series/T10Y2Y",
                "methodology": "<operator review note>",
            },
        ),
    ),
)

FRED_INFLATION_SEED_TEMPLATE = _source_seed_template(
    label="FRED inflation seed template",
    description=(
        "Prepare a reviewed CPI YoY observation with the source series and "
        "calculation note preserved."
    ),
    target_indicator_codes=FRED_US_INFLATION_CODES,
    observations=(
        _seed_observation_template(
            code="us_cpi_yoy",
            source="Audited seed: FRED CPIAUCSL derived YoY",
            components={
                "source_series_id": "CPIAUCSL",
                "source_url": "https://fred.stlouisfed.org/series/CPIAUCSL",
                "calculation": "<YoY calculation note>",
            },
        ),
    ),
)

FRED_LIQUIDITY_SEED_TEMPLATE = _source_seed_template(
    label="FRED liquidity seed template",
    description=(
        "Prepare a reviewed US M2 YoY observation with source and calculation "
        "metadata."
    ),
    target_indicator_codes=FRED_US_LIQUIDITY_CODES,
    observations=(
        _seed_observation_template(
            code="us_m2_yoy",
            source="Audited seed: FRED M2SL derived YoY",
            components={
                "source_series_id": "M2SL",
                "source_url": "https://fred.stlouisfed.org/series/M2SL",
                "calculation": "<YoY calculation note>",
            },
        ),
    ),
)

PBOC_CN_M2_SEED_TEMPLATE = _source_seed_template(
    label="PBOC China M2 seed template",
    description=(
        "Prepare a manually reviewed China M2 YoY observation from an official "
        "or legally reposted source."
    ),
    target_indicator_codes=PBOC_CN_M2_CODES,
    observations=(
        _seed_observation_template(
            code="cn_m2_yoy",
            source="Audited seed: PBOC public monetary statistics",
            components={
                "source_name": "People's Bank of China monetary statistics",
                "source_url": "https://www.pbc.gov.cn/en/3688006/index.html",
                "methodology": "<manual review note>",
            },
        ),
    ),
)

BUFFETT_SEED_TEMPLATE = _source_seed_template(
    label="Buffett Indicator component seed template",
    description=(
        "Prepare market-cap, GDP, and ratio observations with component source "
        "URLs and calculation notes."
    ),
    target_indicator_codes=BUFFETT_INDICATOR_CODES,
    observations=tuple(
        _seed_observation_template(
            code=code,
            source="Audited seed: market capitalization / GDP components",
            components={
                "source_url": "https://data.worldbank.org/indicator/CM.MKT.LCAP.GD.ZS",
                "market_cap_source_url": (
                    "https://data.worldbank.org/indicator/CM.MKT.LCAP.GD.ZS"
                ),
                "gdp_source_url": "https://data.worldbank.org/indicator/NY.GDP.MKTP.CD",
                "calculation": "<market capitalization divided by GDP calculation>",
                "notes": "<component review note>",
            },
        )
        for code in BUFFETT_INDICATOR_CODES
    ),
    review_checklist=(
        *DEFAULT_SEED_TEMPLATE_CHECKLIST,
        SourceSeedTemplateChecklistItem(
            id="review_components",
            label="Record market-cap, GDP, ratio, region, and component URLs.",
            required=True,
            why="Buffett Indicator evidence is only useful when components are auditable.",
        ),
    ),
)

USER_SEED_FILES_TEMPLATE = _source_seed_template(
    label="Generic audited macro seed template",
    description=(
        "Prepare reviewed JSON or CSV observations for any supported macro or "
        "valuation indicator code."
    ),
    target_indicator_codes=MACRO_INDICATOR_CODES,
    observations=(
        _seed_observation_template(
            code="<indicator_code>",
            source="Audited seed: <reviewed source note>",
            components={
                "source_url": "<official or reviewed source URL>",
                "methodology": "<operator review note>",
            },
        ),
    ),
)

INFORMATION_SOURCE_DEFINITIONS: tuple[SourceDefinition, ...] = (
    SourceDefinition(
        id="fred_us_rates",
        label="FRED US rates",
        category="macro",
        authority="Federal Reserve Bank of St. Louis FRED",
        default_status="needs_adapter",
        freshness_policy=(
            "Daily official Treasury series; update after FRED publishes each "
            "business-day observation."
        ),
        ai_usage=(
            "Can support rates and yield-curve context only after audited "
            "observations are imported."
        ),
        next_action=(
            "Add an official-source adapter or reviewed seed import for "
            "DGS10, DGS2, and T10Y2Y."
        ),
        coverage=("DGS10", "DGS2", "T10Y2Y"),
        collection_note=(
            "Collect DGS10, DGS2, and T10Y2Y observations from FRED, then "
            "store reviewed values with source URLs and methodology notes."
        ),
        citation_policy=(
            "FRED links are collection guidance only; AI may cite rates after "
            "reviewed observations are stored locally."
        ),
        seed_template=FRED_RATES_SEED_TEMPLATE,
        collection_links=(
            SourceCollectionLink(
                label="FRED DGS10",
                url="https://fred.stlouisfed.org/series/DGS10",
                source_type="official_series",
            ),
            SourceCollectionLink(
                label="FRED DGS2",
                url="https://fred.stlouisfed.org/series/DGS2",
                source_type="official_series",
            ),
            SourceCollectionLink(
                label="FRED T10Y2Y",
                url="https://fred.stlouisfed.org/series/T10Y2Y",
                source_type="official_series",
            ),
        ),
        evidence_kind="macro_observations",
        indicator_codes=FRED_US_RATES_CODES,
    ),
    SourceDefinition(
        id="fred_us_inflation",
        label="FRED US inflation",
        category="macro",
        authority="Federal Reserve Bank of St. Louis FRED",
        default_status="needs_adapter",
        freshness_policy=(
            "Monthly CPI-derived series; refresh after the official monthly "
            "inflation release is available."
        ),
        ai_usage=(
            "Can support inflation context after a reviewed CPI YoY "
            "observation exists locally."
        ),
        next_action=(
            "Add an adapter or audited derived-series seed for US CPI YoY."
        ),
        coverage=("CPIAUCSL", "us_cpi_yoy"),
        collection_note=(
            "Collect CPIAUCSL or BLS CPI observations, calculate the reviewed "
            "YoY value, and preserve the calculation note."
        ),
        citation_policy=(
            "Inflation context is citeable only after the derived YoY value is "
            "stored with source and calculation metadata."
        ),
        seed_template=FRED_INFLATION_SEED_TEMPLATE,
        collection_links=(
            SourceCollectionLink(
                label="FRED CPIAUCSL",
                url="https://fred.stlouisfed.org/series/CPIAUCSL",
                source_type="official_series",
            ),
            SourceCollectionLink(
                label="BLS CPI-U",
                url="https://data.bls.gov/timeseries/CUUR0000SA0",
                source_type="official_series",
            ),
        ),
        evidence_kind="macro_observations",
        indicator_codes=FRED_US_INFLATION_CODES,
    ),
    SourceDefinition(
        id="fred_us_liquidity",
        label="FRED US liquidity",
        category="macro",
        authority="Federal Reserve Bank of St. Louis FRED",
        default_status="needs_adapter",
        freshness_policy=(
            "Official money-supply series; refresh after the source series "
            "updates and derived YoY value is reviewed."
        ),
        ai_usage=(
            "Can support liquidity summaries after the M2 YoY observation is "
            "stored with source notes."
        ),
        next_action="Add an adapter or audited seed for US M2 YoY.",
        coverage=("M2SL", "us_m2_yoy"),
        collection_note=(
            "Collect M2SL observations from FRED, derive YoY growth if needed, "
            "and store reviewed source/calculation metadata."
        ),
        citation_policy=(
            "Liquidity summaries may cite US M2 only after a reviewed local "
            "observation exists."
        ),
        seed_template=FRED_LIQUIDITY_SEED_TEMPLATE,
        collection_links=(
            SourceCollectionLink(
                label="FRED M2SL",
                url="https://fred.stlouisfed.org/series/M2SL",
                source_type="official_series",
            ),
        ),
        evidence_kind="macro_observations",
        indicator_codes=FRED_US_LIQUIDITY_CODES,
    ),
    SourceDefinition(
        id="pboc_cn_m2_public_manual",
        label="PBOC China M2 public/manual source",
        category="macro",
        authority="People's Bank of China public monetary statistics",
        default_status="needs_manual_seed",
        freshness_policy=(
            "Monthly public release; operator should review the release and "
            "seed the derived YoY observation."
        ),
        ai_usage=(
            "Can support China liquidity summaries only after the manual "
            "source note is present in local observations."
        ),
        next_action=(
            "Seed cn_m2_yoy from a reviewed PBOC public release with source "
            "URL and calculation notes."
        ),
        coverage=("PBOC monetary statistics", "cn_m2_yoy"),
        collection_note=(
            "Review PBOC public monetary statistics or an official reposted "
            "dataset, then seed cn_m2_yoy with source URL and review notes."
        ),
        citation_policy=(
            "China M2 remains manual-review evidence until a local observation "
            "preserves the reviewed source and calculation."
        ),
        seed_template=PBOC_CN_M2_SEED_TEMPLATE,
        collection_links=(
            SourceCollectionLink(
                label="PBOC key indicators",
                url="https://www.pbc.gov.cn/en/3688006/index.html",
                source_type="official_page",
            ),
        ),
        evidence_kind="macro_observations",
        indicator_codes=PBOC_CN_M2_CODES,
    ),
    SourceDefinition(
        id="world_bank_buffett_indicator",
        label="World Bank Buffett Indicator adapter",
        category="valuation",
        authority="World Bank public indicators API",
        default_status="needs_adapter",
        freshness_policy=(
            "Annual public macro series; refresh when World Bank publishes a "
            "new latest available market-cap-to-GDP observation."
        ),
        ai_usage=(
            "Can support Buffett Indicator valuation context after adapter "
            "refresh stores audited local observations."
        ),
        next_action=(
            "Run the World Bank macro refresh for Buffett Indicator regions "
            "and review diagnostics for missing annual data."
        ),
        coverage=(
            "CM.MKT.LCAP.GD.ZS",
            "NY.GDP.MKTP.CD",
            "buffett_indicator_cn",
            "buffett_indicator_hk",
            "buffett_indicator_us",
        ),
        collection_note=(
            "Use the World Bank API adapter to fetch market capitalization as "
            "percent of GDP and same-year GDP context for supported regions."
        ),
        citation_policy=(
            "World Bank links and adapter diagnostics are guidance only; AI may "
            "cite Buffett Indicator values after validated observations are "
            "stored locally."
        ),
        collection_links=(
            SourceCollectionLink(
                label="World Bank market cap / GDP",
                url="https://data.worldbank.org/indicator/CM.MKT.LCAP.GD.ZS",
                source_type="public_dataset",
            ),
            SourceCollectionLink(
                label="World Bank GDP",
                url="https://data.worldbank.org/indicator/NY.GDP.MKTP.CD",
                source_type="public_dataset",
            ),
        ),
        evidence_kind="macro_observations",
        indicator_codes=BUFFETT_INDICATOR_CODES,
    ),
    SourceDefinition(
        id="buffett_manual_valuation_components",
        label="Buffett Indicator manual valuation components",
        category="valuation",
        authority="Operator-reviewed public market capitalization and GDP sources",
        default_status="needs_manual_seed",
        freshness_policy=(
            "Manual valuation seed; refresh when market-cap or GDP component "
            "inputs are reviewed."
        ),
        ai_usage=(
            "Can support valuation context after each region's ratio carries "
            "auditable component metadata."
        ),
        next_action=(
            "Seed Buffett Indicator observations with market-cap, GDP, ratio, "
            "and source notes."
        ),
        coverage=(
            "buffett_indicator_cn",
            "buffett_indicator_hk",
            "buffett_indicator_us",
            "market_cap",
            "gdp",
            "ratio",
        ),
        collection_note=(
            "Collect market-cap and GDP components from reviewed public "
            "sources, calculate the ratio, and store the component URLs."
        ),
        citation_policy=(
            "Buffett Indicator ratios are citeable only after each component "
            "and calculation method are stored locally."
        ),
        seed_template=BUFFETT_SEED_TEMPLATE,
        collection_links=(
            SourceCollectionLink(
                label="World Bank market cap / GDP",
                url="https://data.worldbank.org/indicator/CM.MKT.LCAP.GD.ZS",
                source_type="public_dataset",
            ),
            SourceCollectionLink(
                label="World Bank GDP",
                url="https://data.worldbank.org/indicator/NY.GDP.MKTP.CD",
                source_type="public_dataset",
            ),
        ),
        evidence_kind="macro_observations",
        indicator_codes=BUFFETT_INDICATOR_CODES,
    ),
    SourceDefinition(
        id="generated_reports",
        label="Generated reports",
        category="reports",
        authority="Local GeneratedReport store",
        default_status="no_data",
        freshness_policy=(
            "Use the latest generated report as-of date; regenerate when the "
            "portfolio/watchlist research cycle runs."
        ),
        ai_usage=(
            "Can be cited today when stored reports exist with citations and "
            "source summaries."
        ),
        next_action="Generate or refresh stored reports for followed symbols.",
        coverage=("GeneratedReport.symbol", "GeneratedReport.report_type", "GeneratedReport.as_of"),
        collection_note=(
            "Generate or refresh platform reports so AI summaries have local "
            "report evidence and citations."
        ),
        citation_policy=(
            "Stored reports can be cited after they exist locally with report "
            "citations and source summaries."
        ),
        evidence_kind="generated_reports",
    ),
    SourceDefinition(
        id="stored_news",
        label="Stored news",
        category="news",
        authority="Local NewsArticle store",
        default_status="no_data",
        freshness_policy=(
            "Use the latest stored publication timestamp; refresh through the "
            "news ingestion path when stale."
        ),
        ai_usage=(
            "Can be cited today when locally stored articles include source, "
            "URL, and publication time."
        ),
        next_action="Ingest or refresh stored news for followed symbols.",
        coverage=("NewsArticle.symbol", "NewsArticle.source", "NewsArticle.published_at"),
        collection_note=(
            "Ingest or manually review news items for followed symbols, keeping "
            "publisher, URL, publication time, and summary metadata."
        ),
        citation_policy=(
            "News can be cited only when the article is stored locally with URL "
            "and publication metadata."
        ),
        evidence_kind="news_articles",
    ),
    SourceDefinition(
        id="sec_filings_future_documents",
        label="SEC filings and future documents",
        category="documents",
        authority="SEC EDGAR and issuer disclosure sources",
        default_status="future",
        freshness_policy=(
            "Future adapter family; do not claim filing, transcript, or "
            "announcement coverage until an ingestion policy exists."
        ),
        ai_usage=(
            "Not citeable today from this registry; reserve for future "
            "document ingestion and citation controls."
        ),
        next_action=(
            "Define filing/document adapters, licensing boundaries, and "
            "citation metadata before enabling."
        ),
        coverage=("10-K", "10-Q", "8-K", "issuer announcements", "future transcripts"),
        collection_note=(
            "Use official filing search and issuer pages to identify documents; "
            "define licensing and storage policy before ingesting text."
        ),
        citation_policy=(
            "Future filings, announcements, and transcripts are not citeable "
            "until ingestion, licensing, and citation metadata are implemented."
        ),
        collection_links=(
            SourceCollectionLink(
                label="SEC search filings",
                url="https://www.sec.gov/search-filings",
                source_type="official_search",
            ),
            SourceCollectionLink(
                label="SEC EDGAR full text",
                url="https://www.sec.gov/edgar/search/",
                source_type="official_search",
            ),
        ),
    ),
    SourceDefinition(
        id="user_seed_files",
        label="User seed files",
        category="manual_seed",
        authority="Operator-curated local seed files",
        default_status="needs_manual_seed",
        freshness_policy=(
            "Manual source files should be refreshed when the user audits a "
            "new macro or valuation observation."
        ),
        ai_usage=(
            "Can support AI summaries after seeded observations preserve "
            "source and component notes in the database."
        ),
        next_action=(
            "Add reviewed seed files and load them into "
            "MarketIndicatorObservation with source/component metadata."
        ),
        coverage=("MarketIndicatorObservation.source", "components_json"),
        collection_note=(
            "Prepare reviewed JSON/CSV seed files with source URL or series ID, "
            "methodology, calculation, or review notes before import."
        ),
        citation_policy=(
            "Seed files themselves are not cited; imported observations become "
            "citeable after validation stores source/component metadata."
        ),
        seed_template=USER_SEED_FILES_TEMPLATE,
        evidence_kind="macro_observations",
        indicator_codes=MACRO_INDICATOR_CODES,
    ),
)


def get_information_source_readiness_payload(session: Session) -> dict[str, object]:
    items = [_build_source_item(definition, session=session) for definition in INFORMATION_SOURCE_DEFINITIONS]
    return {
        "status": _overall_status(items),
        "summary": _build_summary(items),
        "groups": _build_groups(items),
        "items": items,
        "diagnostics": _build_diagnostics(items),
    }


def _build_source_item(definition: SourceDefinition, session: Session) -> dict[str, object]:
    evidence = _get_source_evidence(definition, session=session)
    status = _status_for(definition, evidence=evidence)
    return {
        "id": definition.id,
        "label": definition.label,
        "category": definition.category,
        "authority": definition.authority,
        "status": status,
        "freshness_policy": definition.freshness_policy,
        "ai_usage": definition.ai_usage,
        "next_action": definition.next_action,
        "collection_note": definition.collection_note,
        "citation_policy": definition.citation_policy,
        "seed_template": (
            definition.seed_template.to_payload()
            if definition.seed_template is not None
            else None
        ),
        "collection_links": [link.to_payload() for link in definition.collection_links],
        "evidence_count": evidence.count,
        "latest_as_of": evidence.latest_as_of,
        "coverage": list(definition.coverage),
    }


def _get_source_evidence(definition: SourceDefinition, session: Session) -> SourceEvidence:
    if definition.evidence_kind == "macro_observations":
        return _get_macro_observation_evidence(definition.indicator_codes, session=session)
    if definition.evidence_kind == "generated_reports":
        return _get_generated_report_evidence(session=session)
    if definition.evidence_kind == "news_articles":
        return _get_news_article_evidence(session=session)
    return SourceEvidence(count=0, latest_as_of=None)


def _get_macro_observation_evidence(
    indicator_codes: tuple[str, ...],
    session: Session,
) -> SourceEvidence:
    if not indicator_codes:
        return SourceEvidence(count=0, latest_as_of=None)

    base_query = (
        session.query(MarketIndicatorObservation)
        .join(MarketIndicator, MarketIndicatorObservation.indicator_id == MarketIndicator.id)
        .filter(MarketIndicator.code.in_(indicator_codes))
    )
    latest = base_query.order_by(MarketIndicatorObservation.as_of.desc()).first()
    return SourceEvidence(
        count=base_query.count(),
        latest_as_of=_format_as_of(latest.as_of if latest is not None else None),
    )


def _get_generated_report_evidence(session: Session) -> SourceEvidence:
    latest = (
        session.query(GeneratedReport)
        .order_by(GeneratedReport.as_of.desc(), GeneratedReport.created_at.desc())
        .first()
    )
    return SourceEvidence(
        count=session.query(GeneratedReport).count(),
        latest_as_of=_format_as_of(latest.as_of if latest is not None else None),
    )


def _get_news_article_evidence(session: Session) -> SourceEvidence:
    latest = session.query(NewsArticle).order_by(NewsArticle.published_at.desc()).first()
    return SourceEvidence(
        count=session.query(NewsArticle).count(),
        latest_as_of=_format_as_of(latest.published_at if latest is not None else None),
    )


def _status_for(definition: SourceDefinition, evidence: SourceEvidence) -> SourceStatus:
    if definition.default_status == "future":
        return "future"
    if evidence.count > 0:
        return "configured"
    return definition.default_status


def _format_as_of(value: date | datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value.isoformat()


def _overall_status(items: list[dict[str, object]]) -> str:
    if any(item["status"] in ACTIONABLE_STATUSES for item in items):
        return "degraded"
    return "ok"


def _build_summary(items: list[dict[str, object]]) -> dict[str, object]:
    by_status = {
        status: sum(1 for item in items if item["status"] == status)
        for status in (
            "configured",
            "needs_adapter",
            "needs_manual_seed",
            "no_data",
            "future",
        )
    }
    return {
        "total": len(items),
        "configured": by_status["configured"],
        "needs_action": sum(by_status[status] for status in ACTIONABLE_STATUSES),
        "future": by_status["future"],
        "by_status": by_status,
    }


def _build_groups(items: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: list[dict[str, object]] = []
    grouped_items: dict[str, list[dict[str, object]]] = {}
    for item in items:
        category = str(item["category"])
        if category not in grouped_items:
            grouped_items[category] = []
        grouped_items[category].append(item)

    for category, category_items in grouped_items.items():
        groups.append(
            {
                "category": category,
                "label": CATEGORY_LABELS.get(category, category.replace("_", " ").title()),
                "items": category_items,
            }
        )
    return groups


def _build_diagnostics(items: list[dict[str, object]]) -> list[dict[str, object]]:
    diagnostics: list[dict[str, object]] = []
    for item in items:
        status = str(item["status"])
        if status == "configured":
            continue

        severity = "info" if status == "future" else "warning"
        diagnostics.append(
            {
                "code": f"{str(item['id']).upper()}_{status.upper()}",
                "severity": severity,
                "item_id": item["id"],
                "message": (
                    f"{item['label']} is {status.replace('_', ' ')}. "
                    f"Next action: {item['next_action']}"
                ),
            }
        )
    return diagnostics


__all__ = [
    "INFORMATION_SOURCE_DEFINITIONS",
    "SourceCollectionLink",
    "SourceDefinition",
    "SourceSeedTemplate",
    "SourceSeedTemplateChecklistItem",
    "get_information_source_readiness_payload",
]
