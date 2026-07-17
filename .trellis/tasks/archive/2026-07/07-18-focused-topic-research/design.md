# Design: focused topic research workspace

## Boundaries

- `packages/services/topic_research.py` owns the fixed topic taxonomy,
  normalization, database queries, matching reasons, and response projection.
- `apps/api/routers/topic_research.py` exposes a validated GET route and
  delegates the injected SQLAlchemy session.
- `apps/web/lib/topic-research.ts` owns the frontend payload contract and
  database-source validation.
- `/[locale]/topic-research` is a server-rendered read surface. Topic and
  window remain in the URL through links/forms.
- Existing news, industry-ranking, fundamental, instrument-detail, navigation,
  and localization patterns are reused; no new persistence table is required.

## Data Flow

```text
GET page
  -> GET /topic-research?topic=<id>&window=<30d|90d|180d>
    -> SQLAlchemy session
      -> NewsArticle
      -> IndustryDailyRanking
      -> latest FundamentalSnapshot per symbol
    <- bounded normalized payload with match reasons and provenance
  <- localized page with independent section states
```

## Contract

- Top-level source is `database`; taxonomy version is returned explicitly.
- Fixed topic IDs are stable URL values. Bilingual labels remain frontend
  translations; backend keywords are matching metadata, not display copy.
- News matching examines stored title and summary within the requested window.
- Industry matching examines stored industry names within the requested
  window and returns stable date/rank ordering.
- Related-company matching examines the latest stored `company_json` per
  symbol, returns a bounded identity/profile projection, and links only when
  an exact active instrument identity can be resolved.
- Every item includes a normalized `matched_on` reason. Keyword matching is
  case-insensitive and conservative; ambiguous generic terms are excluded.
- Section states are independent. A database exception is a page-level error;
  zero matches is a successful `empty` section.

## Compatibility And Safety

- SQL expressions must work in PostgreSQL and the repository's SQLite tests.
- JSON/company fields are treated defensively and output text is bounded.
- No provider adapter is imported into the service.
- The new sidebar item is desktop-visible but is not added to the five-item
  mobile navigation.
- Rollback removes the route, service, page, navigation link, translations,
  and contract spec without schema migration.
