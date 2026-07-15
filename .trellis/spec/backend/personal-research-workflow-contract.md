# Personal Research Identity and Financial State Contract

## Scenario: Exact Instrument Watch State and Trustworthy Presentation

### 1. Scope / Trigger

- Trigger: a personal user moves from search, the daily shortlist, instruments,
  or watchlist into one exact instrument detail page and reviews or changes its
  watch state.
- Scope: instrument links and detail query parameters, exact instrument
  identity resolution, read-only watchlist membership, detail watch/unwatch,
  watchlist load-state and currency presentation, and missing detail values.
- Non-goals: homepage changes, report generation, alert evaluation, portfolio
  or trading features, watchlist maintenance panels, or automatic enrichment.

### 2. Signatures

- Service read:
  `get_watchlist_item_membership(symbol: str, market: str, session: Session) -> dict[str, object]`.
- FastAPI read: `GET /watchlist/items?symbol=<symbol>&market=<market>`.
- FastAPI write input: `WatchlistItemInput.alert_rules: dict[str, Any] | None`;
  omission means preserve an existing row's rules, while an explicit `{}` means
  clear them.
- Web identity read:
  `fetchInstrumentDetailContext(symbol, market?) -> { identity, watchlistMembership }`.
- Detail query values accept `string | string[] | undefined`; the page uses the
  first value and trims it before calling services or rendering snapshot state.
- Watchlist page fetch returns a discriminated `loaded | failed` result.

### 3. Contracts

- Watchlist identity is the normalized pair `(symbol, market)`. Known source
  links preserve `market`; detail lookup may use a bounded exact fallback but
  never guesses when the same symbol resolves to multiple markets.
- Membership reads query the existing default watchlist and exact item
  directly. They do not create/seed the default list, call enriched watchlist
  serialization, fetch prices, evaluate alerts, write alert history, or commit.
- No exact identity or a failed membership read produces
  `watchlistMembership="unavailable"`; the detail toggle is disabled.
- The detail client uses the same-origin `/api/watchlist/items` POST/DELETE
  proxy, keeps the current URL, shows pending/success/error feedback, and calls
  `router.refresh()` after success. It exposes no report or maintenance action.
- Re-adding a soft-removed row without `alert_rules` preserves its existing
  alert rules. Explicit rule payloads continue to replace them.
- Watchlist transport/HTTP/JSON failure renders `ErrorState` plus a localized
  reload action. Only a successful payload with zero items renders the existing
  empty state and zero-item metrics.
- Watchlist numeric prices map `CN -> CNY`, `HK -> HKD`, and `US -> USD`.
  Unknown markets use locale number formatting without a guessed currency.
- Missing detail latest price, change, or percent change renders the localized
  unavailable label and no movement color. Never synthesize `0.00`, `+0.00`, or
  `+0.00%` for absent values.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Blank membership symbol or market | HTTP 400; no database mutation |
| Default watchlist absent | HTTP 200 `not_watched`; no list/item rows created |
| Exact active item exists | HTTP 200 `watched` with the exact serialized item |
| Same symbol, different market | `not_watched`; do not cross-match |
| Identity lookup is ambiguous or fails | Detail toggle disabled as `unavailable` |
| Membership read fails | Exact identity may render, but mutation remains disabled |
| Re-add omits `alert_rules` | Reactivate while preserving stored rules |
| Re-add sends explicit `{}` | Reactivate and clear stored rules |
| Watchlist request fails | Error state and reload action; no empty KPI projection |
| Watchlist request succeeds with `items=[]` | Genuine empty state |
| Price/change value is absent | Localized unavailable value; no synthetic zero |

### 5. Good / Base / Bad Cases

- Good: a `0700` HK link reaches `?market=HK`, resolves one exact instrument,
  reads membership without writes, and toggles the same row without navigation.
- Good: an item with alert rules is removed and later re-added from detail; the
  rules remain intact because the compact toggle omits `alert_rules`.
- Base: no default watchlist exists; the detail control shows Add while the
  membership read leaves the database untouched.
- Base: a successful empty list shows the existing personal empty state.
- Bad: a GET membership check seeds defaults, enriches prices, evaluates alerts,
  commits alert history, or treats a provider failure as an empty watchlist.
- Bad: a CN value uses USD, an unknown market guesses CNY, or missing detail data
  is displayed as a real zero.

### 6. Tests Required

- Service tests assert absent-list reads create no rows, exact market matching,
  soft-removed behavior, zero alert-history writes, and rule preservation on
  omitted re-add payloads.
- API tests assert exact GET payloads, blank-input HTTP 400 behavior, and no
  mutation from membership reads.
- Next proxy tests assert method, exact forwarded query/body, no-store behavior,
  upstream status, content type, and payload propagation.
- Component/page tests assert toggle pending/success/error/unavailable states,
  same-page refresh, repeated-query normalization, failed-versus-empty watchlist
  branches, CN/HK/US currencies, and unavailable detail values.
- Browser acceptance checks desktop and `375x812` layouts for horizontal
  overflow and verifies exact search/detail navigation when browser policy
  permits interaction.

### 7. Wrong vs Correct

#### Wrong

```python
payload = get_default_watchlist_payload(session=session)
watched = any(item["symbol"] == symbol for item in payload["items"])
```

This read may seed defaults, enrich prices, evaluate alerts, and ignores market
identity.

#### Correct

```python
membership = get_watchlist_item_membership(
    symbol=symbol,
    market=market,
    session=session,
)
```

The direct exact query is side-effect free and keeps unavailable/empty/watched
states distinct.
