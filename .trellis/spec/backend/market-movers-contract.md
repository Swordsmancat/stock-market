# Stored Market Movers Contract

## Scenario: Read-Only A-Share Gainers And Losers

### 1. Scope / Trigger

- Trigger: a personal user opens the market-movers page to review the latest
  stored A-share daily changes.
- Scope: `packages/services/market_movers.py`,
  `apps/api/routers/market_movers.py`, `/[locale]/market-movers`, navigation,
  localization, and focused service/API/page tests.
- Non-goals: live quotes, provider calls, ingestion, refresh actions, fund-flow
  ranking, AI selection, historical ranking persistence, or trading actions.

### 2. Signatures

- Service:
  `get_market_movers_payload(*, session, market="CN", direction="gainers", exchange="all", limit=20) -> dict[str, object]`.
- API:
  `GET /market-movers?market=CN&direction=gainers|losers&exchange=all|SSE|SZSE|BSE&limit=10|20|50`.
- Page: `GET /[locale]/market-movers` with the same direction, exchange, and
  limit URL state.

### 3. Contracts

- Reads active CN stock `DailyBar` rows only. Page rendering and API reads must
  not call a provider, enqueue work, mutate storage, or use fixture fallback.
- Compare the latest two distinct stored market dates. Every result requires an
  exact bar on both dates; a stale per-symbol date is never substituted.
- Choose one deterministic dominant `provider + adjustment` cohort using
  instruments paired on both dates. Break equal cohort sizes lexically and
  require the same cohort for both bars of every result.
- Exclude missing, non-positive, or non-finite previous closes and any row whose
  required numeric values cannot be serialized safely. A non-finite optional
  amount becomes null; it is never replaced by a fabricated zero.
- Rank gainers by percentage change descending, change descending, then symbol;
  rank losers by percentage change ascending, change ascending, then symbol.
- The payload exposes both dates, cohort provenance, source distribution,
  comparable/eligible/omitted counts, bounded items, `data_mode="stored"`, and
  `research_signal_only=true`.
- No coherent pair returns HTTP 200 with `status="no_data"`; database failures
  remain failures and the page renders a distinct localized error state.
- The desktop sidebar owns the route. The existing five-item mobile navigation
  remains unchanged. Narrow tables retain rank, identity, close, and percent
  change without page-level horizontal overflow.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Unsupported market/direction/exchange/limit | HTTP 422; no service work |
| Fewer than two stored dates | `no_data`, null dates, empty items |
| No cohort paired on both dates | `no_data` with selected dates |
| Instrument lacks either exact date or cohort | Omit and count it |
| Previous close is missing, non-positive, or non-finite | Omit and count it |
| Required volume is non-finite | Omit and count it |
| Optional amount is non-finite | Return null amount |
| Database request fails | Preserve failure; page shows localized error |

### 5. Good / Base / Bad Cases

- Good: the latest two dates contain 5,518 paired `akshare/qfq` stocks and the
  page returns a stable top 20 with exact instrument-detail links.
- Base: the cohort is valid but has no negative movers; the losers view returns
  explicit `no_data` with provenance and counts.
- Bad: mix providers across dates, substitute each symbol's last available
  close, fetch Eastmoney on page load, or serialize Decimal NaN/Infinity.

### 6. Tests Required

- Service tests cover exact date pairing, dominant coherent cohort, lexical
  tie behavior, exchange filtering, stable gain/loss ordering, invalid numeric
  omission, source/count metadata, and no-data branches.
- API tests cover all query enums, exact allowed limits, delegation, and the
  injected database session.
- Frontend tests cover decoding, URL filters, stored provenance, exact CN
  detail links, empty/error distinction, localization, desktop-only navigation,
  and unchanged mobile navigation.
- Browser acceptance covers desktop gainers/losers switching and `390x844`
  essential-column rendering with no page-level horizontal overflow.

### 7. Wrong vs Correct

#### Wrong

```python
latest = bars_by_symbol[symbol][-1]
previous = bars_by_symbol[symbol][-2]
return float(latest.amount)
```

This mixes dates and may emit a non-finite JSON number.

#### Correct

```python
current, previous = exact_date_pair(symbol, trade_date, previous_trade_date, cohort)
amount = _finite_decimal(current.amount)
payload_amount = float(amount) if amount is not None else None
```

The comparison boundary and numeric serialization are explicit and auditable.
