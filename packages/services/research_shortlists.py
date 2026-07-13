from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
import threading
from uuid import UUID

from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from packages.domain.models import (
    DailyBar,
    Instrument,
    Market,
    ResearchShortlistCandidate,
    ResearchShortlistRun,
)
from packages.services.research_evidence_backfill import get_evidence_coverage
from packages.services.stock_discovery import (
    build_stock_discovery_citations,
    generate_stock_discovery_explanation,
)
from packages.services.stock_selection import RULE_SET_ID, screen_local_stock_selection
from packages.services.stock_selection_profiles import (
    normalize_stock_selection_criteria,
    resolve_stock_selection_profile,
)


SCORING_MODEL_ID = "daily_research_score_v1"
SUPPORTED_MARKET = "CN"
SUPPORTED_ASSET_TYPE = "stock"
BASE_DIMENSION_WEIGHTS = {
    "fundamental": 0.40,
    "technical": 0.35,
    "liquidity": 0.20,
    "news": 0.05,
}
RULE_DEFINITIONS = {
    "max_pe_ratio": ("fundamental", "max_pe_ratio"),
    "min_revenue_growth": ("fundamental", "growth_margin_min"),
    "min_net_margin": ("fundamental", "growth_margin_min"),
    "min_rsi": ("technical", "oscillator_min_0_100"),
    "max_rsi": ("technical", "oscillator_max_0_100"),
    "require_price_above_ma": ("technical", "price_above_ma_10pct"),
    "required_pattern_codes": ("technical", "categorical_exact"),
    "min_mfi": ("technical", "oscillator_min_0_100"),
    "max_mfi": ("technical", "oscillator_max_0_100"),
    "min_william_r": ("technical", "william_r_min"),
    "max_william_r": ("technical", "william_r_max"),
    "min_chip_benefit_ratio": ("technical", "unit_interval_min"),
    "max_chip_benefit_ratio": ("technical", "unit_interval_max"),
    "min_latest_volume": ("liquidity", "log10_min_multiple"),
    "min_traded_amount": ("liquidity", "log10_min_multiple"),
    "min_news_article_count": ("news", "log10_min_multiple"),
    "required_news_sentiment": ("news", "categorical_exact"),
    "min_news_sentiment_confidence": ("news", "unit_interval_min"),
}
SAFETY_PAYLOAD = {
    "research_signal_only": True,
    "disclaimer": (
        "The daily research shortlist is a research aid only, is not investment advice, "
        "and cannot trigger automated trading."
    ),
    "not_investment_advice": True,
    "no_buy_sell_hold": True,
    "no_target_price": True,
    "no_position_sizing": True,
    "no_automated_trading": True,
    "ai_cannot_change_membership_or_ranking": True,
}
_GENERATION_LOCK_STRIPES = tuple(threading.RLock() for _ in range(64))


@dataclass(frozen=True)
class ResearchShortlistGenerateInput:
    profile_id: str = "balanced_research"
    overrides: dict[str, object] | None = None
    market: str = SUPPORTED_MARKET
    asset_type: str = SUPPORTED_ASSET_TYPE
    shortlist_limit: int = 10
    locale: str = "zh"
    use_llm: bool = True


