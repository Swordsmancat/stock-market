# Design: AI Macro Stock Research Desk

## Boundary

This task enhances existing research surfaces. It does not create a new trading terminal, a new portfolio system, a persistent digest store, or a basket-level AI comparison engine.

The core change is:

```text
Stored macro observations
  -> citable macro context
  -> instrument assistant prompt
  -> evidence-bound answer with validated market_indicator citations

Official source status
  -> AI Research Desk source guidance
  -> next actions and gaps
  -> never cited as evidence
```

## Existing Architecture

- `apps/web/app/[locale]/ai-research/page.tsx`
  - Server component.
  - Already fetches watchlist, market overview, and recommendation payloads.
  - Should add optional official source status fetch.
- `apps/web/components/ai-research-desk.tsx`
  - Client component.
  - Owns selected-symbol basket, active symbol, macro cards, source gap panel, and `MarketAssistantCard`.
  - Should receive source readiness payload and render it as guidance.
- `packages/services/market_assistant.py`
  - Builds assistant context and citations.
  - Should add macro indicator evidence construction.
- `packages/ai/market_assistant.py`
  - Builds LLM prompt and deterministic fallback.
  - Should expose macro context in prompt and fallback summaries.
- `packages/services/market_dashboard.py`
  - Already has macro citation formatting for dashboard brief.
  - Should share or mirror the same `market_indicator:<code>:<as_of>` citation semantics.
- `packages/services/market_indicators.py`
  - Owns indicator definitions, observations, seed import, and `get_macro_indicator_payloads`.
  - Should remain the source of stored macro indicator payloads.

## Backend Design

### Macro Evidence Builder

Add a helper in `packages/services/market_assistant.py`, likely named `_build_macro_indicator_context`, with this contract:

Input:

- `session: Session | None`
- `diagnostics: list[dict[str, object]]`

Output:

- `macro_summary: str`
- `macro_evidence: list[MarketAssistantResearchEvidence]`

Behavior:

- If `session` is missing, add an info diagnostic and return an unavailable summary.
- Call `get_macro_indicator_payloads(session=session)`.
- Treat an item as citable only when:
  - `status == "ok"` or value/as-of/source are present;
  - `value` is not null;
  - `as_of` is present;
  - `source` is present.
- Build citation IDs as `market_indicator:<code>:<as_of>`.
- Use `source="market_indicators"` and `source_type="macro_indicator"`.
- Carry code, region, category, unit, and components in metadata.
- Add non-citable items to diagnostics only; do not emit placeholder citations.

### Citation Semantics

Preferred low-risk implementation:

- Keep dashboard behavior unchanged.
- Either extract dashboard indicator citation formatting into a tiny shared helper or add an assistant-local builder that matches the existing dashboard citation shape.
- Do not import private dashboard functions from `market_assistant.py`.

Allowed citation validation:

- Add `market_indicator:` to `ASSISTANT_CITATION_ID_PREFIXES`.
- Keep unknown citation fallback behavior unchanged.
- Add a test where the LLM returns `[market_indicator:not-present:2026-01-01]` and the assistant falls back.

### Prompt Context

Add `macro_summary` to `MarketAssistantPromptContext` with a default value so existing tests that instantiate the dataclass remain compatible.

Prompt should include a distinct line such as:

```text
Macro context: <macro_summary>
```

Fallback answer should include macro context in the evidence section. If no macro context is available, it should say so rather than inventing data.

### Ranking

Macro citations should rank after price bars and before lower-priority narrative evidence:

```text
bars -> technical indicators -> macro indicators -> fundamentals -> news -> generated reports -> source notes
```

The exact priority number can be adjusted during implementation, but macro evidence should be visible in the first page of citations.

## Frontend Design

### Page Fetch

Add an optional load in `apps/web/app/[locale]/ai-research/page.tsx`:

```text
/market-indicators/official-sources/status
```

Failure behavior:

- Return an empty readiness payload or a single warning diagnostic.
- Do not block rendering the research desk.

### Component Contract

Add source-readiness props to `AiResearchDesk`:

- source status items, or a normalized minimal type containing:
  - `id`
  - `label`
  - `status`
  - `provider`
  - `indicator_codes`
  - `missing_indicator_codes`
  - `next_action`
  - `latest_as_of`
  - `collection_url`
  - `docs_url`
  - `diagnostics`

Keep the type permissive enough to match the existing backend payload without making the client depend on every field.

### UI Placement

Render source readiness in the right-side research context column near `MacroContextPanel` and `SourceGapPanel`.

Recommended shape:

- Existing macro cards stay focused on citable local observations.
- A small source readiness panel lists FRED / World Bank readiness and next actions.
- Source readiness badges should use labels such as `Ready`, `Needs refresh`, `Missing observations`, or the raw status when no mapping exists.
- Panel copy must make clear these are collection/readiness guides, not AI citations.

### Starter Question

Update `assistantInitialQuestion` construction to include:

- active symbol;
- active signal title;
- top citable macro context;
- concise missing source guidance if source statuses report missing macro indicator coverage.

Keep the no-trading-instruction phrase.

## Data Boundaries

| Data | Can AI cite? | Why |
|---|---:|---|
| Stored `MarketIndicatorObservation` with value/as-of/source | Yes | Audited local observation. |
| Market overview macro item without value/as-of/source | No | Data gap only. |
| Official source status item | No | Operational readiness, not evidence. |
| Source URL / collection link | No | Not reviewed/imported as evidence. |
| Seed template | No | Template only. |
| Reviewed/citable research source note | Yes | Existing source-note citation flow. |

## Compatibility

- Existing `/dashboard/market-overview` payload fields remain unchanged.
- Existing assistant API response fields remain unchanged except for additive `context.macro_summary` and additional citations.
- Frontend new props should be optional so older test fixtures can still render.
- Existing homepage and Evidence Center source readiness behavior should not be altered.

## Risks

- Duplicating macro citation formatting can drift from dashboard citations. Prefer a shared helper if the implementation remains small.
- Adding `market_indicator:` to the allowed prefix without adding evidence tests could weaken citation validation. Tests must cover valid and invalid IDs.
- Source readiness text could look like AI evidence. The UI must separate guidance from local evidence.
- Prompt context can grow too large if all indicators are included. Limit the summarized macro items and prioritize favorites / Buffett / rates / inflation / liquidity.

## Rollback

- Backend rollback: remove macro context builder, remove `market_indicator:` from assistant allowed prefixes, and remove `macro_summary` prompt line.
- Frontend rollback: remove source status fetch and readiness panel props.
- No migration or persistent data rollback is required.
