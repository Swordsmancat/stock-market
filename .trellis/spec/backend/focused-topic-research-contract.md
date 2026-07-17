# Focused Topic Research Contract

## Scenario: Database-Only Personal Topic Research

### 1. Scope / Trigger

- Trigger: a personal user scans stored evidence for agriculture, China
  consumption, real estate, or non-ferrous metals.
- Scope: `packages/services/topic_research.py`, `GET /topic-research`, and
  `/[locale]/topic-research`.
- Non-goals: provider refresh, crawling, ingestion, backfill, AI conclusions,
  custom topics, alerts, portfolio mutation, orders, or trading.

### 2. Signatures

- Service:
  `get_topic_research_payload(*, session, topic="agriculture", window="90d", as_of=None) -> dict[str, object]`.
- API:
  `GET /topic-research?topic=agriculture|consumption|real_estate|nonferrous&window=30d|90d|180d`.
- Page: `GET /[locale]/topic-research` with topic and window owned by the URL.

### 3. Contracts

- Read only `NewsArticle`, `IndustryDailyRanking`, `FundamentalSnapshot`,
  `Instrument`, and `Market` rows through the injected session. A page read
  must never call a provider, crawler, worker, AI, or mutation path.
- Keep one centralized, versioned taxonomy. Matching is case-insensitive and
  returns the exact matched field and keyword for every item. Exclude broad
  ambiguous keywords such as bare retail terms that produce unrelated
  companies.
- Use the current `Asia/Shanghai` date as the default projection anchor. An
  explicit `as_of` remains available for deterministic tests.
- For each symbol, inspect fundamental snapshots newest first and select the
  latest snapshot containing a non-empty company dictionary. A newer empty
  `company_json` must not hide older valid company metadata.
- Bound news, ranking, and company sections independently. Each section
  exposes `ready|empty`, total, returned count, latest date, stored provenance,
  and item-level match reasons.
- Empty stored evidence is successful and explicit. Database/API failure is a
  localized page error; neither state triggers live fallback or fixtures.
- The desktop sidebar owns one Topic Research link. The mobile navigation
  remains the existing five items.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Unknown topic or window | HTTP 422; no projection work |
| No matches in one section | Section `empty`; preserve other sections |
| No matches in any section | Top-level `empty`; preserve period and safety metadata |
| Newest company snapshot has empty metadata | Use the newest older non-empty company snapshot |
| Database/API failure | Localized error; no provider fallback |
| Page read | GET only, `cache: no-store`, database source required |

### 5. Tests Required

- Service tests cover validation, conservative field matching, stable ordering,
  limits, section states, Shanghai anchoring, and older non-empty company
  snapshot fallback.
- API tests cover query validation and injected-session delegation.
- Frontend decoder and proxy tests reject malformed or non-database payloads
  and preserve GET query state without caching.
- Page tests cover four topic controls, three windows, evidence timestamps,
  provenance, company links, and independent empty/error states.
- Browser acceptance covers all topics, Chinese rendering, desktop and
  `390x844` overflow, console errors, and the five-item mobile navigation.

### 6. Wrong vs Correct

#### Wrong

```python
snapshot = max(symbol_snapshots, key=lambda row: row.as_of)
if not snapshot.company_json:
    return None
```

This discards valid older metadata when a newer financial snapshot has no
company profile.

#### Correct

```python
snapshot = next(
    row for row in newest_first_snapshots
    if isinstance(row.company_json, dict) and row.company_json
)
```

The projection uses the freshest stored company metadata without fabricating
or fetching data.
