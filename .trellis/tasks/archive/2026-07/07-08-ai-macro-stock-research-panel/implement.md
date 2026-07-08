# Implementation Plan

## Pre-Start Gate

- [x] User approves implementation after reviewing planning artifacts.
- [x] Run `python ./.trellis/scripts/task.py start .trellis/tasks/07-08-ai-macro-stock-research-panel`.
- [x] Load `trellis-before-dev`.
- [x] Read relevant backend and frontend spec index files before editing code.

## Ordered Checklist

### 1. Backend tests first

- [x] Add a test showing the assistant emits `market_indicator:*` citations when stored macro observations are available.
- [x] Add a test showing missing macro observations become diagnostics/gaps, not citations.
- [x] Add a test showing an LLM hallucinated `market_indicator:*` ID triggers citation-validation fallback.
- [x] Add or adjust prompt/fallback tests for the new macro summary line.

Likely file:

- `tests/ai/test_market_assistant.py`

### 2. Backend implementation

- [x] Add macro indicator context loading in `packages/services/market_assistant.py`.
- [x] Build macro `MarketAssistantResearchEvidence` entries from `get_macro_indicator_payloads`.
- [x] Add `market_indicator:` to assistant citation prefix validation.
- [x] Add `macro_summary` to response context.
- [x] Add `macro_summary` to `MarketAssistantPromptContext`, prompt construction, and deterministic fallback text.
- [x] Keep source readiness out of assistant citations.

Likely files:

- `packages/services/market_assistant.py`
- `packages/ai/market_assistant.py`
- Optionally a tiny shared citation helper if needed.

### 3. Frontend tests first

- [x] Add AI Research page fixture for `/market-indicators/official-sources/status`.
- [x] Assert source readiness / next action renders.
- [x] Assert endpoint failure still renders the desk.
- [x] Assert assistant starter question still submits research-only wording with macro context.

Likely file:

- `apps/web/app/[locale]/ai-research/page.test.tsx`

### 4. Frontend implementation

- [x] Add official source status fetch in `apps/web/app/[locale]/ai-research/page.tsx`.
- [x] Add source readiness prop types to `apps/web/components/ai-research-desk.tsx`.
- [x] Render a source readiness panel near macro/source-gap context.
- [x] Update starter question construction to include source guidance when present.
- [x] Add English and Chinese messages for any new labels.

Likely files:

- `apps/web/app/[locale]/ai-research/page.tsx`
- `apps/web/components/ai-research-desk.tsx`
- `apps/web/messages/en.json`
- `apps/web/messages/zh.json`

### 5. Focused validation

- [x] Run backend focused tests:

```powershell
pytest tests/ai/test_market_assistant.py
```

- [x] Run frontend focused test for AI Research page using the repo's existing web test command.
- [x] Run lint/type checks for touched frontend files if the repo exposes focused scripts.
- [x] Run any existing broader check that Trellis / repo guidelines require before commit.

### 6. Finish

- [x] Run `trellis-check` after implementation.
- [x] Update relevant spec only if implementation teaches a reusable contract.
- [ ] Commit the task changes.
- [ ] Archive the Trellis task after successful commit.

## Risky Areas

- `packages/ai/market_assistant.py` has many existing deterministic-answer assertions. Add defaults to `MarketAssistantPromptContext` to avoid breaking older tests.
- Citation validation must remain strict after adding `market_indicator:`.
- The frontend source readiness payload may have more fields than needed. Normalize lightly rather than overfitting the UI to every backend field.
- Existing `parseSymbols` behavior should not be changed in this task unless a test exposes a bug directly related to AI Research.

## Non-Goals During Implementation

- Do not add persistent digest/history storage.
- Do not add browser/local file upload.
- Do not add new official macro adapters.
- Do not implement basket-level AI summary in this slice.
- Do not add trading advice, target price, position sizing, or execution flows.
