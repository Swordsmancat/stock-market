import pandas as pd
import pytest

from packages.analytics.candlestick_patterns import detect_latest_candlestick_patterns
from packages.analytics.chip_distribution import calculate_latest_chip_distribution
from packages.analytics.indicators import (
    calculate_atr,
    calculate_bollinger_bands,
    calculate_kdj,
    calculate_ma,
    calculate_macd,
    calculate_rsi,
)


def test_calculate_ma_returns_rolling_average():
    series = pd.Series([1, 2, 3, 4, 5])
    result = calculate_ma(series, window=3)
    assert result.iloc[-1] == 4


def test_calculate_rsi_bounds_between_zero_and_one_hundred():
    series = pd.Series([1, 2, 3, 2, 4, 5, 4, 6, 7, 8, 7, 9, 10, 11, 12])
    result = calculate_rsi(series, window=14)
    assert 0 <= result.dropna().iloc[-1] <= 100


def test_calculate_bollinger_bands_returns_upper_middle_and_lower():
    series = pd.Series([1, 2, 3, 4, 5])
    result = calculate_bollinger_bands(series, window=3)
    latest = result.iloc[-1]
    assert latest["middle"] == 4
    assert latest["upper"] > latest["middle"]
    assert latest["lower"] < latest["middle"]


def test_calculate_atr_returns_average_true_range():
    high = pd.Series([3, 4, 5, 6])
    low = pd.Series([1, 2, 3, 4])
    close = pd.Series([2, 3, 4, 5])
    result = calculate_atr(high, low, close, window=3)
    assert result.iloc[-1] == 2


def test_calculate_macd_returns_signal_and_histogram():
    close = pd.Series([1.0, 2.0, 3.0])

    result = calculate_macd(close, fast=2, slow=3, signal=2)
    latest = result.iloc[-1]

    assert list(result.columns) == ["macd", "signal", "histogram"]
    assert latest["macd"] == pytest.approx(0.30555555555555536, rel=1e-6)
    assert latest["signal"] == pytest.approx(0.24074074074074053, rel=1e-6)
    assert latest["histogram"] == pytest.approx(0.06481481481481483, rel=1e-6)


def test_calculate_kdj_returns_smoothed_k_d_and_j_values():
    high = pd.Series([10.0, 12.0, 14.0])
    low = pd.Series([8.0, 9.0, 10.0])
    close = pd.Series([9.0, 11.0, 13.0])

    result = calculate_kdj(high, low, close, window=3)
    latest = result.iloc[-1]

    assert list(result.columns) == ["k", "d", "j"]
    assert latest["k"] == pytest.approx(61.111111, rel=1e-6)
    assert latest["d"] == pytest.approx(53.703704, rel=1e-6)
    assert latest["j"] == pytest.approx(75.925926, rel=1e-6)


def test_calculate_kdj_handles_flat_price_ranges():
    high = pd.Series([10.0, 10.0, 10.0])
    low = pd.Series([10.0, 10.0, 10.0])
    close = pd.Series([10.0, 10.0, 10.0])

    result = calculate_kdj(high, low, close, window=3)
    latest = result.iloc[-1]

    assert latest["k"] == pytest.approx(50.0)
    assert latest["d"] == pytest.approx(50.0)
    assert latest["j"] == pytest.approx(50.0)


def test_detect_latest_candlestick_patterns_detects_bullish_engulfing():
    result = detect_latest_candlestick_patterns(
        open_prices=pd.Series([10.0, 8.8]),
        high_prices=pd.Series([10.2, 10.8]),
        low_prices=pd.Series([8.8, 8.7]),
        close_prices=pd.Series([9.0, 10.4]),
    )

    assert result["status"] == "evaluated"
    assert result["research_signal_only"] is True
    assert result["pattern_count"] == 1
    assert result["patterns"][0]["code"] == "bullish_engulfing"
    assert result["patterns"][0]["market_bias"] == "bullish"


