# Homepage macro favorites and AI research entry design

## Architecture And Boundaries

This is a frontend-focused slice under `apps/web`.

- Homepage page: `apps/web/app/[locale]/page.tsx`
- Recommendation card: `apps/web/components/smart-recommendations.tsx`
- Recommendation tests: `apps/web/components/smart-recommendations.test.tsx`
- Homepage page tests: `apps/web/app/[locale]/page.test.tsx`
- Translations: `apps/web/messages/en.json`, `apps/web/messages/zh.json`

Backend contracts should remain unchanged. The task should reuse existing payloads from `/dashboard/market-overview`, `/recommendations`, platform settings, and the existing `/ai-research` route.

## Data Flow

Current homepage flow stays intact:

1. Server page loads platform settings and market overview payload.
2. Favorite macro rows are derived from local settings and `macro_indicators` / `valuation_indicators`.
3. Recommendation items come from `/recommendations`.
4. Homepage renders `SmartRecommendations`, macro favorites, dashboard brief, and other dashboard sections.

The planned change adds navigation affordances only:

- Add a localized homepage link to `/ai-research`.
- Optionally add the same localized link in the favorite macro module if layout remains clean.
- Pass localized labels to `SmartRecommendations` or move its shell text into a translation-aware path without changing recommendation item payloads.

## Compatibility

- Preserve `/evidence` as the Macro Research route.
- Preserve `/ai-research` route and current AI Research Desk API composition.
- Preserve recommendation item shape and existing optional props.
- Preserve default favorite macro indicator behavior and settings persistence.

## Trade-Offs

- Passing label props into `SmartRecommendations` keeps the component easy to test without a Next Intl provider and avoids changing other client-component wiring.
- Using `useTranslations` inside `SmartRecommendations` would reduce prop plumbing, but it forces all isolated tests and future consumers to provide an intl provider. For this small component, label props are lower-risk.
- Adding links rather than query-param preselection keeps this slice small. Query-driven preselection can be a follow-up if the user wants the homepage to open AI Research with a specific macro/stock basket.

## Safety

UI copy should describe AI as research assistance. It must not imply direct trading instructions, target prices, position sizing, or execution advice. Source-readiness and source-capability guidance remains collection guidance, not citable evidence.

## Rollback

The homepage AI entry and localized recommendation labels are isolated frontend changes. If layout or localization regresses, revert the touched frontend files without touching backend services or the pre-existing dirty assistant files.
