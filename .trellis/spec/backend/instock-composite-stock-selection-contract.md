# InStock-Inspired Composite Stock Selection Contract

## Scenario: Research-Only Local Composite Stock Selection

### 1. Scope / Trigger

- Trigger: `GET /stock-selection/screen` screens stored active instruments
  against local fundamental and technical criteria.
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
  - `max_pe_ratio`
  - `min_revenue_growth`
  - `min_net_margin`
  - `min_rsi`
  - `max_rsi`
  - `require_price_above_ma`
  - `limit`, bounded to `1..100`.
- Service entry:
  `screen_local_stock_selection(..., session, symbols=None, market=None, ...)`
- Rule set: `instock_composite_selection_v1`.

### 3. Contracts

- The first slice reads local stored evidence only:
  - `Instrument` scope;
  - latest stored `DailyBar`;
  - latest stored `TechnicalIndicator` values;
  - latest stored `FundamentalSnapshot`.
- At least one selection criterion is required. Empty criteria returns HTTP 400
  at the API boundary and an `invalid_request` service payload.
- Missing local evidence must produce diagnostics and no fabricated match.
- Matching items may expose evidence citation IDs for the stored rows used:
  `bars_1d:*`, `technical_indicators:*`, and `fundamental_metrics:*`.
- The stock-selection result itself is a research analysis payload, not a stored
  assistant citation row and not a trading signal.
- Payloads must include `research_signal_only=true` and the disclaimer:
  `Composite stock selection is a research aid only and is not investment advice.`
- Results must not emit buy/sell/hold actions, target prices, position sizes,
  order intents, portfolio weights, broker routing, or execution instructions.

### 4. Validation & Error Matrix

- No criteria -> HTTP 400 / `NO_SELECTION_CRITERIA`.
- Symbol duplicates -> normalize and screen once.
- Fundamental criterion requested but no `FundamentalSnapshot` -> diagnostic
  `MISSING_FUNDAMENTALS`, no match.
- Technical criterion requested but required indicator is missing -> diagnostic
  with `SELECTION_RULE_NOT_MATCHED` and `missing_value`, no match.
- No stored daily bar -> diagnostic `MISSING_DAILY_BAR`, no match.
- A criterion fails -> diagnostic `SELECTION_RULE_NOT_MATCHED`, no match.
- Matching item -> include stored evidence citations and matched rule details.

### 5. Good/Base/Bad Cases

- Good: `/stock-selection/screen?symbols=AAPL&max_pe_ratio=30&min_rsi=40&max_rsi=70`
  returns AAPL when stored fundamentals and technical indicators satisfy all
  criteria.
- Good: a symbol without fundamentals is skipped with diagnostics instead of a
  fake valuation metric.
- Base: scanning by `market=US` without `symbols` uses stored active instruments
  only and does not fetch provider data.
- Bad: the endpoint calls a live provider for every listed symbol.
- Bad: a selected symbol is described as a buy recommendation, target allocation,
  or executable order.
- Bad: InStock's web/database/strategy/trading runtime is imported.

### 6. Tests Required

- Service tests assert matching across fundamental and technical criteria,
  duplicate symbol normalization, evidence citations, failed criteria diagnostics,
  missing fundamentals diagnostics, and no-criteria validation.
- API tests assert route registration, query parsing, HTTP 400 for no criteria,
  and `research_signal_only=true`.
- Focused validation should include:
  `pytest tests/services/test_stock_selection.py tests/api/test_stock_selection_api.py`,
  ruff on touched stock-selection files, full backend pytest, and
  `git diff --check`.
