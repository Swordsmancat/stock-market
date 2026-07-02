from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from typing import Literal


DataQualityStatus = Literal["OK", "WARN", "FAIL"]


@dataclass(frozen=True)
class DataQualityIssue:
    row_index: int | None
    trade_date: str | None
    issue_type: str
    severity: DataQualityStatus
    message: str
    values: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DataQualityResult:
    checked_bars: int
    missing_dates: list[str]
    invalid_ohlc: list[DataQualityIssue]
    volume_warnings: list[DataQualityIssue]
    status: DataQualityStatus

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def check_daily_bar_quality(
    bars: list[dict[str, object]],
    expected_trade_dates: list[object] | None = None,
) -> DataQualityResult:
    """Check serialized daily OHLCV bars without querying or mutating storage."""
    checked_bars = len(bars)
    parsed_trade_dates: list[date] = []
    invalid_ohlc: list[DataQualityIssue] = []
    volume_warnings: list[DataQualityIssue] = []

    for row_index, bar in enumerate(bars):
        trade_date = _parse_bar_trade_date(bar)
        trade_date_label = trade_date.isoformat() if trade_date is not None else None
        if trade_date is not None:
            parsed_trade_dates.append(trade_date)

        ohlc_values = _parse_ohlc_values(bar)
        if ohlc_values is None:
            invalid_ohlc.append(
                DataQualityIssue(
                    row_index=row_index,
                    trade_date=trade_date_label,
                    issue_type="missing_or_non_numeric_ohlc",
                    severity="FAIL",
                    message="Daily bar OHLC values must all be present and numeric.",
                    values={field_name: bar.get(field_name) for field_name in _OHLC_FIELD_NAMES},
                )
            )
        else:
            invalid_ohlc.extend(
                _find_invalid_ohlc_issues(
                    row_index=row_index,
                    trade_date_label=trade_date_label,
                    ohlc_values=ohlc_values,
                )
            )

        volume_warnings.extend(
            _find_volume_issues(
                row_index=row_index,
                trade_date_label=trade_date_label,
                volume_value=bar.get("volume"),
            )
        )

    missing_dates = _find_missing_dates(parsed_trade_dates, expected_trade_dates)
    status = _determine_status(
        checked_bars=checked_bars,
        missing_dates=missing_dates,
        invalid_ohlc=invalid_ohlc,
        volume_warnings=volume_warnings,
    )
    return DataQualityResult(
        checked_bars=checked_bars,
        missing_dates=missing_dates,
        invalid_ohlc=invalid_ohlc,
        volume_warnings=volume_warnings,
        status=status,
    )


_OHLC_FIELD_NAMES = ("open", "high", "low", "close")


def _parse_bar_trade_date(bar: dict[str, object]) -> date | None:
    raw_trade_date = bar.get("timestamp", bar.get("trade_date"))
    if isinstance(raw_trade_date, datetime):
        return raw_trade_date.date()
    if isinstance(raw_trade_date, date):
        return raw_trade_date
    if isinstance(raw_trade_date, str):
        normalized_trade_date = raw_trade_date.strip()
        if not normalized_trade_date:
            return None
        try:
            return date.fromisoformat(normalized_trade_date)
        except ValueError:
            datetime_value = datetime.fromisoformat(normalized_trade_date.replace("Z", "+00:00"))
            return datetime_value.date()
    return None


def _parse_ohlc_values(bar: dict[str, object]) -> dict[str, float] | None:
    parsed_values: dict[str, float] = {}
    for field_name in _OHLC_FIELD_NAMES:
        parsed_value = _parse_float(bar.get(field_name))
        if parsed_value is None:
            return None
        parsed_values[field_name] = parsed_value
    return parsed_values


