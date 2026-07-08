from datetime import date, timedelta

from packages.services.strategy_screening import (
    evaluate_instock_strategy_signals,
    screen_latest_instock_strategies,
)


def build_bar(
    day_index: int,
    close: float,
    *,
    open_price: float | None = None,
    volume: float = 1_000_000.0,
    amount: float | None = None,
) -> dict[str, object]:
    timestamp = (date(2026, 1, 1) + timedelta(days=day_index)).isoformat()
    open_value = close if open_price is None else open_price
    bar: dict[str, object] = {
        "timestamp": timestamp,
        "open": open_value,
        "high": max(open_value, close) + 1,
        "low": min(open_value, close) - 1,
        "close": close,
        "volume": volume,
    }
    if amount is not None:
        bar["amount"] = amount
    return bar


def test_screens_volume_price_breakout_as_research_signal():
    bars = [build_bar(day_index, 100.0, volume=1_000_000.0) for day_index in range(5)]
    bars.append(
        build_bar(
            5,
            105.0,
            open_price=101.0,
            volume=3_000_000.0,
            amount=315_000_000.0,
        )
    )

    payload = screen_latest_instock_strategies(
        "aapl",
        bars,
        strategy_codes=["volume_price_breakout"],
    )

    assert payload["symbol"] == "AAPL"
    assert payload["status"] == "matched"
    assert payload["research_signal_only"] is True
    assert payload["match_count"] == 1
    match = payload["matches"][0]
    assert match["code"] == "volume_price_breakout"
    assert match["research_signal_only"] is True
    assert match["inspired_by"] == "instock.core.strategy.enter.check_volume"
    assert match["data"]["volume_ratio"] == 3.0
    assert "buy" not in match["reason"].lower()


def test_screens_turtle_breakout_latest_lookback_high():
    bars = [build_bar(day_index, 100.0 + day_index * 0.1) for day_index in range(59)]
    bars.append(build_bar(59, 120.0))

    payload = screen_latest_instock_strategies(
        "AAPL",
        bars,
        strategy_codes=["turtle_breakout"],
    )

    assert payload["status"] == "matched"
    assert payload["matches"][0]["code"] == "turtle_breakout"
    assert payload["matches"][0]["data"]["lookback_bars"] == 60
    assert payload["matches"][0]["data"]["prior_lookback_high"] < 120.0


def test_screens_ma_trend_up_checkpoints():
    bars = [build_bar(day_index, 100.0 + day_index) for day_index in range(60)]

    payload = screen_latest_instock_strategies(
        "AAPL",
        bars,
        strategy_codes=["ma_trend_up"],
    )

    assert payload["status"] == "matched"
    match = payload["matches"][0]
    assert match["code"] == "ma_trend_up"
    assert match["data"]["ma_30_bars_ago"] < match["data"]["ma_20_bars_ago"]
    assert match["data"]["ma_20_bars_ago"] < match["data"]["ma_10_bars_ago"]
    assert match["data"]["ma_10_bars_ago"] < match["data"]["ma_latest"]
    assert match["data"]["growth_ratio"] > 1.2


def test_reports_unknown_and_insufficient_strategy_diagnostics():
    payload = screen_latest_instock_strategies(
        "AAPL",
        [build_bar(day_index, 100.0) for day_index in range(5)],
        strategy_codes=["unknown", "turtle_breakout"],
    )

    assert payload["status"] == "insufficient_data"
    assert payload["matches"] == []
    diagnostic_codes = {diagnostic["code"] for diagnostic in payload["diagnostics"]}
    assert "UNKNOWN_STRATEGY_CODE" in diagnostic_codes
    assert "INSUFFICIENT_BARS" in diagnostic_codes


def test_reports_no_data_without_fabricated_matches():
    payload = screen_latest_instock_strategies("AAPL", [], strategy_codes=["ma_trend_up"])

    assert payload["status"] == "no_data"
    assert payload["match_count"] == 0
    assert payload["matches"] == []
    assert payload["diagnostics"][0]["code"] == "NO_BARS"


def build_volume_price_breakout_evaluation_bars() -> list[dict[str, object]]:
    bars = [build_bar(day_index, 100.0, volume=1_000_000.0) for day_index in range(5)]
    bars.append(
        build_bar(
            5,
            105.0,
            open_price=101.0,
            volume=3_000_000.0,
            amount=315_000_000.0,
        )
    )
    bars.append(build_bar(6, 108.0, volume=1_000_000.0))
    bars.append(build_bar(7, 104.0, volume=1_000_000.0))
    return bars


def test_evaluates_strategy_signals_with_forward_metrics():
    payload = evaluate_instock_strategy_signals(
        "aapl",
        build_volume_price_breakout_evaluation_bars(),
        strategy_codes=["volume_price_breakout"],
        forward_windows=[1, 2],
    )

    assert payload["symbol"] == "AAPL"
    assert payload["status"] == "ok"
    assert payload["research_signal_only"] is True
    assert payload["sample_size"] == 1
    assert payload["snapshots"][0]["strategy_code"] == "volume_price_breakout"
    assert payload["snapshots"][0]["research_signal_only"] is True
    window_1 = payload["metrics"]["volume_price_breakout"]["windows"]["1"]
    assert window_1["sample_size"] == 1
    assert window_1["hit_rate"] == 1.0
    assert window_1["average_forward_return"] > 0
    assert window_1["max_drawdown_after_signal"] is not None
    assert any(diagnostic["code"] == "BENCHMARK_UNAVAILABLE" for diagnostic in payload["diagnostics"])


def test_evaluates_strategy_signals_with_benchmark_relative_return():
    bars = build_volume_price_breakout_evaluation_bars()
    benchmark_bars = [build_bar(day_index, 100.0 + day_index * 0.1) for day_index in range(len(bars))]

    payload = evaluate_instock_strategy_signals(
        "AAPL",
        bars,
        strategy_codes=["volume_price_breakout"],
        forward_windows=[1],
        benchmark_bars=benchmark_bars,
    )

    window_1 = payload["metrics"]["volume_price_breakout"]["windows"]["1"]
    assert window_1["benchmark_relative_return"] is not None
    assert not any(diagnostic["code"] == "BENCHMARK_UNAVAILABLE" for diagnostic in payload["diagnostics"])


def test_evaluates_strategy_signals_reports_insufficient_history_and_bad_windows():
    payload = evaluate_instock_strategy_signals(
        "AAPL",
        [build_bar(day_index, 100.0) for day_index in range(5)],
        strategy_codes=["unknown", "turtle_breakout"],
        forward_windows=[1, -2],
    )

    assert payload["status"] == "no_data"
    assert payload["sample_size"] == 0
    assert payload["metrics"] == {}
    diagnostic_codes = {diagnostic["code"] for diagnostic in payload["diagnostics"]}
    assert "UNKNOWN_STRATEGY_CODE" in diagnostic_codes
    assert "INVALID_FORWARD_WINDOW" in diagnostic_codes
    assert "NOT_ENOUGH_HISTORICAL_BARS" in diagnostic_codes


def test_evaluates_strategy_signals_reports_no_signals_for_flat_history():
    payload = evaluate_instock_strategy_signals(
        "AAPL",
        [build_bar(day_index, 100.0) for day_index in range(80)],
        strategy_codes=["turtle_breakout"],
        forward_windows=[1],
    )

    assert payload["status"] == "no_signals"
    assert payload["sample_size"] == 0
    assert payload["snapshots"] == []
    assert payload["metrics"] == {}
    assert payload["diagnostics"][0]["code"] == "NO_STRATEGY_SNAPSHOTS"
