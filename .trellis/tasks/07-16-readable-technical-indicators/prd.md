# Make technical indicators readable

## Goal

Make the instrument-detail technical indicators useful for repeated personal
research by summarizing complex stored indicator objects instead of rendering
their entire nested payload inline.

## Requirements

- Keep ordinary scalar indicators in the existing compact two-column grid.
- Render `candlestick_patterns` with evaluation status, pattern count, and a
  truthful empty-pattern state; keep remaining fields in an optional disclosure.
- Render `chip_distribution` with current price, weighted average cost, benefit
  ratio, 70%/90% cost ranges, and approximation/limitation context.
- Do not render all 60 chip buckets in the default card view.
- Use native keyboard-accessible progressive disclosure for remaining bounded details.
- Localize new labels in English and Chinese and preserve null as unavailable.
- Do not change indicator calculation, API payloads, database state, AI logic,
  chart behavior, or research thresholds.
- Preserve unrelated five-day acceptance and worktree metadata.

## Acceptance Criteria

- [x] Component tests prove scalar indicators remain visible and complex
      indicators render concise summaries rather than raw object walls.
- [x] Candlestick no-pattern and chip distribution key metrics are truthful.
- [x] Details controls are accessible and optional content is bounded.
- [ ] TypeScript, focused/full Web tests, Trellis validation, desktop/mobile
      browser acceptance, commit, archive, journal, and push pass.
