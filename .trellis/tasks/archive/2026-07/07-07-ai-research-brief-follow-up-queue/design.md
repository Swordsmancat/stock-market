# AI Research Brief and Follow-up Queue Design

## Architecture

This task adds a derived research-action layer. It does not add a new database table, document corpus, scraping pipeline, or assistant execution workflow.

Primary layers:

- Backend queue service: add a pure derivation helper, likely `packages/services/research_follow_up_queue.py`, that builds queue items from serialized Source Notebook notes and the existing information-source readiness payload.
- Dashboard aggregation: add an optional `research_follow_up_queue` field to `GET /dashboard/market-overview` so Evidence Center can reuse the market overview payload it already fetches.
- Source Notebook service: keep existing note creation/listing/citation behavior. Do not weaken `reviewed + is_citable` citation gating.
- Evidence Center page: render the queue after `ResearchSourceNotebook` and before the AI evidence summary so collected notes lead directly into next research actions.
- Frontend component: add a focused queue panel/component for summary counts, categorized items, metadata chips, and safety language.
- Localization/tests: update English and Chinese strings together, then extend existing service/API/page tests.

## Payload Contract

Additive dashboard payload field:

```json
{
  "research_follow_up_queue": {
    "status": "ok",
    "generated_at": "2026-07-07T00:00:00+00:00",
    "summary": {
      "total": 0,
      "source_review": 0,
      "seed_prep": 0,
      "ai_summary_question": 0,
      "source_gap": 0,
      "citable": 0,
      "collection_only": 0,
      "guidance_only": 0
    },
    "items": [],
    "safety": {
      "not_investment_advice": true,
      "citations_require_reviewed_citable_notes": true,
      "no_automated_trading": true
    }
  }
}
```

Queue item shape:

```json
{
  "id": "source_note_ai_follow_up:<note-id>",
  "kind": "ai_summary_question",
  "priority": "high",
  "title": "Review Buffett Indicator source note",
  "prompt": "Summarize how this source supports the US Buffett Indicator calculation.",
  "next_action": "Use this reviewed note as a candidate source for a future AI summary.",
  "citation_policy": "citable",
  "citation_id": "research_source_note:<note-id>",
  "note_id": "<note-id>",
  "note_title": "Buffett Indicator GDP source",
  "source_name": "World Bank",
  "source_type": "valuation_component",
  "source_id": "buffett_manual_valuation_components",
  "source_label": "Buffett Indicator manual valuation components",
  "source_category": "valuation",
  "source_status": "needs_manual_seed",
  "target_indicator_codes": ["buffett_indicator_us"],
  "component_role": "gdp",
  "completeness_status": "complete",
  "as_of": "2026-01-02",
  "retrieved_at": "2026-01-03T00:00:00+00:00"
}
```

Allowed `kind` values for the MVP:

- `source_review`
- `seed_prep`
- `ai_summary_question`
- `source_gap`
- `research_note`

Allowed `citation_policy` values:

- `citable`: only when a Source Notebook note is `reviewed` and `is_citable` and exposes an existing `research_source_note:<id>` citation ID.
- `collection_only`: notebook-derived item that is useful for collection/review but not AI-citable yet.
- `guidance_only`: source-readiness or seed-template item that is not local evidence.

## Derivation Rules

1. Source Notebook `ai_follow_up`
   - Create `ai_summary_question` items from non-empty `ai_follow_up`.
   - Attach `citation_id` only when the note already has an allowed citation ID.
   - For draft/non-citable notes, set `citation_policy="collection_only"`.

2. Source Notebook completeness
   - Create `source_review` items for incomplete linked notes or notes with missing checklist fields.
   - Preserve source target, target indicator codes, component role, and completeness status.
   - Do not make completeness a citation gate; it is advisory.

3. Seed preparation
   - Create `seed_prep` items for source-readiness entries with seed templates or `needs_manual_seed` status.
   - If complete linked notes exist for that source, mention them as preparation context.
   - Do not import observations or imply templates are evidence.

4. Source-readiness gaps
   - Create `source_gap` items for `needs_adapter`, `needs_manual_seed`, `no_data`, and `future` statuses.
   - Use `next_action`, `collection_note`, `citation_policy`, status, target coverage, and seed-template target codes as metadata.
   - Source gaps never expose citation IDs.

5. Stable ordering
   - Sort deterministically by priority, kind, source label/title, and stable ID.
   - Cap the visible queue to a bounded limit, such as 20 items, while preserving summary counts.

## Data Flow

1. `get_market_overview_payload(...)` already builds `information_sources` and `dashboard_brief`.
2. The dashboard service fetches recent Source Notebook notes or accepts an existing note payload.
3. The queue helper combines notes plus source-readiness items into `research_follow_up_queue`.
4. The `/dashboard/market-overview` API returns the additive queue field.
5. Evidence Center reads `payload.research_follow_up_queue` and renders the queue panel.
6. Saving a Source Notebook note already clears the market overview cache, so queue changes become visible after refresh.

## Citation and Safety Boundaries

- Queue items are workflow prompts, not factual evidence by default.
- Only reviewed/citable Source Notebook rows may expose `research_source_note:<id>`.
- Source-readiness IDs, collection links, seed templates, template rows, and draft notebook rows must never appear as citation IDs.
- The queue must not call an LLM, validate LLM output, or generate investment recommendations in this MVP.
- Copy must preserve no-investment-advice, no buy/sell/hold, no target-price, no position-sizing, and no execution boundaries.

## Frontend Design

The queue panel should be dense and operational:

- Header with status badge and summary counts.
- Segmented or chip-like category filters only if the item count makes filtering useful; otherwise render grouped sections.
- Each item shows kind, priority, title, prompt/next action, citation policy, source/readiness metadata, target indicator codes, completeness, dates, and citation ID when allowed.
- Empty state should say that no follow-up actions are available from current local evidence.
- The panel should appear after the Source Notebook and before the AI evidence summary.

## Compatibility

- The dashboard payload change is additive.
- Existing clients can ignore `research_follow_up_queue`.
- No database migration is required.
- Existing Source Notebook and dashboard citation contracts remain unchanged.
- Browser file upload remains client-side text prefill only.

## Rollback

- Remove the queue field from the dashboard payload and queue panel rendering.
- No persisted data needs rollback because queue items are derived.
- Existing Source Notebook rows, source-readiness entries, dashboard brief citations, and assistant citations remain valid.
