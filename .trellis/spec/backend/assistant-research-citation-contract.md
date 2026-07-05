# Assistant Research Citation Contract

## Scenario: Research Evidence and Citation-Enriched Market Assistant

### 1. Scope / Trigger

- Trigger: `POST /assistant/market` now returns enriched research citations and diagnostics built from existing platform evidence.
- Scope: assistant service logic in `packages/services/market_assistant.py`, prompt/citation validation in `packages/ai/market_assistant.py`, FastAPI route behavior in `apps/api/routers/assistant.py`, frontend route/card consumers under `apps/web`, and focused assistant tests.
- Non-goals: production filings/transcripts/announcements ingestion, embeddings/vector search, persistent notebooks, streaming responses, watchlist-level monitoring, paid research entitlements, or direct trading recommendations.

### 2. Signatures

- API: `POST /assistant/market`
- Service entry: market-assistant payload builder in `packages/services/market_assistant.py`
- AI generation: prompt construction and citation validation in `packages/ai/market_assistant.py`
- Response fields preserved: `answer_markdown`, `model`, `context`, `citations`, `diagnostics`, `safety`
- Citation required fields: `id`, `label`, `source`, `url`
- Citation optional fields: `source_type`, `as_of`, `provider`, `retrieved_at`, `excerpt`, `metadata`
- Diagnostic required fields: `source`, `status`, `message`
- Diagnostic optional fields: `severity`, `code`, `citation_id`, `details`

### 3. Contracts

- Daily bars remain the core evidence gate. If required market data is unavailable, the assistant must return `no_data` / degraded-safe output and avoid LLM generation.
- Existing top-level response fields and old minimal citation payloads must remain backward compatible.
- Evidence may come from existing platform sources only: daily bars, stored technical indicators, fundamentals snapshots, news / sentiment payloads, and generated reports.
- Missing optional sources must produce diagnostics, not fabricated evidence or fake citations.
- Citation IDs must be deterministic and source-specific, such as `bars_1d:{symbol}:{as_of}`, `technical_indicators:{symbol}:{as_of}`, `fundamentals:{symbol}:{as_of}`, `news:{symbol}:...`, or `generated_report:{id}`.
- LLM prompts must list available citation IDs and instruct the model to use only those IDs.
- LLM output citation IDs must be validated against the payload citations. Unknown IDs must produce `CITATION_UNKNOWN_ID` diagnostics and should fall back to deterministic output when needed.
- Diagnostics may include safe severity/code metadata, but must not include API keys, prompt internals, stack traces, raw provider secrets, or hidden chain-of-thought.
- The assistant must preserve no-investment-advice and no direct buy/sell/hold/target-price/position-sizing/execution-instruction boundaries.

### 4. Validation & Error Matrix

- Core daily bars unavailable -> response does not call LLM; returns no-data/degraded diagnostics.
- Optional indicators/fundamentals/news/reports missing -> non-blocking diagnostics such as `SOURCE_NO_DATA` or `SOURCE_OMITTED`.
- Source service failure -> sanitized `SOURCE_UNAVAILABLE` diagnostics; no raw secret or stack trace.
- LLM returns unknown inline citation ID -> `CITATION_UNKNOWN_ID` diagnostic and degraded/fallback output; unknown citation is not presented as valid.
- User asks for direct trading instruction -> assistant refuses/reframes per safety policy.
- Old frontend payload with only `id`, `label`, `source`, `url` citations -> still renders.
- Citation URL present -> frontend renders safe link without changing backend API contract.

### 5. Good/Base/Bad Cases

- Good: daily bars, indicators, fundamentals, news, and a generated report are available; response contains deterministic citation IDs, optional metadata/excerpts, compact diagnostics, and an answer using only known citation IDs.
- Base: only daily bars are available; answer remains traceable to bars and diagnostics state missing optional sources.
- Bad: a missing filing/transcript is represented as a live citation. These sources are not production integrations in this slice.
- Bad: an LLM-invented citation ID is rendered as if it existed in `citations`.
- Bad: direct buy/sell/hold advice, target prices, or position sizing is emitted because citations exist.

### 6. Tests Required

- Service/AI tests assert citations are generated for available bars, indicators, fundamentals, news, and generated reports.
- Service tests assert missing optional evidence produces diagnostics rather than fabricated citation items.
- AI tests assert unknown LLM citation IDs are detected and handled with diagnostics/fallback behavior.
- API tests assert backward compatibility and enriched optional fields.
- Frontend route/card tests assert citation links, metadata, diagnostic severity/code, and legacy rendering.
- Safety tests assert direct trading instructions are refused or reframed.
- Full validation should include assistant-focused backend tests, assistant-focused frontend tests, `python -m pytest -q`, and `npm run test:web`.

### 7. Wrong vs Correct

#### Wrong

```python
citations.append({
    "id": "filing:AAPL:latest",
    "label": "Latest filing",
    "source": "filings",
})
```

This fabricates a production filing source when no filings provider exists.

#### Correct

```python
diagnostics.append({
    "source": "filings",
    "status": "omitted",
    "severity": "info",
    "code": "SOURCE_OMITTED",
    "message": "Production filings retrieval is not configured for this assistant slice.",
})
```
