# Official Macro Refresh Contract

## Scenario: Audited FR007 And FDR007 Refresh

### 1. Scope / Trigger

- Trigger: an operator explicitly refreshes the `repo_rates` AkShare family.
- Applies to `packages/providers/akshare_macro_provider.py`,
  `packages/services/market_indicators.py`, and
  `POST /market-indicators/official-refresh/akshare-cn`.
- Dashboard GET routes remain database-only; this is research evidence, not a
  trading signal or background crawler.

### 2. Signatures

- Provider: `AkShareMacroProvider.fetch(family="repo_rates", history_limit=24)`.
- Service: `refresh_akshare_cn_macro_indicators(session, family="repo_rates",
  history_limit=24, dry_run=False)`.
- API body: `{"family":"repo_rates","history_limit":24,"dry_run":false}`.
- Persistence: existing unique `(indicator_id, as_of)`
  `MarketIndicatorObservation` upsert.

### 3. Contracts

- `repo_rate_hist` is called once for the previous calendar month and once for
  the current month to date because each call must remain within one month.
- Source columns map exactly: `FR007 -> cn_fr007`,
  `FDR007 -> cn_fdr007`; both are direct percentages.
- `FDR007` is never renamed to generic `DR007`.
- Components retain `provider`, `provider_function`, `source_url`,
  `source_date_field`, `source_value_field`, `retrieved_at`, and `methodology`.
- Successful rows are deduplicated by date, sorted, and bounded per code.

### 4. Validation & Error Matrix

| Condition | Behavior |
| --- | --- |
| Missing `date`, `FR007`, or `FDR007` column | Family `schema_mismatch`; no repo writes |
| Null/non-finite value | Skip that value; never store zero |
| Invalid date | Skip both values for that row |
| One monthly request raises | Family provider error; preserve old observations |
| `dry_run=true` | Validate/upsert in transaction, then roll back |
| Valid repeated date | Idempotent observation upsert |

### 5. Good / Base / Bad Cases

- Good: both months return valid frames and the latest 24 observations for each
  code are stored with ChinaMoney provenance.
- Base: one column contains a null; the other series still persists that date.
- Bad: call across a month boundary or treat FDR007 as DR007.

### 6. Tests Required

- Provider tests assert two same-month requests, normalization independent of
  source order, exact field provenance, and null skipping.
- Service tests assert both codes persist separately and project as fresh daily
  dashboard values.
- API tests retain partial-family diagnostics and updated dashboard totals.
- Web tests/type-check must resolve symmetric English/Chinese built-in labels.

### 7. Wrong vs Correct

#### Wrong

```python
repo_rate_hist(start_date="20260615", end_date="20260717")
# or: store FDR007 under a code named cn_dr007
```

#### Correct

```python
repo_rate_hist(start_date="20260601", end_date="20260630")
repo_rate_hist(start_date="20260701", end_date="20260717")
# Preserve FR007 and FDR007 as separate source-defined series.
```
