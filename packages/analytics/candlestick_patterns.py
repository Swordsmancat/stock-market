from dataclasses import dataclass

import pandas as pd


RULE_SET_ID = "candlestick_patterns_v1"
INTEGRATION_SOURCE = "instock_inspired_rules"


@dataclass(frozen=True)
class _Candle:
    open: float
    high: float
    low: float
    close: float

    @property
    def body(self) -> float:
        return abs(self.close - self.open)

    @property
    def price_range(self) -> float:
        return self.high - self.low

    @property
    def body_top(self) -> float:
        return max(self.open, self.close)

    @property
    def body_bottom(self) -> float:
        return min(self.open, self.close)

    @property
    def upper_shadow(self) -> float:
        return self.high - self.body_top

    @property
    def lower_shadow(self) -> float:
        return self.body_bottom - self.low

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        return self.close < self.open


def detect_latest_candlestick_patterns(
    open_prices: pd.Series,
    high_prices: pd.Series,
    low_prices: pd.Series,
    close_prices: pd.Series,
) -> dict[str, object]:
    latest = _latest_candle(open_prices, high_prices, low_prices, close_prices)
    if latest is None:
        return _empty_payload(evaluated_bars=len(close_prices), status="no_data")

    previous = _previous_candle(open_prices, high_prices, low_prices, close_prices)
    patterns: list[dict[str, object]] = []
    if previous is not None:
        patterns.extend(_detect_engulfing(previous, latest))
    patterns.extend(_detect_single_bar_patterns(latest))

    return {
        "rule_set": RULE_SET_ID,
        "integration_source": INTEGRATION_SOURCE,
        "status": "evaluated",
        "research_signal_only": True,
        "evaluated_bars": len(close_prices),
        "pattern_count": len(patterns),
        "patterns": patterns,
    }


def _empty_payload(*, evaluated_bars: int, status: str) -> dict[str, object]:
    return {
        "rule_set": RULE_SET_ID,
        "integration_source": INTEGRATION_SOURCE,
        "status": status,
        "research_signal_only": True,
        "evaluated_bars": evaluated_bars,
        "pattern_count": 0,
        "patterns": [],
    }


def _latest_candle(
    open_prices: pd.Series,
    high_prices: pd.Series,
    low_prices: pd.Series,
    close_prices: pd.Series,
) -> _Candle | None:
    return _candle_at(open_prices, high_prices, low_prices, close_prices, -1)


def _previous_candle(
    open_prices: pd.Series,
    high_prices: pd.Series,
    low_prices: pd.Series,
    close_prices: pd.Series,
) -> _Candle | None:
    if len(close_prices) < 2:
        return None
    return _candle_at(open_prices, high_prices, low_prices, close_prices, -2)


def _candle_at(
    open_prices: pd.Series,
    high_prices: pd.Series,
    low_prices: pd.Series,
    close_prices: pd.Series,
    index: int,
) -> _Candle | None:
    series_length = min(len(open_prices), len(high_prices), len(low_prices), len(close_prices))
    if series_length == 0:
        return None
    if index < 0 and series_length < abs(index):
        return None

    values = [
        float(open_prices.iloc[index]),
        float(high_prices.iloc[index]),
        float(low_prices.iloc[index]),
        float(close_prices.iloc[index]),
    ]
    if any(pd.isna(value) for value in values):
        return None

    open_value, high_value, low_value, close_value = values
    normalized_high = max(high_value, open_value, close_value)
    normalized_low = min(low_value, open_value, close_value)
    if normalized_high <= normalized_low:
        return None

    return _Candle(
        open=open_value,
        high=normalized_high,
        low=normalized_low,
        close=close_value,
    )


def _detect_engulfing(previous: _Candle, latest: _Candle) -> list[dict[str, object]]:
    if previous.body == 0 or latest.body == 0:
        return []

    if (
        previous.is_bearish
        and latest.is_bullish
        and latest.body_bottom <= previous.body_bottom
        and latest.body_top >= previous.body_top
        and latest.body >= previous.body
    ):
        return [
            _pattern(
                "bullish_engulfing",
                "Bullish engulfing",
                "bullish",
                lookback_bars=2,
            )
        ]

    if (
        previous.is_bullish
        and latest.is_bearish
        and latest.body_top >= previous.body_top
        and latest.body_bottom <= previous.body_bottom
        and latest.body >= previous.body
    ):
        return [
            _pattern(
                "bearish_engulfing",
                "Bearish engulfing",
                "bearish",
                lookback_bars=2,
            )
        ]

    return []


def _detect_single_bar_patterns(latest: _Candle) -> list[dict[str, object]]:
    patterns: list[dict[str, object]] = []
    if latest.body / latest.price_range <= 0.1:
        patterns.append(_pattern("doji", "Doji", "neutral", lookback_bars=1))

    if _is_hammer(latest):
        patterns.append(_pattern("hammer", "Hammer", "bullish", lookback_bars=1))

    if _is_shooting_star(latest):
        patterns.append(
            _pattern(
                "shooting_star",
                "Shooting star",
                "bearish",
                lookback_bars=1,
            )
        )

    return patterns


def _is_hammer(candle: _Candle) -> bool:
    if candle.body == 0:
        return False
    lower_shadow_is_long = candle.lower_shadow >= max(candle.body * 2, candle.price_range * 0.45)
    upper_shadow_is_small = candle.upper_shadow <= candle.body
    body_sits_near_high = candle.body_top >= candle.low + (candle.price_range * 0.6)
    return lower_shadow_is_long and upper_shadow_is_small and body_sits_near_high


def _is_shooting_star(candle: _Candle) -> bool:
    if candle.body == 0:
        return False
    upper_shadow_is_long = candle.upper_shadow >= max(candle.body * 2, candle.price_range * 0.45)
    lower_shadow_is_small = candle.lower_shadow <= candle.body
    body_sits_near_low = candle.body_bottom <= candle.low + (candle.price_range * 0.4)
    return upper_shadow_is_long and lower_shadow_is_small and body_sits_near_low


def _pattern(code: str, label: str, market_bias: str, *, lookback_bars: int) -> dict[str, object]:
    return {
        "code": code,
        "label": label,
        "market_bias": market_bias,
        "lookback_bars": lookback_bars,
        "rule_set": RULE_SET_ID,
    }
