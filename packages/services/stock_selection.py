from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload

from packages.domain.models import (
    DailyBar,
    FundamentalSnapshot,
    Instrument,
    Market,
    NewsArticle,
    SentimentSignal,
    TechnicalIndicator,
)
from packages.services.watchlists import get_active_watchlist_scope
from packages.services.stock_selection_profiles import (
    normalize_stock_selection_criteria,
    normalize_stock_selection_sentiment,
)


RULE_SET_ID = "instock_composite_selection_v1"
DISCLAIMER = "Composite stock selection is a research aid only and is not investment advice."


@dataclass(frozen=True)
class SelectionEvidence:
    latest_bars: dict[UUID, DailyBar]
    latest_indicators: dict[UUID, dict[str, object]]
    latest_fundamentals: dict[str, FundamentalSnapshot]
    latest_news_sentiment: dict[str, dict[str, object]]


def screen_local_stock_selection(
    *,
    session: Session,
    symbols: list[str] | None = None,
    market: str | None = None,
    asset_type: str | None = None,
    max_pe_ratio: float | None = None,
    min_revenue_growth: float | None = None,
    min_net_margin: float | None = None,
    min_rsi: float | None = None,
    max_rsi: float | None = None,
    require_price_above_ma: bool = False,
    required_pattern_codes: list[str] | None = None,
    min_mfi: float | None = None,
    max_mfi: float | None = None,
    min_william_r: float | None = None,
    max_william_r: float | None = None,
    min_chip_benefit_ratio: float | None = None,
    max_chip_benefit_ratio: float | None = None,
    min_latest_volume: float | None = None,
    min_traded_amount: float | None = None,
    min_news_article_count: int | None = None,
    required_news_sentiment: str | None = None,
    min_news_sentiment_confidence: float | None = None,
    watchlist_only: bool = False,
    limit: int = 20,
    unbounded_results: bool = False,
    as_of: date | None = None,
) -> dict[str, object]:
    criteria = _criteria_payload(
        max_pe_ratio=max_pe_ratio,
        min_revenue_growth=min_revenue_growth,
        min_net_margin=min_net_margin,
        min_rsi=min_rsi,
        max_rsi=max_rsi,
        require_price_above_ma=require_price_above_ma,
        required_pattern_codes=required_pattern_codes,
        min_mfi=min_mfi,
        max_mfi=max_mfi,
        min_william_r=min_william_r,
        max_william_r=max_william_r,
        min_chip_benefit_ratio=min_chip_benefit_ratio,
        max_chip_benefit_ratio=max_chip_benefit_ratio,
        min_latest_volume=min_latest_volume,
        min_traded_amount=min_traded_amount,
        min_news_article_count=min_news_article_count,
        required_news_sentiment=required_news_sentiment,
        min_news_sentiment_confidence=min_news_sentiment_confidence,
    )
    if not _has_active_criteria(criteria):
        return {
            "status": "invalid_request",
            "rule_set": RULE_SET_ID,
            "research_signal_only": True,
            "candidate_scope": _candidate_scope_payload(
                symbols=symbols,
                market=market,
                asset_type=asset_type,
                watchlist_only=watchlist_only,
            ),
            "criteria": criteria,
            "count": 0,
            "items": [],
            "diagnostics": [
                {
                    "code": "NO_SELECTION_CRITERIA",
                    "message": (
                        "At least one fundamental, technical, market-data, or news "
                        "selection criterion is required."
                    ),
                }
            ],
            "disclaimer": DISCLAIMER,
        }

    instruments = _candidate_instruments(
        session=session,
        symbols=symbols,
        market=market,
        asset_type=asset_type,
        watchlist_only=watchlist_only,
    )
    evidence = _load_selection_evidence(
        session=session,
        instruments=instruments,
        include_news=_news_criteria_requested(criteria),
        as_of=as_of,
    )
    detailed_diagnostics = bool(_normalize_symbols(symbols)) or watchlist_only or len(instruments) <= 100
    diagnostics: list[dict[str, object]] = []
    diagnostic_counts: dict[tuple[str, str], int] = {}
    items: list[dict[str, object]] = []

    for instrument in instruments:
        evaluation = _evaluate_instrument(instrument, criteria, evidence=evidence)
        evaluation_diagnostics = evaluation["diagnostics"]
        _accumulate_diagnostic_counts(diagnostic_counts, evaluation_diagnostics)
        if detailed_diagnostics:
            diagnostics.extend(evaluation_diagnostics)
        if evaluation["matched"]:
            items.append(evaluation["item"])

    all_ranked_items = sorted(
        items,
        key=lambda item: (
            float(item.get("score", 0.0)),
            str(item.get("symbol", "")),
        ),
        reverse=True,
    )
    ranked_items = (
        all_ranked_items
        if unbounded_results
        else all_ranked_items[: max(1, min(limit, 100))]
    )
    if not detailed_diagnostics:
        diagnostics = _compact_diagnostics(diagnostic_counts)

    return {
        "status": "ok",
        "rule_set": RULE_SET_ID,
        "research_signal_only": True,
        "candidate_scope": _candidate_scope_payload(
            symbols=symbols,
            market=market,
            asset_type=asset_type,
            watchlist_only=watchlist_only,
        ),
        "criteria": criteria,
        "count": len(ranked_items),
        "items": ranked_items,
        "coverage": _selection_coverage(
            instruments=instruments,
            evidence=evidence,
            matched_count=len(items),
            returned_count=len(ranked_items),
            news_required=_news_criteria_requested(criteria),
        ),
        "diagnostics_summary": _serialize_diagnostic_counts(diagnostic_counts),
        "diagnostics": diagnostics,
        "disclaimer": DISCLAIMER,
    }


