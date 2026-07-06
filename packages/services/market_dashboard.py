import re
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from packages.ai.llm_factory import get_llm_provider
from packages.domain.models import GeneratedReport, NewsArticle
from packages.services.information_sources import get_information_source_readiness_payload
from packages.services.instruments import list_instruments_payload
from packages.services.market_data import (
    MarketDataProviderError,
    get_bars_payload,
    resolve_market_data_provider_name,
)
from packages.services.market_indices import DEFAULT_MARKET_INDICES, MarketIndexDefinition, resolve_provider_symbol
from packages.services.market_indicators import get_macro_indicator_payloads
from packages.services.platform_settings import get_platform_settings
from packages.services.watchlists import get_active_watchlist_item_dicts
from packages.shared.cache import cache_market_overview


FOLLOWED_INSTRUMENT_LIMIT = 6
DASHBOARD_RANGE_DAYS = 92
MILLISECONDS_PER_DAY = 24 * 60 * 60 * 1000
DASHBOARD_BRIEF_MODEL_NAME = "gpt-4o-mini"
DASHBOARD_BRIEF_FALLBACK_MODEL_NAME = "dashboard-brief-deterministic-fallback"
DASHBOARD_BRIEF_CITATION_ID_PATTERN = re.compile(r"\[([A-Za-z0-9_:\-./+]+)\]")
DASHBOARD_BRIEF_CITATION_ID_PREFIXES = (
    "market_indicator:",
    "generated_report:",
    "news:",
)
DASHBOARD_BRIEF_SOURCE_GAP_STATUSES = {
    "needs_adapter",
    "needs_manual_seed",
    "no_data",
    "future",
}


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def _classify_freshness(timestamp: str | None, today: date) -> str:
    parsed_date = _parse_date(timestamp)
    if parsed_date is None:
        return "unavailable"
    days_since_latest_bar = (today - parsed_date).days
    return "fresh" if days_since_latest_bar <= 3 else "stale"


def _derive_daily_movement(items: list[dict[str, Any]]) -> dict[str, object] | None:
    if len(items) < 2:
        return None

    latest_item = items[-1]
    previous_item = items[-2]
    latest_close = float(latest_item["close"])
    previous_close = float(previous_item["close"])
    absolute_change = latest_close - previous_close
    percent_change = None if previous_close == 0 else absolute_change / previous_close
    direction = "up" if absolute_change > 0 else "down" if absolute_change < 0 else "flat"
    return {
        "direction": direction,
        "absolute_change": absolute_change,
        "percent_change": percent_change,
    }


def _build_latest_summary(items: list[dict[str, Any]]) -> dict[str, object] | None:
    if not items:
        return None

    latest_item = items[-1]
    return {
        "timestamp": latest_item.get("timestamp"),
        "close": latest_item.get("close"),
        "movement": _derive_daily_movement(items),
    }


def _build_bars_item(
    *,
    identity: dict[str, object],
    bars_payload: dict[str, object],
    today: date,
    detail_path: str | None = None,
) -> dict[str, object]:
    items = list(bars_payload.get("items", []))
    status = str(bars_payload.get("status") or ("ok" if items else "no_data"))
    latest = _build_latest_summary(items)
    freshness = "no_data" if status == "no_data" else _classify_freshness(str(latest["timestamp"]) if latest else None, today)
    return {
        **identity,
        "status": status,
        "freshness": freshness,
        "latest": latest,
        "bars": items,
        "source": bars_payload.get("source"),
        "provider": bars_payload.get("provider"),
        "requested_provider": bars_payload.get("requested_provider"),
        "effective_provider": bars_payload.get("effective_provider"),
        "detail_path": detail_path,
        "no_data_reason": bars_payload.get("no_data_reason"),
    }


