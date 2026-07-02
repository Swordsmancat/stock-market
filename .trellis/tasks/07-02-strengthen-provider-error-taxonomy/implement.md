# Strengthen Provider Error Taxonomy Implementation Plan

## Phase 1: Planning

- [x] Create Trellis task.
- [x] Write PRD.
- [x] Write design.
- [x] Curate implement/check context manifests.

## Phase 2: Service Taxonomy

- [x] Add provider error subclasses and category/status metadata.
- [x] Classify timeout, unavailable, and rate-limit provider failures.
- [x] Wrap malformed provider bar payload serialization as malformed-payload provider errors.
- [x] Preserve `ValueError` request validation behavior.

## Phase 3: API Mapping

- [x] Map provider taxonomy errors using their HTTP status code.
- [x] Include provider, operation, and category in provider error responses.
- [x] Keep generic provider errors compatible with existing HTTP 502 behavior.

## Phase 4: Tests and Verification

- [x] Add focused market-data service tests.
- [x] Add focused market-data API tests.
- [x] Run focused validation.

Validation result:

- `python -m pytest tests/services/test_market_data_service.py tests/api/test_market_data_api.py -v`: 25 passed.
- Linter diagnostics: 0.
- Focused review: APPROVED after sanitizing provider error public messages.

Validation:

```bash
python -m pytest tests/services/test_market_data_service.py tests/api/test_market_data_api.py -v
```

## Phase 5: Completion

- [x] Update acceptance checkboxes.
- [ ] Commit and push automatically per current user automation authorization.
- [ ] Archive task and push archive commits.
- [ ] Inspect next backlog item.
