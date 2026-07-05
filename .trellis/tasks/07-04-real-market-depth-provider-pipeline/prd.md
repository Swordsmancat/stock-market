# Real Market Depth Provider Pipeline

## Goal

Upgrade the existing market-depth degraded-safe contract into a verified provider-backed pipeline for order book, recent trades, large orders, and fund-flow data where provider permissions and data quality allow.

## Requirements

- Select and document candidate providers for Level-2/order-book, recent trades, large-order detection, and fund-flow data.
- Extend provider contracts without breaking existing degraded-safe payloads.
- Preserve `GET /market-data/{symbol}/depth?depth_levels=5&large_order_threshold_amount=1000000` as the public contract.
- Return real order book, recent trades, large orders, and fund-flow sections only when source data is verified and normalized.
- Keep provider capability matrix explicit for `mock`, `yfinance`, `akshare`, `tushare`, and any new provider.
- Ensure large-order threshold behavior is configurable, documented, and tested.
- Avoid fabricating depth data from daily bars, mock providers, or estimated volume distributions.
- Cover provider unavailable, permission denied, empty response, partial section support, and malformed payload cases.

## Acceptance Criteria

- [x] At least one fixture-verified explicit provider path can populate one or more market-depth sections with real-shaped provider data; production AkShare Level-2 live smoke remains provider/network dependent.
- [x] Unsupported sections remain degraded with explicit reasons and capability metadata.
- [x] Large-order detection uses verified recent trades and an explicit threshold.
- [x] `MarketDepthCard` renders real rows and degraded sections correctly.
- [x] Backend/frontend tests prove real data is never fabricated for unsupported providers.
- [x] Developer manual and provider capability matrix are updated.

## Completion Status

The provider-boundary MVP is complete: explicit market-depth provider models, AkShare fixture-tested candidate parsing, section-level partial/degraded payloads, verified-trade-only large-order derivation, frontend rendering, readiness diagnostics, and documentation are in place.

Production verified Level-2 / tick / fund-flow remains a professional-terminal follow-up because the opt-in AkShare live smoke currently fails with `ConnectionError`. The implementation must therefore continue to label AkShare depth as a candidate/degraded provider path unless a future live smoke succeeds and the capability matrix is updated.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
