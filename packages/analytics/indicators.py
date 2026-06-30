import pandas as pd


def calculate_ma(close: pd.Series, window: int) -> pd.Series:
    return close.rolling(window=window, min_periods=window).mean()


def calculate_ema(close: pd.Series, span: int) -> pd.Series:
    return close.ewm(span=span, adjust=False).mean()


def calculate_macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    fast_ema = calculate_ema(close, fast)
    slow_ema = calculate_ema(close, slow)
    macd = fast_ema - slow_ema
    signal_line = calculate_ema(macd, signal)
    return pd.DataFrame({"macd": macd, "signal": signal_line, "histogram": macd - signal_line})


def calculate_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window=window, min_periods=window).mean()
    loss = -delta.clip(upper=0).rolling(window=window, min_periods=window).mean()
    rs = gain / loss.where(loss != 0)
    return 100 - (100 / (1 + rs))


def calculate_bollinger_bands(
    close: pd.Series,
    window: int = 20,
    std_dev: float = 2.0,
) -> pd.DataFrame:
    middle = calculate_ma(close, window)
    rolling_std = close.rolling(window=window, min_periods=window).std()
    upper = middle + (rolling_std * std_dev)
    lower = middle - (rolling_std * std_dev)
    return pd.DataFrame({"upper": upper, "middle": middle, "lower": lower})


def calculate_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int = 14,
) -> pd.Series:
    previous_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.rolling(window=window, min_periods=window).mean()
