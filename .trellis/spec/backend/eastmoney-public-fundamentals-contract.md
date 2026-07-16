# Eastmoney Public Fundamentals Fallback Contract

## 1. Scope / Trigger

- Trigger: a fundamentals read targets an exact six-digit A-share symbol, the
  existing `akshare_enabled` public-CN gate is on, and either no stored snapshot
  exists or a stored financial snapshot lacks company context.
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

- A stored database row is authoritative for report date, currency, and
  financial metrics. Company enrichment never replaces those values.
- Historical ingestion used exact PE zero as a missing-value compatibility
  placeholder. Database read projections expose exact zero as `null`, remove
  the misleading `PE 0.00` summary, and do not mutate the stored row. Nonzero
  and negative PE values remain unchanged.
- An eligible stored A-share payload may call only the independent CompanySurvey
  operation on a company-cache miss. It must not call the financial endpoint.
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
| Stored A-share exists, company cache miss | Keep database metrics; one CompanySurvey GET |
| Stored PE is exact zero | Return `pe_ratio=null`, leave the ORM value unchanged |
| Stored PE is nonzero or negative | Preserve the stored value |
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
  values, renders PE unavailable, and adds bounded company context.
- Base: a stored non-CN snapshot or disabled gate returns without Redis/network.
- Base: company survey is unavailable but financial metrics remain usable and degraded.
- Bad: fill PE with zero, stitch metrics across periods, copy a future report,
  persist fallback data during GET, or import a browser Cookie to improve coverage.

## 6. Tests Required

- Provider tests assert fixed params/headers, no credentials/redirects/retry,
  bounds, identity/date/finite numbers, percentage normalization, and sanitized errors.
- Service tests assert stored metrics remain authoritative, zero PE projects to
  null, company success/no-data caches, company failure is non-blocking,
  no-snapshot fallback remains normalized, and every GET performs zero ORM writes.
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
row = _latest_fundamental_snapshot(symbol, as_of, session)
if row is not None:
    payload = truthful_database_projection(row)
    return enrich_company_only_when_eligible(payload)
return normalized_public_financial_payload_or_no_data(symbol, as_of)
```

The database financial snapshot remains authoritative while missing company
context is independently bounded, cached, read-only, and truthfully optional.