def _criteria_payload(
    *,
    max_pe_ratio: float | None,
    min_revenue_growth: float | None,
    min_net_margin: float | None,
    min_rsi: float | None,
    max_rsi: float | None,
    require_price_above_ma: bool,
    required_pattern_codes: list[str] | None,
    min_mfi: float | None,
    max_mfi: float | None,
    min_william_r: float | None,
    max_william_r: float | None,
    min_chip_benefit_ratio: float | None,
    max_chip_benefit_ratio: float | None,
    min_latest_volume: float | None,
    min_traded_amount: float | None,
    min_news_article_count: int | None,
    required_news_sentiment: str | None,
    min_news_sentiment_confidence: float | None,
) -> dict[str, object]:
    return normalize_stock_selection_criteria({
        "max_pe_ratio": max_pe_ratio,
        "min_revenue_growth": min_revenue_growth,
        "min_net_margin": min_net_margin,
        "min_rsi": min_rsi,
        "max_rsi": max_rsi,
        "require_price_above_ma": require_price_above_ma,
        "required_pattern_codes": required_pattern_codes,
        "min_mfi": min_mfi,
        "max_mfi": max_mfi,
        "min_william_r": min_william_r,
        "max_william_r": max_william_r,
        "min_chip_benefit_ratio": min_chip_benefit_ratio,
        "max_chip_benefit_ratio": max_chip_benefit_ratio,
        "min_latest_volume": min_latest_volume,
        "min_traded_amount": min_traded_amount,
        "min_news_article_count": min_news_article_count,
        "required_news_sentiment": required_news_sentiment,
        "min_news_sentiment_confidence": min_news_sentiment_confidence,
    })


def _has_active_criteria(criteria: dict[str, object]) -> bool:
    return any(_criteria_value_is_active(value) for value in criteria.values())


def _criteria_value_is_active(value: object) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, list | tuple | set | dict):
        return bool(value)
    return True


def _candidate_instruments(
    *,
    session: Session,
    symbols: list[str] | None,
    market: str | None,
    asset_type: str | None,
    watchlist_only: bool,
) -> list[Instrument]:
    query = (
        session.query(Instrument)
        .options(joinedload(Instrument.market))
        .outerjoin(Market, Instrument.market_id == Market.id)
    )
    query = query.filter(Instrument.is_active.is_(True))

    normalized_symbols = _normalize_symbols(symbols)
    if normalized_symbols:
        query = query.filter(Instrument.symbol.in_(normalized_symbols))

    normalized_market = _normalize_optional_text(market)
    if normalized_market:
        query = query.filter(Market.code == normalized_market)

    normalized_asset_type = _normalize_asset_type(asset_type)
    if normalized_asset_type:
        query = query.filter(Instrument.asset_type == normalized_asset_type)

    if watchlist_only:
        watchlist_entries = get_active_watchlist_scope(session)
        if not watchlist_entries:
            return []
        pair_filters = [
            and_(Instrument.symbol == entry["symbol"], Market.code == entry["market"])
            for entry in watchlist_entries
        ]
        query = query.filter(or_(*pair_filters))

    return query.order_by(Instrument.symbol).all()


