# AI Market Assistant Design

## Scope

This task delivers a first MVP of a natural-language market assistant for the instrument detail workflow. The assistant answers user questions using only platform-available, traceable market context. It does not provide direct buy/sell/hold advice, target prices, or trading instructions.

## Backend Contract

Add a dedicated assistant endpoint:

```http
POST /assistant/market
```

Request shape:

```json
{
  "scope": "instrument",
  "symbol": "AAPL",
  "provider": "yfinance",
  "locale": "zh",
  "timeframe": "1d",
  "start": "2026-01-05",
  "end": "2026-07-04",
  "question": "请总结近期走势和主要风险点。"
}
```

MVP constraints:

- `scope` supports only `instrument`.
- `timeframe` supports only `1d`.
- `question` is required and length-limited by FastAPI validation.
- `start` / `end` are optional; the service defaults to a recent daily-bar lookback.

Response shape:

```json
{
  "status": "ok",
  "answer_markdown": "...",
  "symbol": "AAPL",
  "as_of": "2026-07-03",
  "model": {
    "provider": "openai",
    "name": "gpt-4o-mini",
    "used_llm": true,
    "fallback_reason": null
  },
  "context": {
    "timeframe": "1d",
    "start": "2026-01-05",
    "end": "2026-07-04",
    "latest_close": 123.45,
    "period_change_pct": 4.32,
    "bar_count": 120,
    "indicators": {},
    "fundamental_summary": "...",
    "news_summary": "..."
  },
  "citations": [
    { "id": "bars_1d:AAPL:2026-07-03", "label": "Daily bars", "source": "bars_1d", "url": null }
  ],
  "diagnostics": [
    { "source": "news", "status": "no_data", "message": "No stored news sentiment is available yet." }
  ],
  "safety": {
    "not_investment_advice": true,
    "no_fabricated_market_data": true,
    "disclaimer": "..."
  }
}
```

Status semantics:

- `ok`: core daily bars exist and all requested answer generation paths completed.
- `degraded`: core daily bars exist, but optional context is missing or deterministic fallback was used.
- `no_data`: core daily bars are unavailable; do not call the LLM and do not fabricate analysis.
- `error`: unexpected failure boundary for frontend display.

## Backend Architecture

Add:

- `packages/ai/market_assistant.py`
  - Prompt builder.
  - Deterministic fallback answer builder.
  - Safety/disclaimer constants.
- `packages/services/market_assistant.py`
  - Request defaults.
  - Market context aggregation from existing market-data, indicators, fundamentals, and news services.
  - Citations and diagnostics.
  - LLM/fallback orchestration.
- `apps/api/routers/assistant.py`
  - Thin FastAPI router for `POST /assistant/market`.
- `apps/api/main.py`
  - Include assistant router.

Reuse:

- `packages.ai.llm_factory.get_llm_provider` for OpenAI-compatible providers.
- `packages.services.market_data.get_bars_payload` for daily bars.
- Existing indicator/news/fundamental services for optional context.

## Frontend Architecture

Add:

- `apps/web/lib/market-assistant.ts`
  - Typed request/response contract.
  - `askMarketAssistant` helper calling the web route proxy.
- `apps/web/app/api/assistant/market/route.ts`
  - Thin proxy to backend `/assistant/market`, preserving status and body.
- `apps/web/components/market-assistant-card.tsx`
  - Instrument detail assistant UI.
  - Quick prompts.
  - Question form.
  - Loading, error, `no_data`, degraded/fallback, citations, diagnostics, and disclaimer rendering.
- `apps/web/components/instrument-detail-client.tsx`
  - Insert assistant card after summary cards and before market-depth/intraday details.
- `apps/web/messages/en.json` and `apps/web/messages/zh.json`
  - Add `MarketAssistant` namespace.

## Safety Boundaries

- Do not fabricate prices, news, fundamentals, indicators, or market depth.
- Do not return direct buy/sell/hold recommendations.
- Do not provide target prices, position sizing, or trade execution instructions.
- If the user asks for direct trading advice, explain the boundary and summarize available evidence/risk factors instead.
- Never expose API keys, settings secrets, or hidden prompt internals.
- Treat the user's question as untrusted input inside a strict system prompt.

## Testing Strategy

Backend:

- Prompt/fallback safety tests.
- API tests for success, no-data fallback, optional context missing, and direct-advice question boundaries.

Frontend:

- Route proxy tests.
- Component tests for submit/loading/success/no-data/error states.
- Instrument detail page test asserting assistant entry point exists.

## Rollback

The assistant is additive. Rollback can remove the assistant router include, frontend card insertion, and new files without affecting market data, reports, or existing dashboard flows.
