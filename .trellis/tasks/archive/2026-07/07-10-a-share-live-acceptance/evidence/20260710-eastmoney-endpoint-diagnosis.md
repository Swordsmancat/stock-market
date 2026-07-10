# AkShare Daily-Bar Endpoint Diagnosis

- Execution date: 2026-07-10
- Mode: read-only, no database writes
- AkShare: 1.18.64
- Target operation: A-share daily bars

## Findings

1. `push2his.eastmoney.com`, `82.push2his.eastmoney.com`, and
   `push2.eastmoney.com` resolve successfully.
2. TLS 1.3 handshakes to both K-line hosts succeed.
3. The exact AkShare Eastmoney request fails at the HTTP data stage with
   `ConnectionError`.
4. Browser-like request headers, the alternate Eastmoney K-line host, an SZSE
   symbol, and unadjusted data all produce the same classified failure.
5. AkShare's Sina single-symbol endpoint returns nine rows for both SSE and
   SZSE probes over the same date range.

## Classification

- Primary: `provider_limitation_or_environment_configuration`
- Excluded by evidence: DNS failure, TLS failure, symbol-only failure,
  `qfq`-only failure, short-date-window failure, and missing request headers.
- Confidence: high that the current network path or upstream policy resets the
  Eastmoney K-line HTTP response after TLS establishment.

## Safety decision

The Sina endpoint is not used as an automatic full-market fallback because:

- AkShare documents it as susceptible to IP blocking under bulk collection;
- 5,530-symbol baseline use would create an unsafe provider load pattern;
- current `DailyBar` storage does not retain endpoint-level source provenance;
- using it silently would violate the acceptance contract even though the
  top-level provider name remains AkShare.

No code fallback, threshold reduction, alternate provider, or acceptance write
was performed.