def test_detect_latest_candlestick_patterns_detects_bearish_engulfing():
    result = detect_latest_candlestick_patterns(
        open_prices=pd.Series([9.0, 10.4]),
        high_prices=pd.Series([10.2, 10.6]),
        low_prices=pd.Series([8.8, 8.6]),
        close_prices=pd.Series([10.0, 8.8]),
    )

    assert result["pattern_count"] == 1
    assert result["patterns"][0]["code"] == "bearish_engulfing"
    assert result["patterns"][0]["market_bias"] == "bearish"


def test_detect_latest_candlestick_patterns_detects_single_bar_shapes():
    doji = detect_latest_candlestick_patterns(
        open_prices=pd.Series([10.0]),
        high_prices=pd.Series([11.0]),
        low_prices=pd.Series([9.0]),
        close_prices=pd.Series([10.05]),
    )
    hammer = detect_latest_candlestick_patterns(
        open_prices=pd.Series([10.2]),
        high_prices=pd.Series([10.5]),
        low_prices=pd.Series([9.0]),
        close_prices=pd.Series([10.4]),
    )
    shooting_star = detect_latest_candlestick_patterns(
        open_prices=pd.Series([10.2]),
        high_prices=pd.Series([11.6]),
        low_prices=pd.Series([10.0]),
        close_prices=pd.Series([10.4]),
    )

    assert [pattern["code"] for pattern in doji["patterns"]] == ["doji"]
    assert [pattern["code"] for pattern in hammer["patterns"]] == ["hammer"]
    assert [pattern["code"] for pattern in shooting_star["patterns"]] == ["shooting_star"]


def test_detect_latest_candlestick_patterns_handles_empty_series():
    result = detect_latest_candlestick_patterns(
        open_prices=pd.Series(dtype="float64"),
        high_prices=pd.Series(dtype="float64"),
        low_prices=pd.Series(dtype="float64"),
        close_prices=pd.Series(dtype="float64"),
    )

    assert result["status"] == "no_data"
    assert result["pattern_count"] == 0
    assert result["patterns"] == []


def test_calculate_latest_chip_distribution_returns_research_payload():
    result = calculate_latest_chip_distribution(
        open_prices=pd.Series([10.0, 10.5, 11.0, 11.2]),
        high_prices=pd.Series([11.0, 11.5, 12.0, 12.1]),
        low_prices=pd.Series([9.5, 10.0, 10.8, 11.0]),
        close_prices=pd.Series([10.8, 11.2, 11.5, 11.8]),
        volumes=pd.Series([1000.0, 2000.0, 3000.0, 4000.0]),
        bucket_count=12,
    )

    assert result["status"] == "evaluated"
    assert result["rule_set"] == "chip_distribution_v1"
    assert result["integration_source"] == "instock_inspired_cyq"
    assert result["research_signal_only"] is True
    assert result["approximation"] == "volume_weighted_without_float_shares"
    assert result["evaluated_bars"] == 4
    assert result["bucket_count"] == 12
    assert result["benefit_ratio"] > 0
    assert result["avg_cost"] >= result["price_min"]
    assert result["avg_cost"] <= result["price_max"]
    assert result["cost_ranges"]["70"]["low"] <= result["cost_ranges"]["70"]["high"]
    assert result["cost_ranges"]["90"]["percent"] == 90
    assert len(result["top_buckets"]) <= 5
    assert len(result["buckets"]) == 12


def test_calculate_latest_chip_distribution_handles_missing_volume():
    result = calculate_latest_chip_distribution(
        open_prices=pd.Series([10.0]),
        high_prices=pd.Series([11.0]),
        low_prices=pd.Series([9.0]),
        close_prices=pd.Series([10.5]),
        volumes=pd.Series([0.0]),
    )

    assert result["status"] == "no_data"
    assert result["research_signal_only"] is True
    assert result["avg_cost"] is None
    assert result["buckets"] == []
