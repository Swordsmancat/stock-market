# Provider Trust and Data SLA Dashboard - Design

## Design intent

This task is a frontend-first trust-visibility MVP. The repository already carries provider/status/freshness metadata in many payloads, so the first implementation should normalize and reveal existing metadata rather than redesigning every backend contract.

The design principle is: if data is mock, delayed, degraded, unavailable, stale, provider-derived, cached, or session-bound, the user should see that state before interpreting the number as professional-grade market data.

## Proposed frontend model

Add a pure utility module such as `apps/web/lib/data-trust.ts`.

Recommended normalized type:

```ts
export type DataTrustSeverity =
  | "ok"
  | "fresh"
  | "delayed"
  | "stale"
  | "mock"
  | "degraded"
  | "no_data"
  | "unavailable"
  | "unknown";

export interface DataTrustSignal {
  severity: DataTrustSeverity;
  label: string;
  description: string;
  source?: string | null;
  provider?: string | null;
  requestedProvider?: string | null;
  effectiveProvider?: string | null;
  asOf?: string | null;
  generatedAt?: string | null;
  reason?: string | null;
  isRealtime?: boolean;
  isDelayed?: boolean;
  delayMinutes?: number | null;
  cacheStatus?: string | null;
  sessionStatus?: string | null;
}
```

The normalizer should accept partial raw payload shapes to avoid invasive type rewrites. Example inputs:

- market overview row: `status`, `freshness`, `source`, `provider`, `requested_provider`, `effective_provider`, `no_data_reason`;
- hot sectors: `status`, `data_mode`, `source`, `provider`, `is_realtime`, `is_delayed`, `delay_minutes`, `availability`;
- intraday: `status`, `source`, `availability`, `freshness`, `session`;
- report source summary: `source`, `price_source`, `provider`;
- recommendation diagnostics: `status`, `provider`, `category`.

## Proposed UI component

Add `apps/web/components/data-trust-badge.tsx` or similarly named component.

Recommended modes:

- `compact`: a small badge with label and accessible title/aria-label.
- `summary`: badge plus provider/source/as-of/reason details for card headers.

Visual mapping should use semantic status colors, not market movement colors:

- ok/fresh: neutral or secondary badge;
- delayed/stale: amber outline;
- mock/demo: purple or slate outline;
- degraded/no_data/unavailable: warning/destructive-adjacent but not market red/green;
- unknown: muted outline.

## Integration surfaces

### Slice 1: shared model and tests

Files:

- `apps/web/lib/data-trust.ts`
- `apps/web/lib/data-trust.test.ts`
- `apps/web/components/data-trust-badge.tsx`
- `apps/web/components/data-trust-badge.test.tsx`

### Slice 2: homepage market overview and ticker

Files:

- `apps/web/components/market-overview-client.tsx`
- `apps/web/components/market-ticker.tsx`
- `apps/web/app/[locale]/page.tsx`
- relevant tests

### Slice 3: recommendations no-overclaim

Files:

- `apps/web/components/smart-recommendations.tsx`
- `apps/web/app/api/recommendations/route.ts` if extra metadata pass-through is needed
- relevant tests

### Slice 4: instrument detail and intraday

Files:

- `apps/web/lib/instrument-detail.ts`
- `apps/web/components/instrument-detail-client.tsx`
- `apps/web/components/intraday-price-chart.tsx`
- `apps/web/components/market-depth-card.tsx` if shared badge reuse is low risk
- relevant tests

### Slice 5: reports source summary

Files:

- `apps/web/app/[locale]/reports/page.tsx`
- `apps/web/app/[locale]/reports/[reportId]/page.tsx`
- `apps/web/components/generate-daily-report-button.tsx`
- report route/component tests

## Backend compatibility

Prefer additive frontend changes first. Backend changes are allowed only when existing route proxies drop trust fields or when a default provider would silently become `mock` without user visibility.

Potential backend/API follow-ups:

- keep trust metadata in Next API fallback payloads;
- add top-level `provider/source/generated_at` to recommendations;
- ensure report generation provider is explicit.

## Safety constraints

- Do not fabricate freshness, realtime status, or provider capabilities when absent.
- Unknown metadata must render as unknown/unspecified, not fresh/live.
- If `is_realtime` is not explicitly true, do not show realtime.
- If market depth provider capability is not verified, avoid Level-2 language.
- Preserve existing degraded/no-data behavior in market-depth and hot-sector components.

## Documentation impact

Update docs/manual and developer runbooks with:

- meaning of trust labels;
- why mock/delayed/degraded can appear;
- current provider validation limits;
- why professional parity still needs provider validation and SLA monitoring.