def _evaluate_instrument(
    instrument: Instrument,
    criteria: dict[str, object],
    *,
    evidence: SelectionEvidence,
) -> dict[str, object]:
    symbol = instrument.symbol.upper()
    diagnostics: list[dict[str, object]] = []
    latest_bar = evidence.latest_bars.get(instrument.id)
    if latest_bar is None:
        return _failed_evaluation(
            symbol=symbol,
            diagnostics=[
                {
                    "symbol": symbol,
                    "code": "MISSING_DAILY_BAR",
                    "message": "No stored daily bar is available for stock selection.",
                }
            ],
        )

    latest_indicators = evidence.latest_indicators.get(
        instrument.id,
        {"as_of": None, "values": {}},
    )
    latest_fundamentals = evidence.latest_fundamentals.get(symbol)
    matched_rules: list[dict[str, object]] = []

    market_data_result = _evaluate_market_data_rules(
        symbol=symbol,
        latest_bar=latest_bar,
        criteria=criteria,
    )
    diagnostics.extend(market_data_result["diagnostics"])
    if market_data_result["failed"]:
        return _failed_evaluation(symbol=symbol, diagnostics=diagnostics)
    matched_rules.extend(market_data_result["matched_rules"])

    fundamentals_result = _evaluate_fundamental_rules(
        symbol=symbol,
        snapshot=latest_fundamentals,
        criteria=criteria,
    )
    diagnostics.extend(fundamentals_result["diagnostics"])
    if fundamentals_result["failed"]:
        return _failed_evaluation(symbol=symbol, diagnostics=diagnostics)
    matched_rules.extend(fundamentals_result["matched_rules"])

    technical_result = _evaluate_technical_rules(
        symbol=symbol,
        latest_bar=latest_bar,
        indicators=latest_indicators,
        criteria=criteria,
    )
    diagnostics.extend(technical_result["diagnostics"])
    if technical_result["failed"]:
        return _failed_evaluation(symbol=symbol, diagnostics=diagnostics)
    matched_rules.extend(technical_result["matched_rules"])

    news_sentiment = None
    if _news_criteria_requested(criteria):
        news_sentiment = evidence.latest_news_sentiment.get(
            symbol,
            _empty_news_sentiment_payload(),
        )
        news_result = _evaluate_news_rules(
            symbol=symbol,
            news_sentiment=news_sentiment,
            criteria=criteria,
        )
        diagnostics.extend(news_result["diagnostics"])
        if news_result["failed"]:
            return _failed_evaluation(symbol=symbol, diagnostics=diagnostics)
        matched_rules.extend(news_result["matched_rules"])

    criteria_count = max(1, len([rule for rule in matched_rules if rule["status"] == "matched"]))
    evidence_citations = _evidence_citations(
        symbol=symbol,
        latest_bar=latest_bar,
        indicators=latest_indicators,
        fundamentals=latest_fundamentals,
        news_sentiment=news_sentiment,
    )
    item = {
        "symbol": symbol,
        "name": instrument.name,
        "market": instrument.market.code if instrument.market else None,
        "asset_type": instrument.asset_type,
        "score": round(criteria_count / max(1, _active_criteria_count(criteria)), 4),
        "latest_bar": _serialize_daily_bar(latest_bar),
        "fundamentals": _serialize_fundamentals(latest_fundamentals),
        "technical_indicators_as_of": latest_indicators["as_of"],
        "technical_indicators": latest_indicators["values"],
        "matched_rules": matched_rules,
        "evidence_citations": evidence_citations,
        "research_signal_only": True,
    }
    if news_sentiment is not None:
        item["news_sentiment"] = news_sentiment

    return {
        "matched": True,
        "diagnostics": diagnostics,
        "item": item,
    }


def _failed_evaluation(
    *,
    symbol: str,
    diagnostics: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "matched": False,
        "diagnostics": diagnostics,
        "item": {"symbol": symbol},
    }


def _evaluate_fundamental_rules(
    *,
    symbol: str,
    snapshot: FundamentalSnapshot | None,
    criteria: dict[str, object],
) -> dict[str, object]:
    required = any(
        criteria[key] is not None
        for key in ("max_pe_ratio", "min_revenue_growth", "min_net_margin")
    )
    if required and snapshot is None:
        return {
            "failed": True,
            "matched_rules": [],
            "diagnostics": [
                {
                    "symbol": symbol,
                    "code": "MISSING_FUNDAMENTALS",
                    "message": "Fundamental criteria were requested but no stored snapshot is available.",
                }
            ],
        }
    if snapshot is None:
        return {"failed": False, "matched_rules": [], "diagnostics": []}

    checks = [
        _max_rule("max_pe_ratio", "pe_ratio", snapshot.pe_ratio, criteria["max_pe_ratio"]),
        _min_rule(
            "min_revenue_growth",
            "revenue_growth",
            snapshot.revenue_growth,
            criteria["min_revenue_growth"],
        ),
        _min_rule("min_net_margin", "net_margin", snapshot.net_margin, criteria["min_net_margin"]),
    ]
    return _rule_result(symbol=symbol, checks=checks)


