from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from packages.ai.llm_factory import get_llm_provider
from packages.ai.market_assistant import (
    FALLBACK_MODEL_NAME,
    MarketAssistantCitation,
    MarketAssistantPromptContext,
    build_deterministic_market_answer,
    build_market_assistant_prompt,
    get_safety_disclaimer,
)
from packages.services.fundamentals import get_fundamental_payload
from packages.services.indicators import get_stored_indicators_payload
from packages.services.market_data import get_bars_payload
from packages.services.market_daily_evidence import list_citable_market_daily_evidence_citations
from packages.services.market_indicators import get_macro_indicator_payloads
from packages.services.news import get_news_sentiment_payload
from packages.services.official_disclosure_documents import (
    list_citable_official_disclosure_section_citations,
)
from packages.services.official_disclosures import list_citable_official_disclosure_citations
from packages.services.platform_settings import get_platform_settings, normalize_llm_model
from packages.services.research_source_notes import list_citable_research_source_note_citations
from packages.services.research_shortlists import get_research_shortlist
from packages.services.reports import list_reports_payload


DEFAULT_ASSISTANT_LOOKBACK_DAYS = 180
SUPPORTED_ASSISTANT_SCOPE = "instrument"
SUPPORTED_ASSISTANT_TIMEFRAME = "1d"
ASSISTANT_CITATION_ID_PATTERN = re.compile(r"\[([A-Za-z0-9_:\-./+]+)\]")
ASSISTANT_CITATION_ID_PREFIXES = (
    "bars_1d:",
    "technical_indicators:",
    "fundamental_metrics:",
    "fundamentals:",
    "market_indicator:",
    "news:",
    "news_articles:",
    "generated_report:",
    "research_source_note:",
    "market_daily_event:",
    "official_disclosure:",
    "official_disclosure_section:",
    "research_shortlist:",
)
RESEARCH_SNAPSHOT_FACTOR_FIELDS = (
    "code",
    "field",
    "actual",
    "threshold",
    "normalization",
    "buffer",
    "dimension",
    "dimension_weight",
    "weighted_contribution",
)
RESEARCH_SNAPSHOT_GAP_FIELDS = (
    "source",
    "code",
    "status",
    "as_of",
    "decision_date",
)
RESEARCH_SNAPSHOT_INVALIDATION_FIELDS = (
    "rule",
    "field",
    "invalidates_when",
    "operator",
    "threshold",
    "entry_actual",
)
RESEARCH_SNAPSHOT_DIAGNOSTIC_MESSAGES = {
    "RESEARCH_SNAPSHOT_INVALID_ID": {
        "en": "The requested research snapshot ID is invalid.",
        "zh": "请求的每日候选快照 ID 无效。",
    },
    "RESEARCH_SNAPSHOT_SESSION_UNAVAILABLE": {
        "en": "The requested research snapshot cannot be loaded because the database session is unavailable.",
        "zh": "数据库会话不可用，无法读取请求的每日候选快照。",
    },
    "RESEARCH_SNAPSHOT_UNAVAILABLE": {
        "en": "The requested research snapshot is temporarily unavailable.",
        "zh": "请求的每日候选快照暂不可用。",
    },
    "RESEARCH_SNAPSHOT_NOT_FOUND": {
        "en": "The requested committed research snapshot was not found.",
        "zh": "未找到请求的已提交每日候选快照。",
    },
    "RESEARCH_SNAPSHOT_SYMBOL_MISMATCH": {
        "en": "The requested research snapshot does not contain the exact assistant symbol.",
        "zh": "请求的每日候选快照不包含当前助手标的。",
    },
}


@dataclass(frozen=True)
class MarketAssistantResearchEvidence:
    citation: MarketAssistantCitation
    summary: str
    priority: int
    source_type: str
    title: str | None = None
    as_of: str | None = None
    published_at: str | None = None
    url: str | None = None
    provider: str | None = None
    metadata: dict[str, object] | None = None


@dataclass(frozen=True)
class MarketAssistantResearchSnapshot:
    summary: str
    evidence: list[MarketAssistantResearchEvidence]
    response_context: dict[str, object] | None


