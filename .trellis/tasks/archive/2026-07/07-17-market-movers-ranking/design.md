# Stored market movers design

## Boundary

This child adds one database read service, one thin FastAPI router, and one
server-rendered Next page. It reads `Market`, `Exchange`, `Instrument`, and
`DailyBar`; it does not add tables, migrations, worker tasks, provider clients,
or page-triggered refresh actions.

## Backend contract

`get_market_movers_payload(*, session, market="CN", direction="gainers",
exchange="all", limit=20)` returns:

- `status`, `market`, `direction`, `exchange`, and `count`;
- `trade_date` and `previous_trade_date`;
- `provider`, `adjustment`, and bounded `sources` provenance;
- `eligible_count` and `omitted_count`;
- `items[]` with rank, symbol, name, exchange, close, previous close, absolute
  change, percentage change, volume, amount, provider, source, and adjustment.

Only `CN`, `gainers|losers`, `all|SSE|SZSE|BSE`, and `10|20|50` are accepted.
The router maps these to FastAPI query constraints and delegates to the service
with the injected SQLAlchemy session.

## Query and cohort selection

1. Resolve the latest and immediately preceding distinct stored trade dates
   for active CN stocks. If fewer than two exist, return `no_data`.
2. On the latest date, group bars by `provider, adjustment`, choose the largest
   group, and break ties lexically. This is the authoritative cohort.
3. Join current and previous `DailyBar` aliases to the same active instrument,
   exact market dates, and chosen cohort; optionally filter exchange.
4. Calculate change in Python using `Decimal` after bounded rows are loaded.
   Reject invalid/non-positive previous closes before division.
5. Sort deterministically and slice only after all eligible rows are scored.

The service returns source distribution for eligible current bars while keeping
provider/adjustment singular. It never catches database failures as seed data;
an actual query failure remains a server error and is rendered as unavailable
by the page.

## Frontend

The server page reads validated search params and fetches one backend payload.
Controls are ordinary localized links so they work without client JavaScript.
The page uses the existing financial header, compact controls, and a semantic
table. Positive/negative colors supplement, rather than replace, signed text.
On narrow screens, nonessential amount/source columns collapse while primary
identity and change values remain visible without page-level overflow.

## Compatibility and rollback

All API/page/navigation/message additions are additive. No migration or stored
row changes occur. Rollback removes the router registration, route, navigation
entry, translations, service, and focused tests without touching data.