def _evaluate_market_data_rules(
    *,
    symbol: str,
    latest_bar: DailyBar,
    criteria: dict[str, object],
) -> dict[str, object]:
    checks = [
        _min_rule(
            "min_latest_volume",
            "latest_bar.volume",
            latest_bar.volume,
            criteria["min_latest_volume"],
        ),
        _min_rule(
            "min_traded_amount",
            "latest_bar.traded_amount",
            _traded_amount_from_bar(latest_bar),
            criteria["min_traded_amount"],
        ),
    ]
    return _rule_result(symbol=symbol, checks=checks)


def _evaluate_technical_rules(
    *,
    symbol: str,
    latest_bar: DailyBar,
    indicators: dict[str, object],
    criteria: dict[str, object],
) -> dict[str, object]:
    values = indicators["values"]
    checks = [
        _min_rule("min_rsi", "rsi", _numeric_value(values.get("rsi")), criteria["min_rsi"]),
        _max_rule("max_rsi", "rsi", _numeric_value(values.get("rsi")), criteria["max_rsi"]),
        _pattern_rule(
            "required_pattern_codes",
            "candlestick_patterns.patterns",
            values.get("candlestick_patterns"),
            criteria["required_pattern_codes"],
        ),
        _min_rule("min_mfi", "mfi", _numeric_value(values.get("mfi")), criteria["min_mfi"]),
        _max_rule("max_mfi", "mfi", _numeric_value(values.get("mfi")), criteria["max_mfi"]),
        _min_rule(
            "min_william_r",
            "william_r",
            _numeric_value(values.get("william_r")),
            criteria["min_william_r"],
        ),
        _max_rule(
            "max_william_r",
            "william_r",
            _numeric_value(values.get("william_r")),
            criteria["max_william_r"],
        ),
        _min_rule(
            "min_chip_benefit_ratio",
            "chip_distribution.benefit_ratio",
            _nested_numeric_value(values.get("chip_distribution"), "benefit_ratio"),
            criteria["min_chip_benefit_ratio"],
        ),
        _max_rule(
            "max_chip_benefit_ratio",
            "chip_distribution.benefit_ratio",
            _nested_numeric_value(values.get("chip_distribution"), "benefit_ratio"),
            criteria["max_chip_benefit_ratio"],
        ),
    ]
    if criteria["require_price_above_ma"]:
        checks.append(
            _boolean_rule(
                "require_price_above_ma",
                "close_above_ma",
                _numeric_value(latest_bar.close),
                _numeric_value(values.get("ma")),
            )
        )

    return _rule_result(symbol=symbol, checks=checks)


def _evaluate_news_rules(
    *,
    symbol: str,
    news_sentiment: dict[str, object],
    criteria: dict[str, object],
) -> dict[str, object]:
    checks = [
        _min_rule(
            "min_news_article_count",
            "news.article_count",
            news_sentiment["article_count"],
            criteria["min_news_article_count"],
        ),
        _sentiment_rule(
            "required_news_sentiment",
            "news.latest_sentiment",
            news_sentiment.get("latest_sentiment"),
            criteria["required_news_sentiment"],
        ),
        _min_rule(
            "min_news_sentiment_confidence",
            "news.latest_confidence",
            news_sentiment.get("latest_confidence"),
            criteria["min_news_sentiment_confidence"],
        ),
    ]
    return _rule_result(symbol=symbol, checks=checks)


def _rule_result(
    *,
    symbol: str,
    checks: list[dict[str, object] | None],
) -> dict[str, object]:
    matched_rules: list[dict[str, object]] = []
    diagnostics: list[dict[str, object]] = []
    failed = False
    for check in checks:
        if check is None:
            continue
        if check["status"] == "matched":
            matched_rules.append(check)
            continue
        failed = True
        diagnostics.append(
            {
                "symbol": symbol,
                "code": "SELECTION_RULE_NOT_MATCHED",
                "rule": check["code"],
                "message": "A requested stock-selection criterion was not matched.",
                "details": check,
            }
        )
    return {"failed": failed, "matched_rules": matched_rules, "diagnostics": diagnostics}


