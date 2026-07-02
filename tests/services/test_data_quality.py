from datetime import date, datetime, timezone

from packages.services.data_quality import check_daily_bar_quality


def _daily_bar(
    trade_date: object,
    open_price: float = 100.0,
    high_price: float = 105.0,
    low_price: float = 95.0,
    close_price: float = 102.0,
    volume: float = 1000.0,
) -> dict[str, object]:
    return {
        "trade_date": trade_date,
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "close": close_price,
        "volume": volume,
    }


def test_complete_weekday_series_has_no_gaps():
    bars = [
        {**_daily_bar(date(2026, 1, 5)), "trade_date": None, "timestamp": "2026-01-05"},
        _daily_bar("2026-01-06"),
        {
            **_daily_bar(date(2026, 1, 7)),
            "trade_date": None,
            "timestamp": datetime(2026, 1, 7, tzinfo=timezone.utc),
        },
        _daily_bar(date(2026, 1, 8)),
        _daily_bar("2026-01-09T00:00:00+00:00"),
    ]

    result = check_daily_bar_quality(bars)

    assert result.checked_bars == 5
    assert result.missing_dates == []
    assert result.invalid_ohlc == []
    assert result.volume_warnings == []
    assert result.status == "OK"


def test_missing_weekday_is_reported():
    bars = [
        _daily_bar(date(2026, 1, 5)),
        _daily_bar(date(2026, 1, 7)),
    ]

    result = check_daily_bar_quality(bars)

    assert result.missing_dates == ["2026-01-06"]
    assert result.status == "WARN"


def test_expected_trade_dates_can_skip_weekday_holidays():
    bars = [
        _daily_bar(date(2026, 1, 5)),
        _daily_bar(date(2026, 1, 7)),
    ]

    result = check_daily_bar_quality(
        bars,
        expected_trade_dates=[date(2026, 1, 5), date(2026, 1, 7)],
    )

    assert result.missing_dates == []
    assert result.status == "OK"


def test_expected_trade_dates_report_missing_sessions():
    bars = [
        _daily_bar(date(2026, 1, 5)),
        _daily_bar(date(2026, 1, 8)),
    ]

    result = check_daily_bar_quality(
        bars,
        expected_trade_dates=[
            date(2026, 1, 5),
            date(2026, 1, 6),
            date(2026, 1, 8),
        ],
    )

    assert result.missing_dates == ["2026-01-06"]
    assert result.status == "WARN"


def test_expected_trade_dates_parse_mixed_session_inputs():
    bars = [
        _daily_bar(date(2026, 1, 5)),
        _daily_bar(date(2026, 1, 8)),
    ]

    result = check_daily_bar_quality(
        bars,
        expected_trade_dates=[
            date(2026, 1, 5),
            datetime(2026, 1, 6, tzinfo=timezone.utc),
            "2026-01-07T00:00:00+00:00",
            "2026-01-08",
            "not-a-date",
        ],
    )

    assert result.missing_dates == ["2026-01-06", "2026-01-07"]
    assert result.status == "WARN"


def test_invalid_ohlc_row_is_reported():
    bars = [
        _daily_bar(
            date(2026, 1, 5),
            open_price=100.0,
            high_price=99.0,
            low_price=95.0,
            close_price=98.0,
        ),
    ]

    result = check_daily_bar_quality(bars)

    assert result.status == "FAIL"
    assert len(result.invalid_ohlc) == 1
    assert result.invalid_ohlc[0].row_index == 0
    assert result.invalid_ohlc[0].trade_date == "2026-01-05"
    assert result.invalid_ohlc[0].issue_type == "high_below_open"


def test_zero_volume_is_warn():
    bars = [_daily_bar(date(2026, 1, 5), volume=0.0)]

    result = check_daily_bar_quality(bars)

    assert result.status == "WARN"
    assert len(result.volume_warnings) == 1
    assert result.volume_warnings[0].issue_type == "zero_volume"
    assert result.volume_warnings[0].severity == "WARN"


def test_negative_volume_is_fail():
    bars = [_daily_bar(date(2026, 1, 5), volume=-1.0)]

    result = check_daily_bar_quality(bars)

    assert result.status == "FAIL"
    assert len(result.volume_warnings) == 1
    assert result.volume_warnings[0].issue_type == "negative_volume"
    assert result.volume_warnings[0].severity == "FAIL"


def test_empty_bars_returns_fail_because_quality_cannot_be_assessed():
    result = check_daily_bar_quality([])

    assert result.checked_bars == 0
    assert result.missing_dates == []
    assert result.invalid_ohlc == []
    assert result.volume_warnings == []
    assert result.status == "FAIL"
