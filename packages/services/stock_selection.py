from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

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


RULE_SET_ID = "instock_composite_selection_v1"
DISCLAIMER = "Composite stock selection is a research aid only and is not investment advice."
MAX_SCREENING_SYMBOLS = 100


def screen_local_stock_selection(
    *,
    session: Session,
    symbols: list[str] | None = None,
    market: str | None = None,
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
    min_news_article_count: int | None = None,
    required_news_sentiment: str | None = None,
    min_news_sentiment_confidence: float | None = None,
    watchlist_only: bool = False,
    limit: int = 20,
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
                watchlist_only=watchlist_only,
            ),
            "criteria": criteria,
            "count": 0,
            "items": [],
            "diagnostics": [
                {
                    "code": "NO_SELECTION_CRITERIA",
                    "message": "At least one fundamental, technical, or news selection criterion is required.",
                }
            ],
            "disclaimer": DISCLAIMER,
        }

    instruments = _candidate_instruments(
        session=session,
        symbols=symbols,
        market=market,
        watchlist_only=watchlist_only,
        limit=MAX_SCREENING_SYMBOLS,
    )
    diagnostics: list[dict[str, object]] = []
    items: list[dict[str, object]] = []

    for instrument in instruments:
        evaluation = _evaluate_instrument(instrument, criteria, session=session)
        diagnostics.extend(evaluation["diagnostics"])
        if evaluation["matched"]:
            items.append(evaluation["item"])

    ranked_items = sorted(
        items,
        key=lambda item: (
            float(item.get("score", 0.0)),
            str(item.get("symbol", "")),
        ),
        reverse=True,
    )[: max(1, min(limit, 100))]

    return {
        "status": "ok",
        "rule_set": RULE_SET_ID,
        "research_signal_only": True,
        "candidate_scope": _candidate_scope_payload(
            symbols=symbols,
            market=market,
            watchlist_only=watchlist_only,
        ),
        "criteria": criteria,
        "count": len(ranked_items),
        "items": ranked_items,
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
    min_news_article_count: int | None,
    required_news_sentiment: str | None,
    min_news_sentiment_confidence: float | None,
) -> dict[str, object]:
    return {
        "max_pe_ratio": max_pe_ratio,
        "min_revenue_growth": min_revenue_growth,
        "min_net_margin": min_net_margin,
        "min_rsi": min_rsi,
        "max_rsi": max_rsi,
        "require_price_above_ma": require_price_above_ma,
        "required_pattern_codes": _normalize_pattern_codes(required_pattern_codes),
        "min_mfi": min_mfi,
        "max_mfi": max_mfi,
        "min_william_r": min_william_r,
        "max_william_r": max_william_r,
        "min_chip_benefit_ratio": min_chip_benefit_ratio,
        "max_chip_benefit_ratio": max_chip_benefit_ratio,
        "min_news_article_count": min_news_article_count,
        "required_news_sentiment": _normalize_sentiment(required_news_sentiment),
        "min_news_sentiment_confidence": min_news_sentiment_confidence,
    }


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
    watchlist_only: bool,
    limit: int,
) -> list[Instrument]:
    query = session.query(Instrument).outerjoin(Market, Instrument.market_id == Market.id)
    query = query.filter(Instrument.is_active.is_(True))

    normalized_symbols = _normalize_symbols(symbols)
    if normalized_symbols:
        query = query.filter(Instrument.symbol.in_(normalized_symbols))

    normalized_market = _normalize_optional_text(market)
    if normalized_market:
        query = query.filter(Market.code == normalized_market)

    if watchlist_only:
        watchlist_entries = get_active_watchlist_scope(session)
        if not watchlist_entries:
            return []
        pair_filters = [
            and_(Instrument.symbol == entry["symbol"], Market.code == entry["market"])
            for entry in watchlist_entries
        ]
        query = query.filter(or_(*pair_filters))

    return query.order_by(Instrument.symbol).limit(limit).all()


