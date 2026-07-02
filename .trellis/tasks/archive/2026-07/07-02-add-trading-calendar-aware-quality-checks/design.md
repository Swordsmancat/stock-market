# Add Trading Calendar Aware Quality Checks Design

## Scope

This task updates the pure data-quality service so callers can pass explicit expected trading sessions. It does not introduce a real exchange calendar provider or any database-backed calendar model.

## Current Behavior

- `check_daily_bar_quality(bars)` parses trade dates from serialized bars.
- `_find_missing_weekday_dates(...)` reports every missing weekday between the min and max observed dates.
- This can warn on exchange holidays because weekdays are treated as sessions.

## Target Behavior

Extend `check_daily_bar_quality` with an optional argument, for example:

```python
def check_daily_bar_quality(
    bars: list[dict[str, object]],
    expected_trade_dates: list[object] | None = None,
) -> DataQualityResult:
    ...
```

Rules:

- If `expected_trade_dates` is `None`, keep the current weekday heuristic.
- If `expected_trade_dates` is provided, parse it using the same date parsing logic as bars.
- Report missing dates from expected sessions that are between the first and last observed bar dates and absent from observed bar dates.
- Skip unparseable expected session values rather than failing the entire quality check; malformed bar dates already remain represented by `trade_date=None` downstream validations.
- If no bars are present, return the existing `checked_bars=0`, no missing dates, `FAIL` behavior.

## Compatibility

- Existing callers do not need to change.
- Existing result shape remains unchanged.
- Existing OHLC and volume checks are unchanged.
- Ingestion can adopt explicit calendars later without another result-contract change.

## Testing Strategy

- Preserve existing weekday missing-date test.
- Add test where a weekday holiday is excluded from `expected_trade_dates` and no missing date is reported.
- Add test where a missing expected session is reported.
- Add test with mixed `date`, `datetime`, and ISO string expected session inputs.
