# A-share Multi-Provider Daily-Bar Resilience

## Goal

Keep A-share daily-bar coverage usable when one upstream endpoint is unavailable while preserving source truth for every stored row and every AI coverage decision.

## Background

- `DailyBar` currently stores OHLCV only, so persisted rows cannot distinguish Eastmoney, Sina, Tushare, or legacy data.
- `ingest_symbol_daily_bars` records requested/effective provider only in its transient result payload.
- A-share backfills currently accept only `provider=akshare`, and coverage reports presence/freshness without source distribution.
- The live acceptance preflight proved that AkShare's Eastmoney daily endpoint can reset after TLS while AkShare's Sina daily endpoint remains reachable.
- Existing contracts prohibit silent fallback and require provider failures and missing evidence to remain visible.

## Requirements

### R1. Explicit policy boundary

- Keep `strict` as the default daily-bar policy for API and service callers.
- Add an explicit `cn_resilient` policy to A-share evidence backfill requests and persisted run metadata.
- The AI Research operations panel may submit `cn_resilient`, but it must show that controlled fallback is enabled.
- Resume and retry runs must preserve the originating policy.

### R2. Bounded source chain

- For `provider=akshare` plus `cn_resilient`, try sources in this fixed order: AkShare Eastmoney, AkShare Sina, then Tushare only when its token is configured.
- Do not use yfinance, mock, fixtures, or an unconfigured provider as a fallback.
- Record every attempted source, classified outcome, and selected source without raw upstream payloads or secrets.
- Valid primary data wins. Lower-priority data must not overwrite an already stored higher-priority row.

### R3. Validation and failure semantics

- Validate date range, uniqueness, finite numeric values, OHLC consistency, and non-negative volume before persistence.
- A malformed fallback source is a failed attempt, not valid no-data.
- `strict` failures retain current failure behavior. `cn_resilient` may continue after a classified provider error or valid empty response.
- If all eligible sources fail or return no data, return an explicit terminal classification and retain the symbol in the retry/no-data accounting.

### R4. Provider protection

- Keep source calls sequential with configurable minimum intervals and bounded attempts.
- Open a run-local circuit after repeated source-level failures so a provider-wide outage does not trigger thousands of identical requests.
- Circuit skips and unconfigured Tushare must be visible in sanitized diagnostics.

### R5. Persisted provenance

- Add effective provider, endpoint/source, adjustment mode, source priority, and ingestion timestamp to canonical daily bars.
- Migrate existing rows as `legacy_unknown` without deleting or rewriting OHLCV evidence.
- Replays from the same source remain idempotent; higher-priority data may replace lower-priority data.

### R6. Coverage and AI visibility

- Daily-bar coverage must include source/provider row and instrument distribution plus legacy-unknown counts.
- Latest backfill metadata must expose the selected policy and per-source attempt/selection/failure counters.
- The AI Research coverage panel must display policy and source mix so missing or degraded data is not mistaken for a weak stock signal.
- Preserve the research-only and no-automated-trading boundaries.

## Acceptance Criteria

- [ ] AC1: Strict mode calls only the requested provider/source and preserves existing behavior.
- [ ] AC2: `cn_resilient` selects AkShare Sina after a classified Eastmoney failure and reports the attempt chain.
- [ ] AC3: Tushare is attempted only when configured; mock and yfinance are never eligible fallbacks.
- [ ] AC4: Invalid fallback rows are rejected before persistence with sanitized diagnostics.
- [ ] AC5: Daily bars persist provider, source, adjustment, priority, and ingestion time; migration preserves legacy rows.
- [ ] AC6: Lower-priority replay cannot overwrite higher-priority rows, while primary recovery can replace fallback rows.
- [ ] AC7: Backfill create/resume/retry, TaskRun results, and coverage payloads preserve policy and per-source counters.
- [ ] AC8: Repeated provider-wide failures open a bounded run-local circuit and prevent request flooding.
- [ ] AC9: Coverage reports source mix and legacy-unknown evidence by row/instrument without changing readiness thresholds.
- [ ] AC10: AI Research visibly labels controlled fallback and renders source distribution with localized tests.
- [ ] AC11: Migration, provider, ingestion, backfill, API, worker, coverage, Web, TypeScript, Ruff, and Trellis checks pass.

## Out of Scope

- Multi-source fundamentals, corporate actions, intraday data, or market depth.
- Paid-provider procurement or creation of Tushare credentials.
- Concurrent provider fan-out or several-thousand-request parallelism.
- Automatic price blending, averaging, or broad reconciliation when multiple sources succeed.
- Ranking-model changes, trading instructions, broker integration, or automated execution.
