# Phase 2/3 Remaining Work Audit

## Phase 2 - Professional Feature Enhancement

| Feature | Status | Remaining Work |
|---|---|---|
| K-line chart interactions | Mostly complete | Add MA60, add YTD range, and preserve dark-mode support. Tooltip/zoom behavior should be validated with practical tests where possible. |
| Smart recommendations | MVP complete | Add detail navigation, direct breakout/oversold coverage, and make acceptance limits explicit. |
| Hot sector rotation | Mock MVP | Add an explicit data-status contract and avoid presenting mock sector flow as real market flow. |
| Comparison analysis | Mostly complete | Add component interaction coverage and include correlation/export details in the generated report. |

## Phase 3 - Advanced Features

| Feature | Status | Remaining Work |
|---|---|---|
| Intraday chart | Not complete | Define minute-data payloads, add frontend fallback, previous close, average price, volume, and hover details. |
| Market depth data | Not complete | Define order book, trades, large-order, and fund-flow contracts with provider capability fallbacks. |
| Technical indicators | Partial | Connect MACD and KDJ end-to-end and expose configurable indicator controls. |
| AI assistant | Partial foundation | Build on the existing report generator to add a natural-language assistant with traceable context and safe response boundaries. |

## Recommended First Slice

`07-04-phase2-hardening-acceptance-closure` should run first because it closes visible gaps without introducing new provider dependencies.
