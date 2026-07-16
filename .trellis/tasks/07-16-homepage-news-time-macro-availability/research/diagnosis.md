# Live diagnosis

Captured on 2026-07-16 against the normal local stack.

## Reproduction

- `GET /dashboard/market-overview` returned nine macro rows and zero `ok`
  observations. Every row reported that no audited observation had been seeded.
- `GET /market-indicators/official-sources/status` reported:
  - FRED: `needs_configuration`, zero evidence;
  - World Bank: configured/no credential required, zero evidence.
- World Bank `target=chn` dry-run succeeded with one valid audited candidate,
  code `buffett_indicator_cn`, latest as-of `2025-12-31`.
- World Bank `target=all`, `usa`, and `hkg` dry-runs reproduced sanitized
  `ReadTimeout` errors at the provider's ten-second request budget.

## Conclusion

The homepage is correctly projecting an empty observation store. The product
blocker is a combination of no prior explicit refresh, missing FRED
configuration, and a World Bank timeout too short for the observed public API
latency. The safe fix is to improve the bounded World Bank request budget and
then use the existing audited write refresh. Fetching live data from a homepage
GET or inserting placeholder values would violate the evidence contract.

## Follow-up verification

- World Bank documents both `MRV` (most recent values) and `MRNEV` (most recent
  non-empty values); they are distinct valid parameters, not spelling variants.
- A direct USA comparison reproduced `mrnev=1` taking longer than 45 seconds,
  while `mrv=5` returned the 2021-2025 window within the bounded request budget.
  The service now requests that five-value window and selects the maximum valid
  observation locally after provider null/invalid rows are skipped.
- The same HKG indicator still returned an upstream Request Error with
  `mrv=5`, so no Hong Kong value was fabricated or stored.
- Explicit audited refreshes stored China `79.540605%` and USA `224.044649%`,
  both as of 2025-12-31. The dashboard now reports those two rows as `ok`;
  Hong Kong and unconfigured FRED-backed indicators remain `no_data`.
