# Contrast Evidence

Run context:

- Date/time: 2026-07-05 23:50 Asia/Shanghai
- Local URL: `http://127.0.0.1:3000`
- Viewport: desktop `1440x900`
- Method: browser computed styles plus WCAG relative luminance formula
- Raw sample file: `contrast-samples.json`

## Scope

The pass sampled representative light and dark theme states for:

- ticker text, movement values, and neutral values on black;
- market-overview table headers and cells;
- settings headings, descriptions, labels, inputs, and primary action;
- instrument headings, muted text, large movement value, and table/header text;
- watchlist headings, muted text, table headers/cells, input, and button.

## Fix Applied

Initial sampling found one small contrast defect:

- Home ticker neutral text (`-- (--)`) used `text-muted-foreground` on black in light theme and measured about `4.41:1`, below normal-text WCAG AA (`4.5:1`).

Fix:

- `apps/web/components/market-ticker.tsx` now uses `text-gray-300` for flat or missing ticker movement values on the black ticker surface.
- `apps/web/components/market-ticker.test.tsx` verifies the neutral ticker movement class.

## Final Sample Highlights

| Sample | Light ratio | Dark ratio | Result |
|---|---:|---:|---|
| Home heading | 20.01 | 19.06 | Pass |
| Ticker label on black | 8.27 | 8.27 | Pass |
| Ticker movement on black | 6.37 | 6.37 | Pass |
| Ticker neutral on black | 14.25 | 14.25 | Pass |
| Market table header | 4.76 | 7.41 | Pass |
| Settings description | 4.76 | 7.76 | Pass |
| Instrument large movement | 3.30 | 5.76 | Pass as large text |
| Watchlist table header | 4.76 | 7.41 | Pass |
| Watchlist button | 17.06 | 19.06 | Pass |

The instrument movement value in light theme measured `3.30:1` at `24px` bold, so it passes WCAG AA for large text (`3:1`) but not normal-text AA. If the same market movement color is later used for smaller text on a white background, it should be rechecked or darkened.

## Result

The sampled light and dark theme states satisfy WCAG AA for their text sizes after the ticker neutral-text fix. This is a targeted representative pass, not a full automated accessibility audit of every possible page state.
