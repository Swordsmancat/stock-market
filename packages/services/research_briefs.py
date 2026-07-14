from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from packages.ai.llm_factory import get_llm_provider
from packages.domain.models import ResearchBrief
from packages.services.market_dashboard import get_market_overview_payload
from packages.services.platform_settings import get_platform_settings, normalize_llm_model


RESEARCH_BRIEF_FALLBACK_MODEL_NAME = "research-brief-deterministic-fallback"
RESEARCH_BRIEF_CITATION_ID_PATTERN = re.compile(r"\[([A-Za-z0-9_:\-./+]+)\]")
RESEARCH_BRIEF_CITATION_ID_PREFIXES = (
    "market_indicator:",
    "generated_report:",
    "news:",
    "research_source_note:",
    "market_daily_event:",
)
DEFAULT_BRIEF_LIMIT = 20
MAX_PROMPT_CHARS = 8000


@dataclass(frozen=True)
class ResearchBriefGenerateInput:
    provider_name: str | None = None
    locale: str = "en"
    title: str | None = None


def generate_and_store_research_brief(
    payload: ResearchBriefGenerateInput,
    *,
    session: Session,
) -> dict[str, object]:
    normalized = _normalize_generate_input(payload)
    generated_at = datetime.now(timezone.utc)
    market_overview = get_market_overview_payload(
        session=session,
        provider_name=normalized.provider_name,
    )
    assembled = _assemble_research_brief_context(
        market_overview=market_overview,
        generated_at=generated_at,
        input_payload=normalized,
    )
    generated = _generate_research_brief_content(assembled)
    title = normalized.title or _default_title(generated_at, normalized.locale)

    brief = ResearchBrief(
        title=title,
        brief_type="evidence_center",
        scope_json=assembled["scope"],
        content_markdown=generated["content_markdown"],
        citations_json=assembled["citations"],
        source_summary_json=assembled["source_summary"],
        diagnostics_json=generated["diagnostics"],
        model_json=generated["model"],
        safety_json=_safety_payload(),
    )
    session.add(brief)
    session.commit()
    session.refresh(brief)

    serialized = serialize_research_brief(brief)
    serialized["status"] = "stored"
    return serialized


def list_research_briefs(
    *,
    session: Session,
    limit: int = DEFAULT_BRIEF_LIMIT,
) -> dict[str, object]:
    bounded_limit = max(1, min(limit, 100))
    query = session.query(ResearchBrief)
    total = query.count()
    items = query.order_by(ResearchBrief.created_at.desc()).limit(bounded_limit).all()
    return {
        "items": [serialize_research_brief(item) for item in items],
        "summary": {
            "total": total,
            "returned": len(items),
        },
    }


def serialize_research_brief(brief: ResearchBrief) -> dict[str, object]:
    return {
        "id": str(brief.id),
        "title": brief.title,
        "brief_type": brief.brief_type,
        "scope": brief.scope_json or {},
        "content_markdown": brief.content_markdown,
        "citations": brief.citations_json or [],
        "source_summary": brief.source_summary_json or {},
        "diagnostics": brief.diagnostics_json or [],
        "model": brief.model_json or {},
        "safety": brief.safety_json or {},
        "created_at": brief.created_at.isoformat(),
    }


def _normalize_generate_input(payload: ResearchBriefGenerateInput) -> ResearchBriefGenerateInput:
    return ResearchBriefGenerateInput(
        provider_name=_clean(payload.provider_name),
        locale="zh" if payload.locale == "zh" else "en",
        title=_clip_text(_clean(payload.title), 180),
    )


def _default_title(generated_at: datetime, locale: str) -> str:
    timestamp = generated_at.strftime("%Y-%m-%d %H:%M UTC")
    if locale == "zh":
        return f"Evidence Center AI 摘要 {timestamp}"
    return f"Evidence Center research brief {timestamp}"


def _assemble_research_brief_context(
    *,
    market_overview: dict[str, object],
    generated_at: datetime,
    input_payload: ResearchBriefGenerateInput,
) -> dict[str, object]:
    dashboard_brief = _dict_value(market_overview.get("dashboard_brief"))
    information_sources = _dict_value(market_overview.get("information_sources"))
    follow_up_queue = _dict_value(market_overview.get("research_follow_up_queue"))
    citations = _dict_list(dashboard_brief.get("citations"))
    source_gaps = _extract_source_gaps(information_sources)
    follow_up_items = _dict_list(follow_up_queue.get("items"))
    diagnostics = [
        *_dict_list(dashboard_brief.get("diagnostics")),
        *_dict_list(follow_up_queue.get("diagnostics")),
    ]
    source_summary = {
        "generated_at": generated_at.isoformat(),
        "dashboard_status": dashboard_brief.get("status"),
        "citation_count": len(citations),
        "source_mix": _build_source_mix(citations=citations, information_sources=information_sources),
        "source_gap_count": len(source_gaps),
        "source_gaps": _summarize_source_gaps(source_gaps),
        "follow_up_summary": follow_up_queue.get("summary") if isinstance(follow_up_queue.get("summary"), dict) else {},
        "follow_up_items": _summarize_follow_up_items(follow_up_items),
    }
    return {
        "scope": {
            "kind": "evidence_center",
            "provider": input_payload.provider_name,
            "locale": input_payload.locale,
            "market_overview_generated_at": market_overview.get("generated_at"),
        },
        "dashboard_brief": dashboard_brief,
        "information_sources": information_sources,
        "research_follow_up_queue": follow_up_queue,
        "citations": citations,
        "source_gaps": source_gaps,
        "follow_up_items": follow_up_items,
        "diagnostics": diagnostics,
        "source_summary": source_summary,
    }


def _generate_research_brief_content(context: dict[str, object]) -> dict[str, object]:
    fallback_content = _build_fallback_content(context)

    def fallback(reason: str, extra_diagnostics: list[dict[str, object]] | None = None) -> dict[str, object]:
        diagnostics = [*_dict_list(context.get("diagnostics"))]
        diagnostics.extend(extra_diagnostics or [])
        diagnostics.append(
            {
                "source": "research_brief",
                "status": "fallback",
                "severity": "info",
                "code": "RESEARCH_BRIEF_FALLBACK_USED",
                "message": "The research brief used deterministic fallback instead of an LLM answer.",
                "details": {"reason": reason},
            }
        )
        return {
            "content_markdown": fallback_content,
            "diagnostics": diagnostics,
            "model": _model_payload(
                provider="deterministic",
                name=RESEARCH_BRIEF_FALLBACK_MODEL_NAME,
                used_llm=False,
                fallback_reason=reason,
            ),
        }

    settings = get_platform_settings()
    configured_provider = str(settings.get("llm_provider", "mock")).lower()
    configured_api_key = str(settings.get("llm_api_key", "")).strip()
    configured_model = normalize_llm_model(settings.get("llm_model"))
    if configured_provider != "openai" or not configured_api_key:
        return fallback("OpenAI-compatible LLM provider is not configured.")

    try:
        answer = get_llm_provider(settings).generate(_build_llm_prompt(context)).strip()
    except Exception as error:
        return fallback(f"LLM generation failed: {error.__class__.__name__}.")

    if not answer:
        return fallback("LLM generation returned an empty answer.")

    unknown_ids = _extract_unknown_citation_ids(answer_markdown=answer, citations=_dict_list(context.get("citations")))
    if unknown_ids:
        return fallback(
            "LLM citation validation failed: unknown citation id.",
            [
                {
                    "source": "citations",
                    "status": "invalid",
                    "severity": "warning",
                    "code": "CITATION_UNKNOWN_ID",
                    "message": "The LLM research brief referenced citation IDs that were not present in the assembled evidence.",
                    "details": {"unknown_ids": unknown_ids},
                }
            ],
        )

    return {
        "content_markdown": answer,
        "diagnostics": _dict_list(context.get("diagnostics")),
        "model": _model_payload(
            provider="openai",
            name=configured_model,
            used_llm=True,
            fallback_reason=None,
        ),
    }


