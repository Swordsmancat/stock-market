# InStock Analysis Integration

This project uses `myhhub/stock` as a staged analysis reference, not as a drop-in
runtime dependency.

## Current Slice

- Source reviewed: `myhhub/stock` at commit `b6e0ca2268cfbadd02f5ed052159c187b6670231`.
- Upstream license: Apache-2.0.
- Implemented feature: expanded no-dependency daily technical indicators.
- Implemented feature: stored `candlestick_patterns` technical indicator.
- Implemented feature: stored `chip_distribution` technical indicator, inspired
  by InStock's CYQ / chip-distribution capability.
- Implemented feature: research-only local composite stock selection API.
- Implemented feature: composite stock selection over additional stored
  technical evidence: candlestick pattern codes, MFI, William %R, and
  chip-distribution benefit ratio.
- Implemented feature: watchlist-scoped composite stock selection over active
  default-watchlist entries.
- Implemented feature: composite stock selection over stored news/sentiment
  evidence: article count, latest sentiment, and sentiment confidence.
- Implemented feature: composite stock selection over latest stored market-data
  criteria: volume and traded amount.
- Implemented feature: composite stock selection can scope candidates by stored
  asset type such as `stock` or `etf`.
- Implemented feature: single-symbol daily-bar ingestion can persist stock or
  ETF asset type.
- Implemented feature: explicit-symbol batch daily-bar ingestion with partial
  success diagnostics.
- Implemented feature: research-only `GET /strategies/screen` strategy screening API.
- Implemented feature: research-only `GET /strategies/evaluate` strategy evaluation API.
- Implemented feature: provider-backed A-share individual stock fund-flow ranking API.
- Implemented feature: provider-backed industry/concept fund-flow parameters on `/sectors/hot`.
- Implemented feature: provider-backed A-share limit-up pool/reason context API with explicit degraded states when the provider does not expose reason fields.
- Implemented feature: provider-backed A-share Dragon Tiger List context API.
- Implemented feature: provider-backed A-share block-trade context API.
- Implemented feature: persisted market daily evidence for stock fund flow,
  limit-up context, Dragon Tiger List, block trades, and hot sectors.
- Implemented feature: stable stored citation IDs shaped as
  `market_daily_event:<event_type>:<identity>:<trade_date>`.
- Implemented feature: Evidence Center stored-evidence summary and manual
  "refresh today's market evidence" action.
- Rule set: `candlestick_patterns_v1`.
- CYQ rule set: `chip_distribution_v1`.
- Composite stock selection rule set: `instock_composite_selection_v1`.
- First supported pattern codes:
  - `bullish_engulfing`
  - `bearish_engulfing`
  - `hammer`
  - `shooting_star`
  - `doji`
- Strategy screening rule set: `instock_strategy_screening_v1`.
- Expanded indicator codes:
  - `cci`
  - `obv`
  - `roc`
  - `bias`
  - `mfi`
  - `william_r`
- First supported strategy codes:
  - `volume_price_breakout`
  - `turtle_breakout`
  - `ma_trend_up`

The implementation is pure Python/pandas and does not install TA-Lib or import
InStock's indicator runtime, database, scheduler, proxy/cookie, Tornado UI, or
trade modules.

The first CYQ slice uses local daily OHLCV bars only. Because this project does
not yet store free-float shares or true turnover rate, `chip_distribution` is a
volume-normalized research approximation with
`approximation="volume_weighted_without_float_shares"`. Do not describe it as a
provider-grade chip distribution until reviewed float-share and turnover inputs
exist.

## Evidence Boundary

Candlestick patterns are research signals only. They can be included in stored
technical-indicator evidence after `/indicators/recalculate` writes a local
`TechnicalIndicator` row. They are not trading advice and must not generate
buy/sell/hold language, target prices, position sizing, order intents, or broker
execution.

Expanded technical indicators and `chip_distribution` follow the same evidence
boundary. They can be cited only as stored local technical indicators and, for
CYQ, only with its approximation limitation. They must not be used to claim
institution-grade cost concentration, predict support/resistance, or produce
trading actions.

`GET /stock-selection/screen` is a local evidence screener. It reads stored
`Instrument`, `DailyBar`, `TechnicalIndicator`, and `FundamentalSnapshot` rows,
then returns matched criteria and stored evidence citation IDs. The screener
does not fetch live providers, does not persist selection results, and does not
turn a match into a buy/sell/hold recommendation.

Live calculations, InStock feature lists, and source-readiness notes are not AI
citations by themselves. The citation boundary remains stored local evidence,
such as `technical_indicators:{symbol}:{as_of}`.

