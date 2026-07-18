# Existing contracts

- `GET /economic-calendar/events` reads stored events but caps responses at 200 rows; July 2026 reaches that cap and is unsuitable for complete month counts.
- A read-only production count found 1,133 distinct July 2026 events, so the dedicated endpoint uses a 2,500-row cap and explicit truncation metadata.
- Economic calendar records are timestamped in UTC and already expose Shanghai-local ISO timestamps.
- The existing market-research economic calendar is a table-oriented component and does not provide month/day navigation.
- Official disclosure reads are currently symbol-specific, so month-wide company events need an intentionally bounded watchlist-scoped projection.
- Desktop navigation already supports items excluded from the five-item mobile navigation through `mobile: false`.
- The implementation should preserve existing endpoints and add an aggregate read model rather than widening an unrelated endpoint's contract.
