# Investment calendar implementation

1. Load backend and frontend Trellis specifications and inspect existing calendar, disclosure, watchlist, API-client, navigation, localization, and test patterns.
2. Add the database-only investment-calendar service, router, response contract, and focused backend tests.
3. Add shared frontend calendar types/query helpers and focused tests.
4. Build the localized server route and accessible responsive month/agenda client component.
5. Add desktop navigation, breadcrumb mapping, and Chinese/English messages without changing mobile navigation count.
6. Run formatting, lint, type checking, backend/frontend tests, and full-scope Trellis Check; fix findings.
7. Run the normal stack, verify API output, and visually inspect desktop/mobile light/dark pages and overflow.
8. Review spec learnings, prepare a scoped commit plan, and finish the Trellis task without including unrelated dirty files.

## Rollback points

- The endpoint is additive and can be removed without changing existing schemas or consumers.
- The frontend route and sidebar entry are additive and can be reverted independently of stored data.