`GET /strategies/screen` results are research analysis payloads only. They are
not currently stored citation rows and must not be cited by the assistant as
verified evidence unless a future slice adds reviewed persistence with stable
source metadata.

`GET /market-daily-data/fund-flow/stocks`,
`GET /market-daily-data/limit-up-reasons`,
`GET /market-daily-data/dragon-tiger-list`,
`GET /market-daily-data/block-trades`, and provider-backed `GET /sectors/hot`
rows remain live/delayed provider context and are never citations by themselves.
`POST /market-daily-evidence/import` may persist eligible provider-normalized
`live|delayed` rows; only the resulting `MarketDailyEvidenceEvent` records with
`is_citable=true` can be emitted as `market_daily_event:*` citations. Mock,
static, unavailable, empty, and provider-error payloads remain non-citable.
Limit-up rows from AkShare may be degraded pool context when no provider reason
field is available; do not fabricate reason text. Dragon Tiger List and
block-trade rows may omit optional seat, rank, buyer/seller, discount, or amount
fields; keep those values null rather than inferring them.

## Extension Notes

Future InStock-inspired slices should stay independently verifiable:

- add more no-dependency pattern rules only with deterministic fixtures;
- add more technical indicators only when formulas are pure, tested, and do not
  require TA-Lib/runtime imports;
- refine CYQ only after reviewed free-float/turnover data is available;
- add strategy screening as explainable research signals, not orders;
- use `GET /recommendations/evaluate` for current historical signal metrics;
- add deeper backtest statistics only after the input/output contract names return
  horizon, sample size, assumptions, transaction-cost policy, and survivorship limitations;
- keep automatic trading in a separate paper-trading-first safety track.

## Historical Signal Evaluation API

`GET /recommendations/evaluate` exposes the current deterministic recommendation
signal evaluator as a research endpoint:

```text
GET /recommendations/evaluate?symbol=AAPL&start=2026-01-01&end=2026-02-15&signal_types=breakout&forward_windows=1,5&provider=mock
```

It returns sample size, signal snapshots, per-window hit rate, average/median
forward return, max drawdown after signal, benchmark-relative return when a
benchmark is supplied, diagnostics, source metadata, and
`research_signal_only=true`.

This endpoint is not a production strategy tester. It does not model order
fills, slippage, fees, tax, borrow constraints, portfolio constraints, or live
execution.

## Single-Symbol Stock / ETF Daily-Bar Ingestion

`POST /ingestion/symbol-daily-bars` supports targeted daily-bar jobs for stock
or ETF instruments:

```text
POST /ingestion/symbol-daily-bars?symbol=SPY&market=US&asset_type=etf&start=2026-01-01&end=2026-01-02&provider=mock
```

The supported `asset_type` values are `stock` and `etf`; omitting it preserves
the previous stock default. The value is carried through TaskRun input, Celery
dispatch, the worker result payload, serialized snapshot rows, and
`Instrument.asset_type`.

This is a targeted single-symbol ingestion path. It does not crawl an ETF
universe, import InStock schedulers, use proxy/cookie workflows, or produce
research/trading signals.

## Batch Symbol Daily-Bar Ingestion

`POST /ingestion/symbol-daily-bars-batch` supports explicit comma-separated
symbol batches for one market/date range:

```text
POST /ingestion/symbol-daily-bars-batch?symbols=SPY,QQQ&market=US&asset_type=etf&start=2026-01-01&end=2026-01-02&provider=mock
```

The API normalizes and dedupes symbols before writing TaskRun input. The worker
reuses the single-symbol ingestion path for each symbol, so `asset_type`, daily
bar storage, no-data handling, and quality diagnostics stay consistent.

The result payload includes `symbol_count`, `succeeded_count`, `no_data_count`,
`failed_count`, `total_bar_count`, per-symbol `items[]`, and sanitized
`diagnostics[]`. One symbol failure produces a partial batch result instead of
discarding already ingested symbols.

This is still a targeted ingestion path. It does not scan a provider universe,
import InStock schedulers, mutate watchlists, execute strategies, create order
intents, call brokers, or emit buy/sell/hold guidance.

## Provider-Backed Daily Market Context

`GET /market-daily-data/fund-flow/stocks` exposes a non-persistent A-share
individual stock fund-flow ranking:

```text
GET /market-daily-data/fund-flow/stocks?market=CN&window=today&limit=20&provider=akshare
```

The first provider is AkShare's Eastmoney stock fund-flow ranking. Supported
windows are `today`, `3d`, `5d`, and `10d`. The response includes provider,
source, as-of, availability, capability metadata, sanitized diagnostics, and
ranked flow rows. Provider errors, unsupported windows, and empty rows return
structured unavailable/degraded payloads rather than fabricated values.

