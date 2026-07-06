# Visual Evidence

Run context:

- Date/time: 2026-07-05 23:50 Asia/Shanghai
- Local URL: `http://127.0.0.1:3000`
- Theme used for screenshot artifacts: dark; light and dark themes are both covered by `contrast-evidence.md`
- Viewports: desktop `1440x900`, mobile `390x844`
- Raw observation file: `browser-observations.json`

## Screenshot Artifacts

The screenshots were generated into the task directory with the browser evidence pass. The generation command checked that every output file was non-empty.

| Route | Desktop artifact | Mobile artifact |
|---|---|---|
| `/zh` | `screenshots/home-desktop-1440x900.png` | `screenshots/home-mobile-390x844.png` |
| `/zh/settings` | `screenshots/settings-desktop-1440x900.png` | `screenshots/settings-mobile-390x844.png` |
| `/zh/instruments/AAPL` | `screenshots/instrument-aapl-desktop-1440x900.png` | `screenshots/instrument-aapl-mobile-390x844.png` |
| `/zh/watchlist` | `screenshots/watchlist-desktop-1440x900.png` | `screenshots/watchlist-mobile-390x844.png` |

## Browser Observations

All tested routes rendered their expected route-specific text:

Correct UTF-8 labels: `/zh` = `首页概览`, `/zh/settings` = `设置`, `/zh/instruments/AAPL` = `AAPL`, `/zh/watchlist` = `关注`.

- `/zh`: `首页概览`
- `/zh/settings`: `设置`
- `/zh/instruments/AAPL`: `AAPL`
- `/zh/watchlist`: `关注`

All tested route/viewport pairs had:

- no captured console errors;
- no `Unhandled Runtime Error`, `Application error`, or `Runtime Error` text;
- no document/body horizontal overflow.

Notes:

- `/zh` intentionally contains a horizontally scrollable market ticker. The ticker contents exceed the viewport, but `documentElement.scrollWidth` equals `clientWidth` and `body.scrollWidth` equals `clientWidth` at both tested widths.
- `/zh/watchlist` mobile intentionally contains a wide data table. The table is wider than the viewport, but it does not create document/body horizontal overflow.
- `/zh/settings` exposes `color_scheme` values `china` and `international`, and the `tushare_http_url` input was present in both viewport checks.

## Result

The remaining visual-evidence requirement is satisfied for the selected MVP routes and viewports. This evidence does not claim professional-terminal parity; it only closes the durable screenshot/runtime/overflow proof for the current dashboard UI.
