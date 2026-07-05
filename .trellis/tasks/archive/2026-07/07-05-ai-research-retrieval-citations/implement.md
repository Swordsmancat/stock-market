# AI Research Retrieval and Citation Enhancement Implementation Plan

## Slice 1: Contract and Citation Metadata

1. Read current assistant service, AI prompt, API tests, and frontend types before editing.
2. Extend `MarketAssistantCitation` with optional metadata fields while preserving existing constructor compatibility.
3. Extend frontend `MarketAssistantCitation` and `MarketAssistantDiagnostic` types with optional fields.
4. Add or update serialization helpers so optional fields appear only when safely available.
5. Add focused tests proving old minimal citation payloads still work.

## Slice 1A: Unified Research Evidence Shape

1. Add a service-local research evidence representation that can cover both structured sources and document-like sources.
2. Include future-compatible fields for announcements, filings, transcripts, and research notes without adding real external providers.
3. Keep the abstraction internal to the assistant path unless an existing repository service already provides a clean public boundary.
4. Add tests proving document-like evidence can become citation metadata without claiming unavailable production sources exist.

## Slice 2: Evidence Builders for Existing Sources

1. Keep daily bars as the required core evidence source.
2. Add richer citation metadata to the existing `bars_1d:{symbol}:{as_of}` citation.
3. Add technical-indicator citation generation when stored indicators exist.
4. Add fundamentals citation generation when a snapshot exists.
5. Add news citation generation, preferring article-level URL/title/source/published time where available.
6. Add generated-report citation generation if the existing report service can be reused without broad refactoring, using the document-like evidence shape.
7. For each missing optional source, emit sanitized diagnostics instead of fabricated evidence.

## Slice 3: Prompt and Citation Validation

1. Update assistant prompt instructions to list available citation IDs and require inline citation IDs for factual claims.
2. Add a small validator that extracts citation-like bracketed IDs from LLM output.
3. Compare extracted IDs against known citations.
4. Add `CITATION_UNKNOWN_ID` diagnostics for unknown IDs.
5. Prefer deterministic fallback or degraded output when citation validation fails.
6. Ensure no-data still skips LLM generation when daily bars are unavailable.

## Slice 4: Frontend Rendering

1. Render citation URLs as safe links when present.
2. Display compact metadata such as source type, as-of date, provider, and excerpt when present.
3. Display diagnostic severity and code when present.
4. Preserve old rendering for payloads without enriched fields.
5. Do not add a broad markdown renderer in this slice.

## Slice 5: Documentation and Trellis Records

1. Update assistant-related runbook or user-guide text if the public behavior changes.
2. Record completed validation commands in this file.
3. Record remaining professional gaps: filings/transcripts, vector search, persistent sessions, watchlist monitoring, and notebook workflows.

## Validation Commands

Backend focused validation:

```bash
python -m pytest tests/ai/test_market_assistant.py tests/api/test_assistant_api.py -q
```

Frontend focused validation:

```bash
npx vitest run "apps/web/app/api/assistant/market/route.test.ts" "apps/web/components/market-assistant-card.test.tsx" "apps/web/app/[locale]/instruments/[symbol]/page.test.tsx" --reporter=dot
```

Broader frontend validation when frontend code changes:

```bash
npm run test:web
```

Whitespace check:

```bash
git diff --check -- "packages/ai/market_assistant.py" "packages/services/market_assistant.py" "apps/api/routers/assistant.py" "tests/ai/test_market_assistant.py" "tests/api/test_assistant_api.py" "apps/web/lib/market-assistant.ts" "apps/web/components/market-assistant-card.tsx" "apps/web/app/api/assistant/market/route.test.ts" "apps/web/components/market-assistant-card.test.tsx" "apps/web/app/[locale]/instruments/[symbol]/page.test.tsx"
```

## Risk Controls

- Do not rebuild the assistant endpoint or frontend card from scratch.
- Do not introduce new production ingestion for filings, announcements, transcripts, PDFs, or paid research feeds in this task.
- Do not claim future-compatible document evidence scaffolding is a live filings/transcripts source.
- Do not introduce embeddings/vector infrastructure in this task.
- Do not present optional missing evidence as failure of core daily-bar analysis unless it blocks safe answer generation.
- Do not leak secrets, prompt internals, raw stack traces, or raw provider payloads in diagnostics.
- Do not weaken direct-trading-advice refusal or no-fabrication rules.
- Do not commit unrelated dirty files.

## Review Gate Before Implementation

Implementation starts under the user-selected expanded scope:

> Use a medium-scope unified research evidence/citation layer. Connect existing sources first, and keep real filings/transcripts/vector search/multi-turn notebooks as follow-up tasks.

## Completed Validation

- Backend focused validation passed after adding unified research evidence/citation metadata and LLM citation validation: `python -m pytest tests/ai/test_market_assistant.py tests/api/test_assistant_api.py -q` -> `11 passed`.
- Frontend assistant focused validation passed after rendering citation links, compact citation metadata, and diagnostic severity/code: `npx vitest run "apps/web/app/api/assistant/market/route.test.ts" "apps/web/components/market-assistant-card.test.tsx" "apps/web/app/[locale]/instruments/[symbol]/page.test.tsx" --reporter=dot` -> `3 passed`, `11 passed`.
- Full web test suite passed after frontend assistant changes: `npm run test:web` -> `29 passed`, `98 passed`.
- Whitespace check passed for assistant-related files: `git diff --check -- "packages/ai/market_assistant.py" "packages/services/market_assistant.py" "apps/api/routers/assistant.py" "tests/ai/test_market_assistant.py" "tests/api/test_assistant_api.py" "apps/web/lib/market-assistant.ts" "apps/web/components/market-assistant-card.tsx" "apps/web/app/api/assistant/market/route.test.ts" "apps/web/components/market-assistant-card.test.tsx" "apps/web/app/[locale]/instruments/[symbol]/page.test.tsx"` -> exit code `0` with CRLF conversion warnings only.
- Documentation updated in `docs/runbooks/developer-maintenance.md` and `docs/manual/user-guide.md` to describe the research-citation MVP, optional citation metadata, diagnostic severity/code, LLM citation validation, and remaining professional gaps.
- 2026-07-05 rerun: `python -m pytest tests/ai/test_market_assistant.py tests/api/test_assistant_api.py -q` -> `11 passed`.
- 2026-07-05 rerun: `npx vitest run "apps/web/app/api/assistant/market/route.test.ts" "apps/web/components/market-assistant-card.test.tsx" "apps/web/app/[locale]/instruments/[symbol]/page.test.tsx" --reporter=dot` -> `3 passed`, `11 tests passed`.
- 2026-07-05 rerun: `python -m pytest -q` -> `286 passed`, with existing Redis `setex` deprecation warnings only.
- 2026-07-05 rerun: `npm run test:web` -> `29 passed`, `101 tests passed`.
- 2026-07-05 doc sync: `README.md` Phase 3 AI assistant status now reflects the research-citation MVP and its remaining professional gaps.
