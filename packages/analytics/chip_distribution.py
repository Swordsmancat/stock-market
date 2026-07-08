from dataclasses import dataclass

import pandas as pd


RULE_SET_ID = "chip_distribution_v1"
INTEGRATION_SOURCE = "instock_inspired_cyq"
APPROXIMATION_NOTE = "volume_weighted_without_float_shares"
DEFAULT_LOOKBACK_DAYS = 210
DEFAULT_BUCKET_COUNT = 60


@dataclass(frozen=True)
class _ChipBar:
    open: float
    high: float
    low: float
    close: float
    volume: float

    @property
    def average_price(self) -> float:
        return (self.open + self.high + self.low + self.close) / 4


def calculate_latest_chip_distribution(
    open_prices: pd.Series,
    high_prices: pd.Series,
    low_prices: pd.Series,
    close_prices: pd.Series,
    volumes: pd.Series,
    *,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    bucket_count: int = DEFAULT_BUCKET_COUNT,
) -> dict[str, object]:
    bars = _valid_bars(open_prices, high_prices, low_prices, close_prices, volumes)
    if not bars:
        return _empty_payload(status="no_data", evaluated_bars=0, lookback_days=lookback_days)

    if lookback_days <= 0:
        return _empty_payload(
            status="invalid_input",
            evaluated_bars=len(bars),
            lookback_days=lookback_days,
        )

    selected_bars = bars[-lookback_days:]
    price_min = min(bar.low for bar in selected_bars)
    price_max = max(bar.high for bar in selected_bars)
    current_price = selected_bars[-1].close
    total_volume = sum(bar.volume for bar in selected_bars)
    if total_volume <= 0 or price_max < price_min:
        return _empty_payload(
            status="no_data",
            evaluated_bars=len(selected_bars),
            lookback_days=lookback_days,
        )

    centers = _price_centers(price_min, price_max, bucket_count)
    distribution = [0.0 for _ in centers]
    for bar in selected_bars:
        _allocate_bar_volume(distribution, centers, bar)

    total_chips = sum(distribution)
    if total_chips <= 0:
        return _empty_payload(
            status="no_data",
            evaluated_bars=len(selected_bars),
            lookback_days=lookback_days,
        )

    shares = [value / total_chips for value in distribution]
    cumulative_shares = _cumulative(shares)
    benefit_ratio = sum(share for center, share in zip(centers, shares, strict=True) if center <= current_price)
    average_cost = sum(center * share for center, share in zip(centers, shares, strict=True))
    median_cost = _cost_at_share(centers, cumulative_shares, 0.5)
    range_70 = _cost_range(centers, cumulative_shares, 0.7)
    range_90 = _cost_range(centers, cumulative_shares, 0.9)

    return {
        "rule_set": RULE_SET_ID,
        "integration_source": INTEGRATION_SOURCE,
        "status": "evaluated",
        "research_signal_only": True,
        "approximation": APPROXIMATION_NOTE,
        "lookback_days": lookback_days,
        "evaluated_bars": len(selected_bars),
        "bucket_count": len(centers),
        "current_price": _rounded(current_price),
        "price_min": _rounded(price_min),
        "price_max": _rounded(price_max),
        "total_volume": _rounded(total_volume),
        "benefit_ratio": _rounded_ratio(benefit_ratio),
        "avg_cost": _rounded(median_cost),
        "weighted_average_cost": _rounded(average_cost),
        "cost_ranges": {
            "70": range_70,
            "90": range_90,
        },
        "top_buckets": _top_buckets(centers, shares, limit=5),
        "buckets": _buckets(centers, shares, cumulative_shares),
        "limitations": [
            "uses daily OHLCV bars only",
            "does not know free-float shares or true turnover rate",
            "not comparable to provider-grade CYQ without reviewed float-share inputs",
        ],
    }


def _empty_payload(*, status: str, evaluated_bars: int, lookback_days: int) -> dict[str, object]:
    return {
        "rule_set": RULE_SET_ID,
        "integration_source": INTEGRATION_SOURCE,
        "status": status,
        "research_signal_only": True,
        "approximation": APPROXIMATION_NOTE,
        "lookback_days": lookback_days,
        "evaluated_bars": evaluated_bars,
        "bucket_count": 0,
        "benefit_ratio": None,
        "avg_cost": None,
        "weighted_average_cost": None,
        "cost_ranges": {},
        "top_buckets": [],
        "buckets": [],
        "limitations": [
            "uses daily OHLCV bars only",
            "does not know free-float shares or true turnover rate",
        ],
    }


