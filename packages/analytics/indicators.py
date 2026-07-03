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


def calculate_kdj(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int = 9,
    k_smoothing: int = 3,
    d_smoothing: int = 3,
) -> pd.DataFrame:
    k_values: list[float] = []
    d_values: list[float] = []
    j_values: list[float] = []
    previous_k = 50.0
    previous_d = 50.0

    for index in range(len(close)):
        if index < window - 1:
            k_values.append(float("nan"))
            d_values.append(float("nan"))
            j_values.append(float("nan"))
            continue

        window_start = index - window + 1
        highest_high = float(high.iloc[window_start : index + 1].max())
        lowest_low = float(low.iloc[window_start : index + 1].min())
        current_close = float(close.iloc[index])
        price_range = highest_high - lowest_low
        rsv = 50.0 if price_range == 0 else ((current_close - lowest_low) / price_range) * 100
        current_k = ((k_smoothing - 1) * previous_k + rsv) / k_smoothing
        current_d = ((d_smoothing - 1) * previous_d + current_k) / d_smoothing
        current_j = (3 * current_k) - (2 * current_d)

        k_values.append(current_k)
        d_values.append(current_d)
        j_values.append(current_j)
        previous_k = current_k
        previous_d = current_d

    return pd.DataFrame({"k": k_values, "d": d_values, "j": j_values})


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
