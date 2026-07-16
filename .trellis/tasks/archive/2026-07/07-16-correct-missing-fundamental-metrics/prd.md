# Correct Missing Fundamental Metrics

## Goal

Prevent missing fundamental metrics from being presented as factual zero values
in the personal instrument-research workflow.

## Background

- The representative A-share detail page for `000001` shows revenue growth and
  net margin as `0.00%` even though the provider did not return those metrics.
- A read-only database probe confirmed that the latest `akshare` row contains
  sentinel zeros for PE, revenue growth, and net margin while debt-to-assets is
  populated.
- The web detail payload already accepts nullable metric fields and renders a
  localized unavailable label for `null`.

## Requirements

- Fundamental metric types and persistence must preserve `null` independently
  for PE, revenue growth, net margin, and debt-to-assets.
- Yfinance, AkShare, and Tushare ingestion must not coerce a missing metric to
  `0.0`; a genuine numeric zero must remain a valid value.
- Existing zero sentinels written by the known provider adapters must be
  normalized to `NULL` by an additive migration. Other sources must not be
  rewritten.
- Database and API projections must serialize missing metrics as JSON `null`
  without raising conversion or summary-formatting errors.
- Keep the homepage, provider selection, refresh behavior, thresholds, and all
  mutation-heavy research workflows unchanged.

## Acceptance Criteria

- [x] A focused regression fails before the fix and proves a partially
  populated provider response persists missing metrics as `NULL`.
- [x] A database-backed API regression returns `null` for missing metrics and
  preserves a genuine `0.0` metric.
- [x] The `000001` detail page renders `\u6682\u65e0` for unavailable PE, revenue
  growth, and net margin after the migration, while retaining its real
  debt-to-assets value.
- [x] Focused backend tests, the web test suite, type-checking, Trellis Check,
  and a read-only browser acceptance pass succeed.
