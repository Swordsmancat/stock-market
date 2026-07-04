from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from packages.ai.llm_factory import get_llm_provider
from packages.ai.market_assistant import (
    ASSISTANT_MODEL_NAME,
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
from packages.services.news import get_news_sentiment_payload
from packages.services.platform_settings import get_platform_settings


DEFAULT_ASSISTANT_LOOKBACK_DAYS = 180
SUPPORTED_ASSISTANT_SCOPE = "instrument"
SUPPORTED_ASSISTANT_TIMEFRAME = "1d"


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
    )
    bar_items = _extract_bar_items(bars_payload)
    diagnostics: list[dict[str, str]] = []

    if not bar_items:
        diagnostics.append(
            {
                "source": "bars_1d",
                "status": "no_data",
                "message": "No verified daily bars are available for the requested symbol and date range.",
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
            citations=[],
            diagnostics=diagnostics,
        )
        return _build_response_payload(
            status="no_data",
            symbol=normalized_symbol,
            prompt_context=prompt_context,
            answer_markdown=build_deterministic_market_answer(prompt_context),
            model_metadata=_build_fallback_model_metadata("No verified daily bars are available."),
            bars_payload=bars_payload,
        )

    price_context = _build_price_context(normalized_symbol, timeframe, effective_start, effective_end, bar_items)
    indicator_summary = _build_indicator_summary(normalized_symbol, session, diagnostics)
    fundamental_summary = _build_fundamental_summary(normalized_symbol, effective_end, session, diagnostics)
    news_summary = _build_news_summary(normalized_symbol, session, diagnostics)

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
        fundamental_summary=fundamental_summary,
        news_summary=news_summary,
        citations=price_context["citations"],
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


def _extract_bar_items(bars_payload: dict[str, object]) -> list[dict[str, object]]:
    raw_items = bars_payload.get("items")
    if not isinstance(raw_items, list):
        return []
    return [item for item in raw_items if isinstance(item, dict)]


def _build_price_context(
    symbol: str,
    timeframe: str,
    start: date,
    end: date,
    bar_items: list[dict[str, object]],
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
    citations = [
        MarketAssistantCitation(
            id=f"bars_1d:{symbol}:{as_of}",
            label=f"Daily bars for {symbol} as of {as_of}",
            source=f"bars_{timeframe}",
        )
    ]
    return {
        "as_of": as_of,
        "latest_close": latest_close,
        "period_change_pct": period_change_pct,
        "bar_count": len(bar_items),
        "price_summary": price_summary,
        "citations": citations,
    }


def _build_indicator_summary(symbol: str, session: Session | None, diagnostics: list[dict[str, str]]) -> str:
    if session is None:
        diagnostics.append(
            {
                "source": "indicators",
                "status": "no_data",
                "message": "No database session is available for stored technical indicators.",
            }
        )
        return "No stored technical indicators are available."

    try:
        payload = get_stored_indicators_payload(symbol, session)
    except Exception:
        _rollback_session_if_possible(session)
        diagnostics.append(
            {
                "source": "indicators",
                "status": "unavailable",
                "message": "Stored technical indicators could not be loaded.",
            }
        )
        return "Stored technical indicators could not be loaded."

    indicators = payload.get("indicators")
    if not isinstance(indicators, dict) or not indicators:
        diagnostics.append(
            {
                "source": "indicators",
                "status": "no_data",
                "message": "No stored technical indicators are available for this symbol.",
            }
        )
        return "No stored technical indicators are available."

    formatted_values = [
        f"{indicator_code}={_format_context_value(indicator_value)}"
        for indicator_code, indicator_value in sorted(indicators.items())[:8]
    ]
    return ", ".join(formatted_values)


def _build_fundamental_summary(
    symbol: str,
    as_of: date,
    session: Session | None,
    diagnostics: list[dict[str, str]],
) -> str:
    try:
        payload = get_fundamental_payload(symbol, as_of=as_of, session=session)
    except Exception:
        _rollback_session_if_possible(session)
        diagnostics.append(
            {
                "source": "fundamentals",
                "status": "unavailable",
                "message": "Fundamental metrics could not be loaded.",
            }
        )
        return "Fundamental metrics could not be loaded."

    item = payload.get("item")
    if not isinstance(item, dict) or not item:
        diagnostics.append(
            {
                "source": "fundamentals",
                "status": "no_data",
                "message": "No fundamental snapshot is available for this symbol.",
            }
        )
        return "No fundamental snapshot is available."

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
    return ", ".join(formatted_values) if formatted_values else "Fundamental snapshot is present but empty."


def _build_news_summary(symbol: str, session: Session | None, diagnostics: list[dict[str, str]]) -> str:
    if session is None:
        diagnostics.append(
            {
                "source": "news",
                "status": "no_data",
                "message": "No database session is available for news sentiment.",
            }
        )
        return "No stored news sentiment is available."

    try:
        payload = get_news_sentiment_payload(symbol, session)
    except Exception:
        _rollback_session_if_possible(session)
        diagnostics.append(
            {
                "source": "news",
                "status": "unavailable",
                "message": "News sentiment could not be loaded.",
            }
        )
        return "News sentiment could not be loaded."

    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    article_count = _safe_int(summary.get("article_count")) if isinstance(summary, dict) else 0
    latest_sentiment = summary.get("latest_sentiment") if isinstance(summary, dict) else None
    if article_count <= 0:
        diagnostics.append(
            {
                "source": "news",
                "status": "no_data",
                "message": "No stored news sentiment is available for this symbol.",
            }
        )
        return "No stored news sentiment is available."

    items = payload.get("items")
    article_titles = [
        str(item.get("title"))
        for item in items[:3]
        if isinstance(item, dict) and item.get("title")
    ] if isinstance(items, list) else []
    title_summary = f" Recent titles: {'; '.join(article_titles)}." if article_titles else ""
    return f"Latest sentiment {latest_sentiment}; article count {article_count}.{title_summary}"


def _generate_answer_or_fallback(
    prompt_context: MarketAssistantPromptContext,
) -> tuple[str, dict[str, object]]:
    settings = get_platform_settings()
    configured_provider = str(settings.get("llm_provider", "mock")).lower()
    configured_api_key = str(settings.get("llm_api_key", "")).strip()
    if configured_provider != "openai" or not configured_api_key:
        fallback_reason = "OpenAI-compatible LLM provider is not configured."
        return build_deterministic_market_answer(prompt_context), _build_fallback_model_metadata(fallback_reason)

    try:
        llm_provider = get_llm_provider()
        generated_answer = llm_provider.generate(build_market_assistant_prompt(prompt_context)).strip()
    except Exception as error:
        fallback_reason = f"LLM generation failed: {error.__class__.__name__}."
        return build_deterministic_market_answer(prompt_context), _build_fallback_model_metadata(fallback_reason)

    if not generated_answer:
        fallback_reason = "LLM generation returned an empty answer."
        return build_deterministic_market_answer(prompt_context), _build_fallback_model_metadata(fallback_reason)

    return generated_answer, {
        "provider": "openai",
        "name": ASSISTANT_MODEL_NAME,
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
            "fundamental_summary": prompt_context.fundamental_summary,
            "news_summary": prompt_context.news_summary,
            "source": bars_payload.get("source"),
            "provider": bars_payload.get("provider"),
            "requested_provider": bars_payload.get("requested_provider"),
            "effective_provider": bars_payload.get("effective_provider"),
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