def _evaluate_instrument(
    instrument: Instrument,
    criteria: dict[str, object],
    *,
    session: Session,
) -> dict[str, object]:
    symbol = instrument.symbol.upper()
    diagnostics: list[dict[str, object]] = []
    latest_bar = _latest_daily_bar(instrument, session=session)
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

    latest_indicators = _latest_indicator_payload(instrument, session=session)
    latest_fundamentals = _latest_fundamental_snapshot(symbol, session=session)
    matched_rules: list[dict[str, object]] = []

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
        news_sentiment = _latest_news_sentiment_payload(symbol, session=session)
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


def _latest_daily_bar(instrument: Instrument, *, session: Session) -> DailyBar | None:
    return (
        session.query(DailyBar)
        .filter(DailyBar.instrument_id == instrument.id)
        .order_by(DailyBar.trade_date.desc())
        .first()
    )


def _latest_indicator_payload(instrument: Instrument, *, session: Session) -> dict[str, object]:
    latest = (
        session.query(TechnicalIndicator)
        .filter(TechnicalIndicator.instrument_id == instrument.id)
        .filter(TechnicalIndicator.timeframe == "1d")
        .order_by(TechnicalIndicator.as_of.desc())
        .first()
    )
    if latest is None:
        return {"as_of": None, "values": {}}

    rows = (
        session.query(TechnicalIndicator)
        .filter(TechnicalIndicator.instrument_id == instrument.id)
        .filter(TechnicalIndicator.timeframe == "1d")
        .filter(TechnicalIndicator.as_of == latest.as_of)
        .all()
    )
    return {
        "as_of": _isoformat_utc(latest.as_of),
        "values": {
            row.indicator_code: _serialize_indicator_value(row.value_json["value"])
            for row in rows
            if isinstance(row.value_json, dict) and "value" in row.value_json
        },
    }


def _latest_fundamental_snapshot(symbol: str, *, session: Session) -> FundamentalSnapshot | None:
    return (
        session.query(FundamentalSnapshot)
        .filter(FundamentalSnapshot.symbol == symbol)
        .order_by(FundamentalSnapshot.as_of.desc())
        .first()
    )


def _latest_news_sentiment_payload(symbol: str, *, session: Session) -> dict[str, object]:
    rows = (
        session.query(NewsArticle, SentimentSignal)
        .join(SentimentSignal, SentimentSignal.article_id == NewsArticle.id)
        .filter(NewsArticle.symbol == symbol)
        .order_by(NewsArticle.published_at.desc(), SentimentSignal.created_at.desc())
        .all()
    )
    if not rows:
        return {
            "article_count": 0,
            "latest_sentiment": None,
            "latest_confidence": None,
            "latest_published_at": None,
            "latest_title": None,
            "latest_source": None,
            "latest_url": None,
            "citation_id": None,
        }

    latest_article, latest_signal = rows[0]
    return {
        "article_count": len({article.id for article, _signal in rows}),
        "latest_sentiment": latest_signal.sentiment,
        "latest_confidence": _numeric_value(latest_signal.confidence),
        "latest_published_at": _isoformat_utc(latest_article.published_at),
        "latest_title": latest_article.title,
        "latest_source": latest_article.source,
        "latest_url": latest_article.url,
        "citation_id": f"news:{symbol}:{latest_article.id}",
    }


def _serialize_daily_bar(row: DailyBar) -> dict[str, object]:
    return {
        "trade_date": row.trade_date.isoformat(),
        "open": _numeric_value(row.open),
        "high": _numeric_value(row.high),
        "low": _numeric_value(row.low),
        "close": _numeric_value(row.close),
        "volume": _numeric_value(row.volume),
        "amount": _numeric_value(row.amount),
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
    watchlist_only: bool,
) -> dict[str, object]:
    return {
        "symbols": _normalize_symbols(symbols),
        "market": _normalize_optional_text(market),
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


def _normalize_pattern_codes(pattern_codes: list[str] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for pattern_code in pattern_codes or []:
        normalized_code = pattern_code.strip().lower()
        if not normalized_code or normalized_code in seen:
            continue
        normalized.append(normalized_code)
        seen.add(normalized_code)
    return normalized


def _normalize_sentiment(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    return normalized or None


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


def _numeric_value(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, int | float):
        return float(value)
    return None


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
