# Journal - 何剑锋 (Part 2)

> Continuation from `journal-1.md` (archived at ~2000 lines)
> Started: 2026-07-14

---



## Session 60: Complete personal A-share coverage acceptance

**Date**: 2026-07-14
**Task**: Complete personal A-share coverage acceptance
**Branch**: `master`

### Summary

Monitored the sole normal-stack incremental backfill, cooperatively cancelled it after the configured 30-minute stale threshold, replaced only the blocked solo Worker, and preserved checkpoint 4650. Beat's queued fundamental shard 1/5 then completed 1106/1106 with zero failures. Final local coverage passed bars 99.60%, technical 99.75%, and fundamentals 100% against fixed 95/90/80 gates; no redundant baseline or extra shards were started. Generated sanitized evidence, kept 3000/8000 and Beat healthy, and left the LLM task active for the external DeepSeek canary.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `40aedfa` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 61: Complete DeepSeek live API acceptance

**Date**: 2026-07-14
**Task**: Complete DeepSeek live API acceptance
**Branch**: `master`

### Summary

Verified the refreshed DeepSeek configuration through all three secret-safe settings projections, then ran one stock-discovery and one market-assistant live canary without retries. Both used deepseek-chat with no fallback; deterministic shortlist membership, order, and scores stayed unchanged, citations passed validation, sanitized evidence was recorded, and the LLM API configuration task was completed and archived.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `abf7286` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 62: Personal research workflow acceptance

**Date**: 2026-07-15
**Task**: Personal research workflow acceptance
**Branch**: `master`

### Summary

Streamlined personal navigation and secondary modules, added bounded instrument pagination and secret-safe LLM testing, and completed full browser/live acceptance.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `dc807cc` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 63: Fix empty watchlist report no-op

**Date**: 2026-07-15
**Task**: Fix empty watchlist report no-op
**Branch**: `master`

### Summary

Diagnosed two repeated scheduled report failures, preserved intentionally empty persisted watchlists, added skipped TaskRun regressions and backend contract, verified through the restarted live Celery worker, and restored the five-day acceptance task.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `3c2aa56` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 64: Suppress empty alert TaskRun noise

**Date**: 2026-07-15
**Task**: Suppress empty alert TaskRun noise
**Branch**: `master`

### Summary

Suppressed direct 15-minute no-rule alert TaskRun noise while preserving explicit TaskRuns and failures; validated 60 focused tests plus live queued and Beat-tick acceptance.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `043dc5f` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 65: Fix homepage fund-flow scrolling

**Date**: 2026-07-15
**Task**: Fix homepage fund-flow scrolling
**Branch**: `master`

### Summary

Made the fixed-height homepage fund-flow panel natively scrollable and focusable, restored every loaded row, and validated 279 frontend tests plus desktop/mobile browser overflow behavior.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `660f0c1` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 66: Resilient CN daily-bar fallback

**Date**: 2026-07-15
**Task**: Resilient CN daily-bar fallback
**Branch**: `master`

### Summary

Added market-aware CN daily-bar source fallback from yfinance to configured AkShare/Tushare, preserved provenance through detail and AI, hardened search market resolution and database cohort diagnostics, and verified the isolated live path without disturbing normal services.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `e3df27d` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 67: Multi-source research fallback

**Date**: 2026-07-16
**Task**: Multi-source research fallback
**Branch**: `master`

### Summary

Added validated daily, exact-market intraday, and sequential stored-news fallback with one-shot UI recovery, shared credential/HTML safety validation, migration coverage, and live personal-workflow acceptance while preserving the five-day task state.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `1f09127` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 68: Improve homepage news and macro availability

**Date**: 2026-07-16
**Task**: Improve homepage news and macro availability
**Branch**: `master`

### Summary

Added Shanghai-localized news timestamps, removed homepage provider status, restored audited World Bank CN/US macro values with bounded recent-window selection, and hardened error redaction.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `624dcf9` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 69: Stabilize homepage initial data and localization

**Date**: 2026-07-16
**Task**: Stabilize homepage initial data and localization
**Branch**: `master`

### Summary

Added a dedicated cold overview timeout, localized nine macro labels, restored a full desktop module grid, improved mobile macro readability, and locked the behavior with tests and browser acceptance.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `b50f588` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 70: Harden public research fallbacks