def _min_rule(
    code: str,
    field: str,
    actual: object,
    threshold: object,
) -> dict[str, object] | None:
    if threshold is None:
        return None
    actual_value = _numeric_value(actual)
    threshold_value = _numeric_value(threshold)
    if actual_value is None or threshold_value is None:
        return {
            "code": code,
            "field": field,
            "status": "missing_value",
            "actual": actual_value,
            "threshold": threshold_value,
        }
    return {
        "code": code,
        "field": field,
        "status": "matched" if actual_value >= threshold_value else "not_matched",
        "actual": actual_value,
        "threshold": threshold_value,
    }


def _max_rule(
    code: str,
    field: str,
    actual: object,
    threshold: object,
) -> dict[str, object] | None:
    if threshold is None:
        return None
    actual_value = _numeric_value(actual)
    threshold_value = _numeric_value(threshold)
    if actual_value is None or threshold_value is None:
        return {
            "code": code,
            "field": field,
            "status": "missing_value",
            "actual": actual_value,
            "threshold": threshold_value,
        }
    return {
        "code": code,
        "field": field,
        "status": "matched" if actual_value <= threshold_value else "not_matched",
        "actual": actual_value,
        "threshold": threshold_value,
    }


def _pattern_rule(
    code: str,
    field: str,
    payload: object,
    required_codes: object,
) -> dict[str, object] | None:
    if not isinstance(required_codes, list) or not required_codes:
        return None

    actual_codes = _candlestick_pattern_codes(payload)
    if actual_codes is None:
        return {
            "code": code,
            "field": field,
            "status": "missing_value",
            "actual": None,
            "threshold": required_codes,
        }

    missing_codes = [pattern_code for pattern_code in required_codes if pattern_code not in actual_codes]
    return {
        "code": code,
        "field": field,
        "status": "matched" if not missing_codes else "not_matched",
        "actual": sorted(actual_codes),
        "threshold": required_codes,
        "missing_pattern_codes": missing_codes,
    }


def _boolean_rule(
    code: str,
    field: str,
    actual: float | None,
    threshold: float | None,
) -> dict[str, object]:
    if actual is None or threshold is None:
        return {
            "code": code,
            "field": field,
            "status": "missing_value",
            "actual": actual,
            "threshold": threshold,
        }
    return {
        "code": code,
        "field": field,
        "status": "matched" if actual > threshold else "not_matched",
        "actual": actual,
        "threshold": threshold,
    }


def _sentiment_rule(
    code: str,
    field: str,
    actual: object,
    threshold: object,
) -> dict[str, object] | None:
    if not isinstance(threshold, str) or not threshold:
        return None
    actual_value = _normalize_sentiment(actual)
    if actual_value is None:
        return {
            "code": code,
            "field": field,
            "status": "missing_value",
            "actual": actual_value,
            "threshold": threshold,
        }
    return {
        "code": code,
        "field": field,
        "status": "matched" if actual_value == threshold else "not_matched",
        "actual": actual_value,
        "threshold": threshold,
    }


def _load_selection_evidence(
    *,
    session: Session,
    instruments: list[Instrument],
    include_news: bool,
    as_of: date | None,
) -> SelectionEvidence:
    instrument_ids = [instrument.id for instrument in instruments]
    symbols = sorted({instrument.symbol.upper() for instrument in instruments})
    if not instrument_ids:
        return SelectionEvidence({}, {}, {}, {})
    return SelectionEvidence(
        latest_bars=_bulk_latest_daily_bars(session, instrument_ids, as_of=as_of),
        latest_indicators=_bulk_latest_indicators(session, instrument_ids, as_of=as_of),
        latest_fundamentals=_bulk_latest_fundamentals(session, symbols, as_of=as_of),
        latest_news_sentiment=(
            _bulk_latest_news_sentiment(session, symbols, as_of=as_of)
            if include_news
            else {}
        ),
    )


def _bulk_latest_daily_bars(
    session: Session,
    instrument_ids: list[UUID],
    *,
    as_of: date | None,
) -> dict[UUID, DailyBar]:
    latest_dates_query = (
        session.query(
            DailyBar.instrument_id.label("instrument_id"),
            func.max(DailyBar.trade_date).label("trade_date"),
        )
        .filter(DailyBar.instrument_id.in_(instrument_ids))
    )
    if as_of is not None:
        latest_dates_query = latest_dates_query.filter(DailyBar.trade_date <= as_of)
    latest_dates = latest_dates_query.group_by(DailyBar.instrument_id).subquery()
    rows = (
        session.query(DailyBar)
        .join(
            latest_dates,
            and_(
                DailyBar.instrument_id == latest_dates.c.instrument_id,
                DailyBar.trade_date == latest_dates.c.trade_date,
            ),
        )
        .all()
    )
    return {row.instrument_id: row for row in rows}


