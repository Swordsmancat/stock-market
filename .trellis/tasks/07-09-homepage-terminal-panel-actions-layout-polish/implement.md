# Homepage terminal panel actions and layout polish implementation plan

## Checklist

- [x] Load `trellis-before-dev` before editing implementation files.
- [x] Add localized action strings to `apps/web/messages/en.json` and `apps/web/messages/zh.json`.
- [x] Add compact module action markup in `apps/web/app/[locale]/page.tsx`.
- [x] Wire "More" links for market band, macro, hot sectors, latest news, market overview, fund flow, AI sentiment, and news source status.
- [x] Wire "Add custom indicator" in the macro panel to `/settings#favorite_macro_indicator_codes`.
- [x] Refine the middle panel body layout so Macro indicators, Hot sectors, and Latest news sentiment fit their fixed height.
- [x] Update `apps/web/app/[locale]/page.test.tsx` for action labels and href targets.
- [x] Run focused tests and static checks.
- [x] Run Chrome visual checks at `1920x1080` and `1080x1920`.

## Validation Commands

```powershell
npm run test:web -- "apps/web/app/[locale]/page.test.tsx" "apps/web/components/market-ticker.test.tsx" --reporter=dot
npx tsc -p apps/web/tsconfig.json --noEmit --ignoreDeprecations 6.0
git diff --check
```

## Visual Check Notes

- Start the web app if no usable dev server is already running.
- Prefer system Chrome if bundled Playwright browsers are unavailable:
  - `C:/Program Files/Google/Chrome/Application/chrome.exe`
- Capture or inspect desktop `1920x1080` and mobile `1080x1920`.
- Check:
  - all module actions are visible and aligned
  - middle panel bodies do not overflow their shells
  - mobile viewport has no horizontal scroll
  - empty data states remain readable

## Rollback Points

- Action labels and route changes are isolated to the homepage and locale files.
- Layout changes should be limited to existing homepage panels; avoid touching shared `Card`, `Button`, or app-wide theme tokens.
