import json
import re


SHORTLIST_CITATION_PATTERN = re.compile(r"\[([A-Za-z0-9_:\-./+]+)\]")
SHORTLIST_SYMBOL_PATTERN = re.compile(r"`([A-Z0-9.\-]{1,16})`")
SHORTLIST_FALLBACK_MODEL_NAME = "deterministic-stock-discovery-v1"


def build_stock_discovery_prompt(
    *,
    locale: str,
    profile: dict[str, object],
    effective_criteria: dict[str, object],
    shortlist: list[dict[str, object]],
    citations: list[dict[str, object]],
) -> str:
    response_language = "Simplified Chinese" if locale == "zh" else "English"
    candidate_payload = [
        {
            "rank": index,
            "symbol": item.get("symbol"),
            "name": item.get("name"),
            "score": item.get("total_score", item.get("score")),
            "matched_rules": item.get("matched_rules"),
            "supporting_factors": item.get("supporting_factors"),
            "opposing_factors": item.get("opposing_factors"),
            "data_gaps": item.get("data_gaps"),
            "invalidation_conditions": item.get("invalidation_conditions"),
            "evidence_citations": item.get("evidence_citations"),
        }
        for index, item in enumerate(shortlist, start=1)
    ]
    citation_ids = [str(citation["id"]) for citation in citations]
    return (
        "You explain a deterministic stock-research shortlist.\n"
        f"Respond in {response_language}.\n"
        "The candidate membership and ranking are final. Do not add, remove, reorder, or recommend "
        "buying, selling, holding, position sizing, target prices, or automated trades.\n"
        "Mention every symbol inside backticks exactly as supplied. Use only the citation IDs supplied "
        "below, written inline in square brackets. For every candidate, explain the strongest supporting "
        "evidence, material counterarguments or weak factors, data/freshness gaps, and the most important "
        "rule-derived invalidation conditions. Do not turn a weak factor into a recommendation.\n\n"
        f"Profile: {json.dumps(profile, ensure_ascii=False, default=str)}\n"
        f"Effective criteria: {json.dumps(effective_criteria, ensure_ascii=False, default=str)}\n"
        f"Ranked candidates: {json.dumps(candidate_payload, ensure_ascii=False, default=str)}\n"
        f"Allowed citation IDs: {json.dumps(citation_ids, ensure_ascii=False)}\n\n"
        "Write concise markdown sections for Shortlist comparison, Counterarguments and invalidation, "
        "Evidence gaps, and Safety boundary."
    )


def build_deterministic_stock_discovery_explanation(
    *,
    locale: str,
    profile: dict[str, object],
    shortlist: list[dict[str, object]],
) -> str:
    if not shortlist:
        if locale == "zh":
            return (
                "### 候选结果\n"
                "当前本地证据中没有标的同时满足所选条件。缺失证据不会被推测为满足。\n\n"
                "### 安全边界\n"
                "这是研究筛选结果，不构成投资建议，也不会触发自动交易。"
            )
        return (
            "### Shortlist\n"
            "No locally evidenced candidate matched every selected criterion. Missing evidence was not "
            "treated as a match.\n\n"
            "### Safety boundary\n"
            "This is research screening, not investment advice, and it cannot trigger automated trades."
        )

    lines: list[str] = []
    for rank, item in enumerate(shortlist, start=1):
        symbol = str(item.get("symbol") or "UNKNOWN")
        score = item.get("total_score", item.get("score"))
        rules = item.get("matched_rules")
        rule_codes = [
            str(rule.get("code"))
            for rule in rules
            if isinstance(rule, dict) and rule.get("code")
        ] if isinstance(rules, list) else []
        citation_ids = [
            str(citation_id)
            for citation_id in item.get("evidence_citations", [])
            if isinstance(citation_id, str)
        ]
        supporting = _factor_codes(item.get("supporting_factors"), limit=3)
        opposing = _factor_codes(item.get("opposing_factors"), limit=2)
        gaps = _field_values(item.get("data_gaps"), "code", limit=2)
        invalidations = _field_values(
            item.get("invalidation_conditions"),
            "rule",
            limit=2,
        )
        has_structured_research_case = any(
            key in item
            for key in (
                "supporting_factors",
                "opposing_factors",
                "data_gaps",
                "invalidation_conditions",
            )
        )
        detail_suffix = ""
        if has_structured_research_case:
            detail_suffix = (
                f"Support: {', '.join(supporting) or 'none recorded'}; "
                f"counterarguments: {', '.join(opposing) or 'none below the weak-buffer threshold'}; "
                f"gaps: {', '.join(gaps) or 'none recorded'}; "
                f"invalidation rules: {', '.join(invalidations) or 'none recorded'}."
            )
        citation_suffix = " ".join(f"[{citation_id}]" for citation_id in citation_ids)
        suffix = " ".join(part for part in (detail_suffix, citation_suffix) if part)
        line = f"{rank}. `{symbol}` — score {score}; matched: {', '.join(rule_codes) or 'none'}."
        lines.append(f"{line} {suffix}".rstrip())

    profile_label = str(profile.get("label") or profile.get("id") or "selected profile")
    if locale == "zh":
        return (
            f"### 候选对比\n按 `{profile_label}` 的确定性规则排序：\n"
            + "\n".join(lines)
            + "\n\n### 证据缺口\n仅比较本地已存储证据；缺失数据不会被补写或推断。"
            "\n\n### 安全边界\n候选集合与顺序由规则引擎决定，AI 只做解释；这不是投资建议，"
            "也不会触发自动交易。"
        )
    return (
        f"### Shortlist comparison\nDeterministically ranked with `{profile_label}`:\n"
        + "\n".join(lines)
        + "\n\n### Evidence gaps\nOnly locally stored evidence was compared; missing values were neither "
        "invented nor treated as matches.\n\n### Safety boundary\nThe rule engine fixes membership and "
        "ranking; AI only explains them. This is not investment advice and cannot trigger automated trades."
    )


def unknown_stock_discovery_citations(
    answer_markdown: str,
    allowed_ids: set[str],
) -> list[str]:
    mentioned = set(SHORTLIST_CITATION_PATTERN.findall(answer_markdown))
    return sorted(mentioned - allowed_ids)


def unknown_stock_discovery_symbols(
    answer_markdown: str,
    allowed_symbols: set[str],
) -> list[str]:
    mentioned = set(SHORTLIST_SYMBOL_PATTERN.findall(answer_markdown))
    return sorted(mentioned - allowed_symbols)


def _factor_codes(value: object, *, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [
        f"{item.get('code')} ({item.get('buffer')})"
        for item in value[:limit]
        if isinstance(item, dict) and item.get("code")
    ]


def _field_values(value: object, field: str, *, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [
        str(item[field])
        for item in value[:limit]
        if isinstance(item, dict) and item.get(field)
    ]