def _bulk_latest_indicators(
    session: Session,
    instrument_ids: list[UUID],
    *,
    as_of: date | None,
) -> dict[UUID, dict[str, object]]:
    latest_times_query = (
        session.query(
            TechnicalIndicator.instrument_id.label("instrument_id"),
            func.max(TechnicalIndicator.as_of).label("as_of"),
        )
        .filter(TechnicalIndicator.instrument_id.in_(instrument_ids))
        .filter(TechnicalIndicator.timeframe == "1d")
    )
    cutoff = _exclusive_utc_day_end(as_of)
    if cutoff is not None:
        latest_times_query = latest_times_query.filter(TechnicalIndicator.as_of < cutoff)
    latest_times = latest_times_query.group_by(TechnicalIndicator.instrument_id).subquery()
    rows = (
        session.query(TechnicalIndicator)
        .join(
            latest_times,
            and_(
                TechnicalIndicator.instrument_id == latest_times.c.instrument_id,
                TechnicalIndicator.as_of == latest_times.c.as_of,
            ),
        )
        .filter(TechnicalIndicator.timeframe == "1d")
        .all()
    )
    payloads: dict[UUID, dict[str, object]] = {}
    for row in rows:
        payload = payloads.setdefault(
            row.instrument_id,
            {"as_of": _isoformat_utc(row.as_of), "values": {}},
        )
        values = payload["values"]
        if isinstance(values, dict) and isinstance(row.value_json, dict) and "value" in row.value_json:
            values[row.indicator_code] = _serialize_indicator_value(row.value_json["value"])
    return payloads


def _bulk_latest_fundamentals(
    session: Session,
    symbols: list[str],
    *,
    as_of: date | None,
) -> dict[str, FundamentalSnapshot]:
    latest_dates_query = (
        session.query(
            FundamentalSnapshot.symbol.label("symbol"),
            func.max(FundamentalSnapshot.as_of).label("as_of"),
        )
        .filter(FundamentalSnapshot.symbol.in_(symbols))
    )
    if as_of is not None:
        latest_dates_query = latest_dates_query.filter(FundamentalSnapshot.as_of <= as_of)
    latest_dates = latest_dates_query.group_by(FundamentalSnapshot.symbol).subquery()
    rows = (
        session.query(FundamentalSnapshot)
        .join(
            latest_dates,
            and_(
                FundamentalSnapshot.symbol == latest_dates.c.symbol,
                FundamentalSnapshot.as_of == latest_dates.c.as_of,
            ),
        )
        .all()
    )
    return {row.symbol.upper(): row for row in rows}


def _bulk_latest_news_sentiment(
    session: Session,
    symbols: list[str],
    *,
    as_of: date | None,
) -> dict[str, dict[str, object]]:
    payloads = {symbol: _empty_news_sentiment_payload() for symbol in symbols}
    cutoff = _exclusive_utc_day_end(as_of)
    count_query = (
        session.query(
            NewsArticle.symbol,
            func.count(func.distinct(NewsArticle.id)),
        )
        .join(SentimentSignal, SentimentSignal.article_id == NewsArticle.id)
        .filter(NewsArticle.symbol.in_(symbols))
    )
    if cutoff is not None:
        count_query = count_query.filter(
            NewsArticle.published_at < cutoff,
            SentimentSignal.created_at < cutoff,
        )
    count_rows = count_query.group_by(NewsArticle.symbol).all()
    for symbol, article_count in count_rows:
        payloads[symbol.upper()]["article_count"] = int(article_count)

    latest_published_query = (
        session.query(
            NewsArticle.symbol.label("symbol"),
            func.max(NewsArticle.published_at).label("published_at"),
        )
        .join(SentimentSignal, SentimentSignal.article_id == NewsArticle.id)
        .filter(NewsArticle.symbol.in_(symbols))
    )
    if cutoff is not None:
        latest_published_query = latest_published_query.filter(
            NewsArticle.published_at < cutoff,
            SentimentSignal.created_at < cutoff,
        )
    latest_published = latest_published_query.group_by(NewsArticle.symbol).subquery()
    rows_query = (
        session.query(NewsArticle, SentimentSignal)
        .join(SentimentSignal, SentimentSignal.article_id == NewsArticle.id)
        .join(
            latest_published,
            and_(
                NewsArticle.symbol == latest_published.c.symbol,
                NewsArticle.published_at == latest_published.c.published_at,
            ),
        )
    )
    if cutoff is not None:
        rows_query = rows_query.filter(
            NewsArticle.published_at < cutoff,
            SentimentSignal.created_at < cutoff,
        )
    rows = (
        rows_query
        .order_by(
            NewsArticle.symbol,
            SentimentSignal.created_at.desc(),
            NewsArticle.id.desc(),
        )
        .all()
    )
    populated: set[str] = set()
    for article, signal in rows:
        symbol = article.symbol.upper()
        if symbol in populated:
            continue
        payloads[symbol].update(
            {
                "latest_sentiment": signal.sentiment,
                "latest_confidence": _numeric_value(signal.confidence),
                "latest_published_at": _isoformat_utc(article.published_at),
                "latest_sentiment_created_at": _isoformat_utc(signal.created_at),
                "latest_title": article.title,
                "latest_source": article.source,
                "latest_url": article.url,
                "citation_id": f"news:{symbol}:{article.id}",
            }
        )
        populated.add(symbol)
    return payloads


