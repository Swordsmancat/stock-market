# Real-data usability acceptance execution plan

## 1. Establish real-data evidence

- Probe the four GET APIs and record dates, counts, statuses, and provenance.
- Verify a real two-stock comparison and one stored stock K-line.
- Verify ETF/index catalog totals and all topic section states.
- Inspect Chinese desktop and mobile page behavior without mutations.

## 2. Minimize and classify gaps

- Map every visible empty state to selection, catalog, identity, series,
  section coverage, or load failure.
- Confirm the same result over repeated GET requests.
- Identify whether existing structured payloads are sufficient for truthful
  copy; do not expand backend contracts unless evidence proves otherwise.

## 3. Implement the smallest explanation fix

- Add failing page/message tests for any generic or misleading empty state.
- Update only the owning page and symmetric locale keys.
- Keep operational links secondary and preserve navigation boundaries.

## 4. Verify and deliver

- Re-run focused page tests and the original runtime probes.
- Run full Web tests, TypeScript, locale JSON parsing, Trellis validation, and
  scoped `git diff --check`.
- Write `acceptance.md`, commit task-owned changes separately, archive the
  task, and record the session.

## Rollback points

- Stop after evidence collection if every state is already explicit.
- Revert only localized explanation changes if browser acceptance regresses;
  never alter stored data to make the acceptance pass.