**Date**: 2026-07-16
**Task**: Harden public research fallbacks
**Branch**: `master`

### Summary

Recovered sparse A-share daily bars through validated sources and replaced legacy CN news retrieval with a bounded Cookie-free Eastmoney fallback.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `4b0c7d0` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 71: Stabilize homepage and Docker startup

**Date**: 2026-07-16
**Task**: Stabilize homepage and Docker startup
**Branch**: `master`

### Summary

Filtered non-finite market bars, added bounded AkShare Sina fallback for missing CN indices, kept cold news requests responsive, and made the default Docker Desktop stack serve a health-gated frontend on port 3000.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `9370acb` | (see git log) |
| `f3c0beb` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 72: Eastmoney public fundamentals fallback

**Date**: 2026-07-16
**Task**: Eastmoney public fundamentals fallback
**Branch**: `master`

### Summary

Added a bounded Cookie-free Eastmoney A-share fundamentals and company-profile fallback with database-first reads, normalized Redis caching, detail rendering, AI citation context, executable specs, and full regression coverage.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `8bf9c60` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 73: Truthful stored fundamentals and company context

**Date**: 2026-07-16
**Task**: Truthful stored fundamentals and company context
**Branch**: `master`

### Summary

Corrected legacy zero-PE read projections, added independent cached Eastmoney company enrichment for stored A-share fundamentals, verified the real 600519 search/detail workflow, and preserved database financial authority without GET writes.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `463d747` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 74: Readable technical indicators

**Date**: 2026-07-16
**Task**: Readable technical indicators
**Branch**: `master`

### Summary

Summarized candlestick and chip-distribution indicators into localized, bounded, responsive detail views; added regression coverage and frontend rendering guidance; verified desktop/mobile runtime behavior.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `7854898` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 75: Stable intraday time hydration

**Date**: 2026-07-16
**Task**: Stable intraday time hydration
**Branch**: `master`

### Summary

Fixed instrument-detail hydration by formatting intraday timestamps with explicit locale and market time zones; added cross-zone regression coverage and verified a clean browser console on the rebuilt Web stack.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `e27acc5` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 76: Clean AI research runtime

**Date**: 2026-07-16
**Task**: Clean AI research runtime
**Branch**: `master`

### Summary

Removed AI Research missing-message, duplicate-key, and evidence timestamp hydration errors; added Chinese, page-level, and cross-zone regressions; verified a clean rebuilt browser console without changing research behavior.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `1a452be` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 77: Preserve missing fundamental metrics

**Date**: 2026-07-16
**Task**: Preserve missing fundamental metrics
**Branch**: `master`

### Summary

Made fundamental metrics independently nullable, migrated legacy provider zero sentinels, preserved genuine zero values, and verified the 000001 detail page shows unavailable metrics without hiding the real debt ratio.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `86180db` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 78: Select complete A-share fundamentals fallback

**Date**: 2026-07-16
**Task**: Select complete A-share fundamentals fallback
**Branch**: `master`

### Summary

Selected a strictly more complete coherent Eastmoney public fundamentals snapshot for partial stored A-share data, preserved stored ties and failures, and verified 000001 detail provenance and metrics without writes.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `0865f5e` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 79: Collapse long company profile

**Date**: 2026-07-16
**Task**: Collapse long company profile
**Branch**: `master`

### Summary

Collapsed long instrument company scope and profile behind an accessible localized disclosure while keeping company identity visible; added regression coverage and completed desktop browser QA.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `e32ddb9` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 80: Rebalance instrument detail research layout

**Date**: 2026-07-17
**Task**: Rebalance instrument detail research layout
**Branch**: `master`

### Summary

Replaced the stretched instrument-detail report grid with independent primary/evidence streams, moved charts and news earlier, added responsive layout coverage and frontend guidance, and deployed the verified Web image to the normal 3000 stack.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `80719bb` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 81: Localize instrument technical indicators

**Date**: 2026-07-17
**Task**: Localize instrument technical indicators
**Branch**: `master`

### Summary

Localized all known instrument-detail technical indicator names and Bollinger/MACD fields in Chinese and English, preserved unknown-key fallback, added component and page coverage, and deployed the verified Web image to the normal 3000 stack.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `252d31b` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 82: Localize candlestick pattern labels