def _build_fallback_content(context: dict[str, object]) -> str:
    dashboard_brief = _dict_value(context.get("dashboard_brief"))
    sections = _dict_list(dashboard_brief.get("sections"))
    citations = _dict_list(context.get("citations"))
    source_gaps = _dict_list(context.get("source_gaps"))
    follow_up_items = _dict_list(context.get("follow_up_items"))

    summary_lines = _section_lines(sections, "what_changed") or [
        "No dashboard change summary is available yet."
    ]
    evidence_lines = _format_citation_lines(citations)
    gap_lines = _format_source_gap_lines(source_gaps)
    question_lines = _format_follow_up_lines(follow_up_items)

    return "\n".join(
        [
            "### Summary",
            *[f"- {line}" for line in summary_lines[:4]],
            "",
            "### Key Evidence",
            *evidence_lines,
            "",
            "### Source And Data Gaps",
            *gap_lines,
            "",
            "### Suggested Research Questions",
            *question_lines,
            "",
            "### Safety Note",
            (
                "- This saved brief is a personal research record for information aggregation only. "
                "It is not investment advice, a buy/sell/hold call, a target price, position sizing, "
                "or an execution instruction."
            ),
        ]
    )


def _build_llm_prompt(context: dict[str, object]) -> str:
    prompt = (
        "You are writing a saved research brief for a personal financial information aggregation workspace.\n"
        "Summarize only the structured context below. Do not invent market data, macro observations, filings, "
        "source adapters, URLs, dates, target prices, buy/sell/hold calls, position sizing, or execution instructions.\n"
        "Use only citation IDs listed under Allowed citations. Treat source gaps and follow-up queue items as "
        "research prompts or missing data, not as evidence unless they include an allowed citation ID.\n"
        "Write concise markdown with sections: Summary, Key Evidence, Source And Data Gaps, Suggested Research "
        "Questions, Safety Note.\n\n"
        f"Dashboard brief sections:\n{_format_section_lines(_dict_list(_dict_value(context.get('dashboard_brief')).get('sections')))}\n\n"
        f"Allowed citations:\n{_format_prompt_citation_lines(_dict_list(context.get('citations')))}\n\n"
        f"Source gaps:\n{_format_prompt_source_gap_lines(_dict_list(context.get('source_gaps')))}\n\n"
        f"Research follow-up queue:\n{_format_prompt_follow_up_lines(_dict_list(context.get('follow_up_items')))}\n\n"
        f"Source summary:\n{context.get('source_summary')}"
    )
    return _clip_text(prompt, MAX_PROMPT_CHARS) or prompt


def _extract_unknown_citation_ids(
    *,
    answer_markdown: str,
    citations: list[dict[str, object]],
) -> list[str]:
    known_citation_ids = {str(citation.get("id")) for citation in citations if citation.get("id")}
    extracted_citation_ids = {
        candidate
        for candidate in RESEARCH_BRIEF_CITATION_ID_PATTERN.findall(answer_markdown)
        if candidate.startswith(RESEARCH_BRIEF_CITATION_ID_PREFIXES)
    }
    return sorted(extracted_citation_ids - known_citation_ids)


def _build_source_mix(
    *,
    citations: list[dict[str, object]],
    information_sources: dict[str, object],
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
        "research_source_note_citations": sum(
            1
            for citation in citations
            if citation.get("source") == "research_source_notes"
            or citation.get("source_type") == "research_source_note"
        ),
        "market_daily_citations": sum(
            1
            for citation in citations
            if citation.get("source") == "market_daily_evidence"
            or citation.get("source_type") == "market_daily_event"
        ),
        "information_source_gaps": len(_extract_source_gaps(information_sources)),
    }


def _extract_source_gaps(information_sources: dict[str, object]) -> list[dict[str, object]]:
    items = information_sources.get("items")
    if not isinstance(items, list):
        return []
    gap_statuses = {"needs_adapter", "needs_manual_seed", "no_data", "future"}
    return [item for item in items if isinstance(item, dict) and str(item.get("status") or "") in gap_statuses]


def _summarize_source_gaps(items: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "id": item.get("id"),
            "label": item.get("label"),
            "status": item.get("status"),
            "next_action": item.get("next_action"),
        }
        for item in items[:12]
    ]


def _summarize_follow_up_items(items: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "id": item.get("id"),
            "kind": item.get("kind"),
            "priority": item.get("priority"),
            "title": item.get("title") or item.get("note_title") or item.get("source_label"),
            "prompt": item.get("prompt"),
            "citation_policy": item.get("citation_policy"),
            "citation_id": item.get("citation_id"),
        }
        for item in items[:12]
    ]


