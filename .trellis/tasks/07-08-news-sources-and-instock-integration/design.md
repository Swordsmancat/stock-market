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

## Follow-Up Slice: InStock-Inspired Strategy Screening API

The next non-trading InStock slice ports selected screening rule shapes into a
pure Python service and thin API:

- add `packages/services/strategy_screening.py` with deterministic latest-window
  screening over normalized OHLCV bars;
- support `volume_price_breakout`, `turtle_breakout`, and `ma_trend_up`, inspired
  by InStock's `enter`, `turtle_trade`, and `keep_increasing` strategy modules;
- add `GET /strategies/screen` for multi-symbol screening through the existing
  market-data provider boundary;
- return rule metadata, source/provider metadata, per-symbol diagnostics,
  `research_signal_only=true`, and a non-advice disclaimer;
- do not persist matches or treat them as assistant-citable evidence until a
  future reviewed storage/citation path exists;
- avoid InStock runtime imports, TA-Lib, scheduler replacement, database schema
  copying, strategy execution, and broker order intents.

## Follow-Up Slice: InStock-Inspired Strategy Evaluation API

The companion evaluation slice scans historical bars for the same strategy rule
matches and reports bounded outcome diagnostics:

- add `evaluate_instock_strategy_signals(...)` to reuse the strategy screening
  rule implementation instead of duplicating rule logic;
- add `GET /strategies/evaluate` for one symbol, start/end date, strategy filter,
  forward windows, optional benchmark symbol, and provider;
- return snapshots, per-window sample size, hit rate, average/median forward
  return, max drawdown after signal, benchmark-relative return when available,
  provider metadata, diagnostics, `research_signal_only=true`, and the existing
  non-advice disclaimer;
- keep this as historical diagnostics only, not a production backtest: no fill
  prices, fees, slippage, portfolio simulation, parameter optimization, order
  lifecycle, persistence, or scheduler;
- map provider failures to HTTP 502 for the single-symbol evaluation endpoint
  while preserving partial-success diagnostics for multi-symbol `/strategies/screen`.

## Follow-Up Slice: Social Sentiment Evidence Boundary

The news/search provider MVP already normalizes provider result families such as
SerpAPI `social_results`. The social sentiment boundary keeps those candidates
out of verified-news storage until a separate model exists:

- mark every live search candidate as non-citable collection input through an
  `evidence_boundary` payload;
- classify `social` and `public_opinion` result kinds as `low_social_signal`;
- keep low-strength social candidates visible in search responses but defer them
  from `NewsArticle` / `SentimentSignal` persistence during `search-ingest`;
- return `social_candidate_count` and `social_candidates_deferred` from ingest;
- add a source-readiness row for future social sentiment/public-opinion storage,
  explicitly not citable today;
- continue to require official APIs, licensed provider results, or user-reviewed
  notes for any future social sentiment adapter.

## Follow-Up Slice: InStock-Inspired Chip Distribution

The next non-trading InStock slice ports the CYQ/chip-distribution capability
shape into the existing stored technical-indicator boundary:

- add `packages/analytics/chip_distribution.py` as pure Python/pandas over local
  daily OHLCV bars;
- store results as a `TechnicalIndicator` with `indicator_code="chip_distribution"`;
- return cost-range summaries, benefit ratio, top buckets, and explicit
  limitations under `rule_set="chip_distribution_v1"`;
- mark payloads `research_signal_only=true` and
  `approximation="volume_weighted_without_float_shares"` because the current
  database has volume but not reviewed free-float shares or true turnover;
- avoid InStock runtime imports, JS UI, crawlers, MySQL/Tornado stack, scheduler
  replacement, strategy execution, broker order intents, and any trading advice;
- document `myhhub/stock` Apache-2.0 attribution and the no-trading/no-overclaim
  boundary.

## Follow-Up Slice: Expanded Technical Indicators

The next non-trading InStock slice broadens the stored daily indicator set with
pure formulas from the broader InStock capability shape:

- add no-dependency formulas for `cci`, `obv`, `roc`, `bias`, `mfi`, and
  `william_r` under `packages/analytics/indicators.py`;
- store latest values as ordinary `TechnicalIndicator` rows during
  `/indicators/recalculate`;
- omit formula values when the available OHLCV window is insufficient instead
  of fabricating neutral values;
- preserve existing numeric indicator payloads plus `candlestick_patterns` and
  `chip_distribution`;
- avoid TA-Lib, InStock runtime imports, scheduler replacement, strategy
  execution, broker order intents, and any trading advice.

## Follow-Up Slice: Composite Stock Selection

The next non-trading InStock slice ports the "comprehensive stock selection"
capability shape into a local evidence screener:

- add `packages/services/stock_selection.py` to screen stored active instruments
  against local fundamental and technical criteria;
- add `GET /stock-selection/screen` as a thin FastAPI route;
- use only stored `Instrument`, latest `DailyBar`, latest `TechnicalIndicator`,
  and latest `FundamentalSnapshot` rows in the MVP;
- support first criteria `max_pe_ratio`, `min_revenue_growth`, `min_net_margin`,
  `min_rsi`, `max_rsi`, and `require_price_above_ma`;
- return matched rule details, diagnostics, stored evidence citation IDs,
  `research_signal_only=true`, and a non-advice disclaimer;
- do not fetch live providers, persist selection results, import InStock's
  MySQL/Tornado/web/trading runtime, generate order intents, or emit buy/sell
  advice.

## Follow-Up Slice: Composite Stock Selection Technical Evidence Criteria

The next incremental stock-selection slice broadens the local screener without
changing its evidence boundary:

- add criteria for stored candlestick pattern codes, MFI, William %R, and
  chip-distribution benefit ratio;
- read only the latest stored `TechnicalIndicator` payloads already produced by
  the previous non-trading InStock slices;
- expose query parameters through the existing `GET /stock-selection/screen`
  route instead of creating a second screener;
- keep missing nested payloads diagnostic-only through
  `SELECTION_RULE_NOT_MATCHED` and `missing_value` or `missing_pattern_codes`;
- preserve stored-row evidence citations, `research_signal_only=true`, and the
  non-advice disclaimer;
- avoid live provider scans, persistence of selection results, strategy
  execution, order intents, and buy/sell/hold language.

## Follow-Up Slice: Watchlist-Scoped Composite Stock Selection

The next watchlist/follow slice adapts InStock's watchlist workflow into this
project's local screener:

- add a `watchlist_only` candidate-scope flag to `GET /stock-selection/screen`;
- read active default-watchlist `symbol`/`market` pairs without invoking
  provider-backed watchlist enrichment;
- intersect watchlist scope with optional `symbols` and `market` filters;
- return a `candidate_scope` object so callers can audit the scanned universe;
- keep selection evidence limited to stored daily bars, technical indicators,
  and fundamentals;
- avoid provider scans, watchlist mutation, persisted selection results,
  strategy execution, order intents, and buy/sell/hold language.
