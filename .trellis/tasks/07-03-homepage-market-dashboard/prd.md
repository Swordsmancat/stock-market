# Homepage market dashboard

## Goal

Transform the homepage into a market-dashboard-first experience that makes the most important market information visible immediately: CN/HK/US core indices, followed instruments with compact K-line charts, and important valuation indicators led by the Buffett Indicator.

## User Value

- Users can open the homepage and understand broad market conditions before seeing operational diagnostics.
- Users can visually monitor followed instruments through K-line cards and open the existing instrument detail page for richer chart controls.
- Users can see CN/HK/US index context and valuation context without manually searching for symbols or reports.
- Users can distinguish real daily-bar/valuation data from stale, missing, provider-failed, or not-yet-seeded data.

## Confirmed Facts

- The frontend homepage currently lives at `apps/web/app/[locale]/page.tsx` and loads instruments, watchlist, daily bars, latest bars, reports, portfolio, technical indicators, fundamentals, news, task runs, and alert triggers.
- The homepage already uses `apps/web/components/mini-price-chart.tsx`, but that component renders only a close-price line chart.
- The project already has a K-line-capable `PriceChart` in `apps/web/components/price-chart.tsx`. It uses Recharts custom candlesticks and supports MA(20), Bollinger bands, RSI, and volume toggles.
- `apps/web/lib/chart-indicators.ts` can derive missing OHLC values from close values and compute MA, Bollinger bands, and RSI series.
- Instrument detail pages already use `PriceChart` and load daily OHLCV bars from `/market-data/{symbol}/bars` in `apps/web/app/[locale]/instruments/[symbol]/page.tsx`.
- Backend market-data endpoints in `apps/api/routers/market_data.py` already expose single-symbol bars, single-symbol latest bar, and batch latest bars.
- Backend watchlist endpoints in `apps/api/routers/watchlists.py` expose the default watchlist. Watchlist payloads already include symbol, market, name, activity, alert rules, latest price, RSI, and alert status through the service layer.
- `packages/domain/models.py` has `Instrument.asset_type`, `DailyBar`, `MinuteBar`, `TechnicalIndicator`, and `FundamentalSnapshot`.
- There is no dedicated market-index catalog, macro-indicator model, valuation-indicator model, Buffett-indicator model, or dashboard aggregation API yet.
- Index chart data can reuse existing daily-bar market-data contracts if an index catalog maps internal index codes to provider symbols.

## Product Decisions

- Homepage first screen should be market-dashboard-first. Data health, task runs, provider settings, ingestion diagnostics, reports, news, and portfolio sections should be demoted below market information unless an empty/error state needs a recovery action.
- First implementation depth is full-stack: backend models, service, API, frontend layout, and tests. It is not a frontend-only mock.
- Market coverage is CN + HK + US.
- Default index list is limited to 10 core indices: Shanghai Composite, Shenzhen Component, ChiNext, CSI 300, CSI 500, Hang Seng, Hang Seng Tech, S&P 500, Nasdaq Composite, and Dow Jones Industrial Average.
- Followed-instrument K-line section shows at most 6 instruments, uses approximately 3 months of daily bars, and renders compact candlesticks with MA20 and volume. Full parameter controls remain on the instrument detail page.
- Valuation/macro indicator scope starts with the Buffett Indicator. The backend model should be generic enough for future valuation and macro indicators.
- Buffett Indicator values use auditable seeded real observations for the first implementation. Each value must include `source`, `as_of`, and component data. If a region's values cannot be verified at implementation time, it must show explicit no-data instead of fabricated values.
- Homepage consumes a new aggregated backend endpoint, `GET /dashboard/market-overview`, instead of assembling many independent requests in the page.

## Requirements

### R1. Homepage hierarchy

- The first screen must prioritize market information in this order: core index cards, followed-instrument K-line cards, and valuation indicator cards.
- Operational data-health diagnostics may remain available lower on the page or as recovery links in empty/error states.
- The page must not imply real-time support; labels must describe latest available daily bars where applicable.

### R2. Followed-instrument K-line cards

- The dashboard must select up to 6 active default-watchlist instruments. If the watchlist is empty, it must use a clear fallback sample and label the scope honestly.
- Each card must include symbol/name, market, latest close when available, daily movement when at least two daily bars exist, source/freshness/as-of information, compact candlestick chart, and a link to `/instruments/{symbol}`.
- Missing/provider-failed bars must render a clear unavailable state and next action rather than an empty chart.

### R3. Core index cards

- The dashboard must include the 10 confirmed CN/HK/US default indices.
- Each index item must use an internal code that avoids ambiguous symbols and must maintain provider-symbol mapping separately.
- Each index card must include display name, region, latest level when available, daily movement when at least two bars exist, as-of/freshness, and a small trend visual or unavailable state.

### R4. Valuation indicator cards

- The backend must include generic market-indicator and observation storage that can represent the Buffett Indicator and future valuation/macro indicators.
- The dashboard must include Buffett Indicator cards for CN, HK, and US.
- Each available indicator card must expose value, unit, status, `as_of`, source, and component summary. Missing observations must render explicit no-data.

### R5. Dashboard aggregation API

- Add `GET /dashboard/market-overview?provider=...`.
- The payload must contain followed instruments, indices, valuation indicators, generated date/range metadata, and source/status metadata needed by the frontend.
- Provider failures in one section must not prevent other sections from rendering.

### R6. Localization and accessibility

- New user-visible strings must be localized in `apps/web/messages/en.json` and `apps/web/messages/zh.json`.
- Direction and movement must be text/sign-first, not color-only.
- Cards must use links for navigation and buttons only for actions.

### R7. Testing and validation

- Add focused backend model/service/API tests for market indicators and dashboard aggregation.
- Update focused frontend homepage tests for the new market-dashboard-first structure, links, no-data states, and localized labels.
- Trellis validation must pass before completion.

## Acceptance Criteria

- [ ] `GET /dashboard/market-overview` returns a stable JSON view model with watchlist K-line summaries, 10 core indices, and Buffett Indicator entries.
- [ ] The backend can seed and retrieve auditable Buffett Indicator observations with `source`, `as_of`, and component data.
- [ ] The dashboard returns explicit no-data states when an indicator observation or index/watchlist bar set is unavailable.
- [ ] Homepage first screen displays core indices, followed K-line cards, and valuation cards before operational diagnostics.
- [ ] Followed K-line cards show compact candlesticks with MA20/volume and link to existing instrument detail routes.
- [ ] Default index cards include the confirmed CN/HK/US list and avoid ambiguous provider symbols in the UI contract.
- [ ] New copy is localized in English and Chinese.
- [ ] Focused backend tests, focused frontend tests, and Trellis validation pass.

## Out of Scope

- True real-time quotes, streaming updates, or intraday live charts.
- User-customizable index lists, indicator lists, or homepage chart settings.
- Full automatic external data ingestion for GDP and total-market-cap sources.
- A new charting library.
- Replacing the existing instrument detail chart experience.