class ResearchShortlistReadinessError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def as_detail(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


def generate_research_shortlist(
    payload: ResearchShortlistGenerateInput,
    *,
    session: Session,
) -> dict[str, object]:
    normalized = _normalize_generate_input(payload)
    resolved = resolve_stock_selection_profile(
        normalized.profile_id,
        normalized.overrides,
    )
    effective_criteria = _dict_value(resolved.get("effective_criteria"))
    if not effective_criteria:
        raise ValueError("The selected profile has no active research criteria.")

    decision_date = _latest_decision_date(
        session,
        market=normalized.market,
        asset_type=normalized.asset_type,
    )
    if decision_date is None:
        if session.in_transaction():
            session.rollback()
        raise ResearchShortlistReadinessError(
            "NO_IN_SCOPE_DAILY_BARS",
            "No stored daily bar is available for the active in-scope universe.",
            details={
                "market": normalized.market,
                "asset_type": normalized.asset_type,
            },
        )

    generation_key = build_research_shortlist_generation_key(
        market=normalized.market,
        asset_type=normalized.asset_type,
        profile_id=normalized.profile_id,
        effective_criteria=effective_criteria,
        decision_date=decision_date,
        shortlist_limit=normalized.shortlist_limit,
    )
    with _serialized_generation(session, generation_key):
        return _generate_research_shortlist_locked(
            normalized=normalized,
            resolved=resolved,
            effective_criteria=effective_criteria,
            decision_date=decision_date,
            generation_key=generation_key,
            session=session,
        )


def _generate_research_shortlist_locked(
    *,
    normalized: ResearchShortlistGenerateInput,
    resolved: dict[str, object],
    effective_criteria: dict[str, object],
    decision_date: date,
    generation_key: str,
    session: Session,
) -> dict[str, object]:
    existing = _run_by_generation_key(session, generation_key)
    if existing is not None:
        return _serialize_response(existing, _candidates_for_run(session, existing.id))

    readiness = get_evidence_coverage(
        session=session,
        market=normalized.market,
        provider="akshare",
        as_of=decision_date,
    )
    if readiness.get("status") != "ok":
        raise ResearchShortlistReadinessError(
            "EVIDENCE_COVERAGE_NOT_READY",
            "Stored A-share evidence does not satisfy the publication thresholds.",
            details={"coverage": readiness},
        )

    selection = screen_local_stock_selection(
        session=session,
        market=normalized.market,
        asset_type=normalized.asset_type,
        limit=100,
        unbounded_results=True,
        as_of=decision_date,
        **effective_criteria,
    )
    if selection.get("status") != "ok":
        raise ValueError("The resolved profile could not be evaluated.")

    eligible_items = _dict_list(selection.get("items"))
    diagnostics = _dict_list(selection.get("diagnostics"))
    aligned_items: list[dict[str, object]] = []
    stale_symbols: list[str] = []
    post_decision_symbols: list[str] = []
    point_in_time_diagnostics: list[dict[str, object]] = []
    for item in eligible_items:
        post_decision_evidence = _post_decision_evidence(
            item,
            decision_date=decision_date,
        )
        if post_decision_evidence:
            symbol = str(item.get("symbol") or "")
            post_decision_symbols.append(symbol)
            diagnostic = {
                "source": "research_shortlist",
                "status": "excluded",
                "code": "POST_DECISION_EVIDENCE",
                "symbol": symbol,
                "message": "Candidate evidence after the decision date was rejected.",
                "details": {
                    "decision_date": decision_date.isoformat(),
                    "evidence": post_decision_evidence,
                },
            }
            diagnostics.append(diagnostic)
            point_in_time_diagnostics.append(diagnostic)
            continue
        latest_bar = _dict_value(item.get("latest_bar"))
        if latest_bar.get("trade_date") != decision_date.isoformat():
            symbol = str(item.get("symbol") or "")
            stale_symbols.append(symbol)
            diagnostics.append(
                {
                    "source": "daily_bars",
                    "status": "excluded",
                    "code": "STALE_ENTRY_BAR",
                    "symbol": symbol,
                    "message": "The candidate's latest stored bar is not on the decision date.",
                    "details": {
                        "decision_date": decision_date.isoformat(),
                        "latest_trade_date": latest_bar.get("trade_date"),
                    },
                }
            )
            continue
        aligned_items.append(item)

    if eligible_items and not aligned_items:
        raise ResearchShortlistReadinessError(
            "NO_DECISION_DATE_ALIGNED_CANDIDATES",
            "Eligible candidates do not have valid point-in-time evidence on the decision date.",
            details={
                "decision_date": decision_date.isoformat(),
                "stale_symbols": sorted(stale_symbols),
                "post_decision_symbols": sorted(post_decision_symbols),
                "diagnostics": point_in_time_diagnostics,
            },
        )

    scored_items = [
        _with_research_score(item, effective_criteria=effective_criteria)
        for item in aligned_items
    ]
    scored_items.sort(
        key=lambda item: (
            -float(item["total_score"]),
            -float(item["minimum_rule_buffer"]),
            str(item.get("symbol") or ""),
        )
    )
    shortlist = scored_items[: normalized.shortlist_limit]
    for rank, item in enumerate(shortlist, start=1):
        item["rank"] = rank

    instruments = _instruments_by_symbol(
        session,
        symbols=[str(item["symbol"]) for item in shortlist],
        market=normalized.market,
        asset_type=normalized.asset_type,
    )
    missing_instruments = sorted(
        str(item["symbol"])
        for item in shortlist
        if str(item["symbol"]) not in instruments
    )
    if missing_instruments:
        raise RuntimeError(
            "Selected candidates are missing persisted instrument identity: "
            + ", ".join(missing_instruments)
        )
    entry_bars = _entry_bars_by_instrument(
        session,
        instrument_ids=[instruments[str(item["symbol"])].id for item in shortlist],
        decision_date=decision_date,
    )
    if len(entry_bars) != len(shortlist):
        raise ResearchShortlistReadinessError(
            "ENTRY_BAR_CHANGED_DURING_GENERATION",
            "A candidate entry bar became unavailable before publication.",
            details={"decision_date": decision_date.isoformat()},
        )

    citations = build_stock_discovery_citations(shortlist)
    explanation, model = generate_stock_discovery_explanation(
        locale=normalized.locale,
        resolved=resolved,
        effective_criteria=effective_criteria,
        shortlist=shortlist,
        citations=citations,
        diagnostics=diagnostics,
        use_llm=normalized.use_llm,
    )
    counts = _generation_counts(
        selection=selection,
        eligible_count=len(eligible_items),
        aligned_count=len(aligned_items),
        returned_count=len(shortlist),
    )
    dimension_weights = _normalized_dimension_weights(effective_criteria)
    generated_at = datetime.now(timezone.utc)
    candidate_scope = {
        **_dict_value(selection.get("candidate_scope")),
        "counts": counts,
    }
    run = ResearchShortlistRun(
        generation_key=generation_key,
        status="committed",
        decision_date=decision_date,
        generated_at=generated_at,
        market=normalized.market,
        asset_type=normalized.asset_type,
        profile_id=normalized.profile_id,
        rule_set=RULE_SET_ID,
        scoring_model=SCORING_MODEL_ID,
        locale=normalized.locale,
        shortlist_limit=normalized.shortlist_limit,
        default_criteria_json=_dict_value(resolved.get("default_criteria")),
        effective_criteria_json=effective_criteria,
        overrides_json=_dict_value(resolved.get("overrides")),
        dimension_weights_json=dimension_weights,
        candidate_scope_json=candidate_scope,
        coverage_json={
            **readiness,
            "selection": _dict_value(selection.get("coverage")),
        },
        diagnostics_json=diagnostics,
        explanation_markdown=explanation,
        model_json=model,
        citations_json=citations,
        safety_json=dict(SAFETY_PAYLOAD),
        research_signal_only=True,
    )
    for item in shortlist:
        instrument = instruments[str(item["symbol"])]
        entry_bar = entry_bars[instrument.id]
        run.candidates.append(
            _candidate_record(
                item=item,
                instrument=instrument,
                entry_bar=entry_bar,
                decision_date=decision_date,
            )
        )

    try:
        session.add(run)
        session.commit()
    except IntegrityError:
        session.rollback()
        winner = _run_by_generation_key(session, generation_key)
        if winner is None:
            raise
        return _serialize_response(winner, _candidates_for_run(session, winner.id))
    except Exception:
        session.rollback()
        raise

    session.refresh(run)
    return _serialize_response(run, _candidates_for_run(session, run.id))


def get_latest_research_shortlist(
    *,
    session: Session,
    market: str = SUPPORTED_MARKET,
    profile_id: str = "balanced_research",
) -> dict[str, object]:
    normalized_market = _normalize_market(market)
    normalized_profile = profile_id.strip().lower()
    resolve_stock_selection_profile(normalized_profile)
    run = (
        session.query(ResearchShortlistRun)
        .filter(ResearchShortlistRun.status == "committed")
        .filter(ResearchShortlistRun.market == normalized_market)
        .filter(ResearchShortlistRun.profile_id == normalized_profile)
        .order_by(
            ResearchShortlistRun.decision_date.desc(),
            ResearchShortlistRun.generated_at.desc(),
            ResearchShortlistRun.id.desc(),
        )
        .first()
    )
    if run is None:
        return _no_data_response()
    return _serialize_response(run, _candidates_for_run(session, run.id))


def get_research_shortlist(
    run_id: str,
    *,
    session: Session,
) -> dict[str, object] | None:
    try:
        parsed_id = UUID(run_id)
    except (TypeError, ValueError):
        return None
    run = session.get(ResearchShortlistRun, parsed_id)
    if run is None or run.status != "committed":
        return None
    return _serialize_response(run, _candidates_for_run(session, run.id))


def build_research_shortlist_generation_key(
    *,
    market: str,
    asset_type: str,
    profile_id: str,
    effective_criteria: dict[str, object],
    decision_date: date,
    shortlist_limit: int,
) -> str:
    canonical = {
        "market": market.strip().upper(),
        "asset_type": asset_type.strip().lower(),
        "profile_id": profile_id.strip().lower(),
        "effective_criteria": normalize_stock_selection_criteria(effective_criteria),
        "decision_date": decision_date.isoformat(),
        "eligibility_rule_set": RULE_SET_ID,
        "scoring_model": SCORING_MODEL_ID,
        "shortlist_limit": shortlist_limit,
    }
    encoded = json.dumps(
        canonical,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def score_research_shortlist_candidate(
    item: dict[str, object],
    *,
    effective_criteria: dict[str, object],
) -> dict[str, object]:
    rules = _dict_list(item.get("matched_rules"))
    active_rule_codes = {
        code
        for code, value in effective_criteria.items()
        if _criterion_is_active(value)
    }
    unknown_codes = sorted(
        code for code in active_rule_codes if code not in RULE_DEFINITIONS
    )
    if unknown_codes:
        raise ValueError(
            "Unknown daily research score rule code(s): " + ", ".join(unknown_codes)
        )
    rule_by_code = {str(rule.get("code")): rule for rule in rules if rule.get("code")}
    unexpected_codes = sorted(set(rule_by_code) - set(RULE_DEFINITIONS))
    if unexpected_codes:
        raise ValueError(
            "Unknown daily research score rule code(s): " + ", ".join(unexpected_codes)
        )
    missing_codes = sorted(active_rule_codes - set(rule_by_code))
    if missing_codes:
        raise ValueError(
            "Eligible candidate is missing matched rule(s): " + ", ".join(missing_codes)
        )
    if not active_rule_codes:
        raise ValueError("At least one active rule is required for research scoring.")

    dimension_weights = _normalized_dimension_weights(effective_criteria)
    buffers_by_dimension: dict[str, list[float]] = {}
    scored_rules: list[dict[str, object]] = []
    for code in sorted(active_rule_codes):
        rule = rule_by_code[code]
        dimension, normalization = RULE_DEFINITIONS[code]
        buffer = _rule_buffer(code, rule)
        buffers_by_dimension.setdefault(dimension, []).append(buffer)
        scored_rules.append(
            {
                "code": code,
                "field": rule.get("field"),
                "actual": rule.get("actual"),
                "threshold": rule.get("threshold"),
                "normalization": normalization,
                "buffer": round(buffer, 4),
                "dimension": dimension,
                "dimension_weight": dimension_weights[dimension],
            }
        )

    dimension_scores = {
        dimension: sum(buffers) / len(buffers)
        for dimension, buffers in buffers_by_dimension.items()
    }
    total_score = sum(
        dimension_weights[dimension] * score
        for dimension, score in dimension_scores.items()
    )
    for factor in scored_rules:
        dimension = str(factor["dimension"])
        rule_count = len(buffers_by_dimension[dimension])
        factor["weighted_contribution"] = round(
            float(factor["buffer"]) * dimension_weights[dimension] / rule_count,
            6,
        )

    supporting = sorted(
        (factor for factor in scored_rules if float(factor["buffer"]) >= 0.75),
        key=lambda factor: (-float(factor["buffer"]), str(factor["code"])),
    )[:3]
    opposing = sorted(
        (factor for factor in scored_rules if float(factor["buffer"]) < 0.75),
        key=lambda factor: (float(factor["buffer"]), str(factor["code"])),
    )[:2]
    return {
        "total_score": round(total_score, 4),
        "minimum_rule_buffer": round(
            min(float(factor["buffer"]) for factor in scored_rules),
            4,
        ),
        "dimension_weights": dimension_weights,
        "dimension_scores": {
            dimension: round(score, 4)
            for dimension, score in sorted(dimension_scores.items())
        },
        "factor_scores": scored_rules,
        "supporting_factors": supporting,
        "opposing_factors": opposing,
        "invalidation_conditions": [
            _invalidation_condition(factor) for factor in scored_rules
        ],
    }


def _with_research_score(
    item: dict[str, object],
    *,
    effective_criteria: dict[str, object],
) -> dict[str, object]:
    score = score_research_shortlist_candidate(
        item,
        effective_criteria=effective_criteria,
    )
    decision_date = date.fromisoformat(
        str(_dict_value(item.get("latest_bar"))["trade_date"])
    )
    return {
        **item,
        **score,
        "score": score["total_score"],
        "data_gaps": _candidate_data_gaps(item, decision_date=decision_date),
    }


def _rule_buffer(code: str, rule: dict[str, object]) -> float:
    _, normalization = RULE_DEFINITIONS[code]
    if normalization == "categorical_exact":
        return 0.75
    actual = _required_number(rule.get("actual"), code=code, label="actual")
    threshold = _required_number(rule.get("threshold"), code=code, label="threshold")
    progress = 0.0
    if normalization == "max_pe_ratio":
        progress = (threshold - actual) / max(threshold, 1.0)
    elif normalization == "growth_margin_min":
        progress = (actual - threshold) / 0.20
    elif normalization == "oscillator_min_0_100":
        denominator = 100.0 - threshold
        progress = (actual - threshold) / denominator if denominator > 0 else 0.0
    elif normalization == "oscillator_max_0_100":
        progress = (threshold - actual) / threshold if threshold > 0 else 0.0
    elif normalization == "william_r_min":
        denominator = 0.0 - threshold
        progress = (actual - threshold) / denominator if denominator > 0 else 0.0
    elif normalization == "william_r_max":
        denominator = threshold - (-100.0)
        progress = (threshold - actual) / denominator if denominator > 0 else 0.0
    elif normalization == "unit_interval_min":
        denominator = 1.0 - threshold
        progress = (actual - threshold) / denominator if denominator > 0 else 0.0
    elif normalization == "unit_interval_max":
        progress = (threshold - actual) / threshold if threshold > 0 else 0.0
    elif normalization == "log10_min_multiple":
        denominator = max(threshold, 1.0)
        progress = math.log10(max(actual / denominator, 1.0))
    elif normalization == "price_above_ma_10pct":
        denominator = max(abs(threshold), 1e-12)
        progress = ((actual / denominator) - 1.0) / 0.10
    else:
        raise ValueError(f"Unknown daily research score normalization: {normalization}")
    return 0.5 + 0.5 * _clamp(progress)


def _normalized_dimension_weights(
    effective_criteria: dict[str, object],
) -> dict[str, float]:
    active_dimensions: set[str] = set()
    for code, value in effective_criteria.items():
        if not _criterion_is_active(value):
            continue
        definition = RULE_DEFINITIONS.get(code)
        if definition is None:
            raise ValueError(f"Unknown daily research score rule code: {code}")
        active_dimensions.add(definition[0])
    total_weight = sum(BASE_DIMENSION_WEIGHTS[dimension] for dimension in active_dimensions)
    if total_weight <= 0:
        raise ValueError("At least one score dimension must be active.")
    return {
        dimension: round(BASE_DIMENSION_WEIGHTS[dimension] / total_weight, 6)
        for dimension in sorted(active_dimensions)
    }


def _invalidation_condition(factor: dict[str, object]) -> dict[str, object]:
    code = str(factor["code"])
    if code.startswith("min_"):
        operator = "less_than"
        operator_symbol = "<"
    elif code.startswith("max_"):
        operator = "greater_than"
        operator_symbol = ">"
    elif code == "require_price_above_ma":
        operator = "less_than_or_equal"
        operator_symbol = "<="
    elif code == "required_pattern_codes":
        operator = "missing_required_value"
        operator_symbol = "missing"
    elif code == "required_news_sentiment":
        operator = "not_equal"
        operator_symbol = "!="
    else:
        raise ValueError(f"Unknown daily research score rule code: {code}")
    field = factor.get("field")
    threshold = factor.get("threshold")
    return {
        "rule": code,
        "field": field,
        "invalidates_when": operator,
        "operator": operator_symbol,
        "threshold": threshold,
        "entry_actual": factor.get("actual"),
        "message": f"Invalidated when {field} {operator_symbol} {threshold}.",
    }


def _candidate_record(
    *,
    item: dict[str, object],
    instrument: Instrument,
    entry_bar: DailyBar,
    decision_date: date,
) -> ResearchShortlistCandidate:
    evidence_citations = [
        citation
        for citation in item.get("evidence_citations", [])
        if isinstance(citation, str)
    ]
    evidence = {
        "latest_bar": _dict_value(item.get("latest_bar")),
        "technical_indicators_as_of": item.get("technical_indicators_as_of"),
        "technical_indicators": _dict_value(item.get("technical_indicators")),
        "fundamentals": item.get("fundamentals"),
        "news_sentiment": item.get("news_sentiment"),
    }
    return ResearchShortlistCandidate(
        instrument_id=instrument.id,
        symbol=str(item["symbol"]),
        name=str(item.get("name") or instrument.name),
        market=str(item.get("market") or SUPPORTED_MARKET),
        asset_type=str(item.get("asset_type") or SUPPORTED_ASSET_TYPE),
        rank=int(item["rank"]),
        total_score=Decimal(str(item["total_score"])),
        minimum_rule_buffer=Decimal(str(item["minimum_rule_buffer"])),
        entry_trade_date=decision_date,
        entry_close=entry_bar.close,
        entry_provider=entry_bar.provider,
        entry_source=entry_bar.source,
        entry_adjustment=entry_bar.adjustment,
        entry_source_priority=entry_bar.source_priority,
        entry_ingested_at=entry_bar.ingested_at,
        factor_scores_json=item.get("factor_scores", []),
        supporting_factors_json=item.get("supporting_factors", []),
        opposing_factors_json=item.get("opposing_factors", []),
        data_gaps_json=item.get("data_gaps", []),
        invalidation_conditions_json=item.get("invalidation_conditions", []),
        evidence_json=evidence,
        matched_rules_json=item.get("matched_rules", []),
        citations_json=evidence_citations,
        safety_json=dict(SAFETY_PAYLOAD),
    )


def _candidate_data_gaps(
    item: dict[str, object],
    *,
    decision_date: date,
) -> list[dict[str, object]]:
    gaps: list[dict[str, object]] = []
    technical_as_of = _date_from_iso(item.get("technical_indicators_as_of"))
    if technical_as_of is None:
        gaps.append(
            {
                "source": "technical_indicators",
                "code": "TECHNICAL_AS_OF_UNAVAILABLE",
                "status": "missing",
            }
        )
    elif technical_as_of < decision_date:
        gaps.append(
            {
                "source": "technical_indicators",
                "code": "TECHNICAL_BEFORE_DECISION_DATE",
                "status": "stale",
                "as_of": technical_as_of.isoformat(),
                "decision_date": decision_date.isoformat(),
            }
        )

    fundamentals = item.get("fundamentals")
    if not isinstance(fundamentals, dict):
        gaps.append(
            {
                "source": "fundamentals",
                "code": "FUNDAMENTALS_UNAVAILABLE",
                "status": "missing",
            }
        )
    else:
        fundamental_as_of = _date_from_iso(fundamentals.get("as_of"))
        if fundamental_as_of is not None and fundamental_as_of < decision_date:
            gaps.append(
                {
                    "source": "fundamentals",
                    "code": "FUNDAMENTALS_BEFORE_DECISION_DATE",
                    "status": "stale",
                    "as_of": fundamental_as_of.isoformat(),
                    "decision_date": decision_date.isoformat(),
                }
            )
    if not isinstance(item.get("news_sentiment"), dict):
        gaps.append(
            {
                "source": "news_sentiment",
                "code": "NEWS_NOT_EVALUATED_BY_PROFILE",
                "status": "not_evaluated",
                "message": "News and sentiment were not active eligibility rules for this profile.",
            }
        )
    return gaps


def _post_decision_evidence(
    item: dict[str, object],
    *,
    decision_date: date,
) -> list[dict[str, str]]:
    latest_bar = _dict_value(item.get("latest_bar"))
    fundamentals = _dict_value(item.get("fundamentals"))
    news_sentiment = _dict_value(item.get("news_sentiment"))
    evidence_dates = (
        ("daily_bars", "trade_date", latest_bar.get("trade_date")),
        (
            "technical_indicators",
            "as_of",
            item.get("technical_indicators_as_of"),
        ),
        ("fundamentals", "as_of", fundamentals.get("as_of")),
        ("news", "published_at", news_sentiment.get("latest_published_at")),
        (
            "sentiment",
            "created_at",
            news_sentiment.get("latest_sentiment_created_at"),
        ),
    )
    rejected: list[dict[str, str]] = []
    for source, field, raw_value in evidence_dates:
        evidence_date = _date_from_iso(raw_value)
        if evidence_date is None or evidence_date <= decision_date:
            continue
        rejected.append(
            {
                "source": source,
                "field": field,
                "value": str(raw_value),
            }
        )
    return rejected


def _serialize_response(
    run: ResearchShortlistRun,
    candidates: list[ResearchShortlistCandidate],
) -> dict[str, object]:
    safety = dict(run.safety_json or SAFETY_PAYLOAD)
    return {
        "status": "ok",
        "run": {
            "id": str(run.id),
            "generation_key": run.generation_key,
            "status": run.status,
            "decision_date": run.decision_date.isoformat(),
            "generated_at": _iso_datetime(run.generated_at),
            "market": run.market,
            "asset_type": run.asset_type,
            "profile_id": run.profile_id,
            "profile": {"id": run.profile_id},
            "rule_set": run.rule_set,
            "eligibility_version": run.rule_set,
            "scoring_model": run.scoring_model,
            "locale": run.locale,
            "shortlist_limit": run.shortlist_limit,
            "default_criteria": run.default_criteria_json or {},
            "effective_criteria": run.effective_criteria_json or {},
            "overrides": run.overrides_json or {},
            "dimension_weights": run.dimension_weights_json or {},
            "candidate_scope": run.candidate_scope_json or {},
            "counts": _dict_value(run.candidate_scope_json).get("counts", {}),
            "coverage": run.coverage_json or {},
            "diagnostics": run.diagnostics_json or [],
            "explanation_markdown": run.explanation_markdown,
            "model": run.model_json or {},
            "citations": run.citations_json or [],
            "safety": safety,
            "research_signal_only": bool(run.research_signal_only),
        },
        "items": [_serialize_candidate(candidate) for candidate in candidates],
        "research_signal_only": True,
        "safety": safety,
    }


def _serialize_candidate(candidate: ResearchShortlistCandidate) -> dict[str, object]:
    citations = list(candidate.citations_json or [])
    total_score = float(candidate.total_score)
    entry_observation = {
        "trade_date": candidate.entry_trade_date.isoformat(),
        "close": float(candidate.entry_close),
        "provider": candidate.entry_provider,
        "source": candidate.entry_source,
        "adjustment": candidate.entry_adjustment,
        "source_priority": candidate.entry_source_priority,
        "ingested_at": _iso_datetime(candidate.entry_ingested_at),
    }
    return {
        "id": str(candidate.id),
        "run_id": str(candidate.run_id),
        "instrument_id": str(candidate.instrument_id),
        "symbol": candidate.symbol,
        "name": candidate.name,
        "market": candidate.market,
        "asset_type": candidate.asset_type,
        "rank": candidate.rank,
        "score": total_score,
        "total_score": total_score,
        "minimum_rule_buffer": float(candidate.minimum_rule_buffer),
        "entry_observation": entry_observation,
        "entry": entry_observation,
        "factor_scores": candidate.factor_scores_json or [],
        "supporting_factors": candidate.supporting_factors_json or [],
        "opposing_factors": candidate.opposing_factors_json or [],
        "data_gaps": candidate.data_gaps_json or [],
        "invalidation_conditions": candidate.invalidation_conditions_json or [],
        "evidence": candidate.evidence_json or {},
        "matched_rules": candidate.matched_rules_json or [],
        "evidence_citations": citations,
        "citations": citations,
        "allowed_citation_ids": citations,
        "evidence_count": len(citations),
        "safety": candidate.safety_json or dict(SAFETY_PAYLOAD),
        "research_signal_only": True,
    }


def _no_data_response() -> dict[str, object]:
    return {
        "status": "no_data",
        "run": None,
        "items": [],
        "research_signal_only": True,
        "safety": dict(SAFETY_PAYLOAD),
    }


def _normalize_generate_input(
    payload: ResearchShortlistGenerateInput,
) -> ResearchShortlistGenerateInput:
    market = _normalize_market(payload.market)
    asset_type = payload.asset_type.strip().lower()
    if asset_type != SUPPORTED_ASSET_TYPE:
        raise ValueError(f"Unsupported research shortlist asset type: {payload.asset_type}")
    if payload.shortlist_limit < 1 or payload.shortlist_limit > 20:
        raise ValueError("Research shortlist limit must be between 1 and 20.")
    return ResearchShortlistGenerateInput(
        profile_id=payload.profile_id.strip().lower(),
        overrides=dict(payload.overrides or {}),
        market=market,
        asset_type=asset_type,
        shortlist_limit=payload.shortlist_limit,
        locale="en" if payload.locale == "en" else "zh",
        use_llm=bool(payload.use_llm),
    )


def _normalize_market(value: str) -> str:
    market = value.strip().upper()
    if market != SUPPORTED_MARKET:
        raise ValueError(f"Unsupported research shortlist market: {value}")
    return market


def _latest_decision_date(
    session: Session,
    *,
    market: str,
    asset_type: str,
) -> date | None:
    return (
        session.query(func.max(DailyBar.trade_date))
        .join(Instrument, DailyBar.instrument_id == Instrument.id)
        .join(Market, Instrument.market_id == Market.id)
        .filter(Instrument.is_active.is_(True))
        .filter(Instrument.asset_type == asset_type)
        .filter(Market.code == market)
        .scalar()
    )


def _instruments_by_symbol(
    session: Session,
    *,
    symbols: list[str],
    market: str,
    asset_type: str,
) -> dict[str, Instrument]:
    if not symbols:
        return {}
    rows = (
        session.query(Instrument)
        .join(Market, Instrument.market_id == Market.id)
        .filter(Instrument.symbol.in_(symbols))
        .filter(Instrument.asset_type == asset_type)
        .filter(Market.code == market)
        .all()
    )
    return {row.symbol.upper(): row for row in rows}


def _entry_bars_by_instrument(
    session: Session,
    *,
    instrument_ids: list[UUID],
    decision_date: date,
) -> dict[UUID, DailyBar]:
    if not instrument_ids:
        return {}
    rows = (
        session.query(DailyBar)
        .filter(DailyBar.instrument_id.in_(instrument_ids))
        .filter(DailyBar.trade_date == decision_date)
        .all()
    )
    return {row.instrument_id: row for row in rows}


@contextmanager
def _serialized_generation(
    session: Session,
    generation_key: str,
) -> Iterator[None]:
    dialect_name = session.get_bind().dialect.name
    local_lock: threading.RLock | None = None
    if dialect_name == "postgresql":
        try:
            session.execute(
                text("SELECT pg_advisory_xact_lock(:lock_key)"),
                {"lock_key": _postgres_advisory_lock_key(generation_key)},
            )
        except Exception:
            if session.in_transaction():
                session.rollback()
            raise
    else:
        stripe_index = int(generation_key[:16], 16) % len(_GENERATION_LOCK_STRIPES)
        local_lock = _GENERATION_LOCK_STRIPES[stripe_index]
        local_lock.acquire()
        try:
            if session.in_transaction():
                session.rollback()
        except Exception:
            local_lock.release()
            raise
    try:
        yield
    finally:
        try:
            if session.in_transaction():
                session.rollback()
        finally:
            if local_lock is not None:
                local_lock.release()


def _postgres_advisory_lock_key(generation_key: str) -> int:
    unsigned_value = int(generation_key[:16], 16)
    if unsigned_value >= 2**63:
        return unsigned_value - 2**64
    return unsigned_value


def _run_by_generation_key(
    session: Session,
    generation_key: str,
) -> ResearchShortlistRun | None:
    return (
        session.query(ResearchShortlistRun)
        .filter(ResearchShortlistRun.generation_key == generation_key)
        .filter(ResearchShortlistRun.status == "committed")
        .one_or_none()
    )


def _candidates_for_run(
    session: Session,
    run_id: UUID,
) -> list[ResearchShortlistCandidate]:
    return (
        session.query(ResearchShortlistCandidate)
        .filter(ResearchShortlistCandidate.run_id == run_id)
        .order_by(ResearchShortlistCandidate.rank)
        .all()
    )


def _generation_counts(
    *,
    selection: dict[str, object],
    eligible_count: int,
    aligned_count: int,
    returned_count: int,
) -> dict[str, int]:
    selection_coverage = _dict_value(selection.get("coverage"))
    candidate_count = int(selection_coverage.get("candidate_count") or 0)
    evaluated_count = int(selection_coverage.get("evaluated_count") or candidate_count)
    return {
        "candidate_count": candidate_count,
        "evaluated_count": evaluated_count,
        "matched_count": eligible_count,
        "eligible_count": eligible_count,
        "decision_date_aligned_count": aligned_count,
        "returned_count": returned_count,
    }


def _criterion_is_active(value: object) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, list | tuple | set | dict):
        return bool(value)
    return True


def _required_number(value: object, *, code: str, label: str) -> float:
    if value is None or isinstance(value, bool):
        raise ValueError(f"Score rule {code} has no numeric {label}.")
    if isinstance(value, Decimal | int | float):
        numeric = float(value)
        if math.isfinite(numeric):
            return numeric
    raise ValueError(f"Score rule {code} has an invalid numeric {label}.")


def _clamp(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def _date_from_iso(value: object) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None


def _iso_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _dict_value(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
