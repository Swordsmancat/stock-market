"""InStock-inspired research strategy screening helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

RULE_SET_ID = "instock_strategy_screening_v1"
INTEGRATION_SOURCE = "myhhub_stock_inspired_strategies"
DISCLAIMER = "Strategy screening signals are research aids only and are not investment advice."

DEFAULT_STRATEGY_CODES = (
    "volume_price_breakout",
    "turtle_breakout",
    "ma_trend_up",
)

STRATEGY_METADATA = {
    "volume_price_breakout": {
        "label": "Volume price breakout",
        "market_bias": "bullish",
        "min_bars": 6,
        "inspired_by": "instock.core.strategy.enter.check_volume",
    },
    "turtle_breakout": {
        "label": "Turtle breakout",
        "market_bias": "bullish",
        "min_bars": 60,
        "inspired_by": "instock.core.strategy.turtle_trade.check_enter",
    },
    "ma_trend_up": {
        "label": "MA trend up",
        "market_bias": "bullish",
        "min_bars": 60,
        "inspired_by": "instock.core.strategy.keep_increasing.check",
    },
}

VOLUME_PRICE_CHANGE_PERCENT = 2.0
VOLUME_RATIO_THRESHOLD = 2.0
VOLUME_AMOUNT_FLOOR = 200_000_000.0
TURTLE_LOOKBACK_BARS = 60
MA_TREND_WINDOW = 30
MA_TREND_GROWTH_RATIO = 1.2


def normalize_strategy_bars(items: object) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []

    bars: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        timestamp = item.get("timestamp")
        open_price = _read_float(item.get("open"))
        high = _read_float(item.get("high"))
        low = _read_float(item.get("low"))
        close = _read_float(item.get("close"))
        if not isinstance(timestamp, str) or open_price is None or close is None:
            continue

        normalized_bar: dict[str, Any] = {
            "timestamp": timestamp,
            "open": open_price,
            "high": high if high is not None else max(open_price, close),
            "low": low if low is not None else min(open_price, close),
            "close": close,
        }
        volume = _read_float(item.get("volume"))
        if volume is not None:
            normalized_bar["volume"] = volume
        amount = _read_float(item.get("amount"))
        if amount is not None:
            normalized_bar["amount"] = amount
        bars.append(normalized_bar)

    return bars


def screen_latest_instock_strategies(
    symbol: str,
    bars: list[dict[str, Any]],
    strategy_codes: list[str] | None = None,
) -> dict[str, Any]:
    normalized_symbol = symbol.strip().upper()
    requested_strategy_codes, diagnostics = _normalize_strategy_codes(strategy_codes)
    normalized_bars = normalize_strategy_bars(bars)

    if not normalized_bars:
        return {
            "symbol": normalized_symbol,
            "status": "no_data",
            "rule_set": RULE_SET_ID,
            "integration_source": INTEGRATION_SOURCE,
            "research_signal_only": True,
            "evaluated_bars": 0,
            "strategy_codes": requested_strategy_codes,
            "match_count": 0,
            "matches": [],
            "diagnostics": [
                *diagnostics,
                {
                    "code": "NO_BARS",
                    "message": "No valid OHLC bars were available for strategy screening.",
                },
            ],
            "disclaimer": DISCLAIMER,
        }

    matches: list[dict[str, Any]] = []
    evaluated_strategy_count = 0
    for strategy_code in requested_strategy_codes:
        metadata = STRATEGY_METADATA[strategy_code]
        min_bars = int(metadata["min_bars"])
        if len(normalized_bars) < min_bars:
            diagnostics.append(
                {
                    "code": "INSUFFICIENT_BARS",
                    "strategy_code": strategy_code,
                    "required_bars": min_bars,
                    "available_bars": len(normalized_bars),
                    "message": "Not enough valid bars were available for this strategy rule.",
                }
            )
            continue

        evaluated_strategy_count += 1
        match = _evaluate_strategy(normalized_symbol, normalized_bars, strategy_code)
        if match is not None:
            matches.append(match)

    if matches:
        status = "matched"
    elif evaluated_strategy_count == 0:
        status = "insufficient_data"
    else:
        status = "no_match"
        diagnostics.append(
            {
                "code": "NO_STRATEGY_MATCH",
                "message": "No requested strategy rules matched the latest bar.",
            }
        )

    return {
        "symbol": normalized_symbol,
        "status": status,
        "rule_set": RULE_SET_ID,
        "integration_source": INTEGRATION_SOURCE,
        "research_signal_only": True,
        "evaluated_at": _utc_timestamp(),
        "evaluated_bars": len(normalized_bars),
        "as_of": str(normalized_bars[-1]["timestamp"]),
        "strategy_codes": requested_strategy_codes,
        "match_count": len(matches),
        "matches": matches,
        "diagnostics": diagnostics,
        "disclaimer": DISCLAIMER,
    }


def _normalize_strategy_codes(strategy_codes: list[str] | None) -> tuple[list[str], list[dict[str, Any]]]:
    if not strategy_codes:
        return list(DEFAULT_STRATEGY_CODES), []

    diagnostics: list[dict[str, Any]] = []
    normalized_codes: list[str] = []
    for strategy_code in strategy_codes:
        normalized_code = strategy_code.strip().lower()
        if not normalized_code:
            continue
        if normalized_code not in STRATEGY_METADATA:
            diagnostics.append(
                {
                    "code": "UNKNOWN_STRATEGY_CODE",
                    "strategy_code": normalized_code,
                    "message": "Unknown strategy code was ignored.",
                }
            )
            continue
        if normalized_code not in normalized_codes:
            normalized_codes.append(normalized_code)

    return normalized_codes or list(DEFAULT_STRATEGY_CODES), diagnostics


def _evaluate_strategy(
    symbol: str,
    bars: list[dict[str, Any]],
    strategy_code: str,
) -> dict[str, Any] | None:
    if strategy_code == "volume_price_breakout":
        return _detect_volume_price_breakout(symbol, bars)
    if strategy_code == "turtle_breakout":
        return _detect_turtle_breakout(symbol, bars)
    if strategy_code == "ma_trend_up":
        return _detect_ma_trend_up(symbol, bars)
    return None


def _detect_volume_price_breakout(symbol: str, bars: list[dict[str, Any]]) -> dict[str, Any] | None:
    latest = bars[-1]
    previous = bars[-2]
    latest_close = float(latest["close"])
    previous_close = float(previous["close"])
    latest_open = float(latest["open"])
    if previous_close <= 0:
        return None

    price_change_percent = ((latest_close - previous_close) / previous_close) * 100
    latest_volume = _read_float(latest.get("volume"))
    previous_volumes = [
        float(bar["volume"])
        for bar in bars[-6:-1]
        if _read_float(bar.get("volume")) is not None and float(bar["volume"]) > 0
    ]
    if latest_volume is None or latest_volume <= 0 or not previous_volumes:
        return None

    average_volume = sum(previous_volumes) / len(previous_volumes)
    if average_volume <= 0:
        return None

    volume_ratio = latest_volume / average_volume
    traded_amount = _read_float(latest.get("amount"))
    if traded_amount is None:
        traded_amount = latest_close * latest_volume

    if (
        price_change_percent < VOLUME_PRICE_CHANGE_PERCENT
        or latest_close < latest_open
        or volume_ratio < VOLUME_RATIO_THRESHOLD
        or traded_amount < VOLUME_AMOUNT_FLOOR
    ):
        return None

    return _strategy_match(
        symbol,
        "volume_price_breakout",
        as_of=str(latest["timestamp"]),
        confidence=0.68,
        reason="Latest bar rose on at least 2x recent average volume with sufficient traded amount.",
        data={
            "close": latest_close,
            "open": latest_open,
            "previous_close": previous_close,
            "price_change_percent": price_change_percent,
            "volume": latest_volume,
            "average_volume": average_volume,
            "volume_ratio": volume_ratio,
            "traded_amount": traded_amount,
            "amount_floor": VOLUME_AMOUNT_FLOOR,
        },
    )


def _detect_turtle_breakout(symbol: str, bars: list[dict[str, Any]]) -> dict[str, Any] | None:
    window_bars = bars[-TURTLE_LOOKBACK_BARS:]
    latest = window_bars[-1]
    latest_close = float(latest["close"])
    prior_window_high = max(float(bar["close"]) for bar in window_bars[:-1])
    if latest_close <= prior_window_high:
        return None

    return _strategy_match(
        symbol,
        "turtle_breakout",
        as_of=str(latest["timestamp"]),
        confidence=0.66,
        reason="Latest close set a new high within the configured lookback window.",
        data={
            "close": latest_close,
            "prior_lookback_high": prior_window_high,
            "lookback_bars": TURTLE_LOOKBACK_BARS,
        },
    )


def _detect_ma_trend_up(symbol: str, bars: list[dict[str, Any]]) -> dict[str, Any] | None:
    closes = [float(bar["close"]) for bar in bars]
    latest = bars[-1]
    checkpoints = {
        "ma_30_bars_ago": _moving_average_at(closes, len(closes) - 31, MA_TREND_WINDOW),
        "ma_20_bars_ago": _moving_average_at(closes, len(closes) - 21, MA_TREND_WINDOW),
        "ma_10_bars_ago": _moving_average_at(closes, len(closes) - 11, MA_TREND_WINDOW),
        "ma_latest": _moving_average_at(closes, len(closes) - 1, MA_TREND_WINDOW),
    }
    if any(value is None for value in checkpoints.values()):
        return None

    first = float(checkpoints["ma_30_bars_ago"])
    second = float(checkpoints["ma_20_bars_ago"])
    third = float(checkpoints["ma_10_bars_ago"])
    latest_ma = float(checkpoints["ma_latest"])
    if not (first < second < third < latest_ma and latest_ma > first * MA_TREND_GROWTH_RATIO):
        return None

    return _strategy_match(
        symbol,
        "ma_trend_up",
        as_of=str(latest["timestamp"]),
        confidence=0.64,
        reason="30-day moving average rose across 30/20/10/latest checkpoints.",
        data={
            **checkpoints,
            "growth_ratio": latest_ma / first,
            "required_growth_ratio": MA_TREND_GROWTH_RATIO,
            "ma_window": MA_TREND_WINDOW,
        },
    )


def _moving_average_at(closes: list[float], end_index: int, window: int) -> float | None:
    start_index = end_index - window + 1
    if start_index < 0 or end_index >= len(closes):
        return None
    window_values = closes[start_index : end_index + 1]
    if len(window_values) != window:
        return None
    return sum(window_values) / window


def _strategy_match(
    symbol: str,
    strategy_code: str,
    *,
    as_of: str,
    confidence: float,
    reason: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    metadata = STRATEGY_METADATA[strategy_code]
    return {
        "symbol": symbol,
        "code": strategy_code,
        "label": metadata["label"],
        "market_bias": metadata["market_bias"],
        "confidence": confidence,
        "as_of": as_of,
        "rule_set": RULE_SET_ID,
        "integration_source": INTEGRATION_SOURCE,
        "inspired_by": metadata["inspired_by"],
        "research_signal_only": True,
        "reason": reason,
        "data": data,
    }


def _read_float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
