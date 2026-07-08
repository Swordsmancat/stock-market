# Frontend UI Polish - Design Document

## Architecture Overview

### Design System Foundation

**Color System - Market Movement Colors**
```typescript
// Color scheme types
type ColorScheme = "china" | "international";

// Color definitions
const MARKET_COLORS = {
  china: {
    up: "text-green-600 dark:text-green-400",
    down: "text-red-600 dark:text-red-400",
    upBg: "bg-green-50 dark:bg-green-950",
    downBg: "bg-red-50 dark:bg-red-950",
  },
  international: {
    up: "text-red-600 dark:text-red-400", 
    down: "text-green-600 dark:text-green-400",
    upBg: "bg-red-50 dark:bg-red-950",
    downBg: "bg-green-50 dark:bg-green-950",
  },
};
```

**Typography Scale**
```css
/* Data hierarchy */
.data-primary: 28-32px, font-bold     /* Core values */
.data-secondary: 16-20px, font-medium /* Supporting data */
.data-tertiary: 12-14px, font-normal  /* Labels and metadata */
```

**Spacing System**
```css
/* Card padding reduction */
Current: p-4 (16px)
Target: p-2 (8px) for dense layouts, p-3 (12px) for medium

/* Grid gaps */
Desktop: gap-3 (12px)
Mobile: gap-2 (8px)
```

### Component Architecture

**Market Color Hook**
```typescript
// hooks/use-market-colors.ts
export function useMarketColors() {
  const [colorScheme, setColorScheme] = useState<ColorScheme>("china");
  
  // Load from platform settings
  useEffect(() => {
    loadPlatformSettings().then(settings => {
      setColorScheme(settings.color_scheme || "china");
    });
  }, []);
  
  const colors = MARKET_COLORS[colorScheme];
  
  return {
    colorScheme,
    setColorScheme,
    getMovementColor: (value: number) => value >= 0 ? colors.up : colors.down,
    getMovementBg: (value: number) => value >= 0 ? colors.upBg : colors.downBg,
  };
}
```

**Market Color Context**
```typescript
// context/market-colors-context.tsx
const MarketColorsContext = createContext<MarketColorsContextValue | null>(null);

export function MarketColorsProvider({ children }) {
  const marketColors = useMarketColors();
  return (
    <MarketColorsContext.Provider value={marketColors}>
      {children}
    </MarketColorsContext.Provider>
  );
}
```

## Page-Specific Designs

### 1. Homepage (Market Dashboard)

**Layout Changes**
```
Before: 5-column grid (xl:grid-cols-5)
After:  6-8 column grid (xl:grid-cols-8 2xl:grid-cols-10)

Information density increase: 10 cards → 15-20 cards visible
```

**Index Card Redesign**
```tsx
// Compact index card
<div className="rounded border p-2 hover:bg-muted/50 transition-colors">
  <div className="flex items-start justify-between gap-2 mb-2">
    <div className="text-xs text-muted-foreground">{name}</div>
    <Badge variant="outline" className="text-[10px] px-1 py-0">{freshness}</Badge>
  </div>
  <div className={cn("text-3xl font-bold", colors.getMovementColor(movement))}>
    {formatNumber(close)}
  </div>
  <div className="text-xs text-muted-foreground mt-1">
    {formatMovement(movement)}
  </div>
  <CompactChart data={bars} height={60} />
</div>
```

**Responsive Grid**
```css
/* Breakpoint-specific columns */
xl:grid-cols-8    /* >1280px: 8 columns */
lg:grid-cols-6    /* 1024-1279px: 6 columns */
md:grid-cols-4    /* 768-1023px: 4 columns */
sm:grid-cols-2    /* <768px: 2 columns */
```

### 2. Instrument Detail Page

**Data Sections Layout**
```
┌────────────────────────────────────┐
│ Compact Header (Symbol, Price)    │
├────────────────────────────────────┤
│ Main Chart (Larger, cleaner)      │
├────────────────────────────────────┤
│ Data Grid (4 columns)              │
│ [Open] [High] [Low] [Volume]      │
├────────────────────────────────────┤
│ Technical Indicators (Compact)     │
└────────────────────────────────────┘
```

**Header Optimization**
```tsx
<div className="border-b pb-3 mb-4">
  <div className="flex items-baseline gap-3">
    <h1 className="text-4xl font-bold">{symbol}</h1>
    <span className="text-muted-foreground">{name}</span>
  </div>
  <div className="flex items-baseline gap-4 mt-2">
    <div className={cn("text-3xl font-bold", colors.getMovementColor(change))}>
      {formatPrice(price)}
    </div>
    <div className="text-sm text-muted-foreground">
      {formatMovement(change, percent)}
    </div>
  </div>
</div>
```

### 3. Watchlist Page

