# Frontend UI Polish - Implementation Plan

## Overview

This document provides a detailed, ordered checklist for implementing the financial-style UI optimization across all pages.

## Phase 1: Foundation (Backend + Core Hooks)

### 1.1 Backend - Color Scheme Support

**File**: `packages/services/platform_settings.py`

- [ ] Add `"color_scheme": "china"` to `DEFAULTS` dict
- [ ] Add `color_scheme` field to `get_platform_settings()` return type
- [ ] Add `color_scheme` field to `update_platform_settings()` logic
- [ ] Verify backend starts without errors

**Validation**:
```bash
# Test endpoint
curl http://localhost:8000/settings/platform | jq '.color_scheme'
# Should return "china"
```

### 1.2 Frontend - Market Colors Hook

**File**: `apps/web/hooks/use-market-colors.ts` (new file)

- [ ] Create `ColorScheme` type
- [ ] Define `MARKET_COLORS` constant with china/international configs
- [ ] Implement `useMarketColors()` hook
  - [ ] State for `colorScheme`
  - [ ] `useEffect` to load from platform settings
  - [ ] `getMovementColor()` helper
  - [ ] `getMovementBg()` helper
- [ ] Export hook

**Validation**:
```typescript
// Test in a component
const { getMovementColor } = useMarketColors();
console.log(getMovementColor(1.5)); // Should log green for china
```

### 1.3 Frontend - Market Colors Context

**File**: `apps/web/context/market-colors-context.tsx` (new file)

- [ ] Create `MarketColorsContext`
- [ ] Implement `MarketColorsProvider` component
- [ ] Export `useMarketColorsContext` hook
- [ ] Add provider to root layout (`apps/web/app/[locale]/layout.tsx`)

**File**: `apps/web/app/[locale]/layout.tsx`

- [ ] Import `MarketColorsProvider`
- [ ] Wrap `{children}` with provider (inside `NextIntlClientProvider`)

**Validation**:
```typescript
// In any page component
const colors = useMarketColorsContext();
console.log(colors.colorScheme); // Should log "china"
```

## Phase 2: Settings Page - Color Scheme Switcher

### 2.1 Settings UI

**File**: `apps/web/app/[locale]/settings/page.tsx`

- [ ] Add new Card section for "Display Preferences"
- [ ] Add RadioGroup for color scheme selection
  - [ ] "China Convention" option with color preview
  - [ ] "International Convention" option with color preview
- [ ] Wire up `onValueChange` to update platform settings
- [ ] Add success toast on save

**File**: `apps/web/messages/en.json`

- [ ] Add `displayPreferencesTitle`: "Display Preferences"
- [ ] Add `colorSchemeLabel`: "Market Color Scheme"
- [ ] Add `chinaConvention`: "China Convention (Green Up / Red Down)"
- [ ] Add `internationalConvention`: "International Convention (Red Up / Green Down)"

**File**: `apps/web/messages/zh.json`

- [ ] Add Chinese translations for above keys

**Validation**:
- [ ] Open `/settings`
- [ ] See new "Display Preferences" section
- [ ] Toggle color scheme
- [ ] Refresh page, setting persists

## Phase 3: Homepage Optimization

### 3.1 Index Cards - Layout Density

**File**: `apps/web/app/[locale]/page.tsx`

**Core Indices Section**:
- [ ] Change grid from `md:grid-cols-2 xl:grid-cols-5` to `sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 2xl:grid-cols-10`
- [ ] Reduce gap from `gap-3` to `gap-2`
- [ ] Reduce card padding from `p-3` to `p-2`
- [ ] Increase font size for close price from `text-2xl` to `text-3xl font-bold`
- [ ] Reduce font size for name from `text-xs` to `text-[10px]`
- [ ] Reduce badge size (use `text-[10px] px-1 py-0`)

**Followed K-line Section**:
- [ ] Keep 2-column layout but reduce padding `p-4` → `p-3`
- [ ] Increase close price font size `text-xl` → `text-2xl font-bold`

**Validation**:
- [ ] Desktop (>1280px): Should see 8+ index cards per row
- [ ] Tablet (768-1279px): Should see 4-6 cards per row
- [ ] Mobile (<768px): Should see 2 cards per row

### 3.2 Market Colors Integration

**File**: `apps/web/app/[locale]/page.tsx`

- [ ] Import `useMarketColorsContext`
- [ ] Get `colors` from context
- [ ] Replace hardcoded movement colors with `colors.getMovementColor(movement)`
- [ ] Apply to all movement displays (indices, followed items, valuation)

**Locations to update**:
- [ ] Index card movement display
- [ ] Followed item movement display  
- [ ] Daily movement in dashboard health section

**Validation**:
- [ ] Change color scheme in settings
- [ ] Return to homepage
- [ ] All movement colors should reflect the new scheme

### 3.3 Compact Chart Height

**File**: `apps/web/components/compact-candlestick-chart.tsx`

- [ ] Change default `height` prop from current to `60` or `80`
- [ ] Reduce candlestick `strokeWidth` from `2` to `1`
- [ ] Reduce grid opacity (if configurable)

**Validation**:
- [ ] Charts should be shorter and less visually dominant
- [ ] Data points still clearly visible

## Phase 4: Instrument Detail Page

### 4.1 Header Optimization

**File**: `apps/web/app/[locale]/instruments/[symbol]/page.tsx` (or similar)

- [ ] Find header section
- [ ] Increase symbol font size to `text-4xl font-bold`
- [ ] Increase price font size to `text-3xl font-bold`
- [ ] Add market colors to price change display
- [ ] Reduce header padding

