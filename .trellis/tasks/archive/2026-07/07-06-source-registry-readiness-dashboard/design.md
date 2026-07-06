# Design: Information Source Registry and Readiness Dashboard

## Boundary

This slice makes source coverage visible. It does not fetch live data, scrape documents, or solve licensing. The value is that the personal dashboard can answer:

- which information sources exist.
- which sources already have local evidence.
- which sources are missing.
- what action would make AI summaries more useful.

## Backend Shape

Add a service helper, likely `packages/services/information_sources.py`, with static source definitions and a readiness builder.

Suggested payload:

```json
{
  "status": "degraded",
  "summary": {
    "total": 9,
    "configured": 3,
    "needs_action": 6
  },
  "groups": [
    {
      "category": "macro",
      "label": "Macro sources",
      "items": []
    }
  ],
  "items": [
    {
      "id": "fred_us_rates",
      "label": "FRED US Treasury rates",
      "category": "macro",
      "authority": "Federal Reserve Bank of St. Louis FRED",
      "coverage": ["DGS10", "DGS2", "T10Y2Y"],
      "status": "needs_adapter",
      "freshness_policy": "Daily official series; update after FRED observation publication.",
      "ai_usage": "Can support rates/yield-curve context after observations are imported.",
      "next_action": "Add official-source adapter or audited seed import for DGS10/DGS2/T10Y2Y.",
      "evidence_count": 0,
      "latest_as_of": null
    }
  ],
  "diagnostics": []
}
```

## Readiness Rules

- Macro source entries check whether mapped indicator codes have `ok` payloads or observations.
- Reports source checks `GeneratedReport` count/latest.
- News source checks `NewsArticle` count/latest.
- Manual seed source remains `needs_manual_seed` unless matching macro observations exist.
- Future sources such as SEC filings/transcripts are listed as `future` until an adapter or ingestion policy exists.

## API Integration

Add the readiness payload to `get_market_overview_payload()` as `information_sources`.

Compatibility:

- Existing dashboard fields stay unchanged.
- New field is additive.
- No network calls inside dashboard request.

## Frontend

Render a compact panel near the AI brief or macro board:

- Summary badges: configured, needs action, future.
- Category groups with source label, authority, status, freshness, AI usage, next action.
- Use existing Card/Badge patterns and i18n strings.

## Tests

Backend:

- registry returns static entries with statuses.
- existing generated report/news rows make report/news sources configured.
- macro observation makes a mapped macro source configured.

Frontend:

- homepage renders "Information source readiness".
- renders at least FRED/PBOC/manual seed or SEC future source next action.

## Risks

- The registry can become stale if source URLs or policies change; keep entries small and reviewed.
- Avoid encoding licensing assumptions in code. Use "candidate" or "future" for unimplemented source families.
- Do not treat status as a hard operational SLA; this is a personal research readiness view.