def _section_lines(sections: list[dict[str, object]], section_id: str) -> list[str]:
    for section in sections:
        if str(section.get("id") or "") != section_id:
            continue
        items = section.get("items")
        return [str(item) for item in items if isinstance(item, str)] if isinstance(items, list) else []
    return []


def _format_citation_lines(citations: list[dict[str, object]]) -> list[str]:
    if not citations:
        return ["- No citable local evidence is available yet."]
    lines: list[str] = []
    for citation in citations[:8]:
        citation_id = citation.get("id")
        if not citation_id:
            continue
        label = citation.get("label") or citation_id
        as_of = citation.get("as_of") or "date unavailable"
        lines.append(f"- {label} [{citation_id}] as of {as_of}.")
    return lines or ["- No citable local evidence is available yet."]


def _format_source_gap_lines(source_gaps: list[dict[str, object]]) -> list[str]:
    if not source_gaps:
        return ["- No source-readiness gaps were reported in the current context."]
    lines = []
    for item in source_gaps[:8]:
        label = item.get("label") or item.get("id") or "Source"
        next_action = item.get("next_action") or "Review source readiness before using it in AI context."
        lines.append(f"- {label}: {item.get('status') or 'gap'}; {next_action}")
    return lines


def _format_follow_up_lines(items: list[dict[str, object]]) -> list[str]:
    question_items = [
        item
        for item in items
        if item.get("kind") in {"ai_summary_question", "source_review", "seed_prep", "source_gap"}
    ]
    if not question_items:
        return ["- No research follow-up questions are queued yet."]
    lines = []
    for item in question_items[:6]:
        prompt = item.get("prompt") or item.get("next_action") or item.get("title") or item.get("id")
        policy = item.get("citation_policy") or "not_citable"
        lines.append(f"- {prompt} ({policy})")
    return lines


def _format_section_lines(sections: list[dict[str, object]]) -> str:
    lines: list[str] = []
    for section in sections:
        title = section.get("title") or section.get("id") or "Section"
        lines.append(f"{title}:")
        items = section.get("items")
        if isinstance(items, list):
            lines.extend(f"- {item}" for item in items[:6] if isinstance(item, str))
    return "\n".join(lines) or "- No dashboard sections are available."


def _format_prompt_citation_lines(citations: list[dict[str, object]]) -> str:
    if not citations:
        return "- No allowed citation IDs are available."
    lines: list[str] = []
    for citation in citations[:12]:
        citation_id = citation.get("id")
        if not citation_id:
            continue
        lines.append(
            "- "
            f"[{citation_id}] {citation.get('label') or citation_id} | "
            f"source={citation.get('source') or citation.get('source_type') or 'unknown'} | "
            f"as_of={citation.get('as_of') or 'unavailable'}"
        )
    return "\n".join(lines) or "- No allowed citation IDs are available."


def _format_prompt_source_gap_lines(items: list[dict[str, object]]) -> str:
    lines = [
        f"- {item.get('label') or item.get('id')}: status={item.get('status')}; next_action={item.get('next_action')}"
        for item in items[:12]
    ]
    return "\n".join(lines) or "- No source gaps were reported."


def _format_prompt_follow_up_lines(items: list[dict[str, object]]) -> str:
    lines = [
        "- "
        f"{item.get('kind')}: {item.get('prompt') or item.get('next_action') or item.get('title')} "
        f"| citation_policy={item.get('citation_policy')} | citation_id={item.get('citation_id') or 'none'}"
        for item in items[:12]
    ]
    return "\n".join(lines) or "- No follow-up items were reported."


def _model_payload(
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


def _safety_payload() -> dict[str, bool]:
    return {
        "not_investment_advice": True,
        "no_buy_sell_hold": True,
        "no_target_price": True,
        "no_position_sizing": True,
        "no_automated_trading": True,
        "no_fabricated_macro_data": True,
    }


def _dict_value(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _dict_list(value: object) -> list[dict[str, object]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _clean(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _clip_text(value: str | None, limit: int) -> str | None:
    if value is None or len(value) <= limit:
        return value
    return value[:limit].rstrip()