### 4.2 Data Grid Layout

- [ ] Create 4-column grid for OHLV data
- [ ] Use compact spacing `gap-2`
- [ ] Use smaller font sizes for labels `text-xs`
- [ ] Use larger font for values `text-lg font-mono`

**Validation**:
- [ ] Header is more prominent
- [ ] Data grid is scannable
- [ ] Colors match user's color scheme

## Phase 5: Watchlist Page

### 5.1 Table Layout Conversion

**File**: `apps/web/app/[locale]/watchlist/page.tsx`

- [ ] Import `Table`, `TableHeader`, `TableBody`, `TableRow`, `TableHead`, `TableCell` from shadcn
- [ ] Replace card grid with table structure
- [ ] Add columns: Symbol | Name | Price | Change | Change % | Chart | Actions
- [ ] Use `font-mono` for symbol and price columns
- [ ] Integrate market colors for change columns
- [ ] Add `hover:bg-muted/50` to table rows
- [ ] Keep mini chart in table cell (height 40px)

**Validation**:
- [ ] Watchlist displays as a data table
- [ ] Hover effect works
- [ ] Charts render correctly in table cells
- [ ] Responsive on mobile (table scrolls horizontally or stacks)

## Phase 6: All Pages - Animations

### 6.1 Add Transition Classes

**Files**: All page components

- [ ] Add `transition-colors duration-200` to clickable cards
- [ ] Add `hover:bg-muted/50` to interactive elements
- [ ] Add `transition-opacity duration-300` to loading containers
- [ ] Add `hover:scale-105 transition-transform` to primary buttons

**Validation**:
- [ ] Hover effects are smooth
- [ ] No janky animations
- [ ] No performance degradation

### 6.2 Loading Skeletons

**File**: `apps/web/components/index-card-skeleton.tsx` (new)

- [ ] Create skeleton component matching new compact card layout
- [ ] Use shadcn `Skeleton` component

**File**: `apps/web/app/[locale]/page.tsx`

- [ ] Show skeletons while `marketOverviewResult` is loading
- [ ] Replace current loading state

**Validation**:
- [ ] Refresh page, see skeleton grid
- [ ] Skeleton matches final card layout

## Phase 7: Cross-Page Polish

### 7.1 Apply Consistent Spacing

**All page files**:
- [ ] Card padding: `p-3` or `p-4` for sections, `p-2` for dense data
- [ ] Grid gaps: `gap-3` for standard, `gap-2` for compact
- [ ] Section spacing: `space-y-4` or `space-y-6`

### 7.2 Typography Consistency

- [ ] Page titles: `text-3xl font-bold`
- [ ] Section titles: `text-2xl font-semibold`
- [ ] Data primary: `text-2xl` or `text-3xl font-bold`
- [ ] Data labels: `text-xs` or `text-sm text-muted-foreground`

### 7.3 Market Colors Everywhere

**Files to check**:
- [ ] `apps/web/app/[locale]/instruments/[symbol]/page.tsx`
- [ ] `apps/web/app/[locale]/watchlist/page.tsx`
- [ ] `apps/web/components/price-chart.tsx`
- [ ] `apps/web/components/mini-price-chart.tsx`
- [ ] Any other component displaying movement data

## Phase 8: Testing & Validation

### 8.1 Functional Testing

- [ ] Color scheme toggle works and persists
- [ ] All pages respect color scheme setting
- [ ] Responsive layouts work on all breakpoints
- [ ] Charts render correctly
- [ ] No console errors
- [ ] No TypeScript errors

### 8.2 Visual Testing

- [ ] Light mode: all colors have good contrast
- [ ] Dark mode: all colors have good contrast
- [ ] Check WCAG AA compliance (contrast ratio ≥ 4.5:1 for text)
- [ ] Information hierarchy is clear
- [ ] No overlapping elements

### 8.3 Performance Testing

- [ ] Homepage loads in < 2s
- [ ] No layout shift (CLS)
- [ ] Smooth scrolling
- [ ] Animations don't block main thread

### 8.4 Cross-Browser Testing

- [ ] Chrome/Edge (Chromium)
- [ ] Firefox
- [ ] Safari (if available)

## Phase 9: Documentation & Cleanup

### 9.1 Update Documentation

- [ ] Add comment in `use-market-colors.ts` explaining usage
- [ ] Update README if needed

### 9.2 Code Cleanup

- [ ] Remove unused imports
- [ ] Remove commented-out code
- [ ] Ensure consistent formatting

### 9.3 Git Commit

- [ ] Run linter: `npm run lint:web`
- [ ] Run type check: `npm run type-check:web` (if available)
- [ ] Stage all changes
- [ ] Create descriptive commit message
- [ ] Push to remote

## Rollback Procedure

If critical issues are found:

1. **Color scheme**: Remove from platform_settings, app defaults to current behavior
2. **Layout changes**: Revert grid column changes in affected pages
3. **Component changes**: Git revert specific commits
4. **Full rollback**: `git revert <commit-sha>` and push

## Success Metrics

After completion, verify:
- [ ] Information density increased 50%+ (measure visible cards on 1920x1080 screen)
- [ ] Color scheme setting exists and works
- [ ] All 4+ major pages use consistent financial style
- [ ] Zero regression bugs reported
- [ ] Page load times unchanged or improved

## Notes

- Test each phase before moving to next
- Keep commits atomic (one phase = one commit)
- If a phase blocks, document and move to next
- Update this checklist as implementation progresses
