# InStock-Inspired Composite Stock Selection Contract

## Scenario: Research-Only Local Composite Stock Selection

### 1. Scope / Trigger

- Trigger: `GET /stock-selection/screen` screens stored active instruments
  against local fundamental, technical, market-data, and news criteria.
- Scope: service logic in `packages/services/stock_selection.py`, thin FastAPI
  route in `apps/api/routers/stock_selection.py`, app router registration in
  `apps/api/main.py`, and focused service/API tests.
- Non-goals: live provider scans, remote scraping, InStock MySQL/Tornado runtime,
  strategy execution, portfolio construction, order intents, broker execution,
  or automatic trading.

### 2. Signatures

- API:
  `GET /stock-selection/screen`
- Optional query fields:
  - `symbols`: comma-separated symbols. If omitted, stored active instruments
    are scanned.
  - `market`: market code such as `US`, `CN`, or `HK`.
  - `asset_type`: stored instrument asset type such as `stock` or `etf`.
  - `max_pe_ratio`
  - `min_revenue_growth`
  - `min_net_margin`
  - `min_rsi`
  - `max_rsi`
  - `require_price_above_ma`
  - `required_pattern_codes`: comma-separated candlestick pattern codes stored
    under `candlestick_patterns.patterns[]`.
  - `min_mfi`
  - `max_mfi`
  - `min_william_r`
  - `max_william_r`
  - `min_chip_benefit_ratio`
  - `max_chip_benefit_ratio`
  - `min_latest_volume`
  - `min_traded_amount`
  - `min_news_article_count`
  - `required_news_sentiment`: latest stored sentiment label, such as
    `positive`, `neutral`, or `negative`.
  - `min_news_sentiment_confidence`
  - `watchlist_only`: when `true`, candidate instruments are limited to active
    entries from the default watchlist before criteria evaluation.
  - `limit`, bounded to `1..100`.
- Service entry:
  `screen_local_stock_selection(..., session, symbols=None, market=None, ...)`
- Rule set: `instock_composite_selection_v1`.

### 3. Contracts

- The first slice reads local stored evidence only:
  - `Instrument` scope;
  - latest stored `DailyBar`;
  - latest stored `TechnicalIndicator` values;
  - latest stored `FundamentalSnapshot`;
  - stored `NewsArticle` plus `SentimentSignal` rows when news/sentiment
    criteria are requested.
- Technical criteria may inspect stored scalar indicators (`rsi`, `mfi`,
  `william_r`) and reviewed nested indicator payloads
  (`candlestick_patterns.patterns[]`, `chip_distribution.benefit_ratio`).
- Market-data criteria may inspect the latest stored daily bar only.
  `min_latest_volume` reads `DailyBar.volume`. `min_traded_amount` reads
  `DailyBar.amount` when present and otherwise uses the local `close * volume`
  estimate from the same stored daily bar; it must not call a live provider to
  repair missing values.
- `market`, `asset_type`, and `watchlist_only` are candidate-scope controls,
  not selection criteria and not citable evidence. `watchlist_only` must read
  only active default-watchlist `symbol`/`market` pairs without triggering
  provider enrichment.
- News/sentiment criteria must read only stored local news rows. They must not
  call live search providers, news ingestion, social-candidate persistence, or
  provider fallback while screening.
- At least one selection criterion is required. Scope-only requests, such as
  only `market`, `asset_type`, or `watchlist_only`, return HTTP 400 at the API
  boundary and an `invalid_request` service payload.
- Missing local evidence must produce diagnostics and no fabricated match.
- Matching items may expose evidence citation IDs for the stored rows used:
  `bars_1d:*`, `technical_indicators:*`, `fundamental_metrics:*`, and
  `news:*` when news criteria are active and stored news exists.
- Payloads include `candidate_scope` with normalized `symbols`, optional
  `market`, optional `asset_type`, and `watchlist_only` so callers can audit the
  scanned universe.
- The stock-selection result itself is a research analysis payload, not a stored
  assistant citation row and not a trading signal.
- Payloads must include `research_signal_only=true` and the disclaimer:
  `Composite stock selection is a research aid only and is not investment advice.`
- Results must not emit buy/sell/hold actions, target prices, position sizes,
  order intents, portfolio weights, broker routing, or execution instructions.

### 4. Validation & Error Matrix

- No criteria -> HTTP 400 / `NO_SELECTION_CRITERIA`.
- Symbol duplicates -> normalize and screen once.
- `asset_type` filter -> normalize to lowercase and apply to stored
  `Instrument.asset_type` before criteria evaluation.
- Fundamental criterion requested but no `FundamentalSnapshot` -> diagnostic
  `MISSING_FUNDAMENTALS`, no match.
- Technical criterion requested but required indicator is missing -> diagnostic
  with `SELECTION_RULE_NOT_MATCHED` and `missing_value`, no match.
- Required candlestick pattern code not present -> diagnostic
  `SELECTION_RULE_NOT_MATCHED` with `missing_pattern_codes`, no match.
