# Design: ingestion single fetch

## Scope

This is a design-only artifact for the ingestion refactor. It proposes the smallest production change that makes `ingest_market_snapshot(...)` fetch real provider data once and then use that same serialized snapshot for:

- the returned API payload;
- database writes;
- `quality_diagnostics`;
- `bar_count`.

No production code or tests were changed as part of this design task.

## Current data flow and duplicate fetch points

Current session-backed ingestion flow in `packages/services/ingestion.py` and `packages/services/market_data.py`:

```text
ingest_market_snapshot(market, start, end, session, provider_name)
  |
  |-- provider = get_provider(provider_name)
  |     Creates provider instance A for the writer path.
  |
  |-- snapshot = get_market_snapshot(market, start, end, provider_name)
  |     |
  |     |-- effective_provider_name = resolve_market_data_provider_name(provider_name)
  |     |-- provider = get_provider(effective_provider_name)
  |     |     Creates provider instance B for the return payload path.
  |     |
  |     |-- _fetch_provider_instruments(provider B, market)
  |     |     FIRST instrument fetch.
  |     |
  |     `-- for each instrument:
  |           _fetch_provider_bars(provider B, instrument.symbol, timeframe, start, end)
  |           FIRST bar fetch for each instrument.
  |
  |-- if session is not None:
  |     _write_snapshot_to_database(market, start, end, session, provider A)
  |       |
  |       |-- provider A.fetch_instruments(market)
  |       |     SECOND instrument fetch.
  |       |
  |       `-- for each provider instrument:
  |             provider A.fetch_bars(provider_instrument.symbol, "1d", start, end)
  |             SECOND bar fetch for each instrument.
  |
  |-- else:
  |     bar_count = sum(len(instrument["bars"]) for instrument in snapshot["instruments"])
  |
  `-- return {
        **snapshot,
        "bar_count": bar_count,
        "quality_diagnostics": _build_quality_diagnostics(snapshot),
        "status": "ingested",
      }
```

Summary by path:

- With `session is not None`: `fetch_instruments` is called twice and `fetch_bars` is called twice per instrument.
- With `session is None`: provider bars are fetched once through `get_market_snapshot(...)`, but `ingest_market_snapshot(...)` still creates an unused provider instance before it knows whether a session-backed write is needed.

## Current problem

The returned snapshot, database write, `bar_count`, and `quality_diagnostics` are not guaranteed to describe the same provider result when a database session is present.

- The returned payload is built from `get_market_snapshot(...)` using provider instance B.
- Database rows are written from `_write_snapshot_to_database(...)` using provider instance A.
- `quality_diagnostics` are computed from the returned serialized `snapshot`, not from the bars written to the database.
- `bar_count` on the session path comes from `_write_snapshot_to_database(...)`, so it can reflect the second provider fetch rather than the returned snapshot.

For real providers such as yfinance, the two fetches can diverge because of network timing, upstream corrections, transient failures, rate limiting, provider-side adjusted data changes, or different provider settings resolved between calls. In that case the API can report one set of bars, write another set of bars, and diagnose quality on only the returned set.

## Recommended minimal single-fetch design

Add a serialized-snapshot writer and make `get_market_snapshot(...)` the single fetch boundary for ingestion.

### New ingestion flow

```text
ingest_market_snapshot(market, start, end, session, provider_name)
  |
  |-- snapshot = get_market_snapshot(market, start, end, provider_name=provider_name.lower())
  |     |
  |     |-- one provider instance
  |     |-- one fetch_instruments call
  |     `-- one fetch_bars call per instrument
  |
  |-- if session is not None:
  |     bar_count = _write_serialized_snapshot_to_database(
  |       market_code=market,
  |       snapshot=snapshot,
  |       session=session,
  |     )
  |
  |-- else:
  |     bar_count = _count_serialized_snapshot_bars(snapshot)
  |
  `-- return {
        **snapshot,
        "bar_count": bar_count,
        "quality_diagnostics": _build_quality_diagnostics(snapshot),
        "status": "ingested",
      }
```

### Proposed helper shape

Keep `get_market_snapshot(...)` public behavior unchanged. Add a private writer in `packages/services/ingestion.py` that consumes the already serialized snapshot returned by `get_market_snapshot(...)`:

```python
def _write_serialized_snapshot_to_database(
    market_code: str,
    snapshot: dict[str, object],
    session: Session,
) -> int:
    ...
