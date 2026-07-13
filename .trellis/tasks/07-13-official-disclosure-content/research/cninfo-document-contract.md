# CNINFO document attachment and PDF extraction research

## Official CNINFO response evidence

On 2026-07-13, a read-only request to the official CNINFO announcement query for symbol `000001`, annual reports, and `2026-03-01..2026-05-31` returned HTTP 200 and two records. Exact announcement `1225022887` exposed:

```json
{
  "secCode": "000001",
  "announcementId": "1225022887",
  "announcementTitle": "2025年年度报告",
  "adjunctUrl": "finalpage/2026-03-21/1225022887.PDF",
  "adjunctSize": 1930,
  "adjunctType": "PDF",
  "orgId": "gssz0000001"
}
```

The normalized attachment URL `https://static.cninfo.com.cn/finalpage/2026-03-21/1225022887.PDF` returned:

- HTTP 200
- `Content-Type: application/pdf`
- `Content-Length: 1975076`
- `Last-Modified: Fri, 20 Mar 2026 12:18:17 GMT`

`adjunctSize` is retained as provider metadata rather than trusted as the byte length because its unit is not explicit in the response.

## Existing adapter evidence

AkShare 1.18.64 `stock_zh_a_disclosure_report_cninfo` calls the same official CNINFO query but deliberately projects only code, name, title, publication time, announcement ID, and org ID into a detail URL. It discards `adjunctUrl`, `adjunctSize`, and `adjunctType`. Document attachment discovery therefore needs a separate narrow official-query adapter rather than guessing a static URL from the metadata detail link.

## PDF extraction choice

- Current environment/project has no PDF library installed or declared.
- PyPI and pypdf documentation show pypdf 6.14.2 supports Python 3.9-3.14 and `PdfReader(...).pages[].extract_text()`.
- Select `pypdf>=6.14,<7` for a pure-Python, typed, text-PDF MVP.
- OCR is explicitly excluded; pypdf documentation notes text extraction is not OCR and image-only pages require a separate OCR pipeline.

## Security and evidence boundaries

- Official attachment host/path allowlist: `static.cninfo.com.cn` + `/finalpage/` + `.PDF`.
- Never accept an arbitrary URL from an API caller.
- Exact `announcementId` matching prevents title-based document substitution.
- Validate bytes and PDF signature independently of provider metadata.
- Store immutable content-addressed versions so corrections do not erase prior evidence.
- Only persisted extracted text may become `official_disclosure_section:*`; attachment discovery and stored PDF without text are not document-content citations.

## References

- Official search: `https://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search`
- Official query: `https://www.cninfo.com.cn/new/hisAnnouncement/query`
- Official static attachments: `https://static.cninfo.com.cn/finalpage/...`
- AkShare docs: `https://akshare.akfamily.xyz/data/stock/stock.html`
- pypdf extraction docs: `https://pypdf.readthedocs.io/en/latest/user/extract-text.html`
