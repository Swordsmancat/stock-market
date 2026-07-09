# Local News Source Boundary Scan

Date: 2026-07-08

## Files Inspected

- `packages/domain/models.py`
- `packages/services/news.py`
- `apps/api/routers/news.py`
- `packages/services/information_sources.py`
- `packages/services/platform_settings.py`
- `apps/web/lib/platform-settings-store.ts`
- `apps/web/app/api/settings/route.ts`
- `pyproject.toml`

## Findings

- The domain already has `NewsArticle` and `SentimentSignal`.
- `NewsArticle` stores symbol, title, URL, source, published_at, summary, and dedupe_hash.
- `SentimentSignal` stores article_id, symbol, sentiment, confidence, reason, and created_at.
- Current ingestion supports mock, yfinance, AkShare, and a Tushare placeholder.
- Current FastAPI news router exposes mock ingest and database read only.
- Information-source readiness already treats stored news as citeable only after it exists locally with URL and publication metadata.
- The existing settings pattern can preserve secrets while returning configured flags to the frontend.
- Python dependencies already include `httpx`, which is suitable for server-side provider adapters.

## Implications

- A news-provider MVP should add a provider registry and adapter contract before adding many providers.
- Existing models can handle basic articles, but social sentiment or provider diagnostics may require either a new metadata field/migration or a separate social signal model.
- Existing no-fabrication and citation-boundary language should remain the core product rule.

## Suggested First Slice

1. Add provider configuration fields and capabilities.
2. Add a normalized search result candidate contract.
3. Implement one or two adapters behind mocked tests.
4. Persist only normalized, deduped news into `NewsArticle`.
5. Return explicit diagnostics for skipped/failed providers.
