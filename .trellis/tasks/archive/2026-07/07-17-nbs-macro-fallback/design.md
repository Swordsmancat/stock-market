# Design

## Decision

Treat direct NBS integration as a source-qualification gate. The external
document proves that an `esData` transport exists, but intentionally abbreviates
dataset identifiers and omits every indicator identifier. Transport
reachability is not sufficient evidence that a returned series maps to an
existing `MarketIndicator.code` with the expected unit and transformation.

## Qualification evidence

- Legacy `easyquery` query: official host reachable through public pages, but a
  server-side data query from the runtime returned HTTP 403.
- Current `esData` endpoint: reachable without a cookie; an empty JSON request
  returned HTTP 500, confirming that a structured body and valid identifiers
  are mandatory.
- Reviewed document: gives only one complete unemployment dataset `cid`, no
  unemployment indicator IDs, and abbreviated trade/money/fiscal dataset IDs.

## Production contract when unblocked

1. An explicit POST refresh calls the provider; dashboard GET routes never do.
2. The provider validates expected fields and units before normalization.
3. Observations use the existing `MarketIndicatorObservation` upsert path and
   retain full NBS dataset/indicator IDs, upstream display name, source URL,
   retrieval time, and transformation methodology.
4. Provider failure writes nothing and leaves the last successful rows intact.
5. Tests use captured, redacted fixtures; default tests never require NBS.

## Unblock condition

Obtain a complete official response for each proposed series together with the
full request identifiers, then independently match the display name, period,
unit, and value to an official NBS page. Until then, AkShare remains the active
production adapter for overlapping China macro series.