def _empty_news_sentiment_payload() -> dict[str, object]:
    return {
        "article_count": 0,
        "latest_sentiment": None,
        "latest_confidence": None,
        "latest_published_at": None,
        "latest_sentiment_created_at": None,
        "latest_title": None,
        "latest_source": None,
        "latest_url": None,
        "citation_id": None,
    }


def _selection_coverage(
    *,
    instruments: list[Instrument],
    evidence: SelectionEvidence,
    matched_count: int,
    returned_count: int,
    news_required: bool,
) -> dict[str, object]:
    candidate_count = len(instruments)
    instrument_ids = {instrument.id for instrument in instruments}
    symbols = {instrument.symbol.upper() for instrument in instruments}
    indicator_count = sum(
        1
        for instrument_id in instrument_ids
        if evidence.latest_indicators.get(instrument_id, {}).get("values")
    )
    news_count = sum(
        1
        for symbol in symbols
        if int(evidence.latest_news_sentiment.get(symbol, {}).get("article_count", 0)) > 0
    )
    return {
        "candidate_count": candidate_count,
        "evaluated_count": candidate_count,
        "matched_count": matched_count,
        "returned_count": returned_count,
        "evidence": {
            "daily_bars": _coverage_counter(candidate_count, len(evidence.latest_bars), True),
            "technical_indicators": _coverage_counter(candidate_count, indicator_count, True),
            "fundamentals": _coverage_counter(
                candidate_count,
                len(symbols & set(evidence.latest_fundamentals)),
                True,
            ),
            "news_sentiment": _coverage_counter(candidate_count, news_count, news_required),
        },
    }


def _coverage_counter(total: int, available: int, required: bool) -> dict[str, object]:
    bounded_available = min(max(0, available), total)
    return {
        "required": required,
        "available_count": bounded_available,
        "missing_count": max(0, total - bounded_available),
        "coverage_ratio": round(bounded_available / total, 4) if total else 0.0,
    }


def _accumulate_diagnostic_counts(
    counts: dict[tuple[str, str], int],
    diagnostics: list[dict[str, object]],
) -> None:
    for diagnostic in diagnostics:
        code = str(diagnostic.get("code") or "UNKNOWN")
        dimension = str(diagnostic.get("rule") or _diagnostic_source(code))
        key = (code, dimension)
        counts[key] = counts.get(key, 0) + 1


def _diagnostic_source(code: str) -> str:
    return {
        "MISSING_DAILY_BAR": "daily_bars",
        "MISSING_FUNDAMENTALS": "fundamentals",
    }.get(code, "selection")


def _serialize_diagnostic_counts(
    counts: dict[tuple[str, str], int],
) -> list[dict[str, object]]:
    return [
        {"code": code, "dimension": dimension, "count": count}
        for (code, dimension), count in sorted(counts.items())
    ]


def _compact_diagnostics(
    counts: dict[tuple[str, str], int],
) -> list[dict[str, object]]:
    return [
        {
            "code": code,
            "dimension": dimension,
            "count": count,
            "message": "Stock-selection diagnostics were aggregated for the full candidate universe.",
        }
        for (code, dimension), count in sorted(counts.items())
    ]


