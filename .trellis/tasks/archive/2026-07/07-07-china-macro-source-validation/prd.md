# China macro source validation spike

## Goal

Validate the next China macro data-source path for the personal investment research cockpit and turn the result into durable source-capability metadata. The task should determine whether NBS, PBOC, Trading Economics, World Bank/IMF-style fallbacks, or library-backed sources can safely support audited local macro observations for indicators such as China GDP, CPI, PPI, PMI, M2, and Buffett-related context.

The first slice should strengthen online/API macro information collection and AI source transparency. It must not turn the product into a professional trading terminal, a scraping project, or an unlicensed data redistribution system.

Decision: this task is validation-only. It should not build a production China macro adapter even if one source looks promising; instead it should identify the safest next adapter candidate and document the required follow-up.

## Confirmed Facts

- The product direction is a personal information aggregation and AI research cockpit, not professional trading-terminal parity.
- FRED and World Bank opt-in macro refresh paths already exist for US rates, US CPI/M2, and Buffett Indicator market-cap-to-GDP observations.
- `README.md` documents Information Source Readiness as an implemented collection-guidance MVP and says it performs no live network fetches unless an explicit refresh script is run.
- `docs/manual/user-guide.md` identifies the remaining macro gaps as official macro adapters, macro release calendar/freshness policy, source capability matrix, more official sources, and license/freshness operational records.
- Current macro definitions include `cn_m2_yoy`, but PBOC China M2 is still represented as a manual/public source-readiness item, not as a validated production adapter.
- Current source-readiness status/citation policy must remain conservative: links, seed templates, probe diagnostics, and adapter candidates are not AI citations until validated local observations exist.
- The previous World Bank task proved the preferred adapter pattern: provider -> service refresh -> audited `MarketIndicatorObservation` -> source-readiness configured only from local evidence -> AI citation only after local evidence exists.

## Requirements

### R1. Source Validation Scope

- Validate official/API or legally usable machine-readable paths before implementing any production China macro adapter.
- Cover at least these source families:
  - National Bureau of Statistics of China (NBS) for GDP, CPI, PPI, PMI, industrial/activity-style macro indicators when available.
  - People's Bank of China (PBOC) for China M2/liquidity indicators.
  - World Bank / IMF / World Bank-style public APIs as lower-frequency fallback sources for China macro context where appropriate.
  - Trading Economics or similar aggregator APIs only as optional/vendor candidates with license and credential requirements clearly marked.
  - AkShare/Tushare-style libraries only as candidate convenience paths, not official evidence, unless the source/license chain is explicit.
- Prefer official/API sources over scraped HTML or reverse-engineered web endpoints.

### R2. Capability Matrix MVP

- Add or update durable source-capability metadata that records, per source and indicator family:
  - source name and authority;
  - indicator coverage;
  - access mode (`official_api`, `public_page`, `manual_seed`, `vendor_api`, `library_wrapper`, or `unsupported`);
  - adapter status (`implemented`, `adapter_ready`, `candidate`, `manual_only`, `blocked`, or `future`);
  - credential requirement;
  - license/usage note;
  - freshness/release cadence;
  - latest validation timestamp and diagnostic summary when a probe is run.
- The matrix should be usable by docs and/or source readiness without making candidate sources AI-citable.

### R3. Probe / Research Flow

- Provide a repeatable validation entry point, such as a script or structured research artifact, that can test or document source reachability and schema shape without writing market observations.
- Network access must be opt-in and diagnostics must be sanitized.
- Tests should mock network behavior; no default unit test may depend on live external services.
- If a source blocks automated access, changes schema, requires credentials, or has unclear license terms, mark it as candidate/manual/blocked rather than forcing an adapter.

### R4. Product Boundary

- This task should improve macro information collection and AI summarization readiness.
- It should not add broker/trading features, realtime market-data loops, Redis refresh infrastructure, reverse-engineered scraping as a core source, or direct buy/sell/hold recommendations.
- If a production adapter is created later, it must persist only through audited `MarketIndicatorObservation` rows with source and methodology metadata.

### R5. Documentation

- Update user/maintainer documentation with the validation result, next recommended production adapter candidate, and what remains manual.
- Explain that source capability/probe status is not evidence and cannot be cited by AI until observations are stored locally.

## Acceptance Criteria

- [x] The task records a reviewed capability matrix for China macro source candidates covering NBS, PBOC, at least one global fallback source, and at least one vendor/library candidate.
- [x] The matrix distinguishes adapter-ready, candidate, manual-only, blocked, and future sources without promoting links/probes/templates into AI citations.
- [x] A repeatable validation/probe path or structured research artifact exists and can be rerun or updated later.
- [x] Tests or checks cover the new metadata/probe behavior without requiring live network access.
- [x] Source Readiness, docs, or runbooks expose the new source-capability status in a way that helps decide the next macro adapter.
- [x] The PRD/design explicitly selects validation-only as this task's implementation slice and recommends the next production adapter candidate only after validation.
- [x] Existing FRED, World Bank, seed import, Evidence Center, and AI citation boundaries remain backward compatible.

## Out Of Scope

- Building a production NBS/PBOC adapter before the access path, schema, and license boundary are validated.
- Scraping arbitrary HTML pages or relying on reverse-engineered endpoints as a default source.
- Paid vendor onboarding, account management, or secret handling beyond recording credential requirements.
- Automatic scheduled refresh, Redis caching loops, macro alerting, or release calendar implementation unless the final scope explicitly chooses them.
- Treating source capability rows, probe diagnostics, or source-readiness links as AI evidence.
