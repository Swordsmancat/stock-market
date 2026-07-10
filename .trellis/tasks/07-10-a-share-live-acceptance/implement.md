# A-share Live Acceptance Implementation

- [x] Inspect existing Compose, readiness, API, TaskRun, backfill, discovery, and runbook patterns.
- [x] Add the isolated acceptance Compose stack with dedicated state, ports, health checks, and Web wiring.
- [x] Add guarded/sanitized acceptance runner primitives and focused unit tests.
- [x] Add reproducible operator runbook commands and evidence artifact schema.
- [x] Run focused tests, Ruff, Compose config validation, migration checks, and Trellis validation.
- [x] Commit the repeatable harness before real execution (`1a558e1`).
- [x] Run read-only AkShare preflight; record classified output (universe passed; bars blocked writes after three `ConnectionError` attempts).
- [x] Build both isolated acceptance images reproducibly without starting the write stack.
- [ ] Start the isolated stack and verify database name, migration head, API, worker registration, beat timezone, and Web.
- [ ] Execute universe, preservation, canary, corporate-action, discovery, retry/resume, and browser acceptance slices.
- [ ] Start/monitor the full baseline only after canary success; retain partial/checkpoint evidence on stop.
- [ ] Classify findings and fix only demonstrated in-scope product defects with regression tests.
- [ ] Write sanitized report, update runbook/specs as needed, run full gates, commit, archive child and parent.
