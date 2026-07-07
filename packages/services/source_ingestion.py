from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from packages.ai.llm_factory import get_llm_provider
from packages.services.platform_settings import get_platform_settings


SOURCE_INGESTION_LLM_MODEL_NAME = "gpt-4o-mini"
SOURCE_INGESTION_FALLBACK_MODEL_NAME = "source-ingestion-deterministic-fallback"
MAX_CONTENT_CHARS = 12000
MAX_PROMPT_CONTENT_CHARS = 6000
MAX_SUMMARY_CHARS = 700
MAX_FIELD_CHARS = 500
MAX_LIST_ITEMS = 8

URL_PATTERN = re.compile(r"https?://[^\s)>\]}\"']+")
DATE_PATTERN = re.compile(r"\b(?:20\d{2}|19\d{2})[-/.](?:0?[1-9]|1[0-2])[-/.](?:0?[1-9]|[12]\d|3[01])\b")
YEAR_PATTERN = re.compile(r"\b(?:20\d{2}|19\d{2})\b")

INDICATOR_KEYWORDS: tuple[dict[str, object], ...] = (
    {
        "label": "Buffett Indicator",
        "code": "buffett_indicator_us",
        "keywords": ("buffett", "market cap", "market capitalization", "gdp"),
        "tags": ("valuation", "buffett_indicator"),
    },
    {
        "label": "Market capitalization",
        "code": "market_cap",
        "keywords": ("market cap", "market capitalization"),
        "tags": ("valuation", "market_cap"),
    },
    {
        "label": "GDP",
        "code": "gdp",
        "keywords": ("gdp", "gross domestic product"),
        "tags": ("macro", "gdp"),
    },
    {
        "label": "CPI / inflation",
        "code": "us_cpi_yoy",
        "keywords": ("cpi", "inflation", "consumer price"),
        "tags": ("macro", "inflation"),
    },
    {
        "label": "M2 liquidity",
        "code": "us_m2_yoy",
        "keywords": ("us m2", "m2sl", "us money supply"),
        "tags": ("macro", "liquidity"),
    },
    {
        "label": "China M2",
        "code": "cn_m2_yoy",
        "keywords": ("pboc", "china m2", "cn m2", "monetary statistics"),
        "tags": ("macro", "china", "liquidity"),
    },
    {
        "label": "US 10Y yield",
        "code": "us_10y_yield",
        "keywords": ("10y", "10-year", "dgs10", "treasury yield"),
        "tags": ("macro", "rates"),
    },
    {
        "label": "US 2Y yield",
        "code": "us_2y_yield",
        "keywords": ("2y", "2-year", "dgs2"),
        "tags": ("macro", "rates"),
    },
    {
        "label": "10Y-2Y spread",
        "code": "us_10y_2y_spread",
        "keywords": ("t10y2y", "yield spread", "10y 2y", "10-year 2-year"),
        "tags": ("macro", "yield_curve"),
    },
    {
        "label": "SEC filing context",
        "code": "filing_note",
        "keywords": ("10-k", "10-q", "8-k", "sec", "filing", "edgar"),
        "tags": ("filing", "documents"),
    },
)


@dataclass(frozen=True)
class SourceIngestionExtractionInput:
    content: str
    filename: str | None = None
    source_url: str | None = None
    source_id: str | None = None
    source_label: str | None = None
    source_category: str | None = None
    target_indicator_codes: list[str] | None = None
    component_role: str | None = None
    locale: str = "en"


