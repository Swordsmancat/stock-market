# Localize instrument technical indicators

## Goal

Render known technical indicator names and structured field labels as localized, human-readable summaries while preserving unknown values.

## Requirements

- Localize the 12 known scalar/structured indicator codes emitted by the existing indicator API: `ma`, `rsi`, `bollinger`, `atr`, `macd`, `kdj`, `cci`, `obv`, `roc`, `bias`, `mfi`, and `william_r`.
- Localize the known structured fields for Bollinger (`upper`, `middle`, `lower`) and MACD (`macd`, `signal`, `histogram`); keep KDJ's conventional `K`, `D`, and `J` labels.
- Preserve every numeric value, locale-aware number format, card order, and all specialized candlestick/chip-distribution rendering.
- Keep unknown indicator codes and unknown nested fields visible using their original stored keys.
- Add symmetric English and Chinese messages in the existing `InstrumentDetail` namespace.
- Do not add trading interpretations, thresholds, signals, recommendations, API changes, or backend calculations.

## Acceptance Criteria

- [x] Chinese detail pages show readable Chinese names with the conventional acronym for every known indicator.
- [x] English detail pages show readable English names with the conventional acronym for every known indicator.
- [x] Bollinger and MACD structured values use localized field labels instead of raw `upper/lower/middle/macd/signal/histogram` keys.
- [x] KDJ values retain conventional uppercase `K`, `D`, and `J` labels.
- [x] Unknown indicator and nested-field keys remain visible and their values are unchanged.
- [x] Existing specialized technical summaries and all non-indicator detail-page behavior remain unchanged.
- [x] Focused tests, full Web tests, TypeScript, and desktop/mobile browser checks pass.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
- Browser QA rendered all 12 known Chinese and English labels, localized Bollinger/MACD fields, and no raw `ma` or `william_r` labels. The card and page had no horizontal overflow. The prior 390x844 single-column layout remains structurally unchanged; the new labels wrap naturally and component coverage verifies both catalogs plus unknown-key fallback.
