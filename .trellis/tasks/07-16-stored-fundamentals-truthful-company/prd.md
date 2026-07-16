# Restore truthful stored fundamentals and company context

## Goal

Make existing A-share detail and AI views benefit from the public Eastmoney
company context without replacing authoritative stored financial metrics, and
stop presenting legacy missing-PE placeholders as a real `0.00` value.

## Requirements

- Keep a stored `FundamentalSnapshot` authoritative for its report date,
  currency, revenue growth, net margin, and debt-to-assets values.
- Project an exact stored PE value of zero as `null`; zero is the legacy missing
  placeholder written by existing ingestion paths and is not a meaningful PE.
- For an exact six-digit A-share with the existing public-CN gate enabled,
  enrich a stored payload with the fixed Eastmoney CompanySurvey GET only.
- Cache normalized company success and explicit no-data for 1800 seconds.
- Redis or company-provider failure must not hide stored financial metrics.
- Add no database migration or write from GET/detail/AI reads.
- Keep US/HK behavior, citation IDs, safety rules, and 95/90/80 thresholds unchanged.
- Preserve unrelated five-day acceptance, worktree metadata, and feasibility files.

## Acceptance Criteria

- [x] Provider tests cover the independent fixed CompanySurvey request and
      company identity/schema/response validation without financial GETs.
- [x] Service tests prove stored A-share metrics remain authoritative, PE zero
      becomes null, company context is cached, and failure is non-blocking.
- [x] Stored nonzero PE and non-A-share behavior remain unchanged.
- [x] API/detail/assistant tests cover the enriched stored payload and citation.
- [x] Browser acceptance for `600519` shows PE unavailable and company context.
- [x] Focused/full checks, Trellis validation, commit, archive, journal, and push pass.

## Out Of Scope

- Rewriting or deleting historical fundamental rows.
- Making all fundamental columns nullable or changing ingestion/backfill jobs.
- Account login, Cookies, CAPTCHA, portfolio/watchlist access, or bulk crawling.
- Replacing stored financial metrics with a different report period.
