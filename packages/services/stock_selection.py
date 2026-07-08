from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from packages.domain.models import DailyBar, FundamentalSnapshot, Instrument, Market, TechnicalIndicator


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
    limit: int = 20,
) -> dict[str, object]:
    criteria = _criteria_payload(
        max_pe_ratio=max_pe_ratio,
        min_revenue_growth=min_revenue_growth,
        min_net_margin=min_net_margin,
        min_rsi=min_rsi,
        max_rsi=max_rsi,
        require_price_above_ma=require_price_above_ma,
    )
    if not _has_active_criteria(criteria):
        return {
            "status": "invalid_request",
            "rule_set": RULE_SET_ID,
            "research_signal_only": True,
            "criteria": criteria,
            "count": 0,
            "items": [],
            "diagnostics": [
                {
                    "code": "NO_SELECTION_CRITERIA",
                    "message": "At least one fundamental or technical selection criterion is required.",
                }
            ],
            "disclaimer": DISCLAIMER,
        }

    instruments = _candidate_instruments(
        session=session,
        symbols=symbols,
        market=market,
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
) -> dict[str, object]:
    return {
        "max_pe_ratio": max_pe_ratio,
        "min_revenue_growth": min_revenue_growth,
        "min_net_margin": min_net_margin,
        "min_rsi": min_rsi,
        "max_rsi": max_rsi,
        "require_price_above_ma": require_price_above_ma,
    }


def _has_active_criteria(criteria: dict[str, object]) -> bool:
    return any(value is not None and value is not False for value in criteria.values())


def _candidate_instruments(
    *,
    session: Session,
    symbols: list[str] | None,
    market: str | None,
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

    criteria_count = max(1, len([rule for rule in matched_rules if rule["status"] == "matched"]))
    evidence_citations = _evidence_citations(
        symbol=symbol,
        latest_bar=latest_bar,
        indicators=latest_indicators,
        fundamentals=latest_fundamentals,
    )

    return {
        "matched": True,
        "diagnostics": diagnostics,
        "item": {
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
        },
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
            row.indicator_code: row.value_json["value"]
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
) -> list[str]:
    citations = [f"bars_1d:{symbol}:{latest_bar.trade_date.isoformat()}"]
    indicator_as_of = indicators.get("as_of")
    if isinstance(indicator_as_of, str):
        citations.append(f"technical_indicators:{symbol}:{indicator_as_of}")
    if fundamentals is not None:
        citations.append(f"fundamental_metrics:{symbol}:{fundamentals.as_of.isoformat()}")
    return citations


def _active_criteria_count(criteria: dict[str, object]) -> int:
    return sum(1 for value in criteria.values() if value is not None and value is not False)


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


def _isoformat_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()
