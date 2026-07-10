# InStock A-share research universe and corporate-action evidence

## Goal

Remove watchlist bias from AI-assisted stock selection by building a durable,
provider-backed A-share research universe and making selection evaluate the
eligible local universe rather than an arbitrary first-100 subset. Use
dividend/bonus-transfer and rights-allotment events as the first universe-wide
InStock-inspired evidence enrichment.

## User Value

AI selection and analysis should be broad enough to discover candidates outside
the user's current watchlist. A watchlist remains useful for prioritization and
monitoring, but it must not define the total candidate universe. The system
must also show when a candidate exists but lacks enough evidence, rather than
silently excluding it or treating missing data as a negative signal.

## Confirmed Facts

- The user rejected watchlist-only ingestion because it would make AI selection
  and analysis insufficiently comprehensive.
- `GET /stock-selection/screen` reads only stored active `Instrument` rows.
- `packages/services/stock_selection.py` currently caps candidate loading at
  `MAX_SCREENING_SYMBOLS = 100` before evaluating criteria, so an all-A-share
  instrument table would still scan only the first 100 ordered symbols.
- `AkShareProvider.fetch_instruments()` currently returns only three hard-coded
  CN fixtures instead of a production universe.
- Installed AkShare `1.18.64` exposes `stock_info_a_code_name()` for a single
  provider call returning the Shanghai, Shenzhen, and Beijing A-share list.
- Existing ingestion, `TaskRun`, Celery, `Market`, and `Instrument` boundaries
  can be extended without importing InStock's scheduler, database, or UI.
- Existing stock selection reads stored fundamentals, daily bars, technical
  indicators, news/sentiment, and watchlist state. It does not fetch live
  provider evidence during a screen.
- The current market assistant is single-symbol: its prompt context requires one
  `symbol`, timeframe, and date range. It does not invoke the stock-selection
  service or choose candidates across a universe.
- The current AI Research page builds recommendation symbols from watchlist and
  followed items, so its recommendation surface is also biased toward already
  known symbols rather than discovering candidates across the stored market.
- Installed AkShare exposes dividend/bonus and rights-allotment functions, but
  some are per-symbol. Universe-wide enrichment therefore needs batching,
  limits, retry diagnostics, and resumable progress rather than one synchronous
  request.
- The provider does not expose an equally clear first-class early-session or
  late-session capital-grab API; that capability requires a separate provider
  review instead of proxy/Cookie scraping in this task.

## Requirements

- R1: Add a provider-backed A-share universe sync using a reviewed AkShare
  instrument-list endpoint, with dependency injection and network-free tests.
- R2: Normalize symbol, name, market, exchange, asset type, currency, provider,
  source, as-of time, and active/inactive state without fabricating unsupported
  metadata.
- R3: Upsert the full normalized universe into existing market/instrument
  storage with deterministic identities and reconciliation diagnostics for
  inserted, updated, unchanged, missing, and deactivated rows.
- R4: Expected provider failures or empty responses must preserve the previous
  usable universe and return sanitized degraded/failure diagnostics; they must
  never deactivate every instrument.
- R5: Replace the arbitrary first-100 candidate pre-limit with a scalable,
  deterministic full-universe selection path. Result `limit` may still bound
  returned matches, but it must not determine which candidates are evaluated.
- R6: Selection responses must report candidate-universe size, evaluated count,
  evidence-complete count, insufficient-evidence count, and diagnostic reasons
  so AI consumers can distinguish broad coverage from complete evidence.
- R7: Missing fundamentals, bars, indicators, news, or corporate actions must
  remain explicit evidence gaps. Missing data must not be converted into a
  matched criterion or a negative investment conclusion.
- R8: Keep screens local-evidence-only. Universe refresh and evidence enrichment
  happen before selection through explicit jobs; selection must not fan out to
  thousands of live provider requests.
- R9: Add bounded asynchronous jobs and TaskRun progress for universe refresh
  and per-symbol/report-period evidence enrichment, with partial-success,
  retry, and resumability semantics.
- R10: Watchlist symbols may receive higher refresh priority but the watchlist
  must not be the only universe source or the only AI-selection scope.
- R11: Add normalized provider/service contracts for A-share dividend,
  bonus-transfer, and rights-allotment events and persist eligible rows through
  the existing `market_daily_event:*` evidence/citation boundary.