def _valid_bars(
    open_prices: pd.Series,
    high_prices: pd.Series,
    low_prices: pd.Series,
    close_prices: pd.Series,
    volumes: pd.Series,
) -> list[_ChipBar]:
    bars: list[_ChipBar] = []
    series_length = min(
        len(open_prices),
        len(high_prices),
        len(low_prices),
        len(close_prices),
        len(volumes),
    )
    for index in range(series_length):
        values = [
            float(open_prices.iloc[index]),
            float(high_prices.iloc[index]),
            float(low_prices.iloc[index]),
            float(close_prices.iloc[index]),
            float(volumes.iloc[index]),
        ]
        if any(pd.isna(value) for value in values):
            continue

        open_value, high_value, low_value, close_value, volume = values
        if volume <= 0:
            continue

        normalized_high = max(high_value, open_value, close_value)
        normalized_low = min(low_value, open_value, close_value)
        if normalized_high < normalized_low:
            continue

        bars.append(
            _ChipBar(
                open=open_value,
                high=normalized_high,
                low=normalized_low,
                close=close_value,
                volume=volume,
            )
        )
    return bars


def _price_centers(price_min: float, price_max: float, bucket_count: int) -> list[float]:
    if price_max == price_min:
        return [price_min]

    normalized_bucket_count = max(2, bucket_count)
    step = (price_max - price_min) / (normalized_bucket_count - 1)
    return [price_min + (step * index) for index in range(normalized_bucket_count)]


def _allocate_bar_volume(distribution: list[float], centers: list[float], bar: _ChipBar) -> None:
    if bar.high == bar.low:
        nearest_index = min(range(len(centers)), key=lambda index: abs(centers[index] - bar.close))
        distribution[nearest_index] += bar.volume
        return

    weights: list[float] = []
    for center in centers:
        if center < bar.low or center > bar.high:
            weights.append(0.0)
        elif center <= bar.average_price:
            denominator = bar.average_price - bar.low
            weights.append(1.0 if denominator == 0 else max(0.0, (center - bar.low) / denominator))
        else:
            denominator = bar.high - bar.average_price
            weights.append(1.0 if denominator == 0 else max(0.0, (bar.high - center) / denominator))

    weight_total = sum(weights)
    if weight_total <= 0:
        nearest_index = min(range(len(centers)), key=lambda index: abs(centers[index] - bar.close))
        distribution[nearest_index] += bar.volume
        return

    for index, weight in enumerate(weights):
        if weight > 0:
            distribution[index] += bar.volume * (weight / weight_total)


def _cumulative(values: list[float]) -> list[float]:
    total = 0.0
    result: list[float] = []
    for value in values:
        total += value
        result.append(total)
    if result:
        result[-1] = 1.0
    return result


def _cost_at_share(centers: list[float], cumulative_shares: list[float], share: float) -> float:
    if not centers:
        return 0.0
    for center, cumulative_share in zip(centers, cumulative_shares, strict=True):
        if cumulative_share >= share:
            return center
    return centers[-1]


def _cost_range(centers: list[float], cumulative_shares: list[float], percent: float) -> dict[str, object]:
    lower_share = (1 - percent) / 2
    upper_share = (1 + percent) / 2
    low = _cost_at_share(centers, cumulative_shares, lower_share)
    high = _cost_at_share(centers, cumulative_shares, upper_share)
    width = max(0.0, high - low)
    denominator = high + low
    return {
        "percent": int(percent * 100),
        "low": _rounded(low),
        "high": _rounded(high),
        "width": _rounded(width),
        "concentration": _rounded_ratio(0.0 if denominator == 0 else width / denominator),
    }


def _top_buckets(centers: list[float], shares: list[float], *, limit: int) -> list[dict[str, float]]:
    ranked = sorted(
        ((center, share) for center, share in zip(centers, shares, strict=True) if share > 0),
        key=lambda item: item[1],
        reverse=True,
    )
    return [{"price": _rounded(center), "share": _rounded_ratio(share)} for center, share in ranked[:limit]]


def _buckets(
    centers: list[float],
    shares: list[float],
    cumulative_shares: list[float],
) -> list[dict[str, float]]:
    return [
        {
            "price": _rounded(center),
            "share": _rounded_ratio(share),
            "cumulative_share": _rounded_ratio(cumulative_share),
        }
        for center, share, cumulative_share in zip(centers, shares, cumulative_shares, strict=True)
    ]


def _rounded(value: float) -> float:
    return round(float(value), 6)


def _rounded_ratio(value: float) -> float:
    return round(float(value), 8)