def _serialize_daily_bar(row: DailyBar) -> dict[str, object]:
    return {
        "trade_date": row.trade_date.isoformat(),
        "open": _numeric_value(row.open),
        "high": _numeric_value(row.high),
        "low": _numeric_value(row.low),
        "close": _numeric_value(row.close),
        "volume": _numeric_value(row.volume),
        "amount": _numeric_value(row.amount),
        "traded_amount": _traded_amount_from_bar(row),
        "provider": row.provider,
        "source": row.source,
        "adjustment": row.adjustment,
        "source_priority": row.source_priority,
        "ingested_at": _isoformat_utc(row.ingested_at),
    }


def _serialize_fundamentals(row: FundamentalSnapshot | None) -> dict[str, object] | None:
    if row is None:
        return None
    return {
        "as_of": row.as_of.isoformat(),
        "currency": row.currency,
        "pe_ratio": _numeric_value(row.pe_ratio),
        "revenue_growth": _numeric_value(row.revenue_growth),
        "net_margin": _numeric_value(row.net_margin),
        "debt_to_assets": _numeric_value(row.debt_to_assets),
        "source": row.source,
    }


def _evidence_citations(
    *,
    symbol: str,
    latest_bar: DailyBar,
    indicators: dict[str, object],
    fundamentals: FundamentalSnapshot | None,
    news_sentiment: dict[str, object] | None,
) -> list[str]:
    citations = [f"bars_1d:{symbol}:{latest_bar.trade_date.isoformat()}"]
    indicator_as_of = indicators.get("as_of")
    if isinstance(indicator_as_of, str):
        citations.append(f"technical_indicators:{symbol}:{indicator_as_of}")
    if fundamentals is not None:
        citations.append(f"fundamental_metrics:{symbol}:{fundamentals.as_of.isoformat()}")
    if news_sentiment is not None and isinstance(news_sentiment.get("citation_id"), str):
        citations.append(str(news_sentiment["citation_id"]))
    return citations


def _active_criteria_count(criteria: dict[str, object]) -> int:
    return sum(1 for value in criteria.values() if _criteria_value_is_active(value))


def _candidate_scope_payload(
    *,
    symbols: list[str] | None,
    market: str | None,
    asset_type: str | None,
    watchlist_only: bool,
) -> dict[str, object]:
    return {
        "symbols": _normalize_symbols(symbols),
        "market": _normalize_optional_text(market),
        "asset_type": _normalize_asset_type(asset_type),
        "watchlist_only": watchlist_only,
    }


def _normalize_symbols(symbols: list[str] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for symbol in symbols or []:
        normalized_symbol = symbol.strip().upper()
        if not normalized_symbol or normalized_symbol in seen:
            continue
        normalized.append(normalized_symbol)
        seen.add(normalized_symbol)
    return normalized


def _normalize_sentiment(value: object) -> str | None:
    return normalize_stock_selection_sentiment(value)


def _news_criteria_requested(criteria: dict[str, object]) -> bool:
    return any(
        _criteria_value_is_active(criteria[key])
        for key in (
            "min_news_article_count",
            "required_news_sentiment",
            "min_news_sentiment_confidence",
        )
    )


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    return normalized or None


def _normalize_asset_type(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None


def _numeric_value(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, int | float):
        return float(value)
    return None


def _traded_amount_from_bar(row: DailyBar) -> float | None:
    amount = _numeric_value(row.amount)
    if amount is not None:
        return amount
    close = _numeric_value(row.close)
    volume = _numeric_value(row.volume)
    if close is None or volume is None:
        return None
    return close * volume


def _nested_numeric_value(payload: object, key: str) -> float | None:
    if not isinstance(payload, dict):
        return None
    return _numeric_value(payload.get(key))


def _candlestick_pattern_codes(payload: object) -> set[str] | None:
    if not isinstance(payload, dict):
        return None

    patterns = payload.get("patterns")
    if not isinstance(patterns, list):
        return None

    codes: set[str] = set()
    for pattern in patterns:
        if not isinstance(pattern, dict):
            continue
        code = pattern.get("code")
        if isinstance(code, str) and code.strip():
            codes.add(code.strip().lower())
    return codes


def _serialize_indicator_value(value: object) -> object:
    if isinstance(value, list):
        return [_serialize_indicator_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize_indicator_value(item) for key, item in value.items()}
    if isinstance(value, str | bool) or value is None:
        return value
    return _numeric_value(value)


def _isoformat_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _exclusive_utc_day_end(value: date | None) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value + timedelta(days=1), time.min, tzinfo=timezone.utc)
