# AI Market Assistant Implementation Plan

## Slice 1: Backend Assistant Contract

1. Add `packages/ai/market_assistant.py` with prompt construction, deterministic fallback answer generation, citations formatting, and safety disclaimer constants.
2. Add `packages/services/market_assistant.py` to aggregate daily bars, indicators, fundamentals, and news into a traceable context.
3. Add `apps/api/routers/assistant.py` exposing `POST /assistant/market`.
4. Include the assistant router in `apps/api/main.py`.
5. Add backend tests for success, no daily bars, optional context missing, LLM fallback, and direct-advice question safety.

## Slice 2: Frontend Assistant Proxy and UI

1. Add `apps/web/lib/market-assistant.ts` request/response types and fetch helper.
2. Add `apps/web/app/api/assistant/market/route.ts` as a thin backend proxy.
3. Add `apps/web/components/market-assistant-card.tsx` with quick prompts, text input, loading/error/no-data/degraded/success states, citations, diagnostics, and safety disclaimer.
4. Insert the assistant card in `apps/web/components/instrument-detail-client.tsx` after summary cards and before market-depth/intraday sections.
5. Add English and Chinese `MarketAssistant` i18n strings.

## Slice 3: Tests and Documentation

1. Add Vitest route proxy coverage for `/api/assistant/market`.
2. Add component tests for `MarketAssistantCard`.
3. Update instrument detail page tests to assert the assistant entry point is present.
4. Update user/developer manuals and README feature status from planned to MVP available after tests pass.

## Validation

- `python -m pytest tests/ai/test_market_assistant.py tests/api/test_assistant_api.py`
- `npx vitest run "apps/web/app/api/assistant/market/route.test.ts" "apps/web/components/market-assistant-card.test.tsx" "apps/web/app/[locale]/instruments/[symbol]/page.test.tsx"`
- `npm run test:web`
- `git diff --check`

Completed focused validation:

- `python -m pytest tests/ai/test_market_assistant.py tests/api/test_assistant_api.py`
- `npx vitest run "apps/web/app/api/assistant/market/route.test.ts" "apps/web/components/market-assistant-card.test.tsx" "apps/web/app/[locale]/instruments/[symbol]/page.test.tsx"`
- `npm run test:web`
- `git diff --check`

## Status

Implementation complete for MVP. Backend and frontend assistant contracts, UI, tests, and documentation are in place. Full web test validation and diff whitespace validation passed; the task is ready for archival.

## Risk Controls

- Do not expose the raw hidden prompt, API keys, or platform settings secrets.
- Do not use `MockLLMProvider` prompt echo as a user-facing assistant answer.
- Do not fabricate unavailable market data; return `no_data` or degraded diagnostics.
- Do not include unrelated `apps/web/app/api/recommendations/route.ts` line-ending noise in commits.
