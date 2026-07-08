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


def calculate_roc(close: pd.Series, window: int = 12) -> pd.Series:
    return ((close / close.shift(window)) - 1) * 100


def calculate_bias(close: pd.Series, window: int = 6) -> pd.Series:
    moving_average = calculate_ma(close, window)
    return ((close - moving_average) / moving_average.where(moving_average != 0)) * 100


def calculate_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    obv_values: list[float] = []
    current_obv = 0.0

    for index in range(len(close)):
        if index == 0:
            obv_values.append(current_obv)
            continue

        current_close = float(close.iloc[index])
        previous_close = float(close.iloc[index - 1])
        current_volume = float(volume.iloc[index])
        if current_close > previous_close:
            current_obv += current_volume
        elif current_close < previous_close:
            current_obv -= current_volume
        obv_values.append(current_obv)

    return pd.Series(obv_values, index=close.index)


def calculate_cci(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int = 20,
) -> pd.Series:
    typical_price = (high + low + close) / 3
    moving_average = typical_price.rolling(window=window, min_periods=window).mean()
    mean_deviation = typical_price.rolling(window=window, min_periods=window).apply(
        lambda values: abs(values - values.mean()).mean(),
        raw=False,
    )
    denominator = 0.015 * mean_deviation
    return (typical_price - moving_average) / denominator.where(denominator != 0)


def calculate_william_r(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int = 14,
) -> pd.Series:
    highest_high = high.rolling(window=window, min_periods=window).max()
    lowest_low = low.rolling(window=window, min_periods=window).min()
    price_range = highest_high - lowest_low
    return ((highest_high - close) / price_range.where(price_range != 0)) * -100


def calculate_mfi(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
    window: int = 14,
) -> pd.Series:
    typical_price = (high + low + close) / 3
    raw_money_flow = typical_price * volume
    positive_flow = raw_money_flow.where(typical_price > typical_price.shift(1), 0.0)
    negative_flow = raw_money_flow.where(typical_price < typical_price.shift(1), 0.0)
    positive_sum = positive_flow.rolling(window=window, min_periods=window).sum()
    negative_sum = negative_flow.rolling(window=window, min_periods=window).sum()
    money_flow_ratio = positive_sum / negative_sum.where(negative_sum != 0)
    mfi = 100 - (100 / (1 + money_flow_ratio))
    mfi = mfi.mask((negative_sum == 0) & (positive_sum > 0), 100.0)
    return mfi.mask((positive_sum == 0) & (negative_sum > 0), 0.0)


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
