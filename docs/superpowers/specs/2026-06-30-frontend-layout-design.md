# Frontend Layout & Navigation Design

## Overview
This document outlines the design for the foundational frontend layout and navigation structure of the Stock Analysis Platform. The goal is to replace the current minimal styling with a modern, responsive, and scalable UI architecture.

## Architecture: Hybrid Layout

The application will use a "Hybrid" layout pattern, separating global context from specific navigation.

### 1. Top Navigation Bar (Global Context)
Fixed at the top of the viewport.
- **Left:** Platform Logo and Name ("Stock Analysis Platform").
- **Center:** Global Search Bar (Command Menu/Combobox) for quickly searching and navigating to specific stock symbols or companies.
- **Right:** 
  - Theme Toggle (Dark/Light mode).
  - Global Notifications (e.g., task run completions).
  - User Profile / Settings dropdown.

### 2. Left Sidebar (Main Navigation)
Fixed on the left side, below the Top Bar.
- **Navigation Links:**
  - Dashboard (Home)
  - Watchlist
  - Portfolios
  - Reports
  - Task Runs
- **Behavior:** Collapsible to maximize the data visualization area (charts, tables) in the main content view.

### 3. Main Content Area
The primary viewing area occupying the remaining screen space.
- **Header:** Breadcrumbs for hierarchical context (e.g., `Home > Instruments > AAPL`).
- **Body:** The specific page content (rendered via Next.js `children`).

## Technology Stack

- **Framework:** Next.js (App Router) - *Already in place*.
- **Styling:** Tailwind CSS.
- **UI Components:** [shadcn/ui](https://ui.shadcn.com/). Chosen for its accessibility, modern aesthetic, and because components are owned within the repository rather than installed as an opaque dependency.
- **Icons:** Lucide React (standard companion to shadcn/ui).
- **Theming:** `next-themes` for dark/light mode support.

## Implementation Details

### Component Structure
The layout will be implemented primarily in `apps/web/app/layout.tsx` to ensure it wraps all pages and persists state during navigation.

```tsx
// Conceptual structure
<RootLayout>
  <ThemeProvider>
    <div className="flex h-screen flex-col">
      <TopNavBar />
      <div className="flex flex-1 overflow-hidden">
        <SidebarNavigation />
        <main className="flex-1 overflow-y-auto p-4">
          {/* Breadcrumbs */}
          {children}
        </main>
      </div>
    </div>
  </ThemeProvider>
</RootLayout>
```

### State Management
- **Theme:** Managed by `next-themes` (persisted in localStorage).
- **Sidebar State:** Managed via a React Context provider (`SidebarProvider`) to allow any component to toggle the sidebar, persisted in localStorage or cookies to remember user preference.

## Next Steps for Implementation
1. Initialize Tailwind CSS in the `apps/web` directory.
2. Initialize shadcn/ui and install required base components (button, input, dropdown-menu, sheet/dialog for mobile nav).
3. Create the `TopNavBar` and `SidebarNavigation` components.
4. Update `apps/web/app/layout.tsx` to apply the new structure.
5. Refactor the existing `page.tsx` to fit within the new content area gracefully.