def answer_market_assistant_question(
    *,
    symbol: str,
    question: str,
    scope: str = SUPPORTED_ASSISTANT_SCOPE,
    locale: str = "zh",
    timeframe: str = SUPPORTED_ASSISTANT_TIMEFRAME,
    start: date | None = None,
    end: date | None = None,
    provider_name: str | None = None,
    market: str | None = None,
    research_snapshot_id: str | None = None,
    session: Session | None = None,
) -> dict[str, object]:
    normalized_symbol = _normalize_symbol(symbol)
    normalized_question = _normalize_question(question)
    normalized_locale = "en" if locale == "en" else "zh"
    effective_start, effective_end = _resolve_date_range(start, end)
    _validate_scope_and_timeframe(scope, timeframe)

    bars_payload = get_bars_payload(
        normalized_symbol,
        timeframe,
        effective_start,
        effective_end,
        session=session,
        provider_name=provider_name,
        market=market,
    )
    bar_items = _extract_bar_items(bars_payload)
    diagnostics = _extract_daily_bar_diagnostics(bars_payload)
    research_snapshot = _build_research_snapshot_context(
        research_snapshot_id,
        symbol=normalized_symbol,
        locale=normalized_locale,
        session=session,
        diagnostics=diagnostics,
    )

    if not bar_items:
        daily_bar_status = str(bars_payload.get("status") or "no_data").strip().lower()
        daily_sources_unavailable = daily_bar_status in {
            "degraded",
            "failed",
            "unavailable",
        }
        diagnostic_status = "unavailable" if daily_sources_unavailable else "no_data"
        diagnostic_code = (
            "SOURCE_UNAVAILABLE" if daily_sources_unavailable else "SOURCE_NO_DATA"
        )
        diagnostic_message = (
            "Daily-bar sources were unavailable for the requested symbol and date range."
            if daily_sources_unavailable
            else "No verified daily bars are available for the requested symbol and date range."
        )
        diagnostics.append(
            {
                "source": "bars_1d",
                "status": diagnostic_status,
                "severity": "error",
                "code": diagnostic_code,
                "message": diagnostic_message,
            }
        )
        prompt_context = MarketAssistantPromptContext(
            symbol=normalized_symbol,
            locale=normalized_locale,
            question=normalized_question,
            timeframe=timeframe,
            start=effective_start.isoformat(),
            end=effective_end.isoformat(),
            as_of=None,
            latest_close=None,
            period_change_pct=None,
            bar_count=0,
            price_summary="No verified daily bars are available.",
            indicator_summary="No technical indicators were loaded because price context is unavailable.",
            fundamental_summary="No fundamental context was loaded because price context is unavailable.",
            news_summary="No news context was loaded because price context is unavailable.",
            research_summary=(
                research_snapshot.summary or "No generated research reports were loaded."
            ),
            citations=_rank_research_citations(research_snapshot.evidence),
            diagnostics=diagnostics,
        )
        return _build_response_payload(
            status="degraded" if daily_sources_unavailable else "no_data",
            symbol=normalized_symbol,
            prompt_context=prompt_context,
            answer_markdown=build_deterministic_market_answer(prompt_context),
            model_metadata=_build_fallback_model_metadata(diagnostic_message),
            bars_payload=bars_payload,
            research_snapshot=research_snapshot.response_context,
        )

    price_context = _build_price_context(
        normalized_symbol,
        timeframe,
        effective_start,
        effective_end,
        bar_items,
        provider_name=_stringify_optional(bars_payload.get("effective_provider") or bars_payload.get("provider")),
    )
    research_evidence = list(price_context["evidence"])
    research_evidence.extend(research_snapshot.evidence)
    indicator_summary, indicator_evidence = _build_indicator_context(normalized_symbol, session, diagnostics)
    macro_summary, macro_evidence = _build_macro_indicator_context(session, diagnostics)
    fundamental_summary, fundamental_evidence = _build_fundamental_context(
        normalized_symbol,
        effective_end,
        session,
        diagnostics,
    )
    news_summary, news_evidence = _build_news_context(normalized_symbol, session, diagnostics)
    generated_report_summary, generated_report_evidence = _build_generated_report_context(
        normalized_symbol,
        normalized_question,
        effective_start,
        effective_end,
        session,
        diagnostics,
    )
    source_note_summary, source_note_evidence = _build_research_source_note_context(
        normalized_symbol,
        session,
        diagnostics,
    )
    disclosure_summary, disclosure_evidence = _build_official_disclosure_context(
        normalized_symbol,
        session,
        diagnostics,
    )
    disclosure_section_summary, disclosure_section_evidence = _build_official_disclosure_section_context(
        normalized_symbol,
        session,
        diagnostics,
    )
    market_daily_summary, market_daily_evidence = _build_market_daily_evidence_context(
        normalized_symbol,
        session,
        diagnostics,
    )
    research_evidence.extend(indicator_evidence)
    research_evidence.extend(macro_evidence)
    research_evidence.extend(fundamental_evidence)
    research_evidence.extend(news_evidence)
    research_evidence.extend(generated_report_evidence)
    research_evidence.extend(source_note_evidence)
    research_evidence.extend(disclosure_evidence)
    research_evidence.extend(disclosure_section_evidence)
    research_evidence.extend(market_daily_evidence)
    citations = _rank_research_citations(research_evidence)
    research_summary = " ".join(
        summary
        for summary in (
            research_snapshot.summary,
            generated_report_summary,
            source_note_summary,
            disclosure_summary,
            disclosure_section_summary,
        )
        if summary
    )

    prompt_context = MarketAssistantPromptContext(
        symbol=normalized_symbol,
        locale=normalized_locale,
        question=normalized_question,
        timeframe=timeframe,
        start=effective_start.isoformat(),
        end=effective_end.isoformat(),
        as_of=price_context["as_of"],
        latest_close=price_context["latest_close"],
        period_change_pct=price_context["period_change_pct"],
        bar_count=price_context["bar_count"],
        price_summary=price_context["price_summary"],
        indicator_summary=indicator_summary,
        macro_summary=macro_summary,
        market_daily_summary=market_daily_summary,
        fundamental_summary=fundamental_summary,
        news_summary=news_summary,
        research_summary=research_summary,
        citations=citations,
        diagnostics=diagnostics,
    )

    answer_markdown, model_metadata = _generate_answer_or_fallback(prompt_context)
    response_status = "ok" if model_metadata["used_llm"] and not diagnostics else "degraded"
    return _build_response_payload(
        status=response_status,
        symbol=normalized_symbol,
        prompt_context=prompt_context,
        answer_markdown=answer_markdown,
        model_metadata=model_metadata,
        bars_payload=bars_payload,
        research_snapshot=research_snapshot.response_context,
    )


def _normalize_symbol(symbol: str) -> str:
    normalized_symbol = symbol.strip().upper()
    if not normalized_symbol:
        msg = "Symbol is required."
        raise ValueError(msg)
    return normalized_symbol


def _normalize_question(question: str) -> str:
    normalized_question = question.strip()
    if not normalized_question:
        msg = "Question is required."
        raise ValueError(msg)
    return normalized_question


def _resolve_date_range(start: date | None, end: date | None) -> tuple[date, date]:
    effective_end = end or date.today()
    effective_start = start or effective_end - timedelta(days=DEFAULT_ASSISTANT_LOOKBACK_DAYS)
    if effective_start > effective_end:
        msg = "Start date must be earlier than or equal to end date."
        raise ValueError(msg)
    return effective_start, effective_end


def _validate_scope_and_timeframe(scope: str, timeframe: str) -> None:
    if scope != SUPPORTED_ASSISTANT_SCOPE:
        msg = f"Unsupported assistant scope: {scope}. Only {SUPPORTED_ASSISTANT_SCOPE} is supported."
        raise ValueError(msg)
    if timeframe != SUPPORTED_ASSISTANT_TIMEFRAME:
        msg = f"Unsupported assistant timeframe: {timeframe}. Only {SUPPORTED_ASSISTANT_TIMEFRAME} is supported."
        raise ValueError(msg)


