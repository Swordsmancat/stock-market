# Add Trading Calendar Aware Quality Checks Implementation Plan

## Phase 1: Planning

- [x] Create Trellis task.
- [x] Write PRD.
- [x] Write design.
- [x] Curate implement/check context manifests.

## Phase 2: Implementation

- [x] Add optional expected trading sessions argument to `check_daily_bar_quality(...)`.
- [x] Add helper for parsing expected session dates.
- [x] Add missing-date finder that uses explicit expected sessions when provided.
- [x] Preserve default weekday missing-date behavior.
- [x] Preserve OHLC, volume, and empty-bar behavior.

## Phase 3: Tests and Verification

- [x] Add focused tests for holiday-aware sessions.
- [x] Add focused tests for missing expected sessions.
- [x] Run focused data-quality tests.

Validation result:

- `python -m pytest tests/services/test_data_quality.py -v`: 9 passed.
- Linter diagnostics: 0.
- Focused review: APPROVED.

Validation:

```bash
python -m pytest tests/services/test_data_quality.py -v
```

## Phase 4: Completion

- [x] Update acceptance checkboxes.
- [ ] Commit and push automatically per current user automation authorization.
- [ ] Archive task and push archive commit.
- [ ] Inspect next backlog item.
