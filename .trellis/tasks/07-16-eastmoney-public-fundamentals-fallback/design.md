# Eastmoney public fundamentals fallback design

## Boundaries

The provider module owns HTTP safety and wire normalization. The fundamentals
service owns database-first eligibility, Redis caching, and response projection.
Instrument detail and the market assistant consume additive fields from the
existing `/fundamentals/{symbol}` contract. No ORM or route signature changes.

## Data flow

```text
fundamentals read
  -> stored snapshot exists --------------------> existing database payload
  -> no snapshot + exact A-share + gate enabled
       -> Redis normalized payload hit ---------> Eastmoney public payload
       -> cache miss
            -> fixed financial GET
            -> select newest report <= as_of
            -> fixed company survey GET
            -> validate/bound/normalize
            -> short Redis cache
            -> detail + assistant citation
  -> ineligible symbol -------------------------> existing fixture/no-data path
```

## Provider contract

`fetch_eastmoney_public_fundamentals(symbol, as_of, http_get=...)` returns a
frozen normalized snapshot or raises a sanitized provider error. The financial
operation accepts `text/plain` JSON because that is the verified endpoint
contract; company survey requires JSON. Both use fixed hosts/paths, no redirects,
no Cookie, finite response limits, and one attempt.

Financial rows are sorted by parsed `REPORT_DATE` and filtered to `<= as_of`.
The selected row owns all three metrics. Percentage-point fields are divided by
100. PE remains `None`. Company rows must match the requested symbol; text is
trimmed and capped before it crosses the provider boundary.

## Service and cache contract

The database query remains first. Eligibility is exact six digits plus the
existing `akshare_enabled` public-CN gate. Redis stores only normalized JSON
under a symbol/as-of key for 1800 seconds. Redis read/write errors are ignored;
provider failures return an additive sanitized diagnostic and are not cached.
No read path calls `session.add`, `commit`, or an ingestion function.

## Response and citation contract

Existing fields remain. Additive fields include `status`, `provider`,
`upstream_sources`, `retrieved_at`, `diagnostics`, and `item.company` with
`name`, `industry`, `business_scope`, and `profile`. The citation remains
`fundamental_metrics:<symbol>:<report-date>` so existing assistant validation
continues to work. Citation metadata receives bounded company fields and
upstream operation IDs, never raw payloads.

## Compatibility and rollback

- No migration or persistent data rewrite.
- US/HK fixtures and all explicit ingestion functions remain unchanged.
- Removing the provider/service branch restores prior behavior; Redis keys are
  disposable and expire automatically.
- Live acceptance is read-only and prints normalized metadata only.
