# CNINFO metadata adapter research

## Local dependency evidence

The installed AkShare version is `1.18.64`. It exposes:

```python
stock_zh_a_disclosure_report_cninfo(
    symbol: str = "000001",
    market: str = "沪深京",
    keyword: str = "",
    category: str = "",
    start_date: str = "20230618",
    end_date: str = "20231219",
) -> pandas.DataFrame
```

The function queries CNINFO's announcement search and returns these normalized columns:

- `代码`
- `简称`
- `公告标题`
- `公告时间`
- `公告链接`

The detail URL contains `stockCode`, `announcementId`, `orgId`, and `announcementTime`. The adapter should parse `announcementId` from the URL and use it as the external document identity.

## Boundaries

- This slice stores official publication metadata only.
- The returned detail URL is collection/citation metadata; no PDF or document body is fetched.
- A metadata citation supports only document identity, title, source, category, and publication time.
- Tests inject a fake fetch function and never call CNINFO or AkShare's network path.
- Provider schema changes, missing `announcementId`, invalid host, or invalid timestamps must be visible as sanitized diagnostics/rejections.

## Relevant project contracts

- `.trellis/spec/backend/database-guidelines.md`
- `.trellis/spec/backend/error-handling.md`
- `.trellis/spec/backend/quality-guidelines.md`
- `.trellis/spec/backend/logging-guidelines.md`
- `.trellis/spec/backend/assistant-research-citation-contract.md`
- `.trellis/spec/guides/cross-layer-thinking-guide.md`
- `.trellis/spec/guides/code-reuse-thinking-guide.md`
