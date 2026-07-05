from datetime import date, timedelta

from packages.services.smart_recommendations import evaluate_recommendation_signals


def build_daily_bar(day_index: int, close: float, volume: float = 1_000.0) -> dict[str, object]:
    timestamp = (date(2026, 1, 1) + timedelta(days=day_index)).isoformat()
    return {
        "timestamp": timestamp,
        "open": close,
        "high": close + 1,
        "low": close - 1,
        "close": close,
        "volume": volume,
    }


def append_forward_bars(bars: list[dict[str, object]], closes: list[float]) -> list[dict[str, object]]:
    result = list(bars)
    start_index = len(result)
    for offset, close in enumerate(closes):
        result.append(build_daily_bar(start_index + offset, close))
    return result


def build_breakout_bars() -> list[dict[str, object]]:
    baseline_bars = [build_daily_bar(day_index, 100.0) for day_index in range(28)]
    signal_bars = [build_daily_bar(28, 95.0), build_daily_bar(29, 110.0)]
    return append_forward_bars(baseline_bars + signal_bars, [112.0, 114.0, 116.0, 118.0, 120.0])


def build_volume_anomaly_bars() -> list[dict[str, object]]:
    baseline_bars = [build_daily_bar(day_index, 100.0, volume=1_000.0) for day_index in range(29)]
    signal_bar = build_daily_bar(29, 101.0, volume=3_000.0)
    return append_forward_bars(baseline_bars + [signal_bar], [102.0, 103.0, 104.0, 105.0, 106.0])


def build_oversold_rebound_bars() -> list[dict[str, object]]:
    stable_bars = [build_daily_bar(day_index, 100.0) for day_index in range(24)]
    stable_bars[16] = build_daily_bar(16, 90.0)
    oversold_closes = [96.0, 92.0, 88.0, 84.0, 80.0, 76.0]
    oversold_bars = [build_daily_bar(24 + offset, close) for offset, close in enumerate(oversold_closes)]
    return append_forward_bars(stable_bars + oversold_bars, [78.0, 80.0, 82.0, 84.0, 86.0])


def build_strong_momentum_bars() -> list[dict[str, object]]:
    stable_bars = [build_daily_bar(day_index, 100.0 + day_index * 0.1) for day_index in range(26)]
    momentum_bars = [build_daily_bar(26 + offset, close) for offset, close in enumerate([100.0, 104.0, 108.0, 112.0])]
    return append_forward_bars(stable_bars + momentum_bars, [114.0, 116.0, 118.0, 120.0, 122.0])


def assert_research_metric_payload(payload: dict[str, object], signal_type: str) -> None:
    assert payload["status"] == "ok"
    assert payload["sample_size"] >= 1
    assert payload["disclaimer"] == "Historical signal evaluation is a research aid only and is not investment advice."
    assert payload["snapshots"]
    assert payload["snapshots"][0]["signal_type"] == signal_type
    signal_metrics = payload["metrics"][signal_type]
    assert signal_metrics["sample_size"] >= 1
    assert signal_metrics["windows"]["1"]["sample_size"] >= 1
    assert signal_metrics["windows"]["1"]["hit_rate"] is not None
    assert signal_metrics["windows"]["1"]["average_forward_return"] is not None
    assert signal_metrics["windows"]["1"]["max_drawdown_after_signal"] is not None


def test_evaluates_breakout_signals_with_forward_metrics():
    payload = evaluate_recommendation_signals(
        "AAPL",
        build_breakout_bars(),
        signal_types=["breakout"],
        forward_windows=[1, 5],
    )

    assert_research_metric_payload(payload, "breakout")
    assert payload["metrics"]["breakout"]["windows"]["1"]["hit_rate"] == 1.0


def test_evaluates_volume_anomaly_signals():
    payload = evaluate_recommendation_signals(
        "AAPL",
        build_volume_anomaly_bars(),
        signal_types=["volume_anomaly"],
        forward_windows=[1],
    )

    assert_research_metric_payload(payload, "volume_anomaly")


def test_evaluates_oversold_rebound_signals():
    payload = evaluate_recommendation_signals(
        "AAPL",
        build_oversold_rebound_bars(),
        signal_types=["oversold_rebound"],
        forward_windows=[1],
    )

    assert_research_metric_payload(payload, "oversold_rebound")


def test_evaluates_strong_momentum_signals_with_benchmark_relative_return():
    bars = build_strong_momentum_bars()
    benchmark_bars = [
        build_daily_bar(day_index, 100.0 + day_index * 0.2)
        for day_index in range(len(bars))
    ]

    payload = evaluate_recommendation_signals(
        "AAPL",
        bars,
        signal_types=["strong_momentum"],
        forward_windows=[1],
        benchmark_bars=benchmark_bars,
    )

    assert_research_metric_payload(payload, "strong_momentum")
    assert payload["metrics"]["strong_momentum"]["windows"]["1"]["benchmark_relative_return"] is not None
    assert not any(diagnostic["code"] == "BENCHMARK_UNAVAILABLE" for diagnostic in payload["diagnostics"])


def test_reports_insufficient_history_without_zero_return_metrics():
    payload = evaluate_recommendation_signals(
        "AAPL",
        [build_daily_bar(day_index, 100.0) for day_index in range(10)],
        signal_types=["breakout"],
        forward_windows=[1, -2],
    )

    assert payload["status"] == "no_data"
    assert payload["sample_size"] == 0
    assert payload["metrics"] == {}
    diagnostic_codes = {diagnostic["code"] for diagnostic in payload["diagnostics"]}
    assert "NOT_ENOUGH_HISTORICAL_BARS" in diagnostic_codes
    assert "INVALID_FORWARD_WINDOW" in diagnostic_codes


def test_reports_no_signals_for_flat_history():
    payload = evaluate_recommendation_signals(
        "AAPL",
        [build_daily_bar(day_index, 100.0) for day_index in range(40)],
        signal_types=["breakout"],
        forward_windows=[1],
    )

    assert payload["status"] == "no_signals"
    assert payload["snapshots"] == []
    assert payload["metrics"] == {}
    assert payload["diagnostics"][0]["code"] == "NO_SIGNAL_SNAPSHOTS"
