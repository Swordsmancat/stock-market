# AI stock analysis and recommendation entry implementation plan

## Pre-Implementation Checks

- Confirm task is reviewed and approved, then run `python ./.trellis/scripts/task.py start .trellis/tasks/07-07-ai-stock-analysis-recommendation-entry`.
- Load `trellis-before-dev` before editing application code.
- Read relevant specs before touching files:
  - `.trellis/spec/frontend/index.md`
  - `.trellis/spec/frontend/component-guidelines.md`
  - `.trellis/spec/frontend/type-safety.md`
  - `.trellis/spec/frontend/quality-guidelines.md`
  - `.trellis/spec/guides/cross-layer-thinking-guide.md`
  - `.trellis/spec/backend/assistant-research-citation-contract.md` only if backend assistant behavior changes
- Inspect existing dirty files before editing:
  - `apps/web/components/navigation-items.ts`
  - `apps/web/components/navigation-items.test.ts`
  - `packages/services/market_assistant.py`
  - `tests/ai/test_market_assistant.py`

## Implementation Checklist

- [x] Add localized navigation/message keys for AI Research Desk in English and Chinese.
- [x] Add `/[locale]/ai-research` page that fetches watchlist, market overview, and recommendation context using existing APIs.
- [x] Add a client desk component for symbol selection, manual symbol entry, active symbol state, and assistant request submission.
- [x] Reuse existing `askMarketAssistant` and assistant response/citation/safety rendering where practical.
- [x] Surface deterministic recommendation signals as research inputs with explicit non-advice wording.
- [x] Surface macro context and source gaps from market overview, including Buffett Indicator rows when present.
- [x] Add navigation and/or dashboard affordance to the new desk.
- [x] Fix or avoid hardcoded/mojibake visible strings in any reused recommendation UI touched by this slice.
- [x] Add tests for route rendering, navigation coverage, symbol selection, assistant request behavior, macro/source gap rendering, and safety copy.
- [x] Update docs/manual only if the new user workflow needs a durable user guide entry.

Docs note: no separate manual page was added in this slice because the new workflow is reachable from navigation and includes localized research-only safety guidance inline.

## Validation Commands

Run focused checks first:

```bash
npx vitest run "apps/web/app/[locale]/ai-research/page.test.tsx" "apps/web/components/navigation-items.test.ts" "apps/web/components/market-assistant-card.test.tsx" --reporter=dot
```

Status: passed.

Run broader frontend checks:

```bash
npx tsc -p apps/web/tsconfig.json --noEmit
npm run test:web -- --reporter=dot
```

Status: passed.

Run backend checks only if backend assistant/recommendation contracts change:

```bash
python -m pytest tests/ai/test_market_assistant.py tests/api/test_recommendations_api.py -q
```

Always finish with:

```bash
git diff --check
python ./.trellis/scripts/task.py validate .trellis/tasks/07-07-ai-stock-analysis-recommendation-entry
```

Status: passed.

## Risk Notes

- Navigation tests assert exact hrefs and must be updated deliberately.
- `SmartRecommendations` currently has hardcoded visible copy and mojibake in the working tree; reuse should include localization cleanup or a desk-specific replacement.
- Multi-symbol LLM comparison is intentionally deferred; first slice analyzes one active symbol at a time.
- The feature must preserve the assistant citation boundary and avoid treating source-readiness or seed guidance as citable evidence.
