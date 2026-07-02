# Add trading calendar aware quality checks

## Goal

Make daily bar quality checks aware of explicitly supplied trading sessions so expected market holidays or other non-trading days are not reported as missing weekday data.

## Background

`packages/services/data_quality.py` currently detects missing dates by walking every weekday between the first and last observed bar. This is useful as a default heuristic, but it can produce false warnings for exchange holidays. The next incremental improvement is to allow callers to provide the expected trading sessions and keep the existing weekday behavior as the default fallback.

## Requirements

- Preserve the current public default behavior of `check_daily_bar_quality(bars)` when no calendar/session list is supplied.
- Add an optional expected trading sessions input for daily quality checks.
- When expected sessions are supplied, report missing dates only from that explicit session set.
- Ignore expected sessions outside the observed data span unless the call clearly supplies a bounded check range through observed bars.
- Keep quality checks pure and non-mutating; do not query databases or external calendar providers in this task.
- Preserve existing OHLC and volume validation behavior.
- Add focused data-quality tests for default weekday behavior, holiday-aware sessions, and missing expected sessions.

## Acceptance Criteria

- [x] Existing weekday-based missing-date tests continue to pass without passing a calendar.
- [x] A weekday holiday omitted from `expected_trade_dates` is not reported as missing.
- [x] A date included in `expected_trade_dates` but absent from bars is reported as missing.
- [x] Datetime/date/string session inputs are parsed consistently with bar timestamps.
- [x] Empty bars still produce `FAIL` without attempting to infer missing sessions.
- [x] Focused data-quality tests pass.

## Out of Scope

- Integrating a real exchange calendar library.
- Adding database-backed market calendars.
- Changing ingestion or TaskRun persistence contracts.
- Changing frontend display behavior.

## Validation

```bash
python -m pytest tests/services/test_data_quality.py -v
```