- R12: Repeated imports of the same provider, subtype, symbol, and event date
  must update or skip the same evidence identity while preserving distinct
  plans or implementation events.
- R13: Extend existing API, TaskRun, Evidence Center, and selection surfaces
  instead of introducing a parallel InStock UI or database.
- R14: Add focused tests for universe parsing/reconciliation, failure safety,
  full candidate evaluation, evidence coverage diagnostics, corporate-action
  normalization/dedupe/citation gating, async progress, API contracts, and
  localized frontend states.
- R15: Preserve research-only boundaries: no buy/sell/hold instructions,
  target prices, position sizing, orders, broker calls, or automatic trading.
- R16: Do not import InStock runtime modules, TA-Lib, MySQL/Tornado code,
  proxy/Cookie workflows, or automatic-trading modules.
- R17: Add an AI-research discovery workflow that consumes a bounded,
  deterministic stock-selection shortlist plus its stored evidence citations
  and coverage diagnostics; do not send the full market or raw provider rows
  directly to an LLM.
- R18: Keep candidate scoring/ranking reproducible outside the LLM. AI output
  may explain comparisons, evidence, missing-data caveats, and follow-up
  research questions, but it must not silently add symbols or alter the
  deterministic shortlist.

## Acceptance Criteria

- [ ] A provider-fake test syncs a multi-exchange A-share universe and proves
  deterministic instrument upsert/reconciliation counts.
- [ ] Provider failure or empty output leaves the last good universe active and
  exposes sanitized diagnostics.
- [ ] Stock selection evaluates the complete eligible stored candidate set,
  including a regression fixture with more than 100 instruments, before
  applying the returned-result limit.
- [ ] Selection responses expose universe and evidence-coverage counts so AI
  analysis cannot describe partial evidence as comprehensive coverage.
- [ ] Universe and enrichment jobs expose TaskRun progress, partial failures,
  retry inputs, and deterministic resume boundaries.
- [ ] Eligible dividend/bonus-transfer and rights-allotment rows persist as
  stable `market_daily_event:*` citations; live/mock/error/empty rows remain
  non-citable.
- [ ] AI Research exposes universe freshness/coverage, profile criteria,
  shortlist results, and diagnostics in English and Chinese.
- [ ] Evidence Center exposes corporate-action import counts, citations, and
  sanitized diagnostics in English and Chinese.
- [ ] The AI Research surface can discover candidates outside watchlist/followed
  symbols and explain a deterministic shortlist using only its supplied stored
  citations and coverage diagnostics.
- [ ] Existing watchlist, ingestion, market-daily evidence, citation consumers,
  and explicit-symbol selection remain backward compatible.
- [ ] Backend, frontend, type, lint, migration/schema if needed, full tests, and
  Trellis validation pass.
- [ ] Runbooks/specs document provider, completeness, persistence, attribution,
  failure, scaling, and no-trading boundaries.

## Out of Scope

- Early-session/late-session capital-grab data until a reviewed provider exists.
- Live provider fan-out during AI selection.
- Claiming every A-share has complete fundamentals, technical, news, and event
  evidence immediately after universe discovery.
- Portfolio tax calculations, adjusted-price recalculation, production
  backtesting, paper trading, broker integration, and automatic trading.
- InStock database, scheduler, proxy/Cookie, Tornado UI, or trade runtime import.

## Resolved Decisions

- The default AI candidate universe must not be limited to the active watchlist.
- Build a provider-backed A-share universe and retain watchlist-only screening
  as an optional narrow mode.
- Keep AI selection local-evidence-only; provider collection is handled by
  explicit refresh/enrichment jobs.
- Use a breadth-first rollout: all successfully synced A-share instruments may
  enter the candidate universe, evidence gaps remain explicit, and enrichment
  proceeds in bounded batches. A symbol can be evaluated only against criteria
  supported by its stored evidence, and incomplete coverage must never be
  described as complete analysis.
- Use deterministic full-universe screening to produce a bounded shortlist,
  then let AI compare and explain only that supplied shortlist. AI may not add
  symbols, change reproducible ranking, or treat missing evidence as verified
  facts.
- Use named, transparent selection profiles with visible, editable parameters
  for the first release. Natural-language-to-criteria translation is deferred
  until it has an auditable normalization and ambiguity contract.
