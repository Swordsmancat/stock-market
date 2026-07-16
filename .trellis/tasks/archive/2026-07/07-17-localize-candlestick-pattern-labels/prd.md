# Localize candlestick pattern labels

## Goal

Render the five known candlestick pattern codes as localized labels while preserving unknown-pattern fallback.

## Requirements

- Localize the five codes emitted by `candlestick_patterns_v1`: `bullish_engulfing`, `bearish_engulfing`, `doji`, `hammer`, and `shooting_star`.
- Prefer the localized code label for known patterns even when the stored payload also contains an English `name`.
- Accept both structured pattern objects and legacy string pattern codes.
- Preserve a truthful fallback for unknown patterns: stored `name`, then stored `pattern`, then stored `code` or string value.
- Add symmetric Chinese and English messages in the existing `InstrumentDetail` namespace.
- Do not change detection rules, market bias, pattern counts, evidence payloads, rankings, or trading behavior.

## Acceptance Criteria

- [x] Chinese detail pages show localized labels for all five known pattern codes.
- [x] English detail pages show readable English labels for all five known pattern codes.
- [x] Known structured objects and legacy string codes resolve to the same localized label.
- [x] An unknown structured pattern keeps its stored name, and an unknown string keeps the string value.
- [x] No raw known snake_case pattern code is visible in the default technical summary.
- [x] Focused tests, full Web tests, TypeScript, and browser verification pass.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
