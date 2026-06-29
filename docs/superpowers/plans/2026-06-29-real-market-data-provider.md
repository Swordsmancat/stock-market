# Real Market Data Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a real market data provider path while keeping MockProvider as the default fallback for local development and tests.

**Architecture:** Preserve the existing `ProviderAdapter` protocol and add a `YFinanceProvider` that returns the same `ProviderInstrument` and `ProviderBar` objects as `MockProvider`. Route ingestion through a provider selector so `provider=mock` keeps existing behavior and `provider=yfinance` writes provider bars into the same `bars_1d` table used by indicators, reports, and dashboard flows.

**Tech Stack:** Python, FastAPI, SQLAlchemy, Pandas, optional yfinance runtime dependency, pytest, Ruff.

---

### Task 1: Add YFinance provider adapter

**Files:**
- Create: `packages/providers/yfinance_provider.py`
- Modify: `pyproject.toml`
- Test: `tests/providers/test_yfinance_provider.py`

- [ ] **Step 1: Write failing provider test**

Create `tests/providers/test_yfinance_provider.py` with a fake downloader and assert that `YFinanceProvider.fetch_bars("AAPL", "1d", ...)` returns `ProviderBar` objects with decimal prices.

- [ ] **Step 2: Run provider test to verify RED**

Run: `python -m pytest tests/providers/test_yfinance_provider.py -v`

Expected: FAIL because `packages.providers.yfinance_provider` does not exist.

- [ ] **Step 3: Implement provider**

Create `YFinanceProvider` with instrument fixtures for `US`, `HK`, and `CN`, ticker mapping (`AAPL`, `0700.HK`, `600519.SS`), lazy `yfinance` import, and DataFrame-to-ProviderBar conversion.

- [ ] **Step 4: Run provider test to verify GREEN**

Run: `python -m pytest tests/providers/test_yfinance_provider.py -v`

Expected: PASS.

### Task 2: Add provider selection to ingestion service and API

**Files:**
- Modify: `packages/services/ingestion.py`
- Modify: `packages/services/market_data.py`
- Modify: `apps/api/routers/ingestion.py`
- Test: `tests/services/test_ingestion_service.py`
- Test: `tests/api/test_ingestion_api.py`

- [ ] **Step 1: Write failing service/API tests**

Add tests that call ingestion with `provider_name="mock"` and API with `provider=mock`, expecting existing DB write behavior and `provider` in the payload.

- [ ] **Step 2: Run tests to verify RED**

Run: `python -m pytest tests/services/test_ingestion_service.py tests/api/test_ingestion_api.py -v`

Expected: FAIL because `provider_name` / `provider` is not accepted yet.

- [ ] **Step 3: Implement selector and API parameter**

Add `get_provider(provider_name)` and `ingest_market_snapshot(..., provider_name="mock")`; keep `ingest_mock_market_snapshot` as a wrapper. Add `provider` query parameter to `/ingestion/mock-snapshot`.

- [ ] **Step 4: Run tests to verify GREEN**

Run: `python -m pytest tests/services/test_ingestion_service.py tests/api/test_ingestion_api.py -v`

Expected: PASS.

### Task 3: Update docs and verify closure

**Files:**
- Modify: `docs/runbooks/local-development.md`

- [ ] **Step 1: Document provider usage**

Add commands for `provider=mock` and `provider=yfinance`, and note that mock remains default.

- [ ] **Step 2: Run targeted tests**

Run: `python -m pytest tests/providers/test_yfinance_provider.py tests/services/test_ingestion_service.py tests/api/test_ingestion_api.py -v`

Expected: PASS.

- [ ] **Step 3: Run full verification**

Run: `python -m pytest -v`, `npm run test:web`, and Ruff on changed Python files.

Expected: all PASS.
