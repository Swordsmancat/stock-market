# Integrate personal research modules from reference

## Goal

Absorb the useful modules from the supplied reference sidebar into the existing
single-user stock research product without recreating features that already
exist or turning the product into a broad trading terminal.

## Background

The reference contains Home, Investment Calendar, Industry Ranking, Watchlist,
Portfolio, Macro, Agriculture, China Consumption, Real Estate, FX, Overlay
Comparison, Non-ferrous Metals, Stock/Futures/ETF K-lines, Index Sectors,
Market Movers, Screening, and Stock Comparison.

The repository already has usable equivalents for Home, Investment Calendar,
Industry Ranking, Watchlist, Macro Research, stock detail/K-lines, and AI
screening. Portfolio exists but is intentionally secondary for personal use.
Storage and crawler monitoring are operational support pages and remain
separate from the reference feature map.

## Requirements

- Reuse existing modules instead of creating duplicate routes or data flows.
- Integrate new capabilities in this order:
  1. stored A-share market movers;
  2. stock comparison and overlay comparison as one coherent workflow;
  3. unified discovery/access for stock, ETF, and index K-lines;
  4. focused topic research views for agriculture, China consumption, real
     estate, and non-ferrous metals, built from stored evidence;
  5. futures K-lines only after the preceding personal-research modules prove
     useful, because futures introduce a separate instrument/data domain.
- Keep all new read surfaces database-first. A page load must not trigger a
  provider request, crawler, backfill, shortlist generation, or trading action.
- Preserve the existing research-only boundary. New modules must not add
  orders, broker integration, position sizing, target prices, or automated
  trading.
- Prefer a small number of coherent navigation destinations. Closely related
  reference modules may be merged when that improves personal-use ergonomics.
- Preserve the existing five-item mobile navigation unless a later child task
  provides evidence that it must change.

## Module Map

| Reference module | Product decision |
| --- | --- |
| Home | Reuse `/` |
| Investment Calendar | Reuse `/investment-calendar` |
| Industry Ranking | Reuse `/market-research` |
| Watchlist | Reuse `/watchlist` |
| Portfolio | Keep existing `/portfolios`, secondary |
| Macro | Reuse `/evidence` |
| Stock K-line | Reuse instrument detail |
| Screening | Reuse `/ai-research` |
| Market Movers | Add first as a stored-data read surface |
| Stock Comparison / Overlay Comparison | Add as one comparison workflow |
| ETF / Index K-line access | Improve unified instrument discovery |
| Agriculture / China Consumption / Real Estate / Non-ferrous Metals | Add later as stored-evidence topic views |
| FX | Defer until a concrete personal research workflow requires it |
| Futures K-line | Last; requires a new data-domain acceptance |

## Acceptance Criteria

- [x] Every reference module has an explicit reuse, merge, add, or defer
      decision in this PRD.
- [x] Child tasks are delivered in the stated order and can be verified and
      rolled back independently.
- [x] Added pages are database-first and do not initiate provider or trading
      mutations on load.
- [x] Existing routes remain the authority for already integrated modules.
- [x] The final navigation remains compact and suitable for one person.

## Out of Scope

- Professional terminal parity or cloning the reference product.
- Broker/account integration, orders, execution, or automated trading.
- Adding every reference sidebar label as a separate route.
- Live quote streaming or provider calls initiated by read-only pages.