`GET /sectors/hot` accepts additive provider parameters for the same daily
market context:

```text
GET /sectors/hot?provider=akshare&sector_type=industry&window=today&limit=10
GET /sectors/hot?provider=akshare&sector_type=concept&window=5d&limit=10
```

Omitting `sector_type` and `window` preserves the previous default behavior.

`GET /market-daily-data/limit-up-reasons` exposes A-share limit-up context:

```text
GET /market-daily-data/limit-up-reasons?date=2026-07-09&market=CN&limit=50&provider=akshare
```

AkShare's currently available path may return limit-up pool rows without a
reason/detail field. In that case the payload remains visible but degraded, and
`provider_capabilities.limit_up_reasons.status` is `unavailable`. Do not import
InStock's 10jqka proxy/cookie implementation or scrape a replacement inside
this route without a new reviewed provider contract.

`GET /market-daily-data/dragon-tiger-list` exposes A-share Dragon Tiger List
context:

```text
GET /market-daily-data/dragon-tiger-list?date=2026-07-09&market=CN&limit=50&provider=akshare
```

The first provider path is AkShare's Eastmoney Dragon Tiger List detail
function. The payload includes listing date, close/change, net-buy/buy/sell
amounts, listing reason, and optional seat fields when the provider supplies
them. Rows are research context only and are not stored assistant citations.

`GET /market-daily-data/block-trades` exposes A-share block-trade context:

```text
GET /market-daily-data/block-trades?date=2026-07-09&market=CN&limit=50&provider=akshare
```

The first provider path is AkShare's Eastmoney block-trade daily detail
function for A-share rows. The payload includes trade price, close price,
discount/premium, volume, amount, buyer, seller, and source metadata when
available. Do not treat live block-trade rows as order intent, broker
instruction, or assistant-citable evidence before persistence.

## Persisted Market Daily Evidence

Use the manual import API to store today's default market daily event set:

```text
POST /market-daily-evidence/import
{
  "market": "CN",
  "provider": "akshare",
  "event_types": [
    "stock_fund_flow",
    "limit_up_reason",
    "dragon_tiger_list",
    "block_trade",
    "hot_sector"
  ],
  "limit": 20
}
```

List stored evidence and stable citations with:

```text
GET /market-daily-evidence?market=CN&citable_only=true&limit=50
GET /market-daily-evidence?event_type=block_trade&symbol=000001&date=2026-07-10
```

The table `market_daily_evidence_events` deduplicates on provider, event type,
normalized identity, market, and trade date. Repeated unchanged rows are
skipped; changed normalized rows update the same stored evidence identity.
Block-trade identities include rank or a deterministic row fingerprint so
multiple same-symbol trades for one date do not collapse.

Only normalized payloads with `status=ok|degraded`, `data_mode=live|delayed`, a
real provider, and non-empty rows are persisted. Sensitive provider fields are
removed before JSON storage. Live endpoints, mock/static fixtures, source
readiness rows, and failed imports never create citation IDs.

The Evidence Center uses the Next proxy at `/api/market-daily-evidence` to show
stored counts, latest import metadata, recent citation IDs, and the manual
refresh result. This is a research-evidence action, not a scheduler, historical
backfill workflow, trading signal, or broker operation.

## Strategy Screening API

`GET /strategies/screen` evaluates the latest daily OHLCV window against
deterministic InStock-inspired screening rules:

```text
GET /strategies/screen?symbols=AAPL,MSFT&strategies=turtle_breakout,ma_trend_up&start=2026-01-01&end=2026-03-31&provider=mock
```

The API returns flattened `items[]`, per-symbol payloads, provider metadata,
sanitized diagnostics, `research_signal_only=true`, and the disclaimer:
`Strategy screening signals are research aids only and are not investment advice.`

The first rules are adapted from InStock's strategy module shapes:

- `volume_price_breakout`: latest bar rises on high relative volume and sufficient traded amount.
- `turtle_breakout`: latest close sets a new high within the lookback window.
- `ma_trend_up`: 30-day moving average rises across 30/20/10/latest checkpoints.

These are not executable orders, backtest results, or validated trading strategies.

## Composite Stock Selection API

`GET /stock-selection/screen` screens local stored instruments against
fundamental, technical, market-data, and news criteria:

```text
GET /stock-selection/screen?symbols=AAPL,MSFT&asset_type=stock&watchlist_only=true&max_pe_ratio=30&min_revenue_growth=0.1&min_rsi=40&max_rsi=70&require_price_above_ma=true&required_pattern_codes=hammer&min_mfi=50&min_chip_benefit_ratio=0.6
```