```

Expected behavior:

1. Create or load the `Market` using `market_code`, preserving `_get_or_create_market(...)` behavior.
2. Iterate `snapshot["instruments"]`.
3. Create or load each `Instrument` from serialized instrument metadata:
   - `symbol`
   - `name`
   - `asset_type`
   - `currency`
   - optionally ignore `exchange` because the current `Instrument` create path does not write it.
4. Iterate each serialized instrument's `bars` list.
5. Parse `bar["timestamp"]` to a `date` for `DailyBar.trade_date`.
6. Upsert `DailyBar` using the same key as today: `(instrument.id, trade_date)`.
7. Assign `open`, `high`, `low`, `close`, `volume`, and `amount` from the serialized bar.
8. Increment `bar_count` once per serialized bar processed, matching today's count-per-provider-bar behavior.
9. Commit once at the end, matching today's transaction boundary.

The old `_write_snapshot_to_database(...)` can be replaced by the new helper. If the implementation wants a lower-risk intermediate step, it can leave the old helper unused for one commit and remove it after tests pass.

### Numeric conversion recommendation

`market_data.serialize_bar(...)` currently converts provider `Decimal` values to `float` for the public payload. Writing those floats directly into numeric database columns may introduce binary-float artifacts. The minimal writer should convert serialized numeric values with a small local parser, for example `Decimal(str(value))`, before assigning to `DailyBar` numeric fields.

This does not recover precision already lost by public serialization, but it avoids storing values such as `100.099999999`. If exact provider `Decimal` precision becomes mandatory later, use a larger internal snapshot design that keeps raw `ProviderBar` objects for database writes and derives serialized payload and diagnostics from the same raw fetch. That is intentionally outside this minimal refactor.

### Date parsing recommendation

Use a local explicit timestamp parser for database writes:

- if the value is `datetime`, use `.date()`;
- if the value is `date`, use it directly;
- if the value is a string, first accept `YYYY-MM-DD`, then fall back to `datetime.fromisoformat(value.replace("Z", "+00:00")).date()`;
- raise a clear `ValueError` for missing or unparsable timestamps.

Check `datetime` before `date` because `datetime` is a subclass of `date` in Python.

## Compatibility contract

### Returned payload structure

The returned payload should remain unchanged:

- all fields from `get_market_snapshot(...)` stay as-is;
- `bar_count` stays at the top level;
- `quality_diagnostics` stays at the top level;
- `status` remains `"ingested"`;
- each instrument keeps `symbol`, `name`, `exchange`, `asset_type`, `currency`, and `bars`;
- each bar keeps `timestamp`, `open`, `high`, `low`, `close`, `volume`, and `amount`.

`get_market_snapshot(...)` should remain callable by other services exactly as it is today.

### `bar_count`

Preserve the existing semantic: `bar_count` is the number of bars processed, not the number of inserted rows.

- No-session path: count serialized bars from `snapshot["instruments"]`.
- Session path: `_write_serialized_snapshot_to_database(...)` returns the number of serialized bars it processed.
- After the refactor, both paths count the same snapshot, so `bar_count` cannot diverge from the returned bars.
- If a snapshot contains duplicate bars for the same instrument/date, count each duplicate processed bar and let the final upserted value win, matching the current loop's behavior.

### `quality_diagnostics`

Keep `_build_quality_diagnostics(snapshot)` unchanged unless tests reveal a typing-only cleanup is needed.

- Diagnostics should continue to read serialized bars only.
- Diagnostics should run on the same snapshot that is returned and written.
- Empty instrument snapshots should still return the existing failure payload:
  - `status: "FAIL"`
  - `instrument_count: 0`
  - `instruments: []`
  - `quality_error: "No instruments available for quality diagnostics."`
- Per-instrument diagnostic `checked_bars` should match the number of serialized bars written for that instrument.

### Session and no-session paths

- `session is None`: fetch provider data once through `get_market_snapshot(...)`; compute `bar_count` from the snapshot; no database write.
- `session is not None`: fetch provider data once through `get_market_snapshot(...)`; write the same serialized snapshot to the database; compute diagnostics from the same snapshot.
- Remove the eager `provider = get_provider(provider_name)` from `ingest_market_snapshot(...)`; the provider should be created only inside `get_market_snapshot(...)` for this ingestion path.

### Provider behavior

- Mock provider behavior remains unchanged.
- YFinance behavior remains unchanged except it should be downloaded once per instrument per ingestion call.
- `resolve_market_data_provider_name(...)` remains centralized in `get_market_snapshot(...)` for the ingestion fetch. The returned `snapshot["provider"]` remains the effective provider name.

## Risks and edge cases

1. **Decimal/float conversion**
   - Current provider bars use `Decimal`, but serialized bars expose floats.
   - The minimal design writes from serialized bars, so it may store serialized precision rather than original provider precision.
   - Mitigation: assign database numeric fields from `Decimal(str(serialized_value))`; document a future raw internal snapshot if exact decimal fidelity is required.

2. **Date parsing**
   - Serialized bars use `timestamp`, while database rows use `trade_date`.
   - Date strings and datetime strings with offsets should both parse.
   - `datetime` must be handled before `date`.
   - Invalid timestamps should fail loudly before commit instead of silently writing bad keys.

3. **Provider bar fields versus serialized bar fields**
   - `ProviderBar` includes `symbol`, but serialized bars from `serialize_bar(...)` do not.
   - The writer must use the parent serialized instrument's `symbol` when resolving the `Instrument`.
   - Serialized instrument metadata contains `exchange`, but current `_get_or_create_instrument(...)` does not store it; do not introduce schema or model changes in this minimal refactor.

4. **Upsert behavior**
   - Preserve current behavior: `session.get(DailyBar, (instrument.id, trade_date))`, create if absent, overwrite fields if present.
   - `bar_count` remains processed-bar count, not affected-row count.
   - Duplicate snapshot bars for the same instrument/date should produce last-write-wins behavior, as the current provider loop does.

5. **Snapshot shape typing**
   - `snapshot` is typed as `dict[str, object]`, so implementation will need careful local casts or small helper iterators.
   - Avoid broad `Any`-driven code where possible; fail clearly if required keys are missing.

6. **Transaction semantics**
   - Keep the current single `session.commit()` at the end of the write helper.
   - Do not introduce partial commits per instrument.

7. **Behavior with no instruments**
   - A snapshot with no instruments should write zero bars, return `bar_count == 0`, and keep the existing quality failure payload.

## Required tests before implementation is considered complete

1. **Single provider fetch with session**
   - Use a counting provider or monkeypatch `packages.services.market_data.get_provider(...)`.
   - Call `ingest_market_snapshot(..., session=session, provider_name="mock-or-counting")`.
   - Assert `fetch_instruments` is called once.
   - Assert `fetch_bars` is called once per fetched instrument.

2. **Returned payload, database row, and diagnostics share one snapshot**
   - Use a provider whose bars would differ if fetched a second time.
   - Assert returned bar values match the database row values.
   - Assert `quality_diagnostics["instruments"][...]["checked_bars"]` matches the returned and written bars.

3. **`bar_count` is snapshot-based on both paths**
   - With no session, assert `bar_count == sum(len(instrument["bars"]) ...)`.
   - With a session, assert the same equality and verify database rows are written.

4. **No-session path does not perform writer fetches**
   - Assert ingestion without a session fetches only through `get_market_snapshot(...)` and does not instantiate or call a separate writer provider.

5. **Existing compatibility tests still pass**
   - `test_ingest_market_snapshot_returns_serialized_snapshot`
   - `test_ingest_market_snapshot_includes_quality_diagnostics`
   - `test_ingest_market_snapshot_reports_failed_quality_when_no_instruments`
   - `test_ingest_mock_market_snapshot_remains_compatible`
   - current `tests/services/test_data_quality.py`

6. **Upsert behavior is preserved**
   - Preload a `DailyBar`, ingest a snapshot for the same instrument/date, and assert the existing row is updated rather than duplicated.
   - Assert `bar_count` still counts processed bars.

7. **Timestamp parsing coverage**
   - Write bars with `timestamp` as `YYYY-MM-DD`.
   - Write bars with an ISO datetime string such as `2026-01-01T00:00:00+00:00`.
   - Assert both produce the expected `DailyBar.trade_date`.

8. **Amount and numeric conversion coverage**
   - Assert `amount=None` remains accepted.
   - Assert numeric fields are stored without obvious binary-float artifacts by parsing serialized values through `Decimal(str(value))` or equivalent.

## Recommended implementation steps

1. Add `_count_serialized_snapshot_bars(snapshot)` in `packages/services/ingestion.py` and use it for the no-session path.
2. Add local parsing helpers for serialized bar timestamps and numeric values.
3. Add `_write_serialized_snapshot_to_database(market_code, snapshot, session)` using existing `_get_or_create_market(...)` and `_get_or_create_instrument(...)`.
4. Change `ingest_market_snapshot(...)` to:
   - stop creating the eager writer provider;
   - call `get_market_snapshot(...)` once;
   - pass the returned snapshot to `_write_serialized_snapshot_to_database(...)` when a session exists;
   - build `quality_diagnostics` from the same snapshot.
5. Remove the now-unused `ProviderAdapter` / `get_provider` imports from `ingestion.py` if `_write_snapshot_to_database(...)` is deleted.
6. Add the required tests above, with the single-fetch tests first so the old implementation fails for the right reason.
7. Run focused tests:
   - `pytest tests/services/test_ingestion_service.py tests/services/test_data_quality.py`
   - provider tests touched by monkeypatch assumptions if needed, especially `tests/providers/test_yfinance_provider.py`.
8. Run the repository's normal quality gate if available.

## Rollback plan

This refactor should not require schema changes, data migrations, API changes, or provider changes.

Rollback options:

1. Revert the ingestion service change so the session path calls `_write_snapshot_to_database(...)` again.
2. Revert the focused tests that assert single-fetch behavior.
3. If the old helper is kept for one implementation commit, rollback can be a one-line branch switch in `ingest_market_snapshot(...)` from `_write_serialized_snapshot_to_database(...)` back to `_write_snapshot_to_database(...)`.
4. Because upsert keys and payload shape are unchanged, existing database content does not need cleanup after rollback.

## Recommendation summary

Implement the minimal serialized-snapshot writer. It is the smallest change that guarantees the returned payload, database write, `bar_count`, and `quality_diagnostics` all come from one provider fetch while preserving public payload shape and current upsert semantics. Track the Decimal precision tradeoff explicitly; only move to a larger raw internal snapshot model if exact provider decimal fidelity becomes a hard requirement.
