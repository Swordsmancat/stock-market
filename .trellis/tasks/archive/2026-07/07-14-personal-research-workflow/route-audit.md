# Personal-use route audit

Date: 2026-07-14 (Asia/Shanghai)

## Method

- Inspected every localized Next page and the shared navigation components.
- Loaded all ten top-level routes in the running local app at 1440x1000 and
  390x844 without submitting forms, starting jobs, or calling paid LLM paths.
- Checked visible headings, controls, data/empty states, console errors, and
  horizontal overflow.
- Queried selected read-only APIs to distinguish real data from demo/degraded
  data.

## Shared shell

- `apps/web/components/navigation-items.ts` defines one flat list used by both
  desktop and mobile: home, instruments, AI research, evidence, watchlist,
  portfolios, reports, alerts, task runs, and settings.
- `apps/web/components/mobile-navigation.tsx` exposes all ten items in a
  horizontally scrolling bottom bar.
- `apps/web/components/top-nav-bar.tsx` includes a fake User/email menu and a
  disabled logout action even though this is a single-user installation.
- Global stock search is useful and already opens instrument detail directly.

## Route matrix

| Route | Runtime | Personal classification | Main finding |
|---|---|---|---|
| `/zh` | renders | core, needs replacement focus | 34 no-data mentions; mock US hot sectors and provider status dominate; no daily shortlist/watchlist summary |
| `/zh/instruments` | renders | core, needs simplification | backend returns the full universe; UI shows the first 25 and fans out latest/bar requests instead of query/pagination |
| `/zh/instruments/[symbol]` | renders | strongest core | cited assistant and stored evidence work, but unsupported depth/trades/fund-flow appear before useful technical/fundamental evidence |
| `/zh/ai-research` | renders | core plus operations | valid daily shortlist is present; page is very dense and mixes discovery with coverage/backfill controls |
| `/zh/watchlist` | renders | core concept | current rows are `TEST` and `CN_SHANGHAI_COMPOSITE`; manual symbol/market and alert maintenance dominate onboarding |
| `/zh/evidence` | renders | supporting plus maintenance | 48 no-data mentions, zero citable macro observations, and many ingestion controls; one market-overview failure can hide independent evidence |
| `/zh/reports` | renders | contextual | only historical AAPL examples; generation defaults to AAPL; better reached from stock detail |
| `/zh/reports/[reportId]` | renders | contextual detail | useful only from a stock/report link |
| `/zh/alerts` | renders | contextual | empty until watchlist rules exist; notification bell/watchlist can own access |
| `/zh/portfolios` | renders | low value for current scope | demo USD/AAPL data and MVP-skeleton allocation text; retain route/data but hide from primary nav |
| `/zh/task-runs` | renders | maintenance | large raw task inputs/results and retry controls; not a daily research destination |
| `/zh/task-runs/[taskRunId]` | renders | maintenance detail | contextual diagnostics only |
| `/zh/settings` | renders | supporting | functional but combines basic LLM/data choice with news keys, index/macro preferences, and provider internals |

No tested route had a persistent console error or horizontal overflow. Page
tests exist for all 13 routes, but their mocked upstreams are not live-use proof.

## Read-only data checks

- `/sectors/hot?limit=5`: `status=degraded`, `data_mode=mock`, provider and
  effective provider `static_fixture`; first leader was `TSLA`.
- `/watchlist`: two placeholder rows, `TEST` and
  `CN_SHANGHAI_COMPOSITE`.
- `/dashboard/market-overview`: indices exist, but the inspected macro/valuation
  collection had no dashboard citations.
- Live DeepSeek stock discovery and the market assistant already passed in the
  previous task; the AI core is available and should be promoted instead of
  adding another broad feature area.

## Recommended minimum information architecture

User decision after this audit: preserve the homepage information, composition,
and behavior. The homepage findings above remain an audit snapshot and are not
implementation scope for this task.

Primary:

1. Home: preserve the current page.
2. Research: shortlist/discovery first; operational coverage controls advanced.
3. Stocks: global search plus query/paginated browsing and focused detail.
4. Watchlist: saved candidates and compact alerts.

Utility:

- Settings: essential presets first, manual LLM test, advanced provider/news
  configuration collapsed.
- Data & maintenance: Evidence and Task Runs behind a secondary entry.

Contextual only:

- Reports from stock detail.
- Alert history from watchlist/notification bell.
- Task detail from a diagnostic link.
- Portfolio route retained but hidden from primary navigation.

## Highest-value implementation order

1. Reduce/group navigation and remove fake account UI.
2. Reorder AI Research and stock detail around the cited personal workflow.
3. Simplify watchlist defaults and stock browsing; isolate maintenance tools.
4. Split Settings into essential/advanced and add a manual sanitized LLM test.
