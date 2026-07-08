# News Source Configuration And Adapter MVP - Design

## Scope

This design initially covered the first implementation slice:

- news/search provider registry;
- platform settings for provider enablement, priority, and secrets;
- 1-2 provider adapters;
- normalized news candidate contract;
- ingestion into the existing stored-news path where safe;
- degraded/fallback diagnostics.

Automatic trading remains outside this implementation work. After the news/search
provider MVP was committed, the next non-trading InStock slice adds stored
candlestick-pattern research signals.

## Architecture And Boundaries

- Backend owns provider execution and API-key use.
- Frontend settings may show provider rows and configured flags, but must never receive raw provider API keys.
- The first adapter layer lives under `packages/services/` or `packages/providers/` following existing provider/service patterns.
- The API layer should stay thin: parse request, call service, return normalized payload.
- Existing `NewsArticle` and `SentimentSignal` remain the initial persistence targets.
- A schema migration is allowed only if implementation needs metadata that cannot be safely represented by existing columns.

## Provider Registry

Represent every requested provider, even if not implemented in the first slice:

- `anspire`
- `serpapi_baidu`
- `tavily`
- `bocha`
- `brave`
- `minimax`
- `yfinance`
- `akshare`
- `tushare`
- `mock`

Each provider should expose:

- id and display name;
- enabled flag;
- configured flag;
- priority;
- supported regions/markets;
- supported result kinds;
- credential field names;
- default timeout;
- default max results;
- implementation status: `implemented`, `configured_only`, `needs_contract`, `mock`, or `existing`;
- readiness note and citation/storage caveat.

## Settings Contract

Use the existing `platform_settings.json` pattern.

Suggested stored fields:

```json
{
  "news_search_provider_order": ["anspire", "serpapi_baidu", "yfinance", "mock"],
  "news_search_enabled_providers": ["anspire", "serpapi_baidu"],
  "news_search_provider_keys": {
    "anspire": "<secret>",
    "serpapi_baidu": "<secret>"
  },
  "news_search_max_results": 10,
  "news_search_timeout_seconds": 8
}
```

Public settings should expose only:

- provider order;
- enabled providers;
- configured flags;
- capabilities/readiness notes;
- max results and timeout.

Do not expose `news_search_provider_keys`.

## Normalized Result Contract

Provider adapters should return candidate items:

```py
{
    "symbol": "AAPL",
    "query": "AAPL financial news",
    "title": "...",
    "url": "https://...",
    "source": "publisher or provider",
    "summary": "snippet or summary",
    "published_at": "ISO datetime or None",
    "retrieved_at": "ISO datetime",
    "provider": "anspire",
    "language": "zh",
    "region": "CN",
    "score": 0.81,
    "result_kind": "news",
    "diagnostics": []
}
```

Rules:

- no fabricated publication dates;
- no fabricated publisher;
- no raw API key in diagnostics;
- keep provider raw payload out of user-visible response unless sanitized and small.

## Fallback Flow

For a symbol/query:

1. Resolve enabled providers in configured priority order.
2. For each provider:
   - skip disabled;
   - skip missing credential if credential is required;
   - execute with timeout;
   - normalize results;
   - record diagnostics for skip, empty, invalid, timeout, or provider error.
3. Deduplicate normalized candidates by URL and title.
4. Persist selected candidate articles if the endpoint/action is an ingest operation.
5. If no live provider returns usable results, fall back to existing stored database news.
6. Return diagnostics alongside article counts and provider statuses.

## First Adapters

Selected first adapters:

- Anspire AI Search: best domain fit for A-share/US/HK financial news and public opinion.
- SerpAPI Baidu: Chinese Baidu result coverage and news/social result families for Chinese-market discovery.

Deferred adapters:

- Tavily remains a good general-search follow-up.
- Brave if US/global privacy-oriented web/news coverage matters more.
- Bocha and MiniMax should remain registry-only until their stable in-app API contracts are confirmed.

## Frontend Settings UI

If implemented in the first slice, use the existing Settings page style:

- a compact card/section near current provider settings;
- provider rows/cards with label, status, configured flag, enabled checkbox, priority/order text input or simple textarea;
- secret inputs that preserve existing values when blank;
- localized help text explaining citation boundaries and quota/network behavior.

Follow existing Server Action patterns for settings mutations.

## Tests

- provider registry capability tests;
- settings normalization and secret-preservation tests;
- adapter normalization tests with mocked HTTP responses;
- fallback diagnostics tests for disabled, missing key, timeout, provider error, empty response, and database fallback;
- news ingestion dedupe tests;
- API route tests for ingest/search if an API surface is added;
- frontend settings tests if settings UI changes.

## Rollback

The provider registry can remain harmless if adapters are disabled. Rollback can remove:

- new provider key fields from settings UI/public payloads;
- new API routes;
- new adapters.

Stored unknown fields in `platform_settings.json` should be ignored by readers after rollback.

## Follow-Up Slice: InStock-Inspired Candlestick Patterns

The first non-trading InStock slice ports the capability shape, not the runtime
stack:

- add pure Python/pandas K-line pattern rules under `packages/analytics/`;
- store results as a `TechnicalIndicator` with `indicator_code="candlestick_patterns"`;
- keep output under the existing stored technical-indicator citation boundary;
- make the payload explicitly `research_signal_only`;
- avoid TA-Lib, MySQL, Tornado, proxy/cookie crawling, scheduler replacement, and trading modules;
- document `myhhub/stock` Apache-2.0 attribution and the no-trading boundary.

The first supported pattern codes are `bullish_engulfing`, `bearish_engulfing`,
`hammer`, `shooting_star`, and `doji`.

## Follow-Up Slice: Recommendation Signal Evaluation API

The repository already has a deterministic service-level historical signal
evaluator for `breakout`, `volume_anomaly`, `oversold_rebound`, and
`strong_momentum`. The follow-up API slice exposes it without changing the
storage model:

- add `GET /recommendations/evaluate` as a thin router wrapper;
- fetch daily bars through the existing market-data provider boundary;
- support comma-separated signal types and forward windows;
- optionally fetch benchmark bars for benchmark-relative return;
- return sample size, snapshots, per-window metrics, diagnostics, provider
  metadata, and `research_signal_only`;
- keep `/recommendations` as unbacktested research candidates, not actions;
- avoid persistence, scheduler, transaction-cost modeling, portfolio simulation,
  or order intent generation in this slice.
