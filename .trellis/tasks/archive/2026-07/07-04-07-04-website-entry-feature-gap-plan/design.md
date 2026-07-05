# Website Entry Stability and Feature Gap Plan Design

## Scope

This task is a stabilization and planning task. It verifies the local website entry point, fixes immediate entry blockers, records the current Phase 2 / Phase 3 capability status, and translates professional-platform gaps into prioritized Trellis-ready follow-ups.

## Entry Stability Design

### Reported blocking error

The reported React Server Component boundary error was caused by passing a function prop from the homepage Server Component into the `SmartRecommendations` Client Component:

```tsx
getInstrumentHref={(symbol) => `/instruments/${encodeURIComponent(symbol)}`}
```

Next.js does not allow arbitrary functions to cross from Server Components into Client Components. The minimal safe fix is to stop passing the function and rely on the Client Component's existing default link generation:

```tsx
const instrumentHref = getInstrumentHref?.(rec.symbol) ?? `/instruments/${encodeURIComponent(rec.symbol)}`;
```

This preserves the current user-visible link behavior without changing the component API for tests or future client-only callers.

### Reported script warning

The `next-themes` warning appears around `ThemeProvider` and should be classified by observed behavior:

- If `/zh` renders and can be interacted with, classify it as non-blocking for this task.
- If it causes an error overlay or hydration failure that prevents interaction, split a focused theme-provider follow-up.
- Do not refactor theme infrastructure in this task unless it blocks page entry.

## Feature Status Reconciliation Design

Use the current manuals and runbooks as the source of user-facing truth:

- `README.md`
- `docs/manual/user-guide.md`
- `docs/runbooks/developer-maintenance.md`

The reconciliation should distinguish:

- Complete features: shipped and covered by tests.
- Provider-backed MVP features: real provider path exists for at least one supported provider, with explicit degraded/no-data fallbacks.
- Provider-boundary MVP features: explicit provider contract and UI behavior exist, but built-in production providers are still degraded until verified provider integration.
- Future enhancements: professional-platform gaps that need separate Trellis tasks.

## Professional Benchmark Dimensions

Compare against common capabilities in:

- TradingView-style charting platforms.
- Bloomberg/Koyfin/AlphaSense-style research platforms.
- Broker terminals with Level-2, order flow, and execution workflows.
- CN retail-market terminals with sector rotation, market breadth, fund flow, and local-market discovery features.

## Follow-up Task Design

Only create follow-up Trellis tasks for work that is independently verifiable and larger than a small documentation edit. Good candidates include:

- Theme-provider hydration/script warning cleanup if still reproducible.
- Production Level-2 / recent-trade / fund-flow provider validation.
- Intraday provider cache and market-session governance.
- Hot-sector production provider verification and breadth/contribution metrics.
- AI assistant retrieval and multi-turn context enhancements.

## Risk Controls

- Do not mark provider-dependent financial features as complete unless a verified provider path and tests exist.
- Do not treat a successful UI render as proof that market data is real.
- Do not collapse section-level `degraded` states into top-level success.
- Do not overwrite unrelated dirty files while reconciling status.
