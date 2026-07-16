# Bug Analysis: Homepage cold data, empty layout, and macro label leakage

## 1. Root Cause Category

- **Category**: E - Implicit Assumption, with D - Test Coverage Gap.
- **Specific cause**: Every optional homepage GET shared a five-second timeout,
  although cold market-overview aggregation repeatedly took 6.8-8.9 seconds.
  The UI also assumed backend evidence names were display copy and that a
  three-column grid remained visually complete after a status strip was
  removed.

## 2. Why Earlier Reasoning Could Fail

1. Treating unavailable placeholders as provider absence would add refreshes or more sources but
   would not stop the browser from discarding an already valid cold response.
2. Stretching two fixed chart rows would move whitespace inside cards rather
   than use the viewport for more real modules.
3. Translating only loaded `item.name` values would leave the overview-failure
   projection showing raw codes because those rows have `item=null`.

## 3. Prevention Mechanisms

| Priority | Mechanism | Specific Action | Status |
|---|---|---|---|
| P0 | Test coverage | AbortSignal-aware 6s success and 20s terminal-bound server-component tests | DONE |
| P0 | UI contract | Localize all nine built-ins by code in loaded and failed projections | DONE |
| P1 | Documentation | Record named latency budgets and GET-only boundary in frontend specs | DONE |
| P1 | Browser acceptance | Lock 2x3 desktop geometry, internal scrolling, and mobile overflow checks | DONE |

## 4. Systematic Expansion

- **Similar issues**: Other cold aggregate reads should be measured before they
  inherit a timeout intended for lightweight endpoints.
- **Design improvement**: Keep timeout ownership at each fetch boundary until
  multiple endpoints have proven identical latency and failure semantics.
- **Process improvement**: Browser acceptance must distinguish genuine missing
  evidence from a failed aggregate request before adding providers or writes.

## 5. Knowledge Capture

- [x] Updated `frontend/component-guidelines.md` with read, grid, scroll, and
      macro-label contracts.
- [x] Updated `frontend/quality-guidelines.md` with deterministic timer and
      responsive-browser regression requirements.
- [x] Added focused regressions for the original three symptoms.
- [x] Confirmed no Trellis template mirror exists in this application repo.
