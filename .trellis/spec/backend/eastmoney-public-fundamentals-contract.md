# Eastmoney Public Fundamentals Fallback Contract

## 1. Scope / Trigger

- Trigger: a fundamentals read targets an exact six-digit A-share symbol, the
  existing `akshare_enabled` public-CN gate is on, and either no stored snapshot
  exists, the stored financial snapshot is incomplete, or company context is
  missing.
- Scope: `packages/providers/eastmoney_public_fundamentals.py`,
  `packages/services/fundamentals.py`, `GET /fundamentals/{symbol}`, instrument
  detail, and the market assistant's existing fundamental evidence citation.
- Non-goals: login, Cookies, account data, bulk crawling, persistence from GET,
  scheduler changes, trading, or changes to US/HK behavior.

## 2. Signatures

- Provider:
  `fetch_eastmoney_public_fundamentals(symbol, *, as_of, timeout=8.0, http_get=None)`
- Company provider:
  `fetch_eastmoney_public_company(symbol, *, timeout=8.0, http_get=None)`
- Service:
  `get_fundamental_payload(symbol, as_of=None, session=None)`
- API: `GET /fundamentals/{symbol}?as_of=YYYY-MM-DD`
- Cache key: `fundamentals:eastmoney-public:{symbol}:{as_of}`, TTL 1800 seconds.
- Company cache key: `fundamentals:eastmoney-public-company:{symbol}`, TTL 1800 seconds.
- Citation: `fundamental_metrics:{symbol}:{report-date}`.

## 3. Contracts

- A stored snapshot with at least three non-null core metrics returns without a
  public financial call because the verified public source cannot supply PE and
  therefore cannot be more complete. Company enrichment remains independently
  bounded and never replaces stored financial values.
- An eligible stored snapshot with fewer than three non-null core metrics may
  resolve the existing cached/public Eastmoney payload once. Compare whole
  snapshots across PE, revenue growth, net margin, and debt-to-assets. Select
  the public payload only when its non-null count is strictly greater; a tie or
  worse public payload keeps the stored snapshot.
- Selection never stitches financial fields across report dates. The selected
  payload owns its complete provider, report date, currency, metrics, company,
  diagnostics, and citation projection.
- Public fallback accepts only fixed HTTPS GETs to
  `RPT_F10_FINANCE_MAINFINADATA` and `CompanySurvey/PageAjax`. It sends no Cookie
  or authorization, disables redirects and environment proxy inheritance, caps
  bytes/rows, uses one eight-second attempt, and exposes only sanitized errors.
- Select the newest single financial row whose `REPORT_DATE <= requested as_of`.
  Percentage-point values become decimal ratios. Missing values remain `null`;
  PE is always `null` because the verified response has no reliable PE field.
- Additive response fields are `status`, `provider`, `upstream_sources`,
  `retrieved_at`, `diagnostics`, and `item.company` (`name`, `industry`,
  `business_scope`, `profile`). Company failure degrades valid financial metrics.
- Cache only normalized success/degraded/no-data payloads. Redis failure is
  non-blocking. Provider failure is not cached. No read path adds or commits ORM rows.
- The assistant keeps one fundamental citation and bounds company fields again
  before adding them to summary/metadata. Raw upstream payloads never cross layers.

## 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Stored snapshot exists, gate disabled/non-CN | Return database projection; zero cache/network |
| Stored A-share has at least three core metrics | Skip public financial; optionally enrich company |
| Stored A-share has fewer than three core metrics | Resolve one cached/public coherent snapshot |
| Public snapshot is strictly more complete | Return the whole public projection and provenance |
| Public snapshot ties or is less complete | Keep the whole stored projection; enrich company normally |
| Public financial request is unavailable/no-data | Keep the stored projection; company fallback remains bounded |
| Company result is empty | Keep metrics, cache company no-data, return degraded company state |
| Company request/schema fails | Keep metrics, sanitized diagnostic, do not cache failure |
| Symbol is not exact six digits or gate is off | Preserve existing non-CN/fixture behavior |
| Financial result is empty | `status=no_data`, `item=null`, cache for 1800 seconds |
| Financial HTTP/schema/identity/date/numeric failure | `status=unavailable`, sanitized diagnostic, no cache |
| Company request/schema failure | Keep metrics, `status=degraded`, `company=null` |
| Redis read/write fails | Continue truthfully; do not fail the request |
| Requested date precedes every report | Treat as explicit no-data; never use a future report |

## 5. Good / Base / Bad Cases

- Good: `600519` has no stored row, the gate is enabled, the 2026-06-30 report
  is selected, ratios and company context render, and PE displays unavailable.
- Good: a stored `600519` snapshot keeps its 6.54%/52.22%/12.12% financial
  values without a public financial call, renders PE unavailable, and adds
  bounded company context.
- Good: stored `000001` has only debt-to-assets while one public 2026-03-31
  snapshot has growth, margin, and debt; the whole public snapshot wins and its
  report date/source/citation remain intact.
- Base: a stored non-CN snapshot or disabled gate returns without Redis/network.
- Base: stored and public snapshots have equal non-null counts; stored wins.
- Base: company survey is unavailable but financial metrics remain usable and degraded.
- Bad: fill PE with zero, stitch metrics across periods, prefer a public tie,
  copy a future report, persist fallback data during GET, or import a browser
  Cookie to improve coverage.

## 6. Tests Required

- Provider tests assert fixed params/headers, no credentials/redirects/retry,
  bounds, identity/date/finite numbers, percentage normalization, and sanitized errors.
- Service tests assert complete stored metrics skip public financial calls,
  strictly more complete public snapshots win whole, ties/failures keep stored
  data, company success/no-data caches remain bounded, no-snapshot fallback is
  normalized, and every GET performs zero ORM writes.
- API/component tests assert additive company context and `pe_ratio=null` rendering.
- Assistant tests assert bounded company metadata and unchanged known citation IDs.
- Run focused tests, full Python/Web suites, Ruff, TypeScript, task validation,
  redaction scan, and one sanitized live public GET.

## 7. Wrong vs Correct

### Wrong

```python
snapshot = fetch_public(symbol)
session.add(to_model(snapshot, pe_ratio=snapshot.pe_ratio or 0))
```

This performs a write from a read path and fabricates an unavailable PE value.

### Correct

```python
stored = truthful_database_projection(row)
if metric_count(stored) >= PUBLIC_MAX_METRIC_COUNT:
    return enrich_company_only_when_eligible(stored)
public = normalized_public_financial_payload_or_no_data(symbol, as_of)
return public if metric_count(public) > metric_count(stored) else enrich_company(stored)
```

The selected snapshot remains coherent while missing company context is
independently bounded, cached, read-only, and truthfully optional.