def _build_unavailable_bars_item(
    *,
    identity: dict[str, object],
    provider_name: str,
    message: str,
    detail_path: str | None = None,
) -> dict[str, object]:
    return {
        **identity,
        "status": "unavailable",
        "freshness": "unavailable",
        "latest": None,
        "bars": [],
        "source": "unavailable",
        "provider": provider_name,
        "requested_provider": provider_name,
        "effective_provider": provider_name,
        "detail_path": detail_path,
        "no_data_reason": message,
    }


def _load_followed_instrument_candidates(session: Session) -> tuple[str, list[dict[str, object]]]:
    watchlist_items = get_active_watchlist_item_dicts(session=session)
    if watchlist_items:
        return "watchlist", watchlist_items[:FOLLOWED_INSTRUMENT_LIMIT]

    instruments_payload = list_instruments_payload(session=session)
    fallback_items = [
        {
            "symbol": item["symbol"],
            "name": item["name"],
            "market": item["market"],
            "currency": item.get("currency", ""),
        }
        for item in instruments_payload["items"][:FOLLOWED_INSTRUMENT_LIMIT]
    ]
    return "default_sample", fallback_items


def _serialize_followed_instruments(
    *,
    session: Session,
    provider_name: str,
    start: date,
    end: date,
    today: date,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    scope, candidates = _load_followed_instrument_candidates(session)
    diagnostics: list[dict[str, object]] = []
    items: list[dict[str, object]] = []

    for candidate in candidates:
        symbol = str(candidate["symbol"]).upper()
        market = str(candidate.get("market") or "")
        identity = {
            "symbol": symbol,
            "name": str(candidate.get("name") or symbol),
            "market": market,
            "currency": str(candidate.get("currency") or ""),
        }
        try:
            bars_payload = get_bars_payload(
                symbol,
                "1d",
                start,
                end,
                session=session,
                provider_name=provider_name,
            )
            items.append(
                _build_bars_item(
                    identity=identity,
                    bars_payload=bars_payload,
                    today=today,
                    detail_path=f"/instruments/{symbol}",
                )
            )
        except (MarketDataProviderError, ValueError) as error:
            diagnostics.append({"section": "followed", "symbol": symbol, "status": "unavailable", "message": str(error)})
            items.append(
                _build_unavailable_bars_item(
                    identity=identity,
                    provider_name=provider_name,
                    message=str(error),
                    detail_path=f"/instruments/{symbol}",
                )
            )

    return {"scope": scope, "limit": FOLLOWED_INSTRUMENT_LIMIT, "items": items}, diagnostics


def _serialize_market_index(
    *,
    index: MarketIndexDefinition,
    session: Session,
    provider_name: str,
    start: date,
    end: date,
    today: date,
) -> tuple[dict[str, object], dict[str, object] | None]:
    provider_symbol = resolve_provider_symbol(index, provider_name)
    identity = {
        "code": index.code,
        "name": index.name,
        "name_zh": index.name_zh,
        "region": index.region,
        "market": index.market,
        "currency": index.currency,
        "provider_symbol": provider_symbol,
    }
    try:
        bars_payload = get_bars_payload(
            provider_symbol,
            "1d",
            start,
            end,
            session=session,
            provider_name=provider_name,
        )
        return _build_bars_item(identity=identity, bars_payload=bars_payload, today=today), None
    except (MarketDataProviderError, ValueError) as error:
        diagnostic = {"section": "indices", "code": index.code, "status": "unavailable", "message": str(error)}
        return _build_unavailable_bars_item(identity=identity, provider_name=provider_name, message=str(error)), diagnostic


def _serialize_indices(
    *,
    session: Session,
    provider_name: str,
    start: date,
    end: date,
    today: date,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    items: list[dict[str, object]] = []
    diagnostics: list[dict[str, object]] = []
    for index in sorted(DEFAULT_MARKET_INDICES, key=lambda item: item.display_order):
        item, diagnostic = _serialize_market_index(
            index=index,
            session=session,
            provider_name=provider_name,
            start=start,
            end=end,
            today=today,
        )
        items.append(item)
        if diagnostic is not None:
            diagnostics.append(diagnostic)
    return {"items": items}, diagnostics


def _format_indicator_value(item: dict[str, object]) -> str:
    value = item.get("value")
    unit = item.get("unit")
    if value is None:
        return "no audited value"
    formatted_value = f"{float(value):.2f}" if isinstance(value, (int, float)) else str(value)
    return f"{formatted_value}%" if unit == "percent" else formatted_value


def _build_indicator_citation(item: dict[str, object]) -> dict[str, object]:
    code = str(item.get("code") or "unknown_indicator")
    as_of = str(item.get("as_of") or "unknown")
    return {
        "id": f"market_indicator:{code}:{as_of}",
        "label": str(item.get("name") or code),
        "source": "market_indicators",
        "source_type": "macro_indicator",
        "as_of": item.get("as_of"),
        "provider": item.get("source"),
        "excerpt": f"{item.get('name') or code}: {_format_indicator_value(item)}.",
        "metadata": {
            "code": code,
            "category": item.get("category"),
            "region": item.get("region"),
            "unit": item.get("unit"),
            "components": item.get("components") or {},
        },
    }


def _extract_followed_symbols(followed_payload: dict[str, object]) -> list[str]:
    followed_items = followed_payload.get("items")
    if not isinstance(followed_items, list):
        return []

    symbols: list[str] = []
    for item in followed_items:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol") or "").upper()
        if symbol and symbol not in symbols:
            symbols.append(symbol)
    return symbols


def _build_research_availability_payload(
    *,
    session: Session,
    followed_payload: dict[str, object],
) -> dict[str, object]:
    symbols = _extract_followed_symbols(followed_payload)
    if not symbols:
        return {
            "reports": {"status": "no_data", "count": 0, "latest": None},
            "news": {"status": "no_data", "count": 0, "latest": None},
            "citations": [],
            "diagnostics": [
                {
                    "source": "followed_instruments",
                    "status": "no_data",
                    "severity": "info",
                    "code": "FOLLOWED_SYMBOLS_NO_DATA",
                    "message": "No followed symbols are available for report/news availability checks.",
                }
            ],
        }

    report_query = session.query(GeneratedReport).filter(GeneratedReport.symbol.in_(symbols))
    report_count = report_query.count()
    latest_report = report_query.order_by(GeneratedReport.created_at.desc()).first()
    news_query = session.query(NewsArticle).filter(NewsArticle.symbol.in_(symbols))
    news_count = news_query.count()
    latest_news = news_query.order_by(NewsArticle.published_at.desc()).first()

    citations: list[dict[str, object]] = []
    diagnostics: list[dict[str, object]] = []

    latest_report_payload: dict[str, object] | None = None
    if latest_report is not None:
        latest_report_payload = {
            "id": str(latest_report.id),
            "symbol": latest_report.symbol,
            "report_type": latest_report.report_type,
            "as_of": latest_report.as_of.isoformat(),
            "created_at": latest_report.created_at.isoformat(),
        }
        citations.append(
            {
                "id": f"generated_report:{latest_report.id}",
                "label": f"{latest_report.symbol} {latest_report.report_type} report",
                "source": "generated_reports",
                "source_type": "generated_report",
                "as_of": latest_report.as_of.isoformat(),
                "excerpt": f"Latest generated report for {latest_report.symbol} as of {latest_report.as_of.isoformat()}.",
            }
        )
    else:
        diagnostics.append(
            {
                "source": "generated_reports",
                "status": "no_data",
                "severity": "info",
                "code": "GENERATED_REPORTS_NO_DATA",
                "message": "No generated reports are available for the followed symbols.",
            }
        )

    latest_news_payload: dict[str, object] | None = None
    if latest_news is not None:
        published_at = latest_news.published_at.isoformat()
        latest_news_payload = {
            "symbol": latest_news.symbol,
            "title": latest_news.title,
            "source": latest_news.source,
            "published_at": published_at,
            "url": latest_news.url,
        }
        citations.append(
            {
                "id": f"news:{latest_news.symbol}:{published_at}",
                "label": f"News for {latest_news.symbol}: {latest_news.title}",
                "source": "news",
                "source_type": "news",
                "as_of": published_at,
                "provider": latest_news.source,
                "url": latest_news.url,
                "excerpt": latest_news.summary,
            }
        )
    else:
        diagnostics.append(
            {
                "source": "news",
                "status": "no_data",
                "severity": "info",
                "code": "NEWS_NO_DATA",
                "message": "No stored news articles are available for the followed symbols.",
            }
        )

    return {
        "reports": {"status": "ok" if report_count else "no_data", "count": report_count, "latest": latest_report_payload},
        "news": {"status": "ok" if news_count else "no_data", "count": news_count, "latest": latest_news_payload},
        "citations": citations,
        "diagnostics": diagnostics,
    }


def _extract_dashboard_source_gaps(
    information_sources_payload: dict[str, object],
) -> list[dict[str, object]]:
    source_items = information_sources_payload.get("items")
    if not isinstance(source_items, list):
        return []

    gaps: list[dict[str, object]] = []
    for item in source_items:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "")
        if status in DASHBOARD_BRIEF_SOURCE_GAP_STATUSES:
            gaps.append(item)
    return gaps


def _build_dashboard_narrative_source_mix(
    *,
    citations: list[dict[str, object]],
    information_sources_payload: dict[str, object],
) -> dict[str, int]:
    return {
        "macro_citations": sum(
            1
            for citation in citations
            if citation.get("source") == "market_indicators"
            or citation.get("source_type") == "macro_indicator"
        ),
        "report_citations": sum(
            1
            for citation in citations
            if citation.get("source") == "generated_reports"
            or citation.get("source_type") == "generated_report"
        ),
        "news_citations": sum(
            1
            for citation in citations
            if citation.get("source") == "news" or citation.get("source_type") == "news"
        ),
        "information_source_gaps": len(_extract_dashboard_source_gaps(information_sources_payload)),
    }


def _build_dashboard_brief_model_metadata(
    *,
    provider: str,
    name: str,
    used_llm: bool,
    fallback_reason: str | None,
) -> dict[str, object]:
    return {
        "provider": provider,
        "name": name,
        "used_llm": used_llm,
        "fallback_reason": fallback_reason,
    }


def _append_dashboard_brief_fallback_diagnostic(
    *,
    brief: dict[str, object],
    fallback_reason: str,
) -> None:
    diagnostics = brief.setdefault("diagnostics", [])
    if not isinstance(diagnostics, list):
        brief["diagnostics"] = diagnostics = []
    diagnostics.append(
        {
            "source": "dashboard_brief_narrative",
            "status": "fallback",
            "severity": "info",
            "code": "FALLBACK_USED",
            "message": "The dashboard brief used a deterministic fallback narrative instead of an LLM answer.",
            "details": {"reason": fallback_reason},
        }
    )


def _build_dashboard_brief_fallback_narrative(
    *,
    brief: dict[str, object],
    information_sources_payload: dict[str, object],
) -> str:
    sections = brief.get("sections") if isinstance(brief.get("sections"), list) else []
    section_items: dict[str, list[str]] = {}
    for section in sections:
        if not isinstance(section, dict):
            continue
        items = section.get("items")
        section_items[str(section.get("id") or "")] = [
            str(item) for item in items if isinstance(item, str)
        ] if isinstance(items, list) else []

    citations = brief.get("citations") if isinstance(brief.get("citations"), list) else []
    citable_citations = [item for item in citations if isinstance(item, dict) and item.get("id")]
    source_gaps = _extract_dashboard_source_gaps(information_sources_payload)
    first_citation = citable_citations[0] if citable_citations else None
    evidence_line = (
        f"- Citable evidence is available from {first_citation.get('label')} "
        f"[{first_citation.get('id')}]."
        if first_citation
        else "- No citable dashboard evidence is available yet."
    )
    gap_actions = [
        f"- {item.get('label')}: {item.get('next_action')}"
        for item in source_gaps[:4]
        if item.get("label") and item.get("next_action")
    ]
    if len(source_gaps) > 4:
        gap_actions.append(f"- {len(source_gaps) - 4} additional source gaps need review.")
    if not gap_actions:
        gap_actions.append("- No source-readiness gaps were reported by the local registry.")

    what_changed = section_items.get("what_changed") or [
        "No dashboard change summary is available."
    ]
    why_it_matters = section_items.get("why_it_matters") or [
        "Use the dashboard as a source-aware research summary, not a trading signal."
    ]
    watch_next = section_items.get("what_to_watch_next") or [
        "Review source freshness and missing data before forming a research hypothesis."
    ]
    data_gaps = section_items.get("data_gaps") or [
        "No explicit dashboard data gaps were reported."
    ]

    return "\n".join(
        [
            "### Summary",
            f"- {what_changed[0]}",
            evidence_line,
            "",
            "### Why it matters",
            *[f"- {item}" for item in why_it_matters[:3]],
            "",
            "### What to watch next",
            *[f"- {item}" for item in watch_next[:3]],
            "",
            "### Source and data gaps",
            *[f"- {item}" for item in data_gaps[:4]],
            f"- {len(source_gaps)} information sources are gaps or future inputs.",
            *gap_actions,
            "",
            "### Safety note",
            (
                "This is a personal research summary for information aggregation only. "
                "It is not investment advice, a buy/sell/hold call, or a guarantee."
            ),
        ]
    )


def _format_dashboard_brief_section_lines(brief: dict[str, object]) -> str:
    sections = brief.get("sections") if isinstance(brief.get("sections"), list) else []
    lines: list[str] = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        title = str(section.get("title") or section.get("id") or "Section")
        lines.append(f"{title}:")
        items = section.get("items")
        if isinstance(items, list):
            lines.extend(f"- {item}" for item in items[:6] if isinstance(item, str))
    return "\n".join(lines) or "- No dashboard brief sections are available."


def _format_dashboard_brief_citation_lines(citations: list[dict[str, object]]) -> str:
    if not citations:
        return "- No citable dashboard evidence is available."

    lines: list[str] = []
    for citation in citations[:12]:
        citation_id = citation.get("id")
        if not citation_id:
            continue
        label = citation.get("label") or citation_id
        source = citation.get("source") or "unknown"
        as_of = citation.get("as_of") or "unavailable"
        excerpt = str(citation.get("excerpt") or "").strip()
        excerpt_suffix = f" Excerpt: {excerpt[:260]}" if excerpt else ""
        lines.append(f"- [{citation_id}] {label} | source={source} | as_of={as_of}.{excerpt_suffix}")
    return "\n".join(lines) or "- No citable dashboard evidence is available."


def _format_dashboard_source_gap_lines(
    information_sources_payload: dict[str, object],
) -> str:
    source_gaps = _extract_dashboard_source_gaps(information_sources_payload)
    if not source_gaps:
        return "- No source-readiness gaps were reported."

    lines: list[str] = []
    for item in source_gaps[:12]:
        lines.append(
            "- "
            f"{item.get('label')}: status={item.get('status')}; "
            f"next_action={item.get('next_action') or 'unavailable'}"
        )
    return "\n".join(lines)


def _format_dashboard_diagnostic_lines(brief: dict[str, object]) -> str:
    diagnostics = brief.get("diagnostics") if isinstance(brief.get("diagnostics"), list) else []
    lines = [
        f"- {item.get('code') or item.get('source') or 'diagnostic'}: "
        f"{item.get('message') or item.get('status')}"
        for item in diagnostics[:12]
        if isinstance(item, dict)
    ]
    return "\n".join(lines) or "- No dashboard brief diagnostics are present."


def _build_dashboard_brief_prompt(
    *,
    brief: dict[str, object],
    citations: list[dict[str, object]],
    information_sources_payload: dict[str, object],
    source_mix: dict[str, int],
) -> str:
    return (
        "You are a cautious personal investment research assistant.\n"
        "Summarize only the structured dashboard context below. Do not invent market data, "
        "macro observations, filings, transcripts, realtime feeds, order flow, or source adapters.\n"
        "This dashboard is for personal information aggregation and AI research synthesis, not a "
        "professional trading terminal.\n\n"
        f"Dashboard status: {brief.get('status')}\n"
        f"Generated at: {brief.get('generated_at')}\n"
        f"Source mix: {source_mix}\n\n"
        f"Brief sections:\n{_format_dashboard_brief_section_lines(brief)}\n\n"
        f"Allowed citations:\n{_format_dashboard_brief_citation_lines(citations)}\n\n"
        "Source readiness gaps, not citations:\n"
        f"{_format_dashboard_source_gap_lines(information_sources_payload)}\n\n"
        f"Diagnostics:\n{_format_dashboard_diagnostic_lines(brief)}\n\n"
        "Write concise markdown with sections: Summary, Why it matters, What to watch next, "
        "Source and data gaps, Safety note. Use inline citation IDs in square brackets for factual "
        "claims only when the ID is listed under Allowed citations. Do not cite source-readiness "
        "gaps as evidence. Avoid buy/sell/hold advice, target prices, position sizing, or execution "
        "instructions."
    )


def _extract_unknown_dashboard_brief_citation_ids(
    *,
    answer_markdown: str,
    citations: list[dict[str, object]],
) -> list[str]:
    known_citation_ids = {str(citation.get("id")) for citation in citations if citation.get("id")}
    extracted_citation_ids = {
        candidate
        for candidate in DASHBOARD_BRIEF_CITATION_ID_PATTERN.findall(answer_markdown)
        if candidate.startswith(DASHBOARD_BRIEF_CITATION_ID_PREFIXES)
    }
    return sorted(extracted_citation_ids - known_citation_ids)


def _build_dashboard_brief_narrative(
    *,
    brief: dict[str, object],
    information_sources_payload: dict[str, object],
) -> dict[str, object]:
    citations_payload = brief.get("citations") if isinstance(brief.get("citations"), list) else []
    citations = [item for item in citations_payload if isinstance(item, dict)]
    source_mix = _build_dashboard_narrative_source_mix(
        citations=citations,
        information_sources_payload=information_sources_payload,
    )

    def build_fallback(fallback_reason: str) -> dict[str, object]:
        _append_dashboard_brief_fallback_diagnostic(
            brief=brief,
            fallback_reason=fallback_reason,
        )
        return {
            "answer_markdown": _build_dashboard_brief_fallback_narrative(
                brief=brief,
                information_sources_payload=information_sources_payload,
            ),
            "model": _build_dashboard_brief_model_metadata(
                provider="deterministic",
                name=DASHBOARD_BRIEF_FALLBACK_MODEL_NAME,
                used_llm=False,
                fallback_reason=fallback_reason,
            ),
            "context": {"source_mix": source_mix},
        }

    settings = get_platform_settings()
    configured_provider = str(settings.get("llm_provider", "mock")).lower()
    configured_api_key = str(settings.get("llm_api_key", "")).strip()
    if configured_provider != "openai" or not configured_api_key:
        return build_fallback("OpenAI-compatible LLM provider is not configured.")

    try:
        prompt = _build_dashboard_brief_prompt(
            brief=brief,
            citations=citations,
            information_sources_payload=information_sources_payload,
            source_mix=source_mix,
        )
        generated_answer = get_llm_provider().generate(prompt).strip()
    except Exception as error:
        return build_fallback(f"LLM generation failed: {error.__class__.__name__}.")

    if not generated_answer:
        return build_fallback("LLM generation returned an empty answer.")

    unknown_citation_ids = _extract_unknown_dashboard_brief_citation_ids(
        answer_markdown=generated_answer,
        citations=citations,
    )
    if unknown_citation_ids:
        diagnostics = brief.setdefault("diagnostics", [])
        if not isinstance(diagnostics, list):
            brief["diagnostics"] = diagnostics = []
        diagnostics.append(
            {
                "source": "citations",
                "status": "invalid",
                "severity": "warning",
                "code": "CITATION_UNKNOWN_ID",
                "message": "The LLM dashboard brief referenced citation IDs that were not present in the dashboard evidence.",
                "details": {"unknown_ids": unknown_citation_ids},
            }
        )
        return build_fallback("LLM citation validation failed: unknown citation id.")

    return {
        "answer_markdown": generated_answer,
        "model": _build_dashboard_brief_model_metadata(
            provider="openai",
            name=DASHBOARD_BRIEF_MODEL_NAME,
            used_llm=True,
            fallback_reason=None,
        ),
        "context": {"source_mix": source_mix},
    }


def _build_dashboard_brief(
    *,
    generated_at: str,
    followed_payload: dict[str, object],
    macro_indicator_items: list[dict[str, object]],
    research_availability: dict[str, object],
    information_sources_payload: dict[str, object],
    diagnostics: list[dict[str, object]],
) -> dict[str, object]:
    followed_items = followed_payload.get("items")
    followed_list = followed_items if isinstance(followed_items, list) else []
    fresh_followed_count = sum(1 for item in followed_list if isinstance(item, dict) and item.get("freshness") == "fresh")
    stale_or_missing_count = sum(
        1
        for item in followed_list
        if isinstance(item, dict) and item.get("freshness") in {"stale", "no_data", "unavailable"}
    )
    available_indicators = [item for item in macro_indicator_items if item.get("status") == "ok"]
    missing_indicators = [item for item in macro_indicator_items if item.get("status") != "ok"]
    report_summary = research_availability.get("reports")
    news_summary = research_availability.get("news")
    reports = report_summary if isinstance(report_summary, dict) else {}
    news = news_summary if isinstance(news_summary, dict) else {}
    report_count = int(reports.get("count") or 0)
    news_count = int(news.get("count") or 0)

    what_changed_items = [
        f"{item.get('name')}: {_format_indicator_value(item)} as of {item.get('as_of')}."
        for item in available_indicators[:4]
    ]
    if not what_changed_items:
        what_changed_items.append(
            "Macro and valuation indicators are configured, but no audited observations are available yet."
        )

    why_it_matters_items = [
        "Macro indicators are shown with source and as-of metadata so missing values remain data gaps, not market signals.",
        f"{fresh_followed_count} followed instruments have fresh daily bars; {stale_or_missing_count} need attention.",
        f"{report_count} generated reports and {news_count} stored news items are available for followed-symbol context.",
    ]

    watch_next_items = [
        "Seed audited macro observations or connect official source adapters before relying on macro conclusions.",
        "Review generated reports and watchlist moves together with macro freshness before forming a research hypothesis.",
    ]
    if report_count == 0 or news_count == 0:
        watch_next_items.append("Generate reports or ingest news for followed symbols before relying on narrative context.")
    if diagnostics:
        watch_next_items.append("Inspect dashboard diagnostics for provider or index data gaps.")

    data_gap_items = [
        f"{item.get('name')}: {item.get('no_data_reason') or 'No audited observation is available.'}"
        for item in missing_indicators[:6]
    ]
    if len(missing_indicators) > 6:
        data_gap_items.append(f"{len(missing_indicators) - 6} additional macro indicators have no audited value yet.")
    if not data_gap_items:
        data_gap_items.append("No macro indicator data gaps were detected in the current dashboard payload.")
    if report_count == 0:
        data_gap_items.append("Generated reports: No stored reports are available for the followed symbols.")
    if news_count == 0:
        data_gap_items.append("News: No stored news articles are available for the followed symbols.")

    brief_diagnostics: list[dict[str, object]] = []
    if missing_indicators:
        brief_diagnostics.append(
            {
                "source": "market_indicators",
                "status": "no_data",
                "severity": "info",
                "code": "MACRO_INDICATOR_NO_DATA",
                "message": "Some macro indicators are configured but do not have audited observations yet.",
                "details": {"count": len(missing_indicators)},
            }
        )
    research_diagnostics = research_availability.get("diagnostics")
    if isinstance(research_diagnostics, list):
        brief_diagnostics.extend(item for item in research_diagnostics if isinstance(item, dict))
    research_citations = research_availability.get("citations")
    extra_citations = [item for item in research_citations if isinstance(item, dict)] if isinstance(research_citations, list) else []

    brief: dict[str, object] = {
        "status": "ok" if available_indicators else "degraded",
        "generated_at": generated_at,
        "sections": [
            {"id": "what_changed", "title": "What changed", "items": what_changed_items},
            {"id": "why_it_matters", "title": "Why it matters", "items": why_it_matters_items},
            {"id": "what_to_watch_next", "title": "What to watch next", "items": watch_next_items},
            {"id": "data_gaps", "title": "Data gaps", "items": data_gap_items},
        ],
        "citations": [*[_build_indicator_citation(item) for item in available_indicators], *extra_citations],
        "diagnostics": brief_diagnostics,
        "safety": {
            "not_investment_advice": True,
            "no_buy_sell_hold": True,
            "no_fabricated_macro_data": True,
        },
    }
    brief["narrative"] = _build_dashboard_brief_narrative(
        brief=brief,
        information_sources_payload=information_sources_payload,
    )
    return brief


@cache_market_overview(ttl=300)
def get_market_overview_payload(
    *,
    session: Session,
    provider_name: str | None = None,
    today: date | None = None,
) -> dict[str, object]:
    resolved_today = today or date.today()
    start = resolved_today - timedelta(days=DASHBOARD_RANGE_DAYS)
    effective_provider_name = resolve_market_data_provider_name(provider_name)

    followed_payload, followed_diagnostics = _serialize_followed_instruments(
        session=session,
        provider_name=effective_provider_name,
        start=start,
        end=resolved_today,
        today=resolved_today,
    )
    indices_payload, index_diagnostics = _serialize_indices(
        session=session,
        provider_name=effective_provider_name,
        start=start,
        end=resolved_today,
        today=resolved_today,
    )
    macro_indicator_items = get_macro_indicator_payloads(session=session)
    information_sources_payload = get_information_source_readiness_payload(session=session)
    research_availability = _build_research_availability_payload(
        session=session,
        followed_payload=followed_payload,
    )
    diagnostics = [*followed_diagnostics, *index_diagnostics]
    generated_at = datetime.now(timezone.utc).isoformat()

    return {
        "generated_at": generated_at,
        "provider": effective_provider_name,
        "range": {
            "timeframe": "1d",
            "start": start.isoformat(),
            "end": resolved_today.isoformat(),
        },
        "followed": followed_payload,
        "indices": indices_payload,
        "macro_indicators": {"items": macro_indicator_items},
        "valuation_indicators": {"items": macro_indicator_items},
        "information_sources": information_sources_payload,
        "dashboard_brief": _build_dashboard_brief(
            generated_at=generated_at,
            followed_payload=followed_payload,
            macro_indicator_items=macro_indicator_items,
            research_availability=research_availability,
            information_sources_payload=information_sources_payload,
            diagnostics=diagnostics,
        ),
        "diagnostics": diagnostics,
    }
