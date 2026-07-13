from copy import deepcopy


SUPPORTED_PROFILE_OVERRIDES = (
    "max_pe_ratio",
    "min_revenue_growth",
    "min_net_margin",
    "min_rsi",
    "max_rsi",
    "require_price_above_ma",
    "required_pattern_codes",
    "min_mfi",
    "max_mfi",
    "min_william_r",
    "max_william_r",
    "min_chip_benefit_ratio",
    "max_chip_benefit_ratio",
    "min_latest_volume",
    "min_traded_amount",
    "min_news_article_count",
    "required_news_sentiment",
    "min_news_sentiment_confidence",
)


STOCK_SELECTION_PROFILES: dict[str, dict[str, object]] = {
    "balanced_research": {
        "id": "balanced_research",
        "label": "Balanced research",
        "description": (
            "Balances valuation, growth, trend, and liquidity using only locally stored evidence."
        ),
        "criteria": {
            "max_pe_ratio": 35.0,
            "min_revenue_growth": 0.05,
            "min_rsi": 35.0,
            "max_rsi": 75.0,
            "require_price_above_ma": True,
            "min_latest_volume": 500_000.0,
        },
    },
    "quality_value": {
        "id": "quality_value",
        "label": "Quality value",
        "description": "Prioritizes profitable growth at a bounded stored price-to-earnings ratio.",
        "criteria": {
            "max_pe_ratio": 25.0,
            "min_revenue_growth": 0.08,
            "min_net_margin": 0.10,
        },
    },
    "trend_liquidity": {
        "id": "trend_liquidity",
        "label": "Trend and liquidity",
        "description": "Looks for liquid names with a confirmed stored trend and bounded momentum.",
        "criteria": {
            "min_rsi": 50.0,
            "max_rsi": 75.0,
            "require_price_above_ma": True,
            "min_mfi": 45.0,
            "min_latest_volume": 1_000_000.0,
            "min_traded_amount": 50_000_000.0,
        },
    },
}


def get_stock_selection_profiles_payload() -> dict[str, object]:
    return {
        "status": "ok",
        "items": [
            {
                **deepcopy(STOCK_SELECTION_PROFILES[profile_id]),
                "supported_overrides": list(SUPPORTED_PROFILE_OVERRIDES),
            }
            for profile_id in STOCK_SELECTION_PROFILES
        ],
        "safety": {
            "research_signal_only": True,
            "deterministic_ranking": True,
            "no_automated_trading": True,
            "parameters_visible_and_editable": True,
        },
    }


def resolve_stock_selection_profile(
    profile_id: str,
    overrides: dict[str, object] | None = None,
) -> dict[str, object]:
    normalized_profile_id = profile_id.strip().lower()
    profile = STOCK_SELECTION_PROFILES.get(normalized_profile_id)
    if profile is None:
        raise ValueError(f"Unknown stock-selection profile: {profile_id}")

    raw_overrides = overrides or {}
    normalized_overrides = normalize_stock_selection_criteria(raw_overrides)
    unsupported = sorted(set(normalized_overrides) - set(SUPPORTED_PROFILE_OVERRIDES))
    if unsupported:
        raise ValueError(
            "Unsupported stock-selection profile override(s): " + ", ".join(unsupported)
        )
    criteria = normalize_stock_selection_criteria(profile["criteria"])
    if not isinstance(criteria, dict):
        raise RuntimeError("Stock-selection profile criteria are invalid.")
    criteria.update(normalized_overrides)
    criteria = normalize_stock_selection_criteria(criteria)
    return {
        "profile": {
            "id": profile["id"],
            "label": profile["label"],
            "description": profile["description"],
        },
        "default_criteria": normalize_stock_selection_criteria(profile["criteria"]),
        "overrides": deepcopy(normalized_overrides),
        "effective_criteria": criteria,
        "supported_overrides": list(SUPPORTED_PROFILE_OVERRIDES),
    }


def normalize_stock_selection_criteria(
    criteria: dict[str, object],
) -> dict[str, object]:
    normalized = deepcopy(criteria)
    if "required_pattern_codes" in normalized:
        value = normalized["required_pattern_codes"]
        if isinstance(value, str):
            raw_codes = [value]
        elif isinstance(value, list | tuple | set):
            raw_codes = value
        else:
            raw_codes = []
        normalized["required_pattern_codes"] = sorted(
            {
                str(code).strip().lower()
                for code in raw_codes
                if str(code).strip()
            }
        )
    if "required_news_sentiment" in normalized:
        normalized["required_news_sentiment"] = normalize_stock_selection_sentiment(
            normalized["required_news_sentiment"]
        )
    return normalized


def normalize_stock_selection_sentiment(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    return normalized or None