**Date**: 2026-07-17
**Task**: Localize candlestick pattern labels
**Branch**: `master`

### Summary

Localized the five candlestick_patterns_v1 codes for Chinese and English instrument detail pages, preserved bounded unknown-value fallback, added regression coverage and frontend spec guidance, verified in browser, and deployed the Web container.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `0933f7f` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 83: Simplify AI research evidence context

**Date**: 2026-07-17
**Task**: Simplify AI research evidence context
**Branch**: `master`

### Summary

Localized AI Research macro evidence with a shared code map, limited the default assistant question to citable stored observations, moved source readiness and raw diagnostics into a closed maintenance disclosure, added component/page regressions, verified responsive Chinese and English runtime behavior without a model call, and deployed the Web container.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `69ab110` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 84: Expand macroeconomic dashboard

**Date**: 2026-07-17
**Task**: Expand macroeconomic dashboard
**Branch**: `master`

### Summary

Added a 23-item grouped macroeconomic dashboard, audited explicit AkShare refresh with partial-failure handling, localized responsive cards and sparklines, retained read-only GET and collapsed maintenance tools; verified live 18/23 availability, full tests, Docker deployment, and browser smoke checks.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `a12dc6e` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 85: ChinaMoney repo fixing rates

**Date**: 2026-07-17
**Task**: ChinaMoney repo fixing rates
**Branch**: `master`

### Summary

Qualified the direct NBS candidate without guessing identifiers, added audited FR007/FDR007 observations with localized dashboard labels, passed 1078 backend and 382 web tests, deployed API/Web, and verified a live 48-observation refresh.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `b1480dc` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 86: Stored Eastmoney economic calendar

**Date**: 2026-07-17
**Task**: Stored Eastmoney economic calendar
**Branch**: `master`

### Summary

Added a bounded Cookie-free Eastmoney economic calendar provider, transactional PostgreSQL persistence, database-only API reads, localized Evidence Center panel, source replacement runbook, live July refresh, and cross-layer tests.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `aa2004d` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 87: Database storage overview

**Date**: 2026-07-17
**Task**: Database storage overview
**Branch**: `master`

### Summary

Added a secret-safe PostgreSQL storage inventory API and localized read-only storage dashboard with desktop navigation, responsive table inventory, full tests, and live Docker/browser acceptance.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `f8d5c7c` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 88: Stored market movers ranking

**Date**: 2026-07-18
**Task**: Stored market movers ranking
**Branch**: `master`

### Summary

Added a database-first A-share gainers/losers module with coherent two-date provenance, responsive localized UI, numeric safety, full backend/frontend coverage, and live desktop/mobile acceptance.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `a83bbad` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 89: Stored stock comparison workflow

**Date**: 2026-07-18
**Task**: Stored stock comparison workflow
**Branch**: `master`

### Summary

Added database-only A-share comparison with coherent stored daily-bar cohorts, exact shared-date alignment, localized routed UI, responsive acceptance, and complete cross-layer tests.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `1e036e0` | (see git log) |
| `85d21a3` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 90: Unified stored K-line workspace

**Date**: 2026-07-18
**Task**: Unified stored K-line workspace
**Branch**: `master`

### Summary

Added one database-only stock, ETF, and index K-line catalog and workspace, removed provider-capable list fan-out, unified global search, verified desktop/mobile runtime rendering, and completed focused plus full regression checks.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `7320117` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 91: Focused topic research workspace

**Date**: 2026-07-18
**Task**: Focused topic research workspace
**Branch**: `master`

### Summary

Added a database-only four-topic personal research workspace with conservative evidence matching, Shanghai date anchoring, non-empty company snapshot fallback, localized desktop/mobile UI, and full browser/test acceptance.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `e46402e` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 92: Eastmoney automated pipeline acceptance

**Date**: 2026-07-18
**Task**: Eastmoney automated pipeline acceptance
**Branch**: `master`

### Summary

Completed and live-validated four bounded Eastmoney collection pipelines, corrected deduplicated news status semantics, passed full backend/frontend/type/Ruff checks, and preserved unrelated monitor/calendar work.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `b732805` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete
