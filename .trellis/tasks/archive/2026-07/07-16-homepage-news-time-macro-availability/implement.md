# Homepage news time and macro availability execution plan

## 1. Lock the regressions

- Extend the homepage fixture with published timestamps.
- Assert localized Shanghai news time is visible ahead of source metadata,
  missing/invalid values fall back, provider capability still affects the
  aggregate score, and the provider status strip is absent.
- Update the World Bank provider test to assert the new bounded timeout and the
  documented `mrv` latest-value query parameter, plus a fully sanitized
  exception chain.
- Update the World Bank service regression to request a five-value window and
  prove that only the latest valid observation is stored.
- Run the focused tests once before implementation to confirm the new
  assertions fail for the intended reasons.

## 2. Implement the smallest code changes

- Add the homepage date-time formatter and render timestamp-first news metadata.
- Remove the visible provider status strip and its dead page-only code/copy.
- Increase the World Bank provider default timeout, use a bounded `mrv=5`
  window, and retain local latest-valid selection without changing its error,
  parsing, validation, or persistence contracts.

## 3. Verify code

- Run focused homepage and World Bank provider tests.
- Run the proportional frontend suite and TypeScript check.
- Run relevant backend macro/provider tests.
- Run Trellis validation and `git diff --check` while excluding unrelated dirt
  from staging or commits.

## 4. Restore audited macro data

- Confirm the API has reloaded the provider change.
- Run World Bank dry-run per Buffett target.
- For each successful dry-run, make one explicit write refresh through the
  existing API endpoint.
- Re-read source status and `/dashboard/market-overview`; record only actual
  successful observations and leave unsupported/unconfigured rows as no-data.
- Record the observed result: China and USA stored successfully; Hong Kong
  remained unavailable after a sanitized upstream failure; FRED remained
  unconfigured.

## 5. Browser acceptance

- Verify the Chinese homepage at desktop and mobile widths.
- Confirm timestamp visibility, provider-strip absence, fixed panel layout,
  macro values for refreshed targets, no overlap, and no horizontal overflow.
- Run Trellis check and finish/commit flow for only this task's files and code.
