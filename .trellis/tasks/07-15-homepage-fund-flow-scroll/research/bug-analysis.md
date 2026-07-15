# Bug Analysis: Homepage fund-flow content is clipped

## 1. Root Cause Category

- **Category**: D - Test Coverage Gap.
- **Specific cause**: The frontend spec already required fixed-height panel
  bodies to own an `overflow-y-auto` list area, but the fund-flow panel combined
  an `xl` fixed height with an outer `overflow-hidden` card and an unconstrained
  content body. No test supplied more rows than the visible area or asserted a
  scroll owner, so the violation remained invisible to Vitest.
- **Secondary assumption**: `rows.slice(0, 4)` assumed four labels were enough
  even though the homepage already fetched five sectors. The chart and list
  therefore described different bounded datasets.

## 2. Why Earlier Coverage Failed

1. The homepage test only used three sectors, so content happened to fit well
   enough for DOM assertions and never exercised the fixed-height boundary.
2. JSDOM does not calculate `clientHeight` or `scrollHeight`; visible-text tests
   alone could not detect browser clipping.
3. The shared card's `overflow-hidden` was correct for stable panel borders, so
   changing it globally would have treated the symptom and risked other panels.

## 3. Prevention Mechanisms

| Priority | Mechanism | Specific action | Status |
| --- | --- | --- | --- |
| P0 | Test coverage | Inject five fund-flow rows; assert the named focusable scroll region and fifth row | Done |
| P0 | Component contract | Require overflow owners to be named, focusable, and visibly focused | Done |
| P1 | Browser acceptance | Measure the desktop region and exercise a real wheel scroll | Done |
| P1 | Responsive guard | Constrain overscroll only at `xl`; verify mobile has no horizontal overflow | Done |

## 4. Systematic Expansion

- **Similar issues**: Other fixed-height homepage panels were inspected. Their
  list/table panels already use `min-h-0 flex-1 overflow-y-auto`; chart-only and
  compact sentiment panels currently fit their bounded content. They are not
  changed in this task.
- **Design improvement**: Keep the shared `TerminalPanel` as a stable clipped
  frame and make only the content owner scroll. This preserves panel geometry
  without adding a client component or custom scrollbar dependency.
- **Process improvement**: Any fixed-height data panel test should include more
  rows than the first visible segment, then pair DOM assertions with one real
  browser overflow measurement.

## 5. Knowledge Capture

- [x] Updated `.trellis/spec/frontend/component-guidelines.md`.
- [x] Added the focused homepage regression test.
- [x] Recorded desktop and mobile browser acceptance in this task.
- [x] Confirmed no template-spec mirror exists at `src/templates/markdown/spec`.
