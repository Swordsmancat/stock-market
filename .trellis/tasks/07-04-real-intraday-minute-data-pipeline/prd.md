# Real Intraday Minute Data Pipeline

## Goal

Upgrade the existing intraday chart degraded-safe contract into a real minute-bar data pipeline for at least one verified provider, while preserving explicit degraded/unavailable behavior for unsupported providers.

## Requirements

- Select and document one initial verified provider path for minute-level bars.
- Extend provider/service contracts to fetch normalized intraday bars without reusing daily bars as fake minute data.
- Preserve `GET /market-data/{symbol}/intraday?date=YYYY-MM-DD&timeframe=1m` as the public contract.
- Return real minute-bar items only when provider data is verified and normalized.
- Keep degraded payloads for providers without verified minute-bar support.
- Include previous close, intraday price, average price when available, volume, source, provider, and availability metadata.
- Cover market-session edge cases such as no trading day, partial data, empty provider responses, and unsupported timeframe.
- Add backend and frontend tests proving real-data and degraded paths remain distinct.

## Acceptance Criteria

- [ ] At least one provider returns normalized real minute-bar payloads through `/market-data/{symbol}/intraday`.
- [ ] Unsupported providers continue returning explicit degraded payloads and never fabricate intraday data.
- [ ] `IntradayPriceChart` renders real intraday points and keeps degraded/empty states covered by tests.
- [ ] Provider capability documentation and developer manual are updated.
- [ ] Focused backend and frontend tests pass.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
