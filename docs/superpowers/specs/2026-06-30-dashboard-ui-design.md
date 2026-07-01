# Dashboard (Home) Page UI Design

## Overview
This document outlines the UI redesign for the Dashboard (Home) page (`apps/web/app/page.tsx`) of the Stock Analysis Platform. The goal is to transform the current raw vertical list into a modern, scannable, card-based dashboard using Tailwind CSS and shadcn/ui.

## Architecture: Grid Layout with Cards

The dashboard will use a responsive CSS Grid to organize data into logical "widgets" (Cards).

### 1. Page Header
- **Left:** Page Title ("Dashboard").
- **Right:** Action buttons grouped together:
  - "Trigger Mock Ingestion"
  - "Refresh Analysis"

### 2. Row 1: Summary Metrics (Top KPIs)
A row of small, high-level metric cards (using a 1x3 or 1x4 grid on desktop).
- **Latest Price:** Shows the primary instrument's latest close price.
- **Portfolio Value:** Shows the total simulated portfolio value.
- **Task Status:** Shows the status and duration of the latest automated task run.

### 3. Row 2: Main Content & Overview
A split row (e.g., 2/3 width for reports, 1/3 width for lists).
- **Left Column (AI Reports):**
  - A large card containing the AI Report and Daily Report.
  - Uses a `ScrollArea` if the markdown content is too long.
  - Citations rendered as neat links or footnotes.
- **Right Column (Market Overview):**
  - A card listing the available instruments.
  - Instruments displayed as clickable rows or badges linking to their detail pages.

### 4. Row 3: Detailed Metrics
A row of cards for specific analysis domains (1x3 grid on desktop).
- **Technical Indicators:** Displays MA, RSI, BOLL, ATR in a clean list or small grid.
- **Fundamentals:** Displays the fundamental summary text.
- **News Sentiment:** Displays the latest news title, sentiment (using colored badges: Green for positive, Red for negative), and confidence score.

## Technology Stack

- **Framework:** Next.js (App Router) Server Components.
- **Styling:** Tailwind CSS (Grid, Flexbox, Typography).
- **UI Components (shadcn/ui):**
  - `Card` (CardHeader, CardTitle, CardContent) for widgets.
  - `Badge` for statuses and sentiment.
  - `Button` for actions (already installed).
  - `ScrollArea` for long text content.
- **Icons:** Lucide React (e.g., `TrendingUp`, `Activity`, `Newspaper`, `Briefcase`, `CheckCircle`).

## Implementation Details

### Data Fetching
The existing server-side data fetching logic in `page.tsx` using `Promise.all` will remain unchanged. The fetched data payloads will simply be mapped to the new UI components instead of raw HTML tags.

### Component Structure
```tsx
<main className="space-y-6">
  <div className="flex justify-between items-center">
    <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
    <div className="flex gap-2">
      <IngestionButton />
      <AnalysisRefreshButton />
    </div>
  </div>

  {/* Row 1: KPIs */}
  <div className="grid gap-4 md:grid-cols-3">
    <Card>...</Card> {/* Price */}
    <Card>...</Card> {/* Portfolio */}
    <Card>...</Card> {/* Tasks */}
  </div>

  {/* Row 2: Main Content */}
  <div className="grid gap-4 md:grid-cols-3">
    <Card className="md:col-span-2">...</Card> {/* AI Reports */}
    <Card className="md:col-span-1">...</Card> {/* Market Overview */}
  </div>

  {/* Row 3: Details */}
  <div className="grid gap-4 md:grid-cols-3">
    <Card>...</Card> {/* Technicals */}
    <Card>...</Card> {/* Fundamentals */}
    <Card>...</Card> {/* News */}
  </div>
</main>
```

## Next Steps for Implementation
1. Install required shadcn/ui components: `card`, `badge`, `scroll-area`.
2. Refactor `apps/web/app/page.tsx` to use the new grid layout and Card components.
3. Update `IngestionButton` and `AnalysisRefreshButton` to use shadcn/ui `Button` if they aren't already.