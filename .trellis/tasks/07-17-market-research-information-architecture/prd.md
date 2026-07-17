# Move market calendar and industry rankings out of macro research

## Goal

Keep the personal research information architecture conceptually accurate:
macro research contains macro indicators and evidence, while event timing and
industry performance live on a separate market-research surface.

## Requirements

- Remove the economic release calendar and industry ranking history from the
  Macro Research page, including their server-side data requests.
- Add a localized Market Research page that reuses the existing economic
  calendar and industry ranking panels without changing their API, persistence,
  refresh, filtering, or failure behavior.
- Provide a clear localized link between Macro Research and Market Research.
- Add breadcrumb labels for the new route.
- Keep the primary five-item mobile navigation unchanged; do not make the
  personal-use navigation denser for two secondary research tools.
- Preserve all unrelated working-tree files and active acceptance tasks.

## Acceptance criteria

- [x] `/zh/evidence` and `/en/evidence` do not fetch or render either moved module.
- [x] `/zh/market-research` and `/en/market-research` render both existing panels.
- [x] Loaded, empty, and failed states remain localized and truthful.
- [x] Macro Research exposes a visible Market Research link, and the new page
      exposes a return link.
- [x] Breadcrumbs use localized route labels.
- [x] Focused page tests, full Web tests, type checking, catalogs, and diff checks pass.
- [x] Ports 3000/8000 remain healthy after deployment.