- Missing nested chip-distribution payload or `benefit_ratio` -> diagnostic
  `SELECTION_RULE_NOT_MATCHED` with `missing_value`, no match.
- News article-count criterion requested but no stored news -> diagnostic
  `SELECTION_RULE_NOT_MATCHED` with actual count `0`, no match.
- Required latest sentiment missing or different -> diagnostic
  `SELECTION_RULE_NOT_MATCHED` with `missing_value` or `not_matched`, no match.
- Minimum latest sentiment confidence missing or too low -> diagnostic
  `SELECTION_RULE_NOT_MATCHED`, no match.
- Latest volume or traded amount below requested threshold -> diagnostic
  `SELECTION_RULE_NOT_MATCHED`, no match.
- `min_traded_amount` requested but stored `amount` and local `close * volume`
  estimate cannot be computed -> diagnostic `SELECTION_RULE_NOT_MATCHED` with
  `missing_value`, no match.
- No stored daily bar -> diagnostic `MISSING_DAILY_BAR`, no match.
- A criterion fails -> diagnostic `SELECTION_RULE_NOT_MATCHED`, no match.
- `watchlist_only=true` with an empty active watchlist -> no candidates and an
  empty successful result unless no criteria were supplied.
- Matching item -> include stored evidence citations and matched rule details.

### 5. Good/Base/Bad Cases

- Good: `/stock-selection/screen?symbols=AAPL&max_pe_ratio=30&min_rsi=40&max_rsi=70`
  returns AAPL when stored fundamentals and technical indicators satisfy all
  criteria.
- Good: `/stock-selection/screen?symbols=AAPL&required_pattern_codes=hammer&min_mfi=50&max_william_r=-10&min_chip_benefit_ratio=0.6`
  returns AAPL only when those stored technical-indicator payloads are present
  and satisfy the thresholds.
- Good: `/stock-selection/screen?symbols=AAPL&min_news_article_count=1&required_news_sentiment=positive&min_news_sentiment_confidence=0.7`
  returns AAPL only when stored `NewsArticle` / `SentimentSignal` evidence
  satisfies those local criteria.
- Good: `/stock-selection/screen?symbols=AAPL&min_latest_volume=1000000&min_traded_amount=200000000`
  returns AAPL only when the latest stored daily bar satisfies those local
  market-data thresholds.
- Good: a symbol without fundamentals is skipped with diagnostics instead of a
  fake valuation metric.
- Good: a symbol without stored news is skipped with diagnostics instead of
  fetching live news inside the screener.
- Base: scanning by `market=US` without `symbols` uses stored active instruments
  only and does not fetch provider data.
- Base: scanning by `asset_type=etf` narrows the local candidate universe to
  stored ETF instruments before criteria evaluation.
- Base: `watchlist_only=true` narrows the scan to stored active watchlist
  entries but still requires ordinary stored market/fundamental/technical rows
  before a symbol can match.
- Bad: the endpoint calls a live provider for every listed symbol.
- Bad: the endpoint calls `/news/search`, `/news/search-ingest`, yfinance news,
  or another live provider to satisfy news criteria.
- Bad: watchlist enrichment runs provider-backed price lookups before candidate
  scoping.
- Bad: a selected symbol is described as a buy recommendation, target allocation,
  or executable order.
- Bad: InStock's web/database/strategy/trading runtime is imported.

### 6. Tests Required

- Service tests assert matching across fundamental, technical, market-data, and
  news criteria, duplicate symbol normalization, evidence citations, failed
  criteria diagnostics, missing fundamentals diagnostics, stored news/sentiment
  criteria, missing news diagnostics, watchlist-only candidate scoping, and
  asset-type candidate scoping, and no-criteria validation.
- API tests assert route registration, query parsing, HTTP 400 for no criteria,
  market-data query fields, news/sentiment query fields,
  `candidate_scope.asset_type`, `candidate_scope.watchlist_only`, and
  `research_signal_only=true`.
- Focused validation should include:
  `pytest tests/services/test_stock_selection.py tests/api/test_stock_selection_api.py`,
  ruff on touched stock-selection files, full backend pytest, and
  `git diff --check`.

## Full-Universe and Discovery Addendum

- Candidate loading must not apply a pre-evaluation cap. The service bulk-loads
  latest bars, indicators, fundamentals, and conditional news; only final
  ranked items are limited.
- Responses expose `coverage` and `diagnostics_summary`. Scans above 100
  candidates aggregate diagnostics to avoid multi-thousand-row payloads;
  explicit/small scans preserve detailed diagnostics for compatibility.
- `GET /stock-selection/profiles` exposes the three named transparent profiles.
- `POST /stock-selection/discover` resolves visible overrides, runs the same
  deterministic screener, bounds the shortlist to 20, and optionally generates
  an explanation. AI cannot add/remove/reorder candidates.
- Unknown inline citation IDs or backtick symbols in generated text produce
  deterministic fallback diagnostics without changing shortlist data.
- The complete cross-layer matrix, cases, and required tests are in
  [Comprehensive A-share Research Coverage Contract](./a-share-research-coverage-contract.md).
