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

## Compatibility and rollback

- All new request fields are optional; ordinary assistant calls remain valid.
- No schema migration or new snapshot endpoint is required.
- POST/DELETE watchlist behavior remains compatible.
- Rollback is file-local: remove the optional snapshot field, membership GET,
  toggle rendering, and presentation helpers. Stored data is unchanged.
