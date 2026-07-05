import pandas as pd
import pytest

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