def _build_research_snapshot_context(
    research_snapshot_id: str | None,
    *,
    symbol: str,
    locale: str,
    session: Session | None,
    diagnostics: list[dict[str, object]],
) -> MarketAssistantResearchSnapshot:
    if research_snapshot_id is None:
        return MarketAssistantResearchSnapshot(summary="", evidence=[], response_context=None)

    normalized_snapshot_id = research_snapshot_id.strip()
    parsed_snapshot_id = _canonical_uuid(normalized_snapshot_id)
    if parsed_snapshot_id is None:
        return _degraded_research_snapshot(
            diagnostics,
            status="invalid",
            code="RESEARCH_SNAPSHOT_INVALID_ID",
            locale=locale,
        )

    if session is None:
        return _degraded_research_snapshot(
            diagnostics,
            status="session_unavailable",
            code="RESEARCH_SNAPSHOT_SESSION_UNAVAILABLE",
            locale=locale,
            requested_id=parsed_snapshot_id,
        )

    try:
        snapshot_payload = get_research_shortlist(parsed_snapshot_id, session=session)
    except Exception:
        _rollback_session_if_possible(session)
        return _degraded_research_snapshot(
            diagnostics,
            status="unavailable",
            code="RESEARCH_SNAPSHOT_UNAVAILABLE",
            locale=locale,
            requested_id=parsed_snapshot_id,
        )

    if snapshot_payload is None:
        return _degraded_research_snapshot(
            diagnostics,
            status="missing",
            code="RESEARCH_SNAPSHOT_NOT_FOUND",
            locale=locale,
            requested_id=parsed_snapshot_id,
        )

    run = _optional_dict(snapshot_payload.get("run"))
    raw_items = snapshot_payload.get("items")
    resolved_run_id = _canonical_uuid(run.get("id")) if run is not None else None
    decision_date = _canonical_date(run.get("decision_date")) if run is not None else None
    if resolved_run_id != parsed_snapshot_id or decision_date is None or not isinstance(raw_items, list):
        return _degraded_research_snapshot(
            diagnostics,
            status="unavailable",
            code="RESEARCH_SNAPSHOT_UNAVAILABLE",
            locale=locale,
            requested_id=parsed_snapshot_id,
        )

    candidate = next(
        (
            item
            for item in raw_items
            if isinstance(item, dict)
            and str(item.get("symbol") or "").strip().upper() == symbol
        ),
        None,
    )
    if candidate is None:
        return _degraded_research_snapshot(
            diagnostics,
            status="symbol_mismatch",
            code="RESEARCH_SNAPSHOT_SYMBOL_MISMATCH",
            locale=locale,
            requested_id=parsed_snapshot_id,
            metadata={"run_id": resolved_run_id, "decision_date": decision_date},
        )

    candidate_id = _canonical_uuid(candidate.get("id"))
    rank = _safe_int(candidate.get("rank"))
    score = _safe_float(candidate.get("score"))
    if candidate_id is None or rank <= 0 or score is None:
        return _degraded_research_snapshot(
            diagnostics,
            status="unavailable",
            code="RESEARCH_SNAPSHOT_UNAVAILABLE",
            locale=locale,
            requested_id=parsed_snapshot_id,
        )

    structured_evidence = {
        "decision_date": decision_date,
        "rank": rank,
        "score": score,
        "supporting_factors": _snapshot_structured_records(
            candidate.get("supporting_factors"),
            RESEARCH_SNAPSHOT_FACTOR_FIELDS,
        ),
        "opposing_factors": _snapshot_structured_records(
            candidate.get("opposing_factors"),
            RESEARCH_SNAPSHOT_FACTOR_FIELDS,
        ),
        "data_gaps": _snapshot_structured_records(
            candidate.get("data_gaps"),
            RESEARCH_SNAPSHOT_GAP_FIELDS,
        ),
        "invalidation_conditions": _snapshot_structured_records(
            candidate.get("invalidation_conditions"),
            RESEARCH_SNAPSHOT_INVALIDATION_FIELDS,
        ),
    }
    summary = _build_research_snapshot_summary(
        locale=locale,
        decision_date=decision_date,
        rank=rank,
        score=score,
        structured_evidence=structured_evidence,
    )
    citation_id = f"research_shortlist:{resolved_run_id}:{candidate_id}"
    citation_metadata = {
        "run_id": resolved_run_id,
        "candidate_id": candidate_id,
        "symbol": symbol,
        "structured_evidence": structured_evidence,
    }
    citation_label = (
        f"{symbol} 的已提交每日候选快照（{decision_date}）"
        if locale == "zh"
        else f"Committed daily research shortlist for {symbol} on {decision_date}"
    )
    evidence_title = (
        f"{symbol} 的已提交每日候选快照"
        if locale == "zh"
        else f"Committed daily research shortlist for {symbol}"
    )
    citation = MarketAssistantCitation(
        id=citation_id,
        label=citation_label,
        source="research_shortlist",
        source_type="research_shortlist",
        as_of=decision_date,
        excerpt=_build_safe_excerpt(summary, max_length=1000),
        metadata=citation_metadata,
    )
    evidence = MarketAssistantResearchEvidence(
        citation=citation,
        summary=summary,
        priority=15,
        source_type="research_shortlist",
        title=evidence_title,
        as_of=decision_date,
        metadata=citation_metadata,
    )
    response_context = {
        "requested_id": parsed_snapshot_id,
        "status": "applied",
        "applied": True,
        "run_id": resolved_run_id,
        "candidate_id": candidate_id,
        "decision_date": decision_date,
        "rank": rank,
        "score": score,
        "citation_id": citation_id,
    }
    return MarketAssistantResearchSnapshot(
        summary=summary,
        evidence=[evidence],
        response_context=response_context,
    )


def _build_research_snapshot_summary(
    *,
    locale: str,
    decision_date: str,
    rank: int,
    score: float,
    structured_evidence: dict[str, object],
) -> str:
    supporting = _format_snapshot_record_group(structured_evidence.get("supporting_factors"))
    opposing = _format_snapshot_record_group(structured_evidence.get("opposing_factors"))
    gaps = _format_snapshot_record_group(structured_evidence.get("data_gaps"))
    invalidations = _format_snapshot_record_group(
        structured_evidence.get("invalidation_conditions")
    )
    if locale == "zh":
        return (
            f"已应用已提交的每日候选快照结构化证据：决策日期={decision_date}；排名={rank}；"
            f"得分={score}；支持因素={supporting}；反向因素={opposing}；"
            f"数据缺口={gaps}；失效条件={invalidations}。"
        )
    return (
        f"Committed research shortlist snapshot evidence: decision_date={decision_date}; "
        f"rank={rank}; score={score}; supporting_factors={supporting}; "
        f"opposing_factors={opposing}; data_gaps={gaps}; "
        f"invalidation_conditions={invalidations}."
    )


def _format_snapshot_record_group(value: object) -> str:
    if not isinstance(value, list) or not value:
        return "none"
    rendered_records: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        rendered_records.append(
            "(" + ", ".join(f"{key}={item[key]}" for key in sorted(item)) + ")"
        )
    return "; ".join(rendered_records) or "none"


def _research_snapshot_diagnostic_message(code: str, locale: str) -> str:
    localized = RESEARCH_SNAPSHOT_DIAGNOSTIC_MESSAGES.get(code)
    if localized is None:
        return (
            "请求的每日候选快照暂不可用。"
            if locale == "zh"
            else "The requested research snapshot is temporarily unavailable."
        )
    return localized["zh" if locale == "zh" else "en"]


def _degraded_research_snapshot(
    diagnostics: list[dict[str, object]],
    *,
    status: str,
    code: str,
    locale: str,
    requested_id: str | None = None,
    metadata: dict[str, object] | None = None,
) -> MarketAssistantResearchSnapshot:
    response_context: dict[str, object] = {"status": status, "applied": False}
    if requested_id is not None:
        response_context["requested_id"] = requested_id
    if metadata:
        response_context.update(metadata)
    diagnostics.append(
        {
            "source": "research_shortlist",
            "status": status,
            "severity": "warning",
            "code": code,
            "message": _research_snapshot_diagnostic_message(code, locale),
        }
    )
    return MarketAssistantResearchSnapshot(
        summary="",
        evidence=[],
        response_context=response_context,
    )


def _snapshot_structured_records(
    value: object,
    allowed_fields: tuple[str, ...],
) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    records: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        record: dict[str, object] = {}
        for field_name in allowed_fields:
            if field_name not in item:
                continue
            record[field_name] = _sanitize_snapshot_value(item[field_name])
        if record:
            records.append(record)
    return records


