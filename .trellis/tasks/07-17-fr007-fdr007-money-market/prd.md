# Add FR007 and FDR007 money-market observations

## Goal

Add audited seven-day repo fixing rates from ChinaMoney to the existing macro
dashboard and explicit AkShare refresh workflow.

## Requirements

- Add separate `cn_fr007` and `cn_fdr007` indicator definitions. Do not label
  either series as generic `DR007`.
- Source data through AkShare `repo_rate_hist`, whose upstream authority is the
  China Foreign Exchange Trade System / National Interbank Funding Center.
- Fetch the current and previous calendar month separately because the provider
  requires start/end dates within one month, then deduplicate and normalize.
- Persist only valid finite values through `MarketIndicatorObservation` with
  provider function, source URL, source fields, retrieval time, and methodology.
- Reuse `POST /market-indicators/official-refresh/akshare-cn`; GET routes remain
  database-only and provider failure preserves stored observations.
- Add symmetric English/Chinese built-in labels and keep personal-research and
  no-trading boundaries unchanged.

## Acceptance Criteria

- [x] `family=repo_rates` normalizes FR007 and FDR007 regardless of source order.
- [x] Current/previous month fetches obey the provider date constraint.
- [x] Schema mismatch, missing values, and provider failures write no false zero.
- [x] Both rates appear in the stored macro dashboard and localized UI.
- [x] Focused provider/service/API/frontend tests and full relevant checks pass.
- [x] Source registry and refresh runbook document authority and semantics.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
