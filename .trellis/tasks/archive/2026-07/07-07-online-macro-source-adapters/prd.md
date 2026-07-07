# Online Macro Source Adapters

## Goal

Add the next official/API-backed macro source path for the personal investment research cockpit so macro and valuation indicators can move from manual collection guidance into audited local evidence that AI summaries may cite.

The MVP should strengthen information aggregation, macro indicator collection, Buffett Indicator coverage, and source-transparent AI summarization. It must not compete with professional trading terminals or produce direct buy/sell/hold, target-price, position-sizing, or execution advice.

## Confirmed Facts

- The product direction in `README.md` is a "Personal Investment Research Cockpit" focused on information aggregation, source transparency, macro/valuation indicators, AI summaries, and evidence-backed stock analysis.
- The user manual already says the best comparison set is information aggregation and AI research tools rather than trading-terminal parity, and it lists official macro adapters, source capability matrix, macro release calendar, and watchlist research inbox as likely improvements.
- Existing domain language includes `数据源`, `数据源适配器`, `宏观指标`, `估值指标`, `信息源就绪度`, and `可引用证据` in `CONTEXT.md`.
- Existing macro indicator codes are defined in `packages/services/market_indicators.py:20`, including `buffett_indicator_cn`, `buffett_indicator_hk`, `buffett_indicator_us`, US rates/spread, US CPI/M2 YoY, and CN M2 YoY.
- Existing observations persist through `MarketIndicatorObservationSeed` and `upsert_market_indicator_observation(...)` in `packages/services/market_indicators.py:46` and `packages/services/market_indicators.py:1268`.
- Existing FRED refresh support lives in `packages/services/market_indicators.py:444`, uses `packages/providers/fred_provider.py:50`, and has a CLI at `scripts/refresh_fred_macro_indicators.py:17`.
- Existing source readiness lives in `packages/services/information_sources.py:399` and currently treats World Bank Buffett links as manual collection guidance, not an adapter.
- Existing Evidence Center renders macro/valuation evidence, source readiness, seed templates, saved research briefs, and follow-up queue data through `apps/web/app/[locale]/evidence/page.tsx:739`.
- Existing tests cover FRED provider behavior, FRED refresh, source readiness, seed templates, Evidence Center rendering, and no-citation-until-local-evidence boundaries.
- External-source feasibility research is captured in `research/external-source-feasibility.md`.

## Requirements

### R1. Source Strategy

- Prefer official/API sources before aggregators or reverse-engineered web interfaces.
- Treat FRED as the existing baseline official adapter.
- Add World Bank as the first new adapter candidate for Buffett Indicator and GDP/market-cap context.
- Keep NBS/PBOC/Trading Economics/AkShare/Tushare follow-ups out of the MVP unless the user explicitly changes the first-slice priority.

### R2. World Bank Adapter MVP

- Fetch World Bank observations for the existing Buffett Indicator region codes where data is available:
  - `buffett_indicator_us`
  - `buffett_indicator_cn`
  - `buffett_indicator_hk`
- Use the World Bank market-cap-to-GDP indicator (`CM.MKT.LCAP.GD.ZS`) as the primary Buffett ratio source when available.
- Optionally fetch GDP current USD (`NY.GDP.MKTP.CD`) as component context for the same country/year when it can be retrieved without broadening the scope.
- Skip missing/null values and unsupported country/indicator rows; never store missing data as zero.
- Use mocked HTTP tests. No default test may require live network access.

### R3. Audited Persistence

- Persist adapter results only through the existing audited `MarketIndicatorObservationSeed` and `upsert_market_indicator_observation(...)` path.
- Each stored observation must include source and method metadata sufficient for AI citation:
  - provider name;
  - World Bank country code;
  - World Bank indicator ID;
  - source URL or API URL;
  - retrieved timestamp;
  - source observation date;
  - methodology or calculation note;
  - component metadata when GDP or market-cap context is available.
- Existing manual seed import and FRED refresh behavior must remain backward compatible.

### R4. Diagnostics And Refresh Flow

- Add an explicit refresh entry point that mirrors the FRED CLI/service style: dry-run support, latest-only or bounded date support if practical, concise OK/WARN/FAIL output, and sanitized provider errors.
- Missing data, timeouts, and provider schema mismatch must produce diagnostics; they must not fabricate observations.
- API keys are not expected for World Bank. If a future source requires credentials, secrets must never appear in diagnostics.

### R5. Source Readiness And Evidence Center

- Source readiness should show World Bank-backed Buffett Indicator capability separately from purely manual seed guidance.
- Once a World Bank observation exists locally, the relevant source-readiness item should become configured through local evidence count and latest as-of metadata.
- Evidence Center should remain a macro/source evidence cockpit, not a local-note workflow by default. Existing manual seed and Source Notebook tools may remain as fallback/admin paths, but the first path for this task should be online/API refresh.

### R6. AI Citation Boundary

- AI summaries, saved research briefs, and market assistant responses may cite the new macro data only after a validated local `MarketIndicatorObservation` exists.
- Source-readiness links, adapter IDs, templates, skipped rows, and refresh diagnostics are gaps or metadata, not citation IDs.
- Existing no-fabricated-macro-data and no-trading-advice boundaries must remain intact.

### R7. Documentation

- Update user-facing docs to explain the World Bank refresh path, what it covers, how stale/lagged annual macro data should be interpreted, and when AI can cite the observations.
- Update maintainer docs or README if a new script/env variable/operational command is added.
- Keep wording aligned with the personal research cockpit positioning.

## Out Of Scope

- Scraping HTML pages or relying on reverse-engineered Eastmoney/Snowball/THS-style interfaces as core evidence.
- Building a real-time trading terminal, broker integration, order execution, low-latency market data, or Level-2 parity.
- Automatic scheduled macro refresh, Redis-backed realtime refresh loops, or a macro release calendar unless they are needed as minimal metadata for the adapter.
- NBS production adapter, Trading Economics paid adapter, Tushare/AkShare macro integration, and paid vendor management.
- Full filings/transcripts/document corpus ingestion, OCR/PDF parsing, or vector search.

## Acceptance Criteria

- [x] A World Bank provider/adapter has focused tests for successful observations, missing/null values, schema mismatch, timeout/provider errors, pagination or latest-value selection if applicable, and sanitized diagnostics.
- [x] A service refresh path maps World Bank data to the existing Buffett Indicator codes and persists through `MarketIndicatorObservationSeed` and `upsert_market_indicator_observation(...)`.
- [x] Stored observations include source and methodology metadata that satisfies the existing audit/citation contract.
- [x] A CLI or explicit refresh script supports dry-run mode and reports OK/WARN/FAIL without live-network tests.
- [x] Source readiness distinguishes World Bank adapter-backed Buffett evidence from manual seed guidance and stays backward compatible for existing consumers.
- [x] Evidence Center and dashboard AI citation behavior continues to cite only stored local observations, generated reports, stored news, and reviewed/citable source notes.
- [x] Docs describe the new refresh path, citation boundary, and annual/lagged macro-data limitations.
- [x] Focused backend, script, frontend, message JSON, TypeScript, and diff checks pass for touched areas.

## Product Decision

Decision: start the MVP with the World Bank Buffett/GDP adapter and defer NBS/China macro APIs to a later validation spike.

Rationale: World Bank best matches the existing Buffett Indicator gap, can feed existing indicator codes, and avoids the current access uncertainty around the NBS portal. NBS remains important for China macro depth, but it should first be validated as an API/access spike before being promised as production evidence.
