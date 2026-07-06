# Dashboard Visual Evidence and WCAG Contrast - Design

## Evidence strategy

This task uses browser evidence rather than code changes as the primary artifact. The browser pass should verify that already-implemented UI surfaces render correctly and that the remaining evidence-only acceptance criteria can be closed or converted into focused follow-up tasks.

## Routes and viewport matrix

| Route | Desktop 1440x900 | Mobile 390x844 | Purpose |
| --- | --- | --- | --- |
| `/zh` | required | required | Homepage ticker, market overview, hot sectors, dashboard density |
| `/zh/settings` | required | required | Market-color setting controls, platform configuration form |
| `/zh/instruments/AAPL` | required | required | Instrument detail, chart workspace, assistant, key data values |
| `/zh/watchlist` | required | required | Watchlist table/form layout and navigation |

## Contrast sampling model

Sample representative element types rather than every DOM node:

- primary text on page background;
- muted/descriptive text on page/card background;
- movement-positive, movement-negative, and neutral values;
- ticker text on black background;
- table header/body text;
- button and form control labels;
- selected radio/control states in settings.

If an automated contrast helper is practical, record exact foreground/background and ratio. If not, record the pass as manual/browser evidence and avoid overclaiming exact WCAG compliance.

## Artifact storage

Preferred evidence location:

- `.trellis/tasks/07-05-dashboard-visual-evidence-wcag/evidence/`

Recommended files:

- screenshots named by route, viewport, and theme when applicable;
- `visual-evidence.md` for observations and screenshot index;
- `contrast-evidence.md` for sampled contrast states and outcomes.

## Safety constraints

- Browser evidence may require an existing dev server. Reuse a healthy existing server when possible; avoid starting duplicate servers.
- If screenshots expose local-only state, keep them inside the Trellis task directory and do not publish externally.
- Do not fix broad UI design issues inside this evidence task unless the fix is small and directly needed to close a documented evidence failure.