def _parse_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _find_invalid_ohlc_issues(
    row_index: int,
    trade_date_label: str | None,
    ohlc_values: dict[str, float],
) -> list[DataQualityIssue]:
    open_price = ohlc_values["open"]
    high_price = ohlc_values["high"]
    low_price = ohlc_values["low"]
    close_price = ohlc_values["close"]
    invalid_conditions = [
        ("high_below_low", high_price < low_price, "high must be greater than or equal to low"),
        ("high_below_open", high_price < open_price, "high must be greater than or equal to open"),
        ("high_below_close", high_price < close_price, "high must be greater than or equal to close"),
        ("low_above_open", low_price > open_price, "low must be less than or equal to open"),
        ("low_above_close", low_price > close_price, "low must be less than or equal to close"),
    ]

    return [
        DataQualityIssue(
            row_index=row_index,
            trade_date=trade_date_label,
            issue_type=issue_type,
            severity="FAIL",
            message=message,
            values=dict(ohlc_values),
        )
        for issue_type, is_invalid, message in invalid_conditions
        if is_invalid
    ]


def _find_volume_issues(
    row_index: int,
    trade_date_label: str | None,
    volume_value: object,
) -> list[DataQualityIssue]:
    parsed_volume = _parse_float(volume_value)
    if parsed_volume is None:
        return [
            DataQualityIssue(
                row_index=row_index,
                trade_date=trade_date_label,
                issue_type="missing_or_non_numeric_volume",
                severity="FAIL",
                message="Daily bar volume must be present and numeric.",
                values={"volume": volume_value},
            )
        ]
    if parsed_volume < 0:
        return [
            DataQualityIssue(
                row_index=row_index,
                trade_date=trade_date_label,
                issue_type="negative_volume",
                severity="FAIL",
                message="Daily bar volume cannot be negative.",
                values={"volume": parsed_volume},
            )
        ]
    if parsed_volume == 0:
        return [
            DataQualityIssue(
                row_index=row_index,
                trade_date=trade_date_label,
                issue_type="zero_volume",
                severity="WARN",
                message="Daily bar volume is zero; verify this is expected for the market/session.",
                values={"volume": parsed_volume},
            )
        ]
    return []


def _find_missing_dates(
    parsed_trade_dates: list[date],
    expected_trade_dates: list[object] | None,
) -> list[str]:
    if expected_trade_dates is None:
        return _find_missing_weekday_dates(parsed_trade_dates)

    return _find_missing_expected_trade_dates(parsed_trade_dates, expected_trade_dates)


def _find_missing_weekday_dates(parsed_trade_dates: list[date]) -> list[str]:
    if not parsed_trade_dates:
        return []

    observed_trade_dates = set(parsed_trade_dates)
    current_trade_date = min(observed_trade_dates)
    final_trade_date = max(observed_trade_dates)
    missing_dates: list[str] = []

    while current_trade_date <= final_trade_date:
        is_weekday_session = current_trade_date.weekday() < 5
        if is_weekday_session and current_trade_date not in observed_trade_dates:
            missing_dates.append(current_trade_date.isoformat())
        current_trade_date += timedelta(days=1)

    return missing_dates


def _find_missing_expected_trade_dates(
    parsed_trade_dates: list[date],
    expected_trade_dates: list[object],
) -> list[str]:
    if not parsed_trade_dates:
        return []

    observed_trade_dates = set(parsed_trade_dates)
    first_observed_trade_date = min(observed_trade_dates)
    final_observed_trade_date = max(observed_trade_dates)
    parsed_expected_trade_dates = {
        parsed_trade_date
        for expected_trade_date in expected_trade_dates
        if (parsed_trade_date := _parse_expected_trade_date(expected_trade_date)) is not None
    }

    return [
        expected_trade_date.isoformat()
        for expected_trade_date in sorted(parsed_expected_trade_dates)
        if first_observed_trade_date <= expected_trade_date <= final_observed_trade_date
        and expected_trade_date not in observed_trade_dates
    ]


def _parse_expected_trade_date(expected_trade_date: object) -> date | None:
    try:
        return _parse_bar_trade_date({"trade_date": expected_trade_date})
    except (TypeError, ValueError):
        return None


def _determine_status(
    checked_bars: int,
    missing_dates: list[str],
    invalid_ohlc: list[DataQualityIssue],
    volume_warnings: list[DataQualityIssue],
) -> DataQualityStatus:
    has_failing_volume_issue = any(issue.severity == "FAIL" for issue in volume_warnings)
    if checked_bars == 0 or invalid_ohlc or has_failing_volume_issue:
        return "FAIL"
    if missing_dates or volume_warnings:
        return "WARN"
    return "OK"