def extract_source_ingestion_payload(payload: SourceIngestionExtractionInput) -> dict[str, object]:
    normalized = _normalize_input(payload)
    content = normalized.content
    if len(content) < 8:
        return _invalid_input_payload("Content is required before source extraction.")

    fallback = _build_fallback_payload(normalized)
    settings = get_platform_settings()
    provider_name = str(settings.get("llm_provider", "mock")).lower()
    api_key = str(settings.get("llm_api_key", "")).strip()
    if provider_name != "openai" or not api_key:
        return _with_fallback_model(
            fallback,
            "OpenAI-compatible LLM provider is not configured.",
        )

    try:
        answer = get_llm_provider().generate(_build_llm_prompt(normalized)).strip()
    except Exception as error:
        return _with_fallback_model(
            fallback,
            f"LLM extraction failed: {error.__class__.__name__}.",
        )

    if not answer:
        return _with_fallback_model(fallback, "LLM extraction returned an empty answer.")

    parsed = _parse_json_object(answer)
    normalized_llm = _normalize_llm_payload(parsed, normalized)
    if normalized_llm is None:
        return _with_fallback_model(fallback, "LLM extraction returned invalid JSON.")

    normalized_llm["status"] = "ok"
    normalized_llm["model"] = _model_payload(
        provider="openai",
        name=SOURCE_INGESTION_LLM_MODEL_NAME,
        used_llm=True,
        fallback_reason=None,
    )
    return normalized_llm


def _normalize_input(payload: SourceIngestionExtractionInput) -> SourceIngestionExtractionInput:
    return SourceIngestionExtractionInput(
        content=_clip_text(_clean(payload.content) or "", MAX_CONTENT_CHARS),
        filename=_clean(payload.filename),
        source_url=_clean(payload.source_url),
        source_id=_clean(payload.source_id),
        source_label=_clean(payload.source_label),
        source_category=_clean(payload.source_category),
        target_indicator_codes=_normalize_list(payload.target_indicator_codes),
        component_role=_clean(payload.component_role),
        locale="zh" if payload.locale == "zh" else "en",
    )


def _invalid_input_payload(message: str) -> dict[str, object]:
    return {
        "status": "invalid_input",
        "summary": "",
        "key_indicators": [],
        "citation_clues": [],
        "follow_up_questions": [],
        "suggested_fields": {},
        "model": _model_payload(
            provider="deterministic",
            name=SOURCE_INGESTION_FALLBACK_MODEL_NAME,
            used_llm=False,
            fallback_reason=message,
        ),
        "diagnostics": [
            {
                "source": "source_ingestion",
                "status": "invalid_input",
                "severity": "warning",
                "code": "SOURCE_INGESTION_CONTENT_REQUIRED",
                "message": message,
            }
        ],
        "safety": _safety_payload(),
    }


def _build_fallback_payload(payload: SourceIngestionExtractionInput) -> dict[str, object]:
    indicators = _detect_indicators(payload)
    citation_clues = _build_citation_clues(payload)
    follow_up_questions = _build_follow_up_questions(payload, indicators)
    tags = _dedupe(
        [
            str(tag)
            for indicator in indicators
            for tag in indicator.get("tags", [])
            if str(tag).strip()
        ]
    )
    if payload.source_category:
        tags = _dedupe([payload.source_category, *tags])

    suggested_fields = {
        "title": _suggest_title(payload),
        "source_name": _suggest_source_name(payload),
        "source_type": _suggest_source_type(payload, tags),
        "tags": tags[:MAX_LIST_ITEMS],
        "target_indicator_codes": _suggest_target_indicator_codes(payload, indicators),
        "methodology_note": _suggest_methodology_note(payload),
        "license_note": _suggest_license_note(payload),
        "ai_follow_up": follow_up_questions[0] if follow_up_questions else "",
    }
    return {
        "status": "fallback",
        "summary": _build_summary(payload.content),
        "key_indicators": [
            {
                "label": str(indicator.get("label") or ""),
                "code": str(indicator.get("code") or ""),
                "reason": str(indicator.get("reason") or ""),
            }
            for indicator in indicators[:MAX_LIST_ITEMS]
        ],
        "citation_clues": citation_clues[:MAX_LIST_ITEMS],
        "follow_up_questions": follow_up_questions[:MAX_LIST_ITEMS],
        "suggested_fields": _remove_empty_suggestions(suggested_fields),
        "model": _model_payload(
            provider="deterministic",
            name=SOURCE_INGESTION_FALLBACK_MODEL_NAME,
            used_llm=False,
            fallback_reason=None,
        ),
        "diagnostics": [],
        "safety": _safety_payload(),
    }


