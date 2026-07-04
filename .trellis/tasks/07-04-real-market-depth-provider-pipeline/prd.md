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

- [ ] At least one verified provider path can populate one or more market-depth sections with real data.
- [ ] Unsupported sections remain degraded with explicit reasons and capability metadata.
- [ ] Large-order detection uses verified recent trades and an explicit threshold.
- [ ] `MarketDepthCard` renders real rows and degraded sections correctly.
- [ ] Backend/frontend tests prove real data is never fabricated for unsupported providers.
- [ ] Developer manual and provider capability matrix are updated.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
