# Acceptance Report

## Outcome

The personal research workflow is accepted. The protected homepage source is
unchanged, the shared shell now exposes five primary destinations, retained
research routes remain addressable, and mutation-heavy maintenance controls are
closed by default without hiding independently loaded evidence.

## Automated Verification

- Web: `npm run test:web` -> 86 files, 278 tests passed.
- TypeScript: `npx tsc --noEmit -p apps/web/tsconfig.json` -> passed.
- Backend: `pytest tests` -> 850 tests passed.
- Ruff: all changed Python implementation/test files passed.
- mypy: the four changed Python production files passed.
- English and Chinese message catalogs parsed as JSON.
- `git diff --check` passed; only the existing LF-to-CRLF notices were emitted.
- Secret-pattern scan found no `sk-*` values in tracked diffs or task/new files.

Automated tests use fake LLM providers and do not make paid network requests.

## Runtime Verification

- Web `3000` returned HTTP 200.
- API `8000` returned `status=ok` with runtime `local / stock`.
- PostgreSQL returned `SELECT 1`; Redis returned `PONG`.
- Celery worker `stock-local` returned `pong`; the Beat process remained active.
- The API process was restarted once to load the non-hot-reloaded pagination and
  LLM endpoint code. Web, database, Worker, and Beat stayed running.
- `GET /instruments?limit=25&offset=0` returned 25 of 5,532 rows with
  `has_more=true`; omitting `limit` still returned all 5,532 rows.

## Browser Verification

- Viewports: 375x844, 390x844, 768x900, and 1440x1000.
- Light and dark themes were checked.
- No page-level horizontal overflow or console errors were observed on the
  changed core routes.
- Page 2 of Instruments used URL state, returned 25 rows, and began with symbol
  `000035`.
- AI Research kept shortlist, discovery, cited assistant, and outcomes visible;
  universe status and evidence backfill operations were closed.
- Instrument detail kept the cited assistant, technicals, fundamentals, and
  news before a closed advanced-market-data section.
- Empty Watchlist exposed AI Research and Instruments recovery links; manual
  entry and alert editing were closed.
- Evidence kept stored-evidence and official-disclosure read surfaces outside
  closed refresh/import/ingestion sections.
- Settings showed one Save command, DeepSeek key-only configuration, custom-only
  base/model fields, and a separate non-submit connection-test button.
- Portfolio, Reports, Alerts, and Task Runs remained directly addressable with
  HTTP 200 responses.

Detailed evidence: `artifacts/acceptance/browser-acceptance.json` plus the four
acceptance screenshots.

## Authorized Local Cleanup

Only `TEST:US` and `CN_SHANGHAI_COMPOSITE:CN` were soft-deactivated through the
existing exact-identity API. Both UUID rows remain present, the single watchlist
remains present, active count changed from 2 to 0, and no non-target row existed
or changed. The empty public watchlist did not reseed.

Evidence: `artifacts/acceptance/watchlist-cleanup.json`.

## Manual LLM Acceptance

One browser click called the saved DeepSeek configuration once. It succeeded as
`openai / deepseek-chat` with 906 ms measured latency. There was no retry. The
answer, prompt, key, authorization data, upstream body, and stack trace were not
recorded or rendered.

Evidence: `artifacts/acceptance/llm-connection-test.json` and
`artifacts/acceptance/settings-llm-connected-1440x1000.png`.
