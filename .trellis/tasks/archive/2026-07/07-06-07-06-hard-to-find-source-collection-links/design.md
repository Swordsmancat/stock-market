# Design: Hard-to-Find Source Collection Links

## Boundary

This slice turns the existing source-readiness registry into a practical collection guide. It does not ingest external data. It only exposes official/legal links, collection instructions, and AI citation boundaries so the user knows where to gather missing macro and document evidence.

## Payload Shape

Add optional fields to each `information_sources.items[]` entry:

```json
{
  "collection_links": [
    {
      "label": "FRED DGS10",
      "url": "https://fred.stlouisfed.org/series/DGS10",
      "source_type": "official_series"
    }
  ],
  "collection_note": "Review DGS10, DGS2, and T10Y2Y observations before seeding rates data.",
  "citation_policy": "Can be cited only after a reviewed observation is stored locally."
}
```

The same fields appear inside grouped items because groups reuse the source item objects.

## Backend

- Extend `SourceDefinition` in `packages/services/information_sources.py`.
- Add a small `SourceCollectionLink` dataclass or tuple-friendly type.
- Include `collection_links`, `collection_note`, and `citation_policy` in `_build_source_item()`.
- Keep readiness and evidence-count logic unchanged.
- Avoid live network calls.

## Frontend

- Extend `InformationSourceItem` in `apps/web/app/[locale]/page.tsx`.
- Render collection note and citation policy inside each source readiness item.
- Render `collection_links` as external links with `target="_blank"` and `rel="noreferrer"`.
- Add i18n labels for collection guidance, citation policy, and official sources.

## Tests

- Backend: update `tests/services/test_information_sources_service.py`.
- API/dashboard: existing dashboard API should still pass; add assertion if needed.
- Frontend: update homepage test fixture and assertions.
- Validation: run focused pytest, focused web test, TypeScript, ruff, and diff check.

## Compatibility

The fields are additive. Old consumers that ignore them keep working.