def _with_fallback_model(payload: dict[str, object], reason: str) -> dict[str, object]:
    diagnostics = [item for item in payload.get("diagnostics", []) if isinstance(item, dict)]
    diagnostics.append(
        {
            "source": "source_ingestion",
            "status": "fallback",
            "severity": "info",
            "code": "SOURCE_INGESTION_FALLBACK_USED",
            "message": "Source extraction used deterministic fallback instead of an LLM answer.",
            "details": {"reason": reason},
        }
    )
    return {
        **payload,
        "status": "fallback",
        "model": _model_payload(
            provider="deterministic",
            name=SOURCE_INGESTION_FALLBACK_MODEL_NAME,
            used_llm=False,
            fallback_reason=reason,
        ),
        "diagnostics": diagnostics,
    }


def _build_llm_prompt(payload: SourceIngestionExtractionInput) -> str:
    context = {
        "filename": payload.filename,
        "source_url": payload.source_url,
        "source_id": payload.source_id,
        "source_label": payload.source_label,
        "source_category": payload.source_category,
        "target_indicator_codes": payload.target_indicator_codes or [],
        "component_role": payload.component_role,
        "locale": payload.locale,
    }
    return (
        "You are extracting research metadata for a personal financial information "
        "aggregation workspace. This is not a professional trading terminal.\n"
        "Return JSON only. Do not invent market data, source URLs, dates, citation IDs, "
        "buy/sell/hold calls, target prices, or position sizing.\n"
        "Draft uploads and extracted suggestions are collection notes only; they are not "
        "AI citations. A citation ID can exist only after the user saves a reviewed and "
        "AI-citable Source Notebook entry.\n\n"
        "Required JSON shape:\n"
        "{"
        "\"summary\": string,"
        "\"key_indicators\": [{\"label\": string, \"code\": string, \"reason\": string}],"
        "\"citation_clues\": [{\"kind\": string, \"label\": string, \"value\": string}],"
        "\"follow_up_questions\": [string],"
        "\"suggested_fields\": {"
        "\"title\": string, \"source_name\": string, \"source_type\": string, "
        "\"tags\": [string], \"target_indicator_codes\": [string], "
        "\"methodology_note\": string, \"license_note\": string, \"ai_follow_up\": string"
        "}"
        "}\n\n"
        f"Source context JSON:\n{json.dumps(context, ensure_ascii=False, sort_keys=True)}\n\n"
        f"Source content:\n{_clip_text(payload.content, MAX_PROMPT_CONTENT_CHARS)}"
    )


def _parse_json_object(answer: str) -> dict[str, object] | None:
    text = answer.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            payload = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return payload if isinstance(payload, dict) else None


def _normalize_llm_payload(
    parsed: dict[str, object] | None,
    source_input: SourceIngestionExtractionInput,
) -> dict[str, object] | None:
    if parsed is None:
        return None
    summary = _clean(parsed.get("summary"))
    key_indicators = _normalize_indicator_items(parsed.get("key_indicators"))
    citation_clues = _normalize_clue_items(parsed.get("citation_clues"))
    follow_up_questions = _normalize_list(parsed.get("follow_up_questions"))
    suggested_fields = _normalize_suggested_fields(parsed.get("suggested_fields"), source_input)
    if not summary or not isinstance(parsed.get("suggested_fields"), dict):
        return None
    return {
        "summary": _clip_text(summary, MAX_SUMMARY_CHARS),
        "key_indicators": key_indicators[:MAX_LIST_ITEMS],
        "citation_clues": citation_clues[:MAX_LIST_ITEMS],
        "follow_up_questions": follow_up_questions[:MAX_LIST_ITEMS],
        "suggested_fields": suggested_fields,
        "diagnostics": [],
        "safety": _safety_payload(),
    }


