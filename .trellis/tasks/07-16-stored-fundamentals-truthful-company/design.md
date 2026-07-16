# Truthful stored fundamentals and company enrichment design

## Data flow

```text
stored FundamentalSnapshot
  -> serialize stored financial metrics
  -> PE == 0 becomes null in the read projection only
  -> exact A-share + public gate
       -> normalized Redis company cache
       -> fixed CompanySurvey GET on miss
       -> merge company/status/provenance into response
  -> detail and assistant consume the same fundamental citation
```

## Provider boundary

Expose an independent `fetch_eastmoney_public_company()` entry point using the
same symbol validation, exchange mapping, headers, timeout, byte/media limits,
redirect rejection, identity checks, text bounds, and sanitized errors as the
combined fundamentals provider. It performs exactly one CompanySurvey GET.

## Service boundary

Database lookup stays first and stored financial values are never replaced by
the company request. The normalized company cache is keyed only by exact symbol
because company profile fields are not report-period metrics. Success and
explicit no-data cache for 1800 seconds; failures do not cache and add a bounded
diagnostic while returning the stored item.

The read projection maps `pe_ratio == 0` to `null` and removes the legacy summary
that claimed `PE 0.00`. It does not mutate the ORM row. Nonzero and negative PE
values remain unchanged.

## Compatibility and rollback

- No migration, historical rewrite, scheduler, or API route change.
- Removing the enrichment helper restores the previous database-only payload.
- Redis keys are disposable and expire automatically.
