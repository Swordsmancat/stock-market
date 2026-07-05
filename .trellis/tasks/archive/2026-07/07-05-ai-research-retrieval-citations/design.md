# AI Research Retrieval and Citation Enhancement Design

## Overview

This task extends the existing single-instrument AI market assistant instead of rebuilding it. The design keeps `POST /assistant/market` compatible while adding a unified research-evidence layer, richer citation metadata, safer citation validation, and compact frontend rendering improvements.

The MVP deliberately uses existing platform data first:

- daily bars and derived price context,
- stored technical indicators,
- fundamentals snapshots,
- news articles / news sentiment payloads,
- generated reports when available.

The expanded scope also introduces an internal shape for future document-like sources such as announcements, filings, transcripts, and research notes. Real external providers, paid feeds, embeddings, and persistent research notebooks remain follow-up work.

## Current Architecture

The current request path is:

```text
MarketAssistantCard
  -> apps/web/lib/market-assistant.ts
  -> apps/web/app/api/assistant/market/route.ts
  -> apps/api/routers/assistant.py
  -> packages/services/market_assistant.py
  -> packages/ai/market_assistant.py
```

The existing backend service already gathers daily bars, indicators, fundamentals, and news summaries. The current weakness is not the absence of source data, but that source evidence is mostly collapsed into summary strings and only daily bars are consistently represented as citation objects.

## Data Contracts

### Citation Contract

Keep existing required fields:

```text
id: string
label: string
source: string
url?: string | null
```

Add optional backward-compatible fields:

```text
source_type?: string | null
as_of?: string | null
provider?: string | null
retrieved_at?: string | null
excerpt?: string | null
metadata?: dict / object
```

Recommended `source_type` values for this MVP:

- `bars`
- `technical_indicator`
- `fundamental`
- `news`
- `generated_report`

Stable ID examples:

```text
bars_1d:AAPL:2026-07-02
technical_indicators:AAPL:2026-07-02
fundamentals:AAPL:2026-07-02
news:AAPL:2026-07-02:<stable-url-or-title-hash>
generated_report:123
```

### Diagnostic Contract

Keep existing required fields:

```text
source: string
status: string
message: string
```

Add optional backward-compatible fields:

```text
severity?: "info" | "warning" | "error"
code?: string
citation_id?: string | null
```

Recommended diagnostic codes:

- `SOURCE_NO_DATA`
- `SOURCE_UNAVAILABLE`
- `SOURCE_OMITTED`
- `SOURCE_STALE`
- `CITATION_UNKNOWN_ID`
- `CITATION_NOT_USED`
- `FALLBACK_USED`

Diagnostics must remain sanitized. They may expose a safe exception class name when useful, but must not include secrets, prompt internals, API keys, raw provider payloads, or stack traces.

## Backend Design

### Evidence Layer

Introduce a small internal evidence representation in `packages/services/market_assistant.py` or a nearby helper module if the service becomes too large:

```python
@dataclass(frozen=True)
class MarketAssistantEvidenceItem:
    citation: MarketAssistantCitation
    summary: str
    priority: int
```

The expanded version should be able to represent both structured evidence and document-like evidence. If helpful, add fields such as `source_type`, `title`, `published_at`, `as_of`, `url`, and `metadata`, but keep the object internal to the assistant path for this slice. It does not require a vector index or public `/research/search` endpoint.

### Future Document-Like Evidence Shape

Document-like evidence should map cleanly into the same citation contract:

```text
source_type: announcement | filing | transcript | research_note | generated_report | news
title: human-readable document title
excerpt: short safe snippet or summary
url: optional source URL
as_of / published_at: source date
provider/source: source system or vendor
metadata: small sanitized fields only
```

For this task, existing news and generated reports should exercise this shape. Announcements, filings, transcripts, and external research can be represented in tests or documented extension points, but should not be presented as live production sources unless real repository support already exists.

### Source Builders

Source-specific builders should keep the current service behavior but emit citations whenever usable evidence exists:

