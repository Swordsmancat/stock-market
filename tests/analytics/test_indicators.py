import pandas as pd

from packages.analytics.indicators import calculate_atr, calculate_bollinger_bands, calculate_ma, calculate_rsi


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