def _sanitize_snapshot_value(value: object) -> object:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return [_sanitize_snapshot_value(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _sanitize_snapshot_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if not _is_snapshot_prose_field(str(key))
        }
    return None


def _is_snapshot_prose_field(field_name: str) -> bool:
    normalized_field = field_name.strip().casefold()
    prose_tokens = (
        "description",
        "explanation",
        "label",
        "markdown",
        "message",
        "name",
        "note",
        "prose",
        "title",
    )
    return any(token in normalized_field for token in prose_tokens)


def _canonical_uuid(value: object) -> str | None:
    if value is None:
        return None
    try:
        return str(UUID(str(value).strip()))
    except (TypeError, ValueError, AttributeError):
        return None


def _canonical_date(value: object) -> str | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(str(value).strip()).isoformat()
    except (TypeError, ValueError, AttributeError):
        return None


def _extract_bar_items(bars_payload: dict[str, object]) -> list[dict[str, object]]:
    raw_items = bars_payload.get("items")
    if not isinstance(raw_items, list):
        return []
    return [item for item in raw_items if isinstance(item, dict)]


def _extract_daily_bar_diagnostics(
    bars_payload: dict[str, object],
) -> list[dict[str, object]]:
    raw_diagnostics = bars_payload.get("diagnostics")
    if not isinstance(raw_diagnostics, list):
        return []
    diagnostics: list[dict[str, object]] = []
    for raw_diagnostic in raw_diagnostics:
        if not isinstance(raw_diagnostic, dict):
            continue
        diagnostic = {
            field: raw_diagnostic[field]
            for field in ("source", "status", "severity", "code", "message")
            if isinstance(raw_diagnostic.get(field), str)
        }
        dropped_row_count = raw_diagnostic.get("dropped_row_count")
        if isinstance(dropped_row_count, int) and dropped_row_count >= 0:
            diagnostic["dropped_row_count"] = dropped_row_count
        if diagnostic:
            diagnostics.append(diagnostic)
    return diagnostics


def _build_price_context(
    symbol: str,
    timeframe: str,
    start: date,
    end: date,
    bar_items: list[dict[str, object]],
    provider_name: str | None = None,
) -> dict[str, Any]:
    first_bar = bar_items[0]
    latest_bar = bar_items[-1]
    first_close = _safe_float(first_bar.get("close"))
    latest_close = _safe_float(latest_bar.get("close"))
    period_change_pct = _calculate_period_change_pct(first_close, latest_close)
    latest_timestamp = _stringify_timestamp(latest_bar.get("timestamp") or latest_bar.get("trade_date"))
    as_of = latest_timestamp or end.isoformat()
    price_summary = (
        f"Daily bars from {start.isoformat()} to {end.isoformat()}; latest close "
        f"{_format_optional_number(latest_close)} as of {as_of}; period change "
        f"{_format_optional_number(period_change_pct)}%; bar count {len(bar_items)}."
    )
    citation = MarketAssistantCitation(
        id=f"bars_1d:{symbol}:{as_of}",
        label=f"Daily bars for {symbol} as of {as_of}",
        source=f"bars_{timeframe}",
        source_type="bars",
        as_of=as_of,
        provider=provider_name,
        excerpt=price_summary,
        metadata={"bar_count": len(bar_items), "timeframe": timeframe},
    )
    evidence = [
        MarketAssistantResearchEvidence(
            citation=citation,
            summary=price_summary,
            priority=10,
            source_type="bars",
            title=f"Daily bars for {symbol}",
            as_of=as_of,
            provider=provider_name,
            metadata={"bar_count": len(bar_items), "timeframe": timeframe},
        )
    ]
    return {
        "as_of": as_of,
        "latest_close": latest_close,
        "period_change_pct": period_change_pct,
        "bar_count": len(bar_items),
        "price_summary": price_summary,
        "citations": [citation],
        "evidence": evidence,
    }


def _build_indicator_context(
    symbol: str,
    session: Session | None,
    diagnostics: list[dict[str, object]],
) -> tuple[str, list[MarketAssistantResearchEvidence]]:
    if session is None:
        diagnostics.append(
            {
                "source": "indicators",
                "status": "no_data",
                "severity": "info",
                "code": "SOURCE_NO_DATA",
                "message": "No database session is available for stored technical indicators.",
            }
        )
        return "No stored technical indicators are available.", []

    try:
        payload = get_stored_indicators_payload(symbol, session)
    except Exception:
        _rollback_session_if_possible(session)
        diagnostics.append(
            {
                "source": "indicators",
                "status": "unavailable",
                "severity": "warning",
                "code": "SOURCE_UNAVAILABLE",
                "message": "Stored technical indicators could not be loaded.",
            }
        )
        return "Stored technical indicators could not be loaded.", []

    indicators = payload.get("indicators")
    if not isinstance(indicators, dict) or not indicators:
        diagnostics.append(
            {
                "source": "indicators",
                "status": "no_data",
                "severity": "info",
                "code": "SOURCE_NO_DATA",
                "message": "No stored technical indicators are available for this symbol.",
            }
        )
        return "No stored technical indicators are available.", []

    formatted_values = [
        f"{indicator_code}={_format_context_value(indicator_value)}"
        for indicator_code, indicator_value in sorted(indicators.items())[:8]
    ]
    summary = ", ".join(formatted_values)
    as_of = _stringify_optional(payload.get("as_of")) or "latest"
    provider_name = _stringify_optional(payload.get("source"))
    citation = MarketAssistantCitation(
        id=f"technical_indicators:{symbol}:{as_of}",
        label=f"Technical indicators for {symbol} as of {as_of}",
        source="indicators",
        source_type="technical_indicator",
        as_of=as_of,
        provider=provider_name,
        excerpt=summary,
        metadata={"indicator_codes": sorted(str(indicator_code) for indicator_code in indicators)},
    )
    evidence = [
        MarketAssistantResearchEvidence(
            citation=citation,
            summary=summary,
            priority=20,
            source_type="technical_indicator",
            title=f"Technical indicators for {symbol}",
            as_of=as_of,
            provider=provider_name,
            metadata={"indicator_codes": sorted(str(indicator_code) for indicator_code in indicators)},
        )
    ]
    return summary, evidence


def _build_macro_indicator_context(
    session: Session | None,
    diagnostics: list[dict[str, object]],
) -> tuple[str, list[MarketAssistantResearchEvidence]]:
    if session is None:
        diagnostics.append(
            {
                "source": "market_indicators",
                "status": "no_data",
                "severity": "info",
                "code": "SOURCE_NO_DATA",
                "message": "No database session is available for stored macro indicators.",
            }
        )
        return "No stored macro indicator observations are available.", []

    try:
        indicator_items = get_macro_indicator_payloads(session=session)
    except Exception:
        _rollback_session_if_possible(session)
        diagnostics.append(
            {
                "source": "market_indicators",
                "status": "unavailable",
                "severity": "warning",
                "code": "SOURCE_UNAVAILABLE",
                "message": "Stored macro indicators could not be loaded.",
            }
        )
        return "Stored macro indicators could not be loaded.", []

    prioritized_items = _prioritize_macro_indicator_items(indicator_items)
    citable_items = [item for item in prioritized_items if _is_citable_macro_indicator_item(item)]
    missing_codes = [
        str(item.get("code"))
        for item in prioritized_items
        if item.get("code") and not _is_citable_macro_indicator_item(item)
    ]
    if missing_codes:
        diagnostics.append(
            {
                "source": "market_indicators",
                "status": "no_data",
                "severity": "info",
                "code": "MACRO_INDICATOR_NO_DATA",
                "message": "Some macro indicators are configured but do not have audited observations yet.",
                "details": {"missing_indicator_codes": missing_codes[:12], "count": len(missing_codes)},
            }
        )

    if not citable_items:
        return "No stored macro indicator observations are available.", []

    evidence_items = [
        _build_macro_indicator_evidence_item(item, item_index)
        for item_index, item in enumerate(citable_items[:8])
    ]
    summary = "; ".join(evidence_item.summary for evidence_item in evidence_items[:6])
    return summary, evidence_items


def _prioritize_macro_indicator_items(indicator_items: list[dict[str, object]]) -> list[dict[str, object]]:
    settings = get_platform_settings()
    favorite_codes = settings.get("favorite_macro_indicator_codes")
    favorite_order = (
        {str(code): index for index, code in enumerate(favorite_codes)}
        if isinstance(favorite_codes, list)
        else {}
    )

    return sorted(
        indicator_items,
        key=lambda item: _macro_indicator_sort_key(item, favorite_order),
    )


def _macro_indicator_sort_key(item: dict[str, object], favorite_order: dict[str, int]) -> tuple[int, int, str]:
    code = str(item.get("code") or "")
    category = str(item.get("category") or "")
    if code in favorite_order:
        return (0, favorite_order[code], code)
    if "buffett" in code:
        return (1, 0, code)
    category_order = {"rates": 2, "inflation": 3, "liquidity": 4, "valuation": 5}
    return (category_order.get(category, 9), 0, code)


def _is_citable_macro_indicator_item(item: dict[str, object]) -> bool:
    return (
        item.get("value") is not None
        and bool(_stringify_optional(item.get("as_of")))
        and bool(_stringify_optional(item.get("source")))
    )


def _build_macro_indicator_evidence_item(
    item: dict[str, object],
    item_index: int,
) -> MarketAssistantResearchEvidence:
    code = str(item.get("code") or "unknown_indicator")
    name = str(item.get("name") or code)
    as_of = _stringify_optional(item.get("as_of")) or "unknown"
    provider_name = _stringify_optional(item.get("source"))
    summary = f"{name}={_format_macro_indicator_value(item)} as of {as_of}."
    citation = MarketAssistantCitation(
        id=f"market_indicator:{code}:{as_of}",
        label=name,
        source="market_indicators",
        source_type="macro_indicator",
        as_of=as_of,
        provider=provider_name,
        excerpt=summary,
        metadata={
            "code": code,
            "category": item.get("category"),
            "region": item.get("region"),
            "unit": item.get("unit"),
            "components": item.get("components") if isinstance(item.get("components"), dict) else {},
        },
    )
    return MarketAssistantResearchEvidence(
        citation=citation,
        summary=summary,
        priority=25 + item_index,
        source_type="macro_indicator",
        title=name,
        as_of=as_of,
        provider=provider_name,
        metadata=citation.metadata,
    )


def _format_macro_indicator_value(item: dict[str, object]) -> str:
    value = item.get("value")
    if value is None:
        return "unavailable"
    numeric_value = _safe_float(value)
    formatted_value = f"{numeric_value:.4g}" if numeric_value is not None else str(value)
    return f"{formatted_value}%" if item.get("unit") == "percent" else formatted_value


def _build_fundamental_context(
    symbol: str,
    as_of: date,
    session: Session | None,
    diagnostics: list[dict[str, object]],
) -> tuple[str, list[MarketAssistantResearchEvidence]]:
    try:
        payload = get_fundamental_payload(symbol, as_of=as_of, session=session)
    except Exception:
        _rollback_session_if_possible(session)
        diagnostics.append(
            {
                "source": "fundamentals",
                "status": "unavailable",
                "severity": "warning",
                "code": "SOURCE_UNAVAILABLE",
                "message": "Fundamental metrics could not be loaded.",
            }
        )
        return "Fundamental metrics could not be loaded.", []

    item = payload.get("item")
    if not isinstance(item, dict) or not item:
        diagnostics.append(
            {
                "source": "fundamentals",
                "status": "no_data",
                "severity": "info",
                "code": "SOURCE_NO_DATA",
                "message": "No fundamental snapshot is available for this symbol.",
            }
        )
        return "No fundamental snapshot is available.", []

    important_fields = ("pe_ratio", "revenue_growth", "net_margin", "debt_to_assets", "currency")
    formatted_values = [
        f"{field_name}={_format_context_value(item[field_name])}"
        for field_name in important_fields
        if field_name in item and item[field_name] is not None
    ]
    if not formatted_values:
        formatted_values = [
            f"{field_name}={_format_context_value(field_value)}"
            for field_name, field_value in list(item.items())[:6]
            if field_value is not None
        ]
    summary = ", ".join(formatted_values) if formatted_values else "Fundamental snapshot is present but empty."
    citation_id = _stringify_optional(payload.get("citation")) or f"fundamentals:{symbol}:{as_of.isoformat()}"
    citation_as_of = _stringify_optional(payload.get("as_of")) or as_of.isoformat()
    provider_name = _stringify_optional(payload.get("source"))
    citation = MarketAssistantCitation(
        id=citation_id,
        label=f"Fundamental metrics for {symbol} as of {citation_as_of}",
        source="fundamentals",
        source_type="fundamental",
        as_of=citation_as_of,
        provider=provider_name,
        excerpt=summary,
        metadata={
            "currency": item.get("currency"),
            "pe_ratio": item.get("pe_ratio"),
            "revenue_growth": item.get("revenue_growth"),
            "net_margin": item.get("net_margin"),
            "debt_to_assets": item.get("debt_to_assets"),
        },
    )
    evidence = [
        MarketAssistantResearchEvidence(
            citation=citation,
            summary=summary,
            priority=30,
            source_type="fundamental",
            title=f"Fundamental metrics for {symbol}",
            as_of=citation_as_of,
            provider=provider_name,
            metadata=citation.metadata,
        )
    ]
    return summary, evidence


def _build_news_context(
    symbol: str,
    session: Session | None,
    diagnostics: list[dict[str, object]],
) -> tuple[str, list[MarketAssistantResearchEvidence]]:
    if session is None:
        diagnostics.append(
            {
                "source": "news",
                "status": "no_data",
                "severity": "info",
                "code": "SOURCE_NO_DATA",
                "message": "No database session is available for news sentiment.",
            }
        )
        return "No stored news sentiment is available.", []

    try:
        payload = get_news_sentiment_payload(symbol, session)
    except Exception:
        _rollback_session_if_possible(session)
        diagnostics.append(
            {
                "source": "news",
                "status": "unavailable",
                "severity": "warning",
                "code": "SOURCE_UNAVAILABLE",
                "message": "News sentiment could not be loaded.",
            }
        )
        return "News sentiment could not be loaded.", []

    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    article_count = _safe_int(summary.get("article_count")) if isinstance(summary, dict) else 0
    latest_sentiment = summary.get("latest_sentiment") if isinstance(summary, dict) else None
    if article_count <= 0:
        diagnostics.append(
            {
                "source": "news",
                "status": "no_data",
                "severity": "info",
                "code": "SOURCE_NO_DATA",
                "message": "No stored news sentiment is available for this symbol.",
            }
        )
        return "No stored news sentiment is available.", []

    items = payload.get("items")
    article_items = items[:3] if isinstance(items, list) else []
    article_titles = [str(item.get("title")) for item in article_items if isinstance(item, dict) and item.get("title")]
    title_summary = f" Recent titles: {'; '.join(article_titles)}." if article_titles else ""
    summary_text = f"Latest sentiment {latest_sentiment}; article count {article_count}.{title_summary}"
    evidence = [
        _build_news_evidence_item(symbol, item, item_index)
        for item_index, item in enumerate(article_items)
        if isinstance(item, dict) and item.get("title")
    ]
    return summary_text, evidence


def _generate_answer_or_fallback(
    prompt_context: MarketAssistantPromptContext,
) -> tuple[str, dict[str, object]]:
    settings = get_platform_settings()
    configured_provider = str(settings.get("llm_provider", "mock")).lower()
    configured_api_key = str(settings.get("llm_api_key", "")).strip()
    configured_model = normalize_llm_model(settings.get("llm_model"))
    if configured_provider != "openai" or not configured_api_key:
        fallback_reason = "OpenAI-compatible LLM provider is not configured."
        _append_fallback_diagnostic(prompt_context, fallback_reason)
        return build_deterministic_market_answer(prompt_context), _build_fallback_model_metadata(fallback_reason)

    try:
        llm_provider = get_llm_provider(settings)
        generated_answer = llm_provider.generate(build_market_assistant_prompt(prompt_context)).strip()
    except Exception as error:
        fallback_reason = f"LLM generation failed: {error.__class__.__name__}."
        _append_fallback_diagnostic(prompt_context, fallback_reason)
        return build_deterministic_market_answer(prompt_context), _build_fallback_model_metadata(fallback_reason)

    if not generated_answer:
        fallback_reason = "LLM generation returned an empty answer."
        _append_fallback_diagnostic(prompt_context, fallback_reason)
        return build_deterministic_market_answer(prompt_context), _build_fallback_model_metadata(fallback_reason)

    unknown_citation_ids = _extract_unknown_inline_citation_ids(generated_answer, prompt_context.citations)
    if unknown_citation_ids:
        prompt_context.diagnostics.append(
            {
                "source": "citations",
                "status": "invalid",
                "severity": "warning",
                "code": "CITATION_UNKNOWN_ID",
                "message": "The LLM response referenced citation IDs that were not present in the retrieved evidence.",
                "details": {"unknown_ids": unknown_citation_ids},
            }
        )
        fallback_reason = "LLM citation validation failed: unknown citation id."
        _append_fallback_diagnostic(prompt_context, fallback_reason)
        return build_deterministic_market_answer(prompt_context), _build_fallback_model_metadata(fallback_reason)

    return generated_answer, {
        "provider": "openai",
        "name": configured_model,
        "used_llm": True,
        "fallback_reason": None,
    }


def _build_response_payload(
    *,
    status: str,
    symbol: str,
    prompt_context: MarketAssistantPromptContext,
    answer_markdown: str,
    model_metadata: dict[str, object],
    bars_payload: dict[str, object],
    research_snapshot: dict[str, object] | None,
) -> dict[str, object]:
    return {
        "status": status,
        "answer_markdown": answer_markdown,
        "symbol": symbol,
        "as_of": prompt_context.as_of,
        "model": model_metadata,
        "context": {
            "scope": SUPPORTED_ASSISTANT_SCOPE,
            "timeframe": prompt_context.timeframe,
            "start": prompt_context.start,
            "end": prompt_context.end,
            "latest_close": prompt_context.latest_close,
            "period_change_pct": prompt_context.period_change_pct,
            "bar_count": prompt_context.bar_count,
            "price_summary": prompt_context.price_summary,
            "indicator_summary": prompt_context.indicator_summary,
            "macro_summary": prompt_context.macro_summary,
            "market_daily_summary": prompt_context.market_daily_summary,
            "fundamental_summary": prompt_context.fundamental_summary,
            "news_summary": prompt_context.news_summary,
            "research_summary": prompt_context.research_summary,
            "research_snapshot": research_snapshot,
            "source": bars_payload.get("source"),
            "provider": bars_payload.get("provider"),
            "requested_provider": bars_payload.get("requested_provider"),
            "effective_provider": bars_payload.get("effective_provider"),
            "upstream_source": bars_payload.get("upstream_source"),
            "market": bars_payload.get("market"),
            "adjustment": bars_payload.get("adjustment"),
            "provenance_known": bars_payload.get("provenance_known"),
            "provenance_corrected": bars_payload.get("provenance_corrected", False),
            "fallback_used": bars_payload.get("fallback_used", False),
            "source_attempts": bars_payload.get("source_attempts", []),
            "bars_status": bars_payload.get("status")
            or ("ok" if prompt_context.bar_count else "no_data"),
            "bars_no_data_reason": bars_payload.get("no_data_reason"),
        },
        "citations": [citation.to_payload() for citation in prompt_context.citations],
        "diagnostics": prompt_context.diagnostics,
        "safety": {
            "not_investment_advice": True,
            "no_fabricated_market_data": True,
            "disclaimer": get_safety_disclaimer(prompt_context.locale),
        },
    }


def _build_fallback_model_metadata(fallback_reason: str) -> dict[str, object]:
    return {
        "provider": "deterministic",
        "name": FALLBACK_MODEL_NAME,
        "used_llm": False,
        "fallback_reason": fallback_reason,
    }


def _append_fallback_diagnostic(prompt_context: MarketAssistantPromptContext, fallback_reason: str) -> None:
    prompt_context.diagnostics.append(
        {
            "source": "assistant_model",
            "status": "fallback",
            "severity": "info",
            "code": "FALLBACK_USED",
            "message": "The assistant used a deterministic fallback response instead of an LLM answer.",
            "details": {"reason": fallback_reason},
        }
    )


def _calculate_period_change_pct(first_close: float | None, latest_close: float | None) -> float | None:
    if first_close is None or latest_close is None or first_close == 0:
        return None
    return ((latest_close - first_close) / first_close) * 100


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


def _safe_int(value: object) -> int:
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _stringify_timestamp(value: object) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return str(value.isoformat())
    return str(value)


def _format_optional_number(value: float | None) -> str:
    if value is None:
        return "unavailable"
    return f"{value:.2f}"


def _format_context_value(value: object) -> str:
    numeric_value = _safe_float(value)
    if numeric_value is not None:
        return f"{numeric_value:.4g}"
    return str(value)


def _rollback_session_if_possible(session: Session | None) -> None:
    if session is None:
        return
    try:
        session.rollback()
    except Exception:
        return


def _build_news_evidence_item(
    symbol: str,
    item: dict[str, object],
    item_index: int,
) -> MarketAssistantResearchEvidence:
    title = str(item.get("title") or f"News item {item_index + 1}")
    url = _stringify_optional(item.get("url"))
    published_at = _stringify_optional(item.get("published_at")) or "unknown"
    provider_name = _stringify_optional(item.get("source")) or "news"
    summary = str(item.get("summary") or title)
    excerpt = _build_safe_excerpt(summary)
    stable_hash = _stable_short_hash(url or f"{published_at}:{title}:{item_index}")
    citation_id = f"news:{symbol}:{_citation_safe_token(published_at)}:{stable_hash}"
    citation = MarketAssistantCitation(
        id=citation_id,
        label=f"News for {symbol}: {title}",
        source="news",
        url=url,
        source_type="news",
        as_of=published_at,
        provider=provider_name,
        retrieved_at=_utc_now_isoformat(),
        excerpt=excerpt,
        metadata={
            "title": title,
            "sentiment": item.get("sentiment"),
            "confidence": item.get("confidence"),
        },
    )
    return MarketAssistantResearchEvidence(
        citation=citation,
        summary=excerpt,
        priority=40 + item_index,
        source_type="news",
        title=title,
        as_of=published_at,
        published_at=published_at,
        url=url,
        provider=provider_name,
        metadata=citation.metadata,
    )


def _build_generated_report_context(
    symbol: str,
    question: str,
    start: date,
    end: date,
    session: Session | None,
    diagnostics: list[dict[str, object]],
) -> tuple[str, list[MarketAssistantResearchEvidence]]:
    if session is None:
        diagnostics.append(
            {
                "source": "generated_reports",
                "status": "no_data",
                "severity": "info",
                "code": "SOURCE_NO_DATA",
                "message": "No database session is available for generated research reports.",
            }
        )
        return "No generated research reports are available.", []

    try:
        payload = list_reports_payload(
            session,
            symbol=symbol,
            report_type=None,
            query=None,
            as_of_start=start,
            as_of_end=end,
            limit=3,
            offset=0,
        )
    except Exception:
        _rollback_session_if_possible(session)
        diagnostics.append(
            {
                "source": "generated_reports",
                "status": "unavailable",
                "severity": "warning",
                "code": "SOURCE_UNAVAILABLE",
                "message": "Generated research reports could not be loaded.",
            }
        )
        return "Generated research reports could not be loaded.", []

    items = payload.get("items")
    if not isinstance(items, list) or not items:
        diagnostics.append(
            {
                "source": "generated_reports",
                "status": "no_data",
                "severity": "info",
                "code": "SOURCE_NO_DATA",
                "message": "No generated research reports are available for this symbol and date range.",
            }
        )
        return "No generated research reports are available.", []

    evidence_items = [
        _build_generated_report_evidence_item(symbol, question, item, item_index)
        for item_index, item in enumerate(items[:3])
        if isinstance(item, dict) and item.get("id")
    ]
    if not evidence_items:
        diagnostics.append(
            {
                "source": "generated_reports",
                "status": "no_data",
                "severity": "info",
                "code": "SOURCE_NO_DATA",
                "message": "Generated reports were found but could not be converted into research evidence.",
            }
        )
        return "Generated reports were found but could not be summarized.", []

    report_titles = [item.title for item in evidence_items if item.title]
    return f"Generated reports available: {'; '.join(report_titles)}.", evidence_items


def _build_research_source_note_context(
    symbol: str,
    session: Session | None,
    diagnostics: list[dict[str, object]],
) -> tuple[str, list[MarketAssistantResearchEvidence]]:
    if session is None:
        diagnostics.append(
            {
                "source": "research_source_notes",
                "status": "no_data",
                "severity": "info",
                "code": "SOURCE_NO_DATA",
                "message": "No database session is available for research source notes.",
            }
        )
        return "No reviewed source notebook entries were loaded.", []

    try:
        citations = list_citable_research_source_note_citations(
            session=session,
            symbols=[symbol],
            limit=3,
        )
    except Exception:
        _rollback_session_if_possible(session)
        diagnostics.append(
            {
                "source": "research_source_notes",
                "status": "unavailable",
                "severity": "warning",
                "code": "SOURCE_UNAVAILABLE",
                "message": "Reviewed source notebook entries could not be loaded.",
            }
        )
        return "Reviewed source notebook entries could not be loaded.", []

    if not citations:
        return "No reviewed source notebook entries are available for this symbol.", []

    evidence_items = [
        MarketAssistantResearchEvidence(
            citation=MarketAssistantCitation(
                id=str(citation["id"]),
                label=str(citation.get("label") or "Research source note"),
                source=str(citation.get("source") or "research_source_notes"),
                url=_stringify_optional(citation.get("url")),
                source_type=_stringify_optional(citation.get("source_type")),
                as_of=_stringify_optional(citation.get("as_of")),
                provider=_stringify_optional(citation.get("provider")),
                retrieved_at=_stringify_optional(citation.get("retrieved_at")),
                excerpt=_stringify_optional(citation.get("excerpt")),
                metadata=citation.get("metadata") if isinstance(citation.get("metadata"), dict) else None,
            ),
            summary=str(citation.get("excerpt") or citation.get("label") or "Reviewed source note."),
            priority=45 + item_index,
            source_type="research_source_note",
            title=_stringify_optional(citation.get("label")),
            as_of=_stringify_optional(citation.get("as_of")),
            url=_stringify_optional(citation.get("url")),
            provider=_stringify_optional(citation.get("provider")),
            metadata=citation.get("metadata") if isinstance(citation.get("metadata"), dict) else None,
        )
        for item_index, citation in enumerate(citations)
    ]
    titles = [item.title for item in evidence_items if item.title]
    return f"Reviewed source notebook entries available: {'; '.join(titles)}.", evidence_items


def _build_official_disclosure_context(
    symbol: str,
    session: Session | None,
    diagnostics: list[dict[str, object]],
) -> tuple[str, list[MarketAssistantResearchEvidence]]:
    if session is None:
        return "No official disclosure metadata was loaded.", []

    try:
        citations = list_citable_official_disclosure_citations(
            session=session,
            symbols=[symbol],
            limit=3,
        )
    except ValueError:
        return "Official A-share disclosure metadata is not applicable to this symbol.", []
    except Exception:
        _rollback_session_if_possible(session)
        diagnostics.append(
            {
                "source": "official_disclosures",
                "status": "unavailable",
                "severity": "warning",
                "code": "SOURCE_UNAVAILABLE",
                "message": "Official disclosure metadata could not be loaded.",
            }
        )
        return "Official disclosure metadata could not be loaded.", []

    if not citations:
        return "No persisted official disclosure metadata is available for this symbol.", []

    evidence_items = [
        MarketAssistantResearchEvidence(
            citation=MarketAssistantCitation(
                id=str(citation["id"]),
                label=str(citation.get("label") or "Official disclosure metadata"),
                source=str(citation.get("source") or "official_disclosures"),
                url=_stringify_optional(citation.get("url")),
                source_type=_stringify_optional(citation.get("source_type")),
                as_of=_stringify_optional(citation.get("as_of")),
                provider=_stringify_optional(citation.get("provider")),
                retrieved_at=_stringify_optional(citation.get("retrieved_at")),
                excerpt=_stringify_optional(citation.get("excerpt")),
                metadata=_optional_dict(citation.get("metadata")),
            ),
            summary=str(citation.get("excerpt") or citation.get("label") or "Official disclosure metadata."),
            priority=40 + item_index,
            source_type="official_disclosure",
            title=_stringify_optional(citation.get("label")),
            as_of=_stringify_optional(citation.get("as_of")),
            url=_stringify_optional(citation.get("url")),
            provider=_stringify_optional(citation.get("provider")),
            metadata=_optional_dict(citation.get("metadata")),
        )
        for item_index, citation in enumerate(citations)
    ]
    titles = [item.title for item in evidence_items if item.title]
    return (
        "Official disclosure metadata available (document bodies not ingested): "
        f"{'; '.join(titles)}.",
        evidence_items,
    )


def _build_official_disclosure_section_context(
    symbol: str,
    session: Session | None,
    diagnostics: list[dict[str, object]],
) -> tuple[str, list[MarketAssistantResearchEvidence]]:
    if session is None:
        return "No extracted official disclosure sections were loaded.", []
    try:
        citations = list_citable_official_disclosure_section_citations(
            session=session,
            symbols=[symbol],
            limit=4,
        )
    except ValueError:
        return "Official A-share disclosure sections are not applicable to this symbol.", []
    except Exception:
        _rollback_session_if_possible(session)
        diagnostics.append(
            {
                "source": "official_disclosure_sections",
                "status": "unavailable",
                "severity": "warning",
                "code": "SOURCE_UNAVAILABLE",
                "message": "Extracted official disclosure sections could not be loaded.",
            }
        )
        return "Extracted official disclosure sections could not be loaded.", []

    if not citations:
        return "No persisted extracted disclosure sections are available for this symbol.", []

    evidence_items = [
        MarketAssistantResearchEvidence(
            citation=MarketAssistantCitation(
                id=str(citation["id"]),
                label=str(citation.get("label") or "Official disclosure section"),
                source=str(citation.get("source") or "official_disclosure_sections"),
                url=_stringify_optional(citation.get("url")),
                source_type=_stringify_optional(citation.get("source_type")),
                as_of=_stringify_optional(citation.get("as_of")),
                provider=_stringify_optional(citation.get("provider")),
                retrieved_at=_stringify_optional(citation.get("retrieved_at")),
                excerpt=_stringify_optional(citation.get("excerpt")),
                metadata=_optional_dict(citation.get("metadata")),
            ),
            summary=str(citation.get("excerpt") or citation.get("label") or "Official disclosure section."),
            priority=35 + item_index,
            source_type="official_disclosure_section",
            title=_stringify_optional(citation.get("label")),
            as_of=_stringify_optional(citation.get("as_of")),
            url=_stringify_optional(citation.get("url")),
            provider=_stringify_optional(citation.get("provider")),
            metadata=_optional_dict(citation.get("metadata")),
        )
        for item_index, citation in enumerate(citations)
    ]
    return (
        f"Extracted official disclosure sections available: {len(evidence_items)} "
        "page-anchored excerpts.",
        evidence_items,
    )


def _build_market_daily_evidence_context(
    symbol: str,
    session: Session | None,
    diagnostics: list[dict[str, object]],
) -> tuple[str, list[MarketAssistantResearchEvidence]]:
    if session is None:
        return "No stored market daily evidence was loaded.", []

    try:
        citations = list_citable_market_daily_evidence_citations(
            session=session,
            symbols=[symbol],
            limit=5,
        )
    except Exception:
        _rollback_session_if_possible(session)
        diagnostics.append(
            {
                "source": "market_daily_evidence",
                "status": "unavailable",
                "severity": "warning",
                "code": "SOURCE_UNAVAILABLE",
                "message": "Stored market daily evidence could not be loaded.",
            }
        )
        return "Stored market daily evidence could not be loaded.", []

    if not citations:
        return "No stored market daily evidence is available for this symbol or current market context.", []

    evidence_items = [
        MarketAssistantResearchEvidence(
            citation=MarketAssistantCitation(
                id=str(citation["id"]),
                label=str(citation.get("label") or "Market daily evidence"),
                source=str(citation.get("source") or "market_daily_evidence"),
                source_type=_stringify_optional(citation.get("source_type")),
                as_of=_stringify_optional(citation.get("as_of")),
                provider=_stringify_optional(citation.get("provider")),
                retrieved_at=_stringify_optional(citation.get("retrieved_at")),
                excerpt=_stringify_optional(citation.get("excerpt")),
                metadata=citation.get("metadata") if isinstance(citation.get("metadata"), dict) else None,
            ),
            summary=str(citation.get("excerpt") or citation.get("label") or "Stored market daily evidence."),
            priority=42 + item_index,
            source_type="market_daily_event",
            title=_stringify_optional(citation.get("label")),
            as_of=_stringify_optional(citation.get("as_of")),
            provider=_stringify_optional(citation.get("provider")),
            metadata=citation.get("metadata") if isinstance(citation.get("metadata"), dict) else None,
        )
        for item_index, citation in enumerate(citations)
    ]
    labels = [item.title for item in evidence_items if item.title]
    return f"Stored market daily evidence available: {'; '.join(labels)}.", evidence_items


def _build_generated_report_evidence_item(
    symbol: str,
    question: str,
    item: dict[str, object],
    item_index: int,
) -> MarketAssistantResearchEvidence:
    report_id = str(item.get("id"))
    report_type = str(item.get("report_type") or "stock")
    as_of = _stringify_optional(item.get("as_of")) or "unknown"
    content_markdown = str(item.get("content_markdown") or "")
    excerpt = _build_safe_excerpt(content_markdown or question)
    title = f"{symbol} {report_type} report as of {as_of}"
    source_summary = item.get("source_summary")
    provider_name = _extract_report_provider(source_summary)
    citation = MarketAssistantCitation(
        id=f"generated_report:{report_id}",
        label=title,
        source="generated_reports",
        source_type="generated_report",
        as_of=as_of,
        provider=provider_name,
        retrieved_at=_stringify_optional(item.get("created_at")),
        excerpt=excerpt,
        metadata={
            "report_type": report_type,
            "task_run_id": item.get("task_run_id"),
            "source_citations": item.get("citations") if isinstance(item.get("citations"), list) else [],
        },
    )
    return MarketAssistantResearchEvidence(
        citation=citation,
        summary=excerpt,
        priority=50 + item_index,
        source_type="generated_report",
        title=title,
        as_of=as_of,
        provider=provider_name,
        metadata=citation.metadata,
    )


def _rank_research_citations(evidence_items: list[MarketAssistantResearchEvidence]) -> list[MarketAssistantCitation]:
    ranked_evidence_items = sorted(evidence_items, key=lambda item: (item.priority, item.citation.id))
    citations_by_id: dict[str, MarketAssistantCitation] = {}
    for evidence_item in ranked_evidence_items:
        citations_by_id.setdefault(evidence_item.citation.id, evidence_item.citation)
    return list(citations_by_id.values())


def _extract_unknown_inline_citation_ids(
    answer_markdown: str,
    citations: list[MarketAssistantCitation],
) -> list[str]:
    known_citation_ids = {citation.id for citation in citations}
    extracted_citation_ids = {
        candidate
        for candidate in ASSISTANT_CITATION_ID_PATTERN.findall(answer_markdown)
        if candidate.startswith(ASSISTANT_CITATION_ID_PREFIXES)
    }
    return sorted(extracted_citation_ids - known_citation_ids)


def _extract_report_provider(source_summary: object) -> str | None:
    if isinstance(source_summary, dict):
        return _stringify_optional(source_summary.get("source") or source_summary.get("provider"))
    return None


def _build_safe_excerpt(value: str, max_length: int = 280) -> str:
    normalized_value = " ".join(value.split())
    if len(normalized_value) <= max_length:
        return normalized_value
    return f"{normalized_value[: max_length - 3].rstrip()}..."


def _stringify_optional(value: object) -> str | None:
    if value is None:
        return None
    value_text = str(value).strip()
    return value_text or None


def _optional_dict(value: object) -> dict[str, object] | None:
    return value if isinstance(value, dict) else None


def _stable_short_hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]


def _citation_safe_token(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "-", value).strip("-") or "unknown"


def _utc_now_isoformat() -> str:
    return datetime.now(timezone.utc).isoformat()
