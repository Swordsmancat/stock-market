# Personal research workflow blocker design

## Scope

This change repairs four verified workflow boundaries without redesigning the
homepage or adding product modules:

1. Top-shell hydration and global search.
2. Immutable shortlist context reaching the assistant.
3. Exact, side-effect-free watchlist membership on instrument detail.
4. Honest empty/error/currency/missing-value presentation.

## Global search boundary

`TopNavBar` currently makes the whole header one client boundary even though it
only needs translated shell text. Search, notifications, language, and theme
then hydrate as one subtree. Real-browser checks show all of these controls
remain closed while their scripts load successfully.

Convert `TopNavBar` to an async server component using
`next-intl/server`. Keep `GlobalSearch` and the three sibling controls as small
independent client islands. Retain the controlled Radix dialog; do not add a
native-dialog or pointer-event workaround. Preserve known `market` when a
search result navigates to detail.

## Shortlist-to-assistant contract

The cross-layer contract is exactly:

```text
UI event/query -> { symbol, researchSnapshotId? }
web request    -> research_snapshot_id
API/service    -> committed run lookup + exact symbol membership
prompt         -> deterministic structured snapshot summary
response       -> applied snapshot metadata + synthetic citation
```

The assistant service reuses `get_research_shortlist`. It creates context only
from decision date, rank, score, and structured factor/gap/invalidation fields.
Persisted message, label, and explanation prose are excluded. A matching
candidate contributes one `research_shortlist:{run}:{candidate}` evidence item
and citation. Invalid, missing, uncommitted, or symbol-mismatched snapshots add
an explicit diagnostic and degrade the response rather than silently falling
back.

The AI desk stores the snapshot ID associated with the active symbol. Daily
shortlist handoff sets it; manual, watchlist, recommendation, and ordinary
discovery selection clear it. `MarketAssistantCard` keys and requests include
the optional ID so changing cohort cannot retain an old answer.

Instrument detail consumes `research_snapshot_id` and optional `market` query
parameters and passes the ID to the same assistant card. No snapshot arrays are
serialized through the browser.

## Instrument identity and watchlist membership

Watchlist identity is `(symbol, market)`. Source links preserve market when
known; instrument detail uses an exact instrument metadata lookup as fallback.
Ambiguous or failed identity resolution remains unavailable.

Add a read-only service/API query for one watchlist membership. It directly
queries the default watchlist item and never calls the enriched watchlist path,
because enrichment evaluates alerts and can commit alert-history writes.

Instrument detail receives serialized identity and membership state and renders
a small client toggle. It reuses the existing same-origin POST/DELETE proxy,
shows pending/success/error feedback, refreshes server state, and never exposes
report-generation or refresh controls. Unknown membership disables the action.

## Financial state presentation

`fetchWatchlist` returns a discriminated loaded/failed result. Only a loaded
empty list renders the empty state. Failed loads render `ErrorState` plus a
localized reload link.

Watchlist price formatting maps `CN -> CNY`, `HK -> HKD`, and `US -> USD` with
`Intl.NumberFormat`; unknown markets show a locale-formatted number without a
guessed currency. Detail price/change metrics use nullable formatting, and
movement color is applied only when the value exists.

## Market-aware daily-bar fallback

The browser carries canonical `symbol + market` from search to detail and from
detail to the assistant. Provider-specific symbols remain an adapter concern;
the fallback decision never guesses a market from an ambiguous code.

`get_bars_payload` keeps its database-first behavior. When the database has no
matching rows and `market=CN`, it delegates one complete request range to the
existing `DailyBarFetchCoordinator`. The ordered sources are:

```text
requested provider
  -> configured AkShare stock_zh_a_hist
  -> configured AkShare stock_zh_a_daily
  -> configured Tushare pro.daily
```

Duplicate providers/sources are removed, each source is attempted at most
once, and mock is never added. The coordinator validates symbol, date range,
finite values, OHLC consistency, duplicates, and volume before selecting one
whole source. Bars from different adjustment policies are never mixed.

The additive result contract is:

```text
requested_provider, effective_provider, provider, source, adjustment,
fallback_used, source_attempts, status, no_data_reason
```

Attempts expose provider/source/status/row count and sanitized exception type
only. A configured alternate success returns `status=ok`. All-empty sources
return `no_data`; failed/invalid sources with no usable result return a
degraded empty payload rather than fabricated bars.

Latest and indicator payloads inherit the same provenance from bars. Detail
uses `bars.effective_provider` as the assistant provider and shows a localized
switch notice when requested and effective providers differ. Intraday and
market-depth capabilities remain independent; this slice does not claim that
daily fallback makes those sections available.

HK, US, missing-market, provider-specific index symbols, and mock requests keep
their existing single-provider behavior. Yahoo ticker normalization is made
market-aware for canonical CN/HK symbols, but no CN adapter is called outside
an exact CN request.

## Compatibility and rollback

- All new request fields are optional; ordinary assistant calls remain valid.
- Daily fallback metadata is additive; old clients can ignore it.
- Omitting `market` preserves the previous single-provider behavior.
- No schema migration or new snapshot endpoint is required.
- POST/DELETE watchlist behavior remains compatible.
- Rollback is file-local: remove the optional snapshot field, membership GET,
  toggle rendering, and presentation helpers. Stored data is unchanged.
- The fallback slice rolls back by removing the optional market forwarding and
  coordinator call; no stored rows or settings require migration.