**Table-Based Layout** (replacing card grid)
```tsx
<Table>
  <TableHeader>
    <TableRow className="text-xs">
      <TableHead>Symbol</TableHead>
      <TableHead>Name</TableHead>
      <TableHead className="text-right">Price</TableHead>
      <TableHead className="text-right">Change</TableHead>
      <TableHead className="text-right">Change %</TableHead>
      <TableHead>Chart</TableHead>
      <TableHead>Actions</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    {items.map(item => (
      <TableRow key={item.symbol} className="hover:bg-muted/50">
        <TableCell className="font-mono font-medium">{item.symbol}</TableCell>
        <TableCell className="text-sm text-muted-foreground">{item.name}</TableCell>
        <TableCell className="text-right font-mono">{item.price}</TableCell>
        <TableCell className={cn("text-right", colors.getMovementColor(item.change))}>
          {formatChange(item.change)}
        </TableCell>
        <TableCell className={cn("text-right", colors.getMovementColor(item.change))}>
          {formatPercent(item.changePercent)}
        </TableCell>
        <TableCell><MiniChart data={item.bars} height={40} /></TableCell>
        <TableCell><Button variant="ghost" size="sm">Details</Button></TableCell>
      </TableRow>
    ))}
  </TableBody>
</Table>
```

### 4. Settings Page

**Color Scheme Setting**
```tsx
<Card>
  <CardHeader>
    <CardTitle>Display Preferences</CardTitle>
  </CardHeader>
  <CardContent>
    <div className="space-y-4">
      <div>
        <label className="text-sm font-medium">Market Color Scheme</label>
        <RadioGroup value={colorScheme} onValueChange={setColorScheme}>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="china" id="china" />
            <Label htmlFor="china">
              China Convention
              <span className="ml-2 text-xs">
                <span className="text-green-600">Up</span> / 
                <span className="text-red-600">Down</span>
              </span>
            </Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="international" id="international" />
            <Label htmlFor="international">
              International Convention
              <span className="ml-2 text-xs">
                <span className="text-red-600">Up</span> / 
                <span className="text-green-600">Down</span>
              </span>
            </Label>
          </div>
        </RadioGroup>
      </div>
    </div>
  </CardContent>
</Card>
```

## Chart Component Redesigns

### CompactCandlestickChart Improvements

**Visual Changes**
- Candlestick width: thinner (1-2px)
- Grid opacity: 0.1 → 0.05 (more subtle)
- Height reduction: current → 60-80px
- Remove unnecessary padding

**Color Integration**
```typescript
const chartColors = useMarketColors();

const config = {
  upColor: chartColors.colorScheme === "china" ? "#16a34a" : "#dc2626",
  downColor: chartColors.colorScheme === "china" ? "#dc2626" : "#16a34a",
  // ...
};
```

## Backend Integration

### Platform Settings Schema

**Add color_scheme field**
```python
# packages/services/platform_settings.py
DEFAULTS: dict[str, Any] = {
    # ... existing fields
    "color_scheme": "china",  # "china" | "international"
}
```

**API Endpoint** (already exists at `/settings/platform`)

### Frontend API Client

```typescript
// lib/platform-settings-store.ts
export type PlatformSettings = {
  // ... existing fields
  color_scheme?: "china" | "international";
};

export async function updateColorScheme(scheme: "china" | "international") {
  const current = await getPlatformSettings();
  return updatePlatformSettings({
    ...current,
    color_scheme: scheme,
  });
}
```

## Animation Specifications

**Transition Classes**
```css
/* Component transitions */
.transition-base: transition-all duration-200 ease-in-out
.transition-colors: transition-colors duration-150
.hover-lift: hover:translate-y-[-1px] transition-transform

/* Loading states */
.animate-pulse: opacity pulse animation
.skeleton: bg-muted animate-pulse rounded
```

**Usage Examples**
```tsx
// Card hover
<div className="transition-colors hover:bg-muted/50">

// Data update
<div className="transition-all duration-300">
  {value}
</div>

// Button interaction
<Button className="hover:scale-105 transition-transform">
```

## Loading States

### Skeleton Components

```tsx
function IndexCardSkeleton() {
  return (
    <div className="rounded border p-2">
      <Skeleton className="h-3 w-24 mb-2" />
      <Skeleton className="h-8 w-32 mb-1" />
      <Skeleton className="h-3 w-20 mb-2" />
      <Skeleton className="h-16 w-full" />
    </div>
  );
}
```

## Migration Strategy

**Phase 1: Foundation**
1. Add color_scheme to backend
2. Create useMarketColors hook
3. Create MarketColorsProvider
4. Add color scheme setting UI

**Phase 2: Homepage**
1. Optimize index card layout (6-8 columns)
2. Reduce card padding
3. Integrate market colors
4. Add loading skeletons

**Phase 3: Other Pages**
1. Apply to detail page
2. Refactor watchlist to table
3. Update all chart components
4. Add transition animations

**Phase 4: Polish**
1. Test responsive layouts
2. Verify WCAG contrast ratios
3. Performance optimization
4. Cross-browser testing

## Technical Constraints

- No external animation libraries (use CSS only)
- Maintain existing API contracts
- Support SSR (Next.js 16)
- Keep bundle size minimal
- Preserve accessibility features

## Rollback Plan

If issues arise:
1. Color scheme: defaults to "china", user can switch back
2. Layout: responsive grid degrades gracefully
3. Components: old components remain, new ones parallel
4. All changes are additive, not destructive
