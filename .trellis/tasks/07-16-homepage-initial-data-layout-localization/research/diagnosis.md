# Homepage diagnosis

Captured on 2026-07-16 against the normal local 3000/8000 stack using GET-only
runtime probes.

## Initial Data

- Homepage optional timeout: 5000 ms for every read.
- Cold `/dashboard/market-overview`: HTTP 200 in 6776 ms and 8866 ms on two
  independent cold-cache probes.
- Warm requests: HTTP 200 in 132 ms and 120 ms.
- Initial browser render: explicit overview failure and 47 `暂无` occurrences.
- Warm browser render: no overview failure; China and USA Buffett values present.

Conclusion: the first page discards a valid cold response before it arrives.
The data is not absent and homepage GET must not be converted into a mutation.

## Layout

- Viewport: 1440x1000; main content width: 1216 px and already full-width.
- Successful-load bottom panels: top 588, bottom 816, height 228.
- About 184 px remained unused below the panel grid.

Conclusion: removing the provider strip exposed that six fixed-height modules
were compressed into a three-column, two-row grid. A two-column, three-row
desktop grid uses the viewport for real content without stretching charts.

## Localization

The Chinese macro panel rendered backend English names and raw codes. The
catalog has nine built-in favorite codes, including `us_2y_yield`, but no
homepage-specific built-in name translations exist. Localization belongs at the
UI rendering boundary; stored evidence names and codes remain unchanged.
