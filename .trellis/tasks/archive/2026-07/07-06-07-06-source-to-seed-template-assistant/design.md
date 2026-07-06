# Design: Source-to-Seed Template Assistant

## Boundary

This slice makes source collection guidance operational by showing audited seed-file templates for macro and valuation observations. It does not fetch source data, scrape websites, validate remote links, ingest documents, or write observations. The user still reviews values manually and imports them through the existing `scripts/import_market_indicator_seeds.py` path.

## Payload Shape

Add an optional field to each `information_sources.items[]` entry:

```json
{
  "seed_template": {
    "label": "FRED rates seed template",
    "description": "Prepare reviewed daily Treasury observations before importing.",
    "target_indicator_codes": ["us_10y_yield", "us_2y_yield"],
    "required_fields": ["code", "as_of", "value", "source", "components"],
    "json_template": {
      "observations": [
        {
          "code": "us_10y_yield",
          "as_of": "YYYY-MM-DD",
          "value": "<reviewed decimal>",
          "source": "Audited seed: FRED DGS10",
          "components": {
            "source_series_id": "DGS10",
            "source_url": "https://fred.stlouisfed.org/series/DGS10",
            "methodology": "<operator review note>"
          }
        }
      ]
    },
    "csv_header": ["code", "as_of", "value", "source", "components_json"],
    "csv_example_rows": [
      "us_10y_yield,YYYY-MM-DD,<reviewed decimal>,Audited seed: FRED DGS10,\"{...}\""
    ],
    "review_checklist": [
      {
        "id": "replace_placeholders",
        "label": "Replace every placeholder before import.",
        "required": true,
        "why": "The template is not an observation until reviewed values are supplied."
      },
      {
        "id": "preserve_source",
        "label": "Preserve source URL or source series ID.",
        "required": true,
        "why": "The importer requires source metadata for auditability."
      }
    ],
    "warnings": [
      "Template placeholders are not import-ready market data."
    ],
    "import_command": "python scripts/import_market_indicator_seeds.py path/to/macro-seeds.json",
    "citation_boundary": "The template is not evidence; imported observations become citeable after validation stores metadata."
  }
}
```

Groups reuse the item objects, so grouped items receive the same optional field.

## Backend

- Add a `SourceSeedTemplate` dataclass in `packages/services/information_sources.py`.
- Add `seed_template` to `SourceDefinition` with default `None`.
- Include `seed_template.to_payload()` in `_build_source_item()`.
- Define static templates for FRED rates, FRED inflation, FRED liquidity, PBOC China M2, Buffett manual valuation components, and user seed files.
- Keep `_get_source_evidence()` and `_status_for()` unchanged.
- Keep placeholders explicit. Do not use fresh-looking market values.
- Keep CSV rows syntactically shaped like the importer expects: `components_json` should show valid JSON text with placeholder values.
- Template presence must not affect `status`, `evidence_count`, `latest_as_of`, `dashboard_brief.citations`, or assistant citations.

## Frontend

- Extend `InformationSourceItem` in `apps/web/app/[locale]/page.tsx`.
- Render seed-template guidance below collection links:
  - label/description.
  - target indicator codes as badges.
  - required fields.
  - import command.
  - review checklist.
  - compact JSON template and CSV row previews.
  - citation boundary.
- Add English and Chinese i18n strings.
- Avoid a large interactive editor in this slice. Static copyable-looking code blocks are enough.

## Tests

- Backend service tests:
  - FRED rates item has seed template target codes and placeholder JSON.
  - Buffett manual valuation item has component-oriented template/checklist.
  - User seed files item has generic required fields/import command.
  - Existing statuses/evidence counts remain unchanged.
- API test:
  - dashboard payload exposes `seed_template` additively on `information_sources.items[0]`.
- Frontend test:
  - homepage renders seed-template labels, import command, a placeholder value, and target code.

## Compatibility

The field is additive. Existing consumers that ignore `seed_template` keep working.

## Risks

- Template examples could look like real data. Use placeholder values and checklist text.
- Users might think templates import automatically. Documentation and UI must say the user must review and run the import command.
- AI citations could be inflated. Keep the citation contract clear: templates are guidance only.
