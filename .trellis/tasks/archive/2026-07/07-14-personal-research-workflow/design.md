# Personal research workflow design

## Boundary and invariants

This task reorganizes existing personal-use surfaces and adds two bounded API
capabilities: instrument pagination and a manual LLM connection test. It does
not create a new product area.

Protected boundaries:

- Do not edit `apps/web/app/[locale]/page.tsx` or change homepage messages,
  section order, links, data selection, visual tokens, or runtime behavior.
- Keep the current Tailwind/shadcn-style financial terminal components, light
  and dark themes, typography, spacing scale, and market color convention.
- Keep every existing route and stored record addressable. Navigation removal
  is not service or data deletion.
- Keep deterministic shortlist membership/ranking, citation validation,
  research-only wording, and the no-trading boundary unchanged.
- Automated tests never call a real LLM. The manual test is user-triggered,
  single-call, and has no retry path.

The task stays as one coherent implementation because the same navigation,
route hierarchy, localization, and browser acceptance define all retained
personal workflows. Work is still split into rollback-friendly stages.

## Information architecture

`NAVIGATION_ITEMS` becomes the single source of truth for exactly five primary
destinations, in this order:

1. Home (`/`)
2. AI Research (`/ai-research`)
3. Instruments (`/instruments`)
4. Watchlist (`/watchlist`)
5. Settings (`/settings`)

Desktop keeps the current sidebar pattern. Mobile uses the same five labeled
Lucide-icon destinations without horizontal scrolling. Active state and deep
links remain intact.

Secondary access:

| Surface | Access after change |
|---|---|
| Reports | Instrument detail and generated-report links |
| Alerts | Notification bell and Watchlist |
| Evidence | Settings `Data and maintenance` section and existing contextual links |
| Task Runs | Settings maintenance section and task-result links |
| Portfolio | Direct URL only |

The top bar retains the logo, global search, notification bell, language, and
theme controls. The fake account/email/profile/logout menu is removed because
there is no account system in this single-user app.

## UX composition

Use existing `FinancialPageHeader`, `FinancialTerminalCard`,
`FinancialTerminalSurface`, `Button`, `Badge`, `Table`, `EmptyState`, and
`ErrorState` primitives. Do not introduce a hero, marketing copy, nested cards,
new fonts, new palette, or decorative animation.

Accessibility and responsive contracts:

- Five items maximum in mobile bottom navigation.
- Core content precedes advanced content in DOM and visual order.
- All interactive controls retain visible labels, keyboard focus, and at least
  the existing touch target dimensions.
- Native `details` or the repository's existing accessible collapsible
  primitive owns advanced sections; do not implement clickable `div` toggles.
- No horizontal page overflow at 375, 390, 768, or 1440 px.
- Empty and failed states remain distinct.

### AI Research

Render the frozen daily shortlist, stock discovery, and cited analysis first.
Watchlist/research handoff remains close to each candidate. Evidence coverage,
universe refresh, backfill start/resume/retry/cancel, and raw operational state
move into an initially collapsed advanced maintenance section. Existing API and
TaskRun contracts remain unchanged.

### Instrument detail

Keep the quote/chart and cited assistant first, followed by stored technical,
fundamental, news, report, and research context. Provider-unsupported depth,
recent trades, large-order, and fund-flow panels move into an advanced market
data section, collapsed initially when unavailable. Existing fetches and
response types remain compatible.

### Watchlist

The normal view prioritizes saved symbols, price/evidence state, open-detail,
and remove actions. Adding from Instrument Detail continues to reuse
`addInstrumentToWatchlistAction`. Manual symbol/market entry and alert-rule
editing are secondary controls. An empty watchlist links to AI Research and
Instruments rather than seeding demo rows.

### Evidence

Each major server fetch produces an independent loaded/failed result. A failed
market-overview aggregate must not return early and hide source notes, saved
briefs, market evidence, or disclosures that loaded successfully. Personal
notes/briefs render before ingestion and source-maintenance tools; mutation
controls are grouped under advanced maintenance.

### Settings

The first section contains the LLM preset, key status/input, save command, and
manual connection test. DeepSeek and OpenAI use their preset URL/model without
requiring the user to edit those values. Custom URL/model controls appear only
for the custom preset through a small isolated client component. Market/news
provider details, homepage preferences, and maintenance links are advanced.
One visible save command owns the form submission.

## Instrument query contract

Extend the existing endpoint additively:

```text
GET /instruments?q=<optional>&market=<optional>&limit=25&offset=0
```

Validation:

- `limit`: optional integer, API-bounded `1..100` when supplied. Omission means
  no limit and preserves the complete-list behavior used by the protected
  homepage and other legacy callers.
- `offset`: integer, default `0`, minimum `0`.

Response:

```json
{
  "source": "database",
  "items": [],
  "total": 5530,
  "limit": 25,
  "offset": 0,
  "has_more": true
}
```

`limit` in response metadata is the supplied integer or `null` for an unlimited
legacy request. The service applies query/market filters and total count before
offset/limit.
The database path filters and paginates in SQL; the small seed fallback filters
then slices in memory. Existing callers that omit pagination still receive the
complete `items` behavior plus additive metadata.

The Instruments page uses `page` URL state and requests 25 rows. Latest-bar
fan-out is limited to those rows and comparison remains bounded to eight. The
global search waits for non-blank input, requests a bounded query result, and
does not download the full universe when opened.

## Manual LLM test contract

Backend signature:

```text
POST /settings/llm/test
```

The service reads normalized private platform settings, verifies provider/key/
base/model, calls the existing provider once with a minimal fixed prompt, does
not retain or return the answer, and measures elapsed time with a monotonic
clock.

Success payload:

```json
{
  "status": "ok",
  "code": "connected",
  "provider": "openai",
  "model": "deepseek-chat",
  "latency_ms": 1234
}
```

Error payloads contain only `status`, stable `code`, provider/model when safe,
and a sanitized message. They never contain the key, authorization header,
prompt, answer, upstream body, stack trace, or credential-bearing URL.

Error matrix:

| Condition | HTTP | Code |
|---|---:|---|
| provider disabled | 400 | `provider_disabled` |
| missing/unusable key | 400 | `key_not_configured` |
| invalid explicit base/model | 400 | `invalid_configuration` |
| provider exception/status failure | 502 | `provider_unavailable` |
| empty/malformed generation | 502 | `invalid_provider_response` |

Next exposes a same-origin POST proxy and a small client test control with
pending, success, and error states. One click creates at most one backend call;
the control is disabled while pending and has no retry loop. Saving settings
does not test automatically, and a failed test never mutates settings.

## Authorized local cleanup

After code rollout and before final browser acceptance:

1. Record the current active watchlist identities.
2. Call the existing watchlist removal service/API for exact matches
   `TEST:US` and `CN_SHANGHAI_COMPOSITE:CN` only.
3. Verify both rows are inactive rather than deleted and no other row changed.
4. Verify an empty watchlist does not re-seed because historical rows still
   exist, then verify the new empty-state recovery links.

No cleanup matcher, migration, scheduled task, or reusable delete script is
added to production code.

## Rollout and rollback

- Navigation/page composition is frontend-only and reversible by commit.
- Pagination is additive; omitting `limit`/`offset` preserves existing callers.
- The LLM test endpoint is isolated from save and all scheduled workflows.
- Local cleanup uses soft deactivation and can be reversed with the existing
  watchlist upsert path if explicitly requested.
- Homepage source and behavior are checked before and after every frontend
  stage; any homepage content diff blocks rollout.
