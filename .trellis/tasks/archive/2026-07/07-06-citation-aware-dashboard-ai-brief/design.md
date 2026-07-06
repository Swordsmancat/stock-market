# Design: Citation-aware Dashboard AI Brief

## Boundary

This slice upgrades the existing `dashboard_brief` into an AI-ready, citation-aware brief with an optional LLM-generated narrative. It does not add new external data ingestion.

The existing deterministic sections remain the source of truth. The LLM can only summarize those sections and use the citation IDs already provided by the dashboard payload.

## Payload Shape

Add a backward-compatible `narrative` object under `dashboard_brief`:

```json
{
  "dashboard_brief": {
    "status": "degraded",
    "sections": [],
    "citations": [],
    "diagnostics": [],
    "safety": {},
    "narrative": {
      "answer_markdown": "### Summary...",
      "model": {
        "provider": "deterministic",
        "name": "dashboard-brief-deterministic-fallback",
        "used_llm": false,
        "fallback_reason": "OpenAI-compatible LLM provider is not configured."
      },
      "context": {
        "source_mix": {
          "macro_citations": 0,
          "report_citations": 0,
          "news_citations": 0,
          "information_source_gaps": 8
        }
      }
    }
  }
}
```

Existing fields stay unchanged.

## Backend Flow

1. Build existing `dashboard_brief` sections/citations/diagnostics.
2. Build narrative context from:
   - brief sections.
   - known citations.
   - brief diagnostics.
   - information source readiness summary/items.
   - safety flags.
3. If LLM is unavailable, build deterministic markdown fallback.
4. If LLM is configured:
   - create prompt that lists only known citation IDs.
   - require inline citations in square brackets for factual claims.
   - validate output citations against known IDs.
   - on unknown IDs, append `CITATION_UNKNOWN_ID` diagnostic and return fallback.
5. Return additive `dashboard_brief.narrative`.

## Reuse

Use the same concepts as the market assistant:

- configured model from platform settings.
- `get_llm_provider()`.
- deterministic fallback metadata.
- unknown inline citation detection.
- no direct buy/sell/hold advice.

If shared helpers can be extracted cheaply, do so. Otherwise keep the dashboard helper private and document the contract in tests.

## Frontend

Render the narrative inside the existing dashboard brief panel:

- show markdown-ish text in a compact block.
- show model state: `AI generated` when `used_llm=true`, otherwise `Deterministic fallback`.
- preserve current sections, citations, and diagnostics.
- keep the module visually framed as research summary and not as trade recommendation.

## Tests

Backend:

- no LLM config returns deterministic narrative and fallback diagnostic.
- LLM success returns generated narrative and `used_llm=true`.
- unknown citation IDs trigger `CITATION_UNKNOWN_ID` and deterministic fallback.
- information source gaps are counted/summarized in narrative context.

Frontend:

- homepage renders narrative text.
- homepage renders fallback/model state.
- existing citation/diagnostic rendering still works.

## Compatibility

- `/dashboard/market-overview` remains additive.
- Old frontend consumers that ignore `dashboard_brief.narrative` keep working.
- Existing dashboard brief section/citation tests should continue to pass with updated assertions.
