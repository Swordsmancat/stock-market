from sqlalchemy.orm import Session

from packages.ai.llm_factory import get_llm_provider
from packages.ai.stock_discovery import (
    SHORTLIST_FALLBACK_MODEL_NAME,
    SHORTLIST_MODEL_NAME,
    build_deterministic_stock_discovery_explanation,
    build_stock_discovery_prompt,
    unknown_stock_discovery_citations,
    unknown_stock_discovery_symbols,
)
from packages.services.platform_settings import get_platform_settings
from packages.services.stock_selection import screen_local_stock_selection
from packages.services.stock_selection_profiles import resolve_stock_selection_profile


def discover_local_stocks(
    *,
    session: Session,
    profile_id: str = "balanced_research",
    overrides: dict[str, object] | None = None,
    market: str = "CN",
    asset_type: str = "stock",
    watchlist_only: bool = False,
    shortlist_limit: int = 10,
    locale: str = "zh",
    use_llm: bool = True,
) -> dict[str, object]:
    resolved = resolve_stock_selection_profile(profile_id, overrides)
    effective_criteria = resolved["effective_criteria"]
    if not isinstance(effective_criteria, dict):
        raise RuntimeError("Resolved stock-selection criteria are invalid.")
    bounded_limit = max(1, min(shortlist_limit, 20))
    selection = screen_local_stock_selection(
        session=session,
        market=market,
        asset_type=asset_type,
        watchlist_only=watchlist_only,
        limit=bounded_limit,
        **effective_criteria,
    )
    shortlist = selection["items"]
    if not isinstance(shortlist, list):
        shortlist = []
    citations = _shortlist_citations(shortlist)
    diagnostics = list(selection.get("diagnostics", []))
    explanation, model = _generate_explanation_or_fallback(
        locale="en" if locale == "en" else "zh",
        resolved=resolved,
        effective_criteria=effective_criteria,
        shortlist=shortlist,
        citations=citations,
        diagnostics=diagnostics,
        use_llm=use_llm,
    )
    return {
        "status": "no_matches" if not shortlist else ("ok" if model["used_llm"] else "degraded"),
        "profile": resolved["profile"],
        "default_criteria": resolved["default_criteria"],
        "overrides": resolved["overrides"],
        "effective_criteria": effective_criteria,
        "candidate_scope": selection["candidate_scope"],
        "coverage": selection.get("coverage"),
        "shortlist": shortlist,
        "shortlist_count": len(shortlist),
        "explanation_markdown": explanation,
        "citations": citations,
        "diagnostics": diagnostics,
        "model": model,
        "safety": {
            "research_signal_only": True,
            "deterministic_shortlist": True,
            "ai_cannot_change_membership_or_ranking": True,
            "not_investment_advice": True,
            "no_automated_trading": True,
        },
    }


def _generate_explanation_or_fallback(
    *,
    locale: str,
    resolved: dict[str, object],
    effective_criteria: dict[str, object],
    shortlist: list[dict[str, object]],
    citations: list[dict[str, object]],
    diagnostics: list[dict[str, object]],
    use_llm: bool,
) -> tuple[str, dict[str, object]]:
    fallback = build_deterministic_stock_discovery_explanation(
        locale=locale,
        profile=resolved["profile"],
        shortlist=shortlist,
    )
    if not shortlist:
        return fallback, _fallback_model("No candidates matched the deterministic criteria.")
    if not use_llm:
        return fallback, _fallback_model("LLM explanation was disabled for this request.")

    settings = get_platform_settings()
    configured_provider = str(settings.get("llm_provider", "mock")).lower()
    configured_api_key = str(settings.get("llm_api_key", "")).strip()
    if configured_provider != "openai" or not configured_api_key:
        return fallback, _fallback_model("OpenAI-compatible LLM provider is not configured.")

    try:
        generated = get_llm_provider().generate(
            build_stock_discovery_prompt(
                locale=locale,
                profile=resolved["profile"],
                effective_criteria=effective_criteria,
                shortlist=shortlist,
                citations=citations,
            )
        ).strip()
    except Exception as exc:
        reason = f"LLM generation failed: {type(exc).__name__}."
        diagnostics.append(_fallback_diagnostic(reason))
        return fallback, _fallback_model(reason)
    if not generated:
        reason = "LLM generation returned an empty explanation."
        diagnostics.append(_fallback_diagnostic(reason))
        return fallback, _fallback_model(reason)

    citation_ids = {str(citation["id"]) for citation in citations}
    unknown_citations = unknown_stock_discovery_citations(generated, citation_ids)
    if unknown_citations:
        reason = "LLM citation validation failed: unknown citation id."
        diagnostics.append(
            {
                "source": "citations",
                "status": "invalid",
                "code": "CITATION_UNKNOWN_ID",
                "message": reason,
                "details": {"unknown_ids": unknown_citations},
            }
        )
        return fallback, _fallback_model(reason)

    symbols = {str(item["symbol"]) for item in shortlist if item.get("symbol")}
    unknown_symbols = unknown_stock_discovery_symbols(generated, symbols)
    if unknown_symbols:
        reason = "LLM shortlist validation failed: unknown candidate symbol."
        diagnostics.append(
            {
                "source": "shortlist",
                "status": "invalid",
                "code": "SHORTLIST_UNKNOWN_SYMBOL",
                "message": reason,
                "details": {"unknown_symbols": unknown_symbols},
            }
        )
        return fallback, _fallback_model(reason)

    return generated, {
        "provider": "openai",
        "name": SHORTLIST_MODEL_NAME,
        "used_llm": True,
        "fallback_reason": None,
    }


def _shortlist_citations(shortlist: list[dict[str, object]]) -> list[dict[str, object]]:
    citations: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in shortlist:
        symbol = str(item.get("symbol") or "")
        citation_ids = item.get("evidence_citations")
        if not isinstance(citation_ids, list):
            continue
        for citation_id in citation_ids:
            if not isinstance(citation_id, str) or citation_id in seen:
                continue
            seen.add(citation_id)
            citations.append(
                {
                    "id": citation_id,
                    "symbol": symbol,
                    "source_type": citation_id.split(":", 1)[0],
                    "label": citation_id,
                }
            )
    return citations


def _fallback_model(reason: str) -> dict[str, object]:
    return {
        "provider": "deterministic",
        "name": SHORTLIST_FALLBACK_MODEL_NAME,
        "used_llm": False,
        "fallback_reason": reason,
    }


def _fallback_diagnostic(reason: str) -> dict[str, object]:
    return {
        "source": "stock_discovery_model",
        "status": "fallback",
        "code": "FALLBACK_USED",
        "message": "The deterministic shortlist explanation was used.",
        "details": {"reason": reason},
    }
