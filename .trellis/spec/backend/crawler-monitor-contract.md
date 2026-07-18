# Read-Only Crawler Monitor Contract

## 1. Scope / Trigger

- Trigger: a UI or diagnostic needs to summarize the health of curated collection pipelines from stored `TaskRun` rows.
- Scope: `packages/services/crawler_monitor.py`, `apps/api/routers/crawler_monitor.py`, and the localized `/crawler-monitor` page.
- Non-goals: dispatching, retrying, cancelling, expiring, scraping, or contacting a provider.

This boundary matters because the existing generic TaskRun GET helpers call
`expire_stale_task_runs()` and therefore mutate old running rows. A health page
must not change the state it is observing.

## 2. Signatures

- Service: `get_crawler_monitor(session: Session, *, now: datetime | None = None) -> dict[str, object]`.
- API: `GET /crawler-monitor`.
- Storage: one bounded, newest-first SQLAlchemy query over curated task names in `task_runs`.
- The monitor itself remains read-only even when a separately owned collection task is added to its curated list.

## 3. Contracts

The API returns exactly twelve stable pipeline IDs: `market_cn`, `market_us`,
`market_hk`, `universe_cn`, `evidence_incremental`, `fundamental_shard`, and
`official_disclosures`, plus `eastmoney_calendar`, `eastmoney_industry`,
`eastmoney_news`, `eastmoney_fundamentals`, and `fund_index_cn`. Shared task names are separated by equality selectors
over allowlisted `input_json` fields such as `market` and `run_kind`.

Each item exposes only its stable ID/status, task name, scope/provider,
cadence, latest TaskRun ID, timestamps, duration, bounded progress, recent
failure count, diagnostic code, and generic error summary. Raw `input_json`,
raw `result_json`, error text, stack traces, provider bodies, credentials,
cookies, proxies, and environment values are forbidden.

Statuses are `running`, `healthy`, `overdue`, `stalled`, `failed`, and
`not_recorded`. Stale running heartbeats project as `stalled` without updating
the TaskRun. The frontend validates the complete twelve-item contract, refreshes
the server route every 30 seconds, and localizes pipeline/scope/status/cadence
labels while leaving provider identifiers as evidence metadata.

## 4. Validation & Error Matrix

| Condition | Required result |
| --- | --- |
| No matching TaskRun | Return the pipeline as `not_recorded` |
| Fresh running heartbeat | `running`; preserve the stored row |
| Old running heartbeat/start | `stalled` plus `stale_heartbeat`; preserve the stored row |
| Recent success | `healthy` |
| Success outside the pipeline freshness window | `overdue` plus `freshness_window_exceeded` |
| Latest failed TaskRun | `failed` with a generic summary; never expose `error_message` |
| Unknown TaskRun status | `failed` plus `unsupported_task_run_status` |
| Invalid/unbounded progress | Omit progress rather than coercing raw JSON |
| Unsafe provider string | Use the curated provider fallback |
| API or decoder failure | Render an explicit unavailable state, not twelve `not_recorded` rows |

## 5. Good / Base / Bad Cases

- Good: a fundamental shard has a fresh heartbeat and `675/1105` progress; the monitor displays it as running and leaves the row unchanged.
- Base: a fresh database returns all twelve definitions as `not_recorded`, preserving the shape expected by navigation and translations.
- Bad: reuse `get_recent_task_runs_payload()` from `packages/services/task_runs.py`; its stale-expiry side effect turns an observational GET into a write.

## 6. Tests Required

- Service tests use SQLite and assert selector separation, every status class,
  bounded progress, unsafe provider fallback, twelve-item summary counts, and
  that stalled rows remain `running` in storage.
- API tests override `get_session` and assert the additive GET route.
- Frontend decoder tests reject missing, duplicate, and unsupported pipeline
  items. Page tests cover loaded/error states, progress, task links, navigation,
  and the desktop-only entry. Refresh tests lock the 30-second interval.
- Runtime acceptance checks real PostgreSQL projection plus desktop/mobile,
  light/dark, no horizontal overflow, and no console errors.

## 7. Wrong vs Correct

### Wrong

```python
def get_monitor(session: Session):
    return get_recent_task_runs_payload(session, limit=2000)
```

This leaks raw task payloads and calls stale-task expiry during a GET.

### Correct

```python
def get_monitor(session: Session):
    rows = (
        session.query(TaskRun)
        .filter(TaskRun.task_name.in_(CURATED_TASK_NAMES))
        .order_by(TaskRun.started_at.desc())
        .limit(2000)
        .all()
    )
    return project_allowlisted_pipeline_status(rows)
```

The query is bounded and read-only; status projection and sanitization are
owned by the dedicated monitor service.
