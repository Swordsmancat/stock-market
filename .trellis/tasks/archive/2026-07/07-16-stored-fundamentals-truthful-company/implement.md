# Truthful stored fundamentals and company enrichment execution plan

## 1. Provider TDD

- Add an independent company-only request test and implement the public provider entry point.
- Keep combined fundamentals provider behavior unchanged.

## 2. Service TDD

- Add stored zero-PE projection, stored company enrichment/cache, failure,
  nonzero PE, and non-A-share regressions.
- Implement normalized company cache and database payload projection.

## 3. Cross-layer verification

- Extend API and assistant assertions for stored metrics plus company context.
- Reuse the existing detail component contract and rendering tests.

## 4. Validate and deliver

- Run focused provider/service/API/assistant/web tests, Ruff, TypeScript, full suites,
  live browser acceptance, Trellis validation, diff/redaction checks.
- Update the executable contract, commit task-owned files, archive, journal, and push.