def _normalize_indicator_items(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    items: list[dict[str, str]] = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        label = _clean(entry.get("label"))
        code = _clean(entry.get("code"))
        reason = _clean(entry.get("reason"))
        if not label:
            continue
        items.append(
            {
                "label": _clip_text(label, 120),
                "code": _clip_text(code or "", 80),
                "reason": _clip_text(reason or "", 200),
            }
        )
    return items


def _normalize_clue_items(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    items: list[dict[str, str]] = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        kind = _clean(entry.get("kind")) or "source"
        label = _clean(entry.get("label"))
        clue_value = _clean(entry.get("value"))
        if not label or not clue_value:
            continue
        items.append(
            {
                "kind": _clip_text(kind, 40),
                "label": _clip_text(label, 120),
                "value": _clip_text(clue_value, 240),
            }
        )
    return items


def _normalize_suggested_fields(
    value: object,
    source_input: SourceIngestionExtractionInput,
) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, object] = {}
    for key in (
        "title",
        "source_name",
        "source_type",
        "methodology_note",
        "license_note",
        "ai_follow_up",
    ):
        text = _clean(value.get(key))
        if text:
            normalized[key] = _clip_text(text, MAX_FIELD_CHARS)
    tags = _normalize_list(value.get("tags"))
    if tags:
        normalized["tags"] = tags[:MAX_LIST_ITEMS]
    target_codes = _normalize_list(value.get("target_indicator_codes"))
    if not target_codes:
        target_codes = source_input.target_indicator_codes or []
    if target_codes:
        normalized["target_indicator_codes"] = target_codes[:MAX_LIST_ITEMS]
    return normalized


def _detect_indicators(payload: SourceIngestionExtractionInput) -> list[dict[str, object]]:
    text = f"{payload.source_label or ''} {payload.source_id or ''} {payload.content}".lower()
    detected: list[dict[str, object]] = []
    for definition in INDICATOR_KEYWORDS:
        keywords = tuple(str(keyword) for keyword in definition["keywords"])
        matched = [keyword for keyword in keywords if keyword.lower() in text]
        if not matched:
            continue
        detected.append(
            {
                "label": definition["label"],
                "code": definition["code"],
                "reason": f"Matched {', '.join(matched[:3])}.",
                "tags": definition["tags"],
            }
        )
    for code in payload.target_indicator_codes or []:
        if not any(item.get("code") == code for item in detected):
            detected.append(
                {
                    "label": code.replace("_", " ").title(),
                    "code": code,
                    "reason": "Selected source-readiness target includes this indicator.",
                    "tags": ("macro",),
                }
            )
    return detected


def _build_citation_clues(payload: SourceIngestionExtractionInput) -> list[dict[str, str]]:
    clues: list[dict[str, str]] = []
    if payload.filename:
        clues.append({"kind": "document", "label": "Browser filename", "value": payload.filename})
    if payload.source_url:
        clues.append({"kind": "url", "label": "Source URL", "value": payload.source_url})
    for url in URL_PATTERN.findall(payload.content):
        clues.append({"kind": "url", "label": "URL found in text", "value": url.rstrip(".,;")})
    for value in DATE_PATTERN.findall(payload.content):
        clues.append({"kind": "date", "label": "Date found in text", "value": value})
    if not any(item["kind"] == "date" for item in clues):
        for value in YEAR_PATTERN.findall(payload.content):
            clues.append({"kind": "date", "label": "Year found in text", "value": value})
            break
    if payload.source_label:
        clues.append({"kind": "source", "label": "Source target", "value": payload.source_label})

    for line in _meaningful_lines(payload.content):
        lowered = line.lower()
        if any(keyword in lowered for keyword in ("method", "calculation", "source", "license", "notes")):
            clues.append({"kind": "methodology", "label": "Review clue", "value": _clip_text(line, 240)})
        if len(clues) >= MAX_LIST_ITEMS:
            break
    return _dedupe_clues(clues)


def _build_follow_up_questions(
    payload: SourceIngestionExtractionInput,
    indicators: list[dict[str, object]],
) -> list[str]:
    questions: list[str] = []
    source_label = payload.source_label or payload.source_id or "this source"
    if _has_buffett_context(payload, indicators):
        questions.extend(
            [
                "Verify whether market-cap and GDP components use the same region and period.",
                "Record the calculation method before importing a Buffett Indicator observation.",
            ]
        )
    if payload.source_id or payload.source_label:
        questions.append(
            f"Check whether {source_label} has enough source, date, excerpt, method, and license metadata for review."
        )
    if payload.target_indicator_codes:
        questions.append(
            "Confirm whether the selected target indicator codes match the reviewed source content."
        )
    if not questions:
        questions.append(
            "Identify which macro, valuation, or filing workflow this source should support."
        )
    questions.append(
        "Decide whether this should remain a collection note or become reviewed AI-citable evidence later."
    )
    return _dedupe(questions)[:MAX_LIST_ITEMS]


def _has_buffett_context(
    payload: SourceIngestionExtractionInput,
    indicators: list[dict[str, object]],
) -> bool:
    text = f"{payload.source_id or ''} {payload.source_label or ''} {payload.content}".lower()
    return "buffett" in text or any(str(item.get("code", "")).startswith("buffett") for item in indicators)


def _suggest_title(payload: SourceIngestionExtractionInput) -> str:
    if payload.filename:
        return re.sub(r"\.[^.]+$", "", payload.filename).strip()[:160]
    if payload.source_label:
        return f"{payload.source_label} source review"
    host = _host_from_url(payload.source_url)
    if host:
        return f"{host} source review"
    return "Research source review"


def _suggest_source_name(payload: SourceIngestionExtractionInput) -> str:
    if payload.source_label:
        return payload.source_label
    return _host_from_url(payload.source_url) or ""


def _suggest_source_type(payload: SourceIngestionExtractionInput, tags: list[str]) -> str:
    if payload.source_category:
        return payload.source_category
    if "valuation" in tags:
        return "valuation"
    if "filing" in tags:
        return "filing"
    return "macro" if "macro" in tags else "research_note"


def _suggest_target_indicator_codes(
    payload: SourceIngestionExtractionInput,
    indicators: list[dict[str, object]],
) -> list[str]:
    codes = [str(item.get("code")) for item in indicators if _clean(item.get("code"))]
    codes = [code for code in codes if code not in {"market_cap", "gdp", "filing_note"}]
    return _dedupe([*(payload.target_indicator_codes or []), *codes])[:MAX_LIST_ITEMS]


def _suggest_methodology_note(payload: SourceIngestionExtractionInput) -> str:
    for line in _meaningful_lines(payload.content):
        lowered = line.lower()
        if "method" in lowered or "calculation" in lowered:
            return _clip_text(line, MAX_FIELD_CHARS)
    return "Review calculation method, source date, and component consistency before import."


def _suggest_license_note(payload: SourceIngestionExtractionInput) -> str:
    for line in _meaningful_lines(payload.content):
        if "license" in line.lower() or "terms" in line.lower():
            return _clip_text(line, MAX_FIELD_CHARS)
    return "Confirm public-source or permitted personal research usage before AI citation."


def _build_summary(content: str) -> str:
    lines = _meaningful_lines(content)
    if not lines:
        return ""
    summary = " ".join(lines[:3])
    return _clip_text(summary, MAX_SUMMARY_CHARS)


def _meaningful_lines(content: str) -> list[str]:
    lines = []
    for raw_line in content.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = re.sub(r"\s+", " ", raw_line).strip(" -\t")
        if len(line) < 4:
            continue
        lines.append(line)
    return lines


def _remove_empty_suggestions(values: dict[str, object]) -> dict[str, object]:
    cleaned: dict[str, object] = {}
    for key, value in values.items():
        if isinstance(value, str) and value.strip():
            cleaned[key] = value
        elif isinstance(value, list) and value:
            cleaned[key] = value
    return cleaned


def _dedupe(values: list[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        cleaned = _clean(value)
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)
    return normalized


def _dedupe_clues(values: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[dict[str, str]] = []
    for value in values:
        key = (value["kind"], value["label"], value["value"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(value)
    return deduped


def _normalize_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return _dedupe([str(item) for item in value])[:MAX_LIST_ITEMS]


def _host_from_url(value: str | None) -> str:
    if not value:
        return ""
    parsed = urlparse(value)
    return parsed.netloc.replace("www.", "")


def _clean(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _clip_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[:limit].rstrip()


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
        "drafts_are_not_citations": True,
        "no_automated_trading": True,
    }