Supported criteria include:

- `max_pe_ratio`
- `min_revenue_growth`
- `min_net_margin`
- `min_rsi`
- `max_rsi`
- `require_price_above_ma`
- `required_pattern_codes`
- `min_mfi`
- `max_mfi`
- `min_william_r`
- `max_william_r`
- `min_chip_benefit_ratio`
- `max_chip_benefit_ratio`
- `min_latest_volume`
- `min_traded_amount`
- `min_news_article_count`
- `required_news_sentiment`
- `min_news_sentiment_confidence`

Scope controls include:

- `symbols`
- `market`
- `asset_type`
- `watchlist_only` to limit candidate instruments to active default-watchlist
  entries before criteria evaluation

At least one criterion is required. Missing local bars, fundamentals, or
technical indicators produce diagnostics and no fabricated match. Nested
criteria read only stored `candlestick_patterns.patterns[]` and
`chip_distribution.benefit_ratio` payloads. Returned `evidence_citations` point
to stored rows used in the screen, while the selection result itself remains a
research-only analysis payload.

`market`, `asset_type`, and `watchlist_only` are candidate-scope flags, not
evidence or criteria. `asset_type` filters stored `Instrument.asset_type`.
`watchlist_only` reads active watchlist `symbol`/`market` pairs without
provider-backed watchlist enrichment. Scope filters still require ordinary
stored evidence rows and at least one real criterion before a symbol can match.

News/sentiment criteria read only stored `NewsArticle` plus `SentimentSignal`
rows. They do not call live news/search providers, do not persist social search
candidates, and do not treat social/public-opinion candidates as verified news.
When matched, the screener includes a `news:*` evidence citation for the stored
local article used by the latest sentiment rule.

Market-data criteria read only the latest stored `DailyBar`. `min_latest_volume`
uses stored volume. `min_traded_amount` uses stored amount when present and
falls back to the local `close * volume` estimate from the same stored bar when
amount is missing. The screener does not call live providers to repair missing
bar fields.

## Strategy Evaluation API

`GET /strategies/evaluate` scans historical bars for the same strategy screening
rules and reports bounded forward-return diagnostics:

```text
GET /strategies/evaluate?symbol=AAPL&start=2026-01-01&end=2026-03-31&strategies=volume_price_breakout&forward_windows=1,5&benchmark_symbol=SPY&provider=mock
```

It returns snapshots, per-window sample size, hit rate, average/median forward
return, return-distribution diagnostics, max drawdown after signal, optional
benchmark-relative return, provider metadata, sanitized diagnostics,
`research_signal_only=true`, and the same non-advice disclaimer.

Per-window return-distribution diagnostics include win/loss/flat counts,
best/worst forward return, positive/negative average forward return, forward
return standard deviation, and average win/loss ratio. They are calculated only
from already evaluated forward returns and do not imply executable backtest
quality.

This endpoint is not a production backtest. It does not model fills, slippage,
fees, tax, borrow constraints, portfolio sizing, survivorship assumptions,
parameter optimization, scheduler execution, or broker orders.

## Validation

Use focused checks after changing this slice:

```powershell
pytest tests/analytics/test_indicators.py tests/services/test_indicator_persistence_service.py tests/api/test_indicators_db_api.py
pytest tests/api/test_recommendations_api.py tests/services/test_recommendation_signal_evaluation.py
pytest tests/services/test_ingestion_service.py tests/api/test_ingestion_api.py tests/services/test_task_dispatch.py tests/worker/test_tasks.py
pytest tests/services/test_strategy_screening.py tests/api/test_strategy_screening_api.py
pytest tests/services/test_stock_selection.py tests/api/test_stock_selection_api.py
python -m ruff check packages/analytics/indicators.py packages/analytics/candlestick_patterns.py packages/analytics/chip_distribution.py packages/services/indicators.py packages/services/ingestion.py packages/services/task_dispatch.py packages/services/strategy_screening.py packages/services/stock_selection.py apps/api/routers/ingestion.py apps/api/routers/strategy_screening.py apps/api/routers/stock_selection.py apps/worker/tasks/ingestion.py tests/analytics/test_indicators.py tests/helpers/celery_sync.py tests/services/test_indicator_persistence_service.py tests/services/test_ingestion_service.py tests/services/test_task_dispatch.py tests/services/test_strategy_screening.py tests/services/test_stock_selection.py tests/api/test_indicators_db_api.py tests/api/test_ingestion_api.py tests/api/test_strategy_screening_api.py tests/api/test_stock_selection_api.py tests/worker/test_tasks.py
git diff --check
```