1. Price builder
   - Continue deriving latest close, period change, and price summary from daily bars.
   - Continue producing `bars_1d:{symbol}:{as_of}` citation.
   - Add optional citation metadata such as `source_type="bars"`, `as_of`, and provider/source when available.

2. Technical indicator builder
   - Use the existing stored indicators payload.
   - If latest indicator values exist, create one citation for the indicator snapshot.
   - If absent, produce a non-blocking diagnostic.

3. Fundamental builder
   - Use the existing fundamentals snapshot service.
   - If a snapshot exists, create one citation for the snapshot and include compact metric/source metadata.
   - If absent or unavailable, produce a diagnostic.

4. News builder
   - Use existing news payloads or articles exposed by the news service.
   - Prefer article-level citations with title, source, published time, URL, and short excerpt where available.
   - If only aggregate sentiment is available, produce a source-level citation and a diagnostic noting limited granularity.

5. Generated report builder
   - Reuse existing report listing/detail services if the symbol and date range match.
   - Add one citation per selected report, including report id, report type, as-of date, and short excerpt.
   - If no generated reports are present, emit a low-severity diagnostic rather than degrading the entire answer.

### Ranking

Use simple deterministic ranking for the MVP:

1. Exact symbol match.
2. Date range match or recency.
3. Source priority: bars, indicators, fundamentals, news, reports.
4. Question keyword match where existing report/news text is available.

This is enough for a traceable MVP and avoids prematurely adding embeddings or a search index.

### Prompt Changes

Update `packages/ai/market_assistant.py` so the prompt:

- lists available citation IDs explicitly,
- instructs the model to use only listed citation IDs,
- asks the model to cite important factual claims with inline IDs in square brackets,
- instructs the model to say when a requested research source is unavailable instead of inventing it,
- preserves existing safety rules and no-investment-advice boundaries.

### Citation Validation

After LLM generation, validate inline citation IDs found in `answer_markdown`:

1. Extract bracketed IDs that match known citation-like prefixes.
2. Compare extracted IDs with `citations[].id`.
3. If unknown IDs are found, add `CITATION_UNKNOWN_ID` diagnostics.
4. Prefer deterministic fallback if the unknown citation is material or the answer depends on it.
5. Do not present hallucinated IDs as valid.

The deterministic fallback can remain the safe output path because it uses service-built citations and diagnostics rather than model-invented source IDs.

## API Design

`apps/api/routers/assistant.py` should keep the same request model. A response model can be added if it remains compatible, but this task does not require a breaking response-model migration.

API-level tests should verify that enriched optional fields pass through and that old fields remain present.

## Frontend Design

Update `apps/web/lib/market-assistant.ts` types with optional citation and diagnostic fields. Existing payloads should still type-check.

Update `apps/web/components/market-assistant-card.tsx` to:

- render `citation.url` as a safe link when present,
- show source type, as-of date, provider, or excerpt when available,
- show diagnostic `severity` and `code` when available,
- preserve current rendering for payloads that only have `id`, `label`, `source`, `source/status/message`.

No broad markdown renderer migration is required for this task.

## Compatibility and Rollback

- Existing clients remain compatible because all added fields are optional.
- If generated report retrieval proves too invasive during execution, it may be left behind a diagnostic and documented as follow-up while still delivering richer bars/indicator/fundamental/news citations.
- If the unified research-evidence helper becomes too invasive for the first implementation slice, keep it as service-local dataclasses and defer any database or router scaffolding.
- If LLM citation validation is too strict for the first slice, fallback-to-deterministic is the safer rollback behavior.
- The assistant must continue to return `no_data` without calling the LLM when core daily bars are unavailable.

## Remaining Professional Gaps After This Task

Even after this MVP, the system will still lack:

- production filings/transcripts ingestion,
- vector search and document chunks,
- persistent multi-turn research sessions,
- watchlist-level research monitoring,
- notebook workflows,
- paid research entitlement governance,
- full AlphaSense/Bloomberg-style research parity.
