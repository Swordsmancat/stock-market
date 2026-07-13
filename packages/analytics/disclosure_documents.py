from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader


DEFAULT_MAX_PAGES = 500
DEFAULT_MAX_TOTAL_CHARS = 5_000_000
DEFAULT_MAX_SECTION_CHARS = 4_000
DEFAULT_MAX_SECTIONS = 2_000
EXTRACTION_METHOD = "pypdf"
HEADING_PATTERN = re.compile(
    r"^(?:第[一二三四五六七八九十百千万0-9]+[章节篇]|"
    r"[0-9]+(?:\.[0-9]+)*[、.．\s]+|"
    r"[一二三四五六七八九十]+、)"
)
TOPIC_KEYWORDS = {
    "risks": (
        "风险因素",
        "重大风险提示",
        "可能面对的风险",
        "risk factors",
        "principal risks",
    ),
    "financials": (
        "主要财务数据",
        "财务报表",
        "资产负债表",
        "利润表",
        "现金流量表",
        "financial statements",
        "financial highlights",
    ),
    "operations": (
        "管理层讨论与分析",
        "经营情况讨论与分析",
        "主营业务",
        "业务概要",
        "management discussion",
        "business overview",
    ),
    "major_events": (
        "重要事项",
        "重大事项",
        "公司治理",
        "material events",
        "corporate governance",
    ),
}


@dataclass(frozen=True)
class ExtractedDisclosureSection:
    section_index: int
    page_number: int
    heading: str
    topic: str
    content_text: str
    content_hash: str


@dataclass(frozen=True)
class DisclosureExtractionResult:
    status: str
    page_count: int | None
    sections: list[ExtractedDisclosureSection]
    diagnostics: list[dict[str, object]]
    extraction_method: str = EXTRACTION_METHOD


def extract_disclosure_pdf_sections(
    content: bytes,
    *,
    max_pages: int = DEFAULT_MAX_PAGES,
    max_total_chars: int = DEFAULT_MAX_TOTAL_CHARS,
    max_section_chars: int = DEFAULT_MAX_SECTION_CHARS,
    max_sections: int = DEFAULT_MAX_SECTIONS,
) -> DisclosureExtractionResult:
    limits = (max_pages, max_total_chars, max_section_chars, max_sections)
    if any(limit <= 0 for limit in limits):
        raise ValueError("PDF extraction limits must be positive.")
    try:
        reader = PdfReader(BytesIO(content), strict=False)
    except Exception as error:
        return _failed_result(
            "PDF_PARSE_FAILED",
            f"PDF parsing failed: {error.__class__.__name__}.",
        )

    if reader.is_encrypted:
        try:
            decrypted = reader.decrypt("")
        except Exception:
            decrypted = 0
        if not decrypted:
            return _failed_result(
                "PDF_ENCRYPTED",
                "PDF is encrypted and cannot be extracted without credentials.",
            )

    try:
        page_count = len(reader.pages)
    except Exception as error:
        return _failed_result(
            "PDF_PAGE_TREE_FAILED",
            f"PDF page tree could not be read: {error.__class__.__name__}.",
        )
    if page_count > max_pages:
        return _rejected_result(
            "PDF_PAGE_LIMIT_EXCEEDED",
            f"PDF has {page_count} pages, above the {max_pages}-page extraction limit.",
            page_count=page_count,
        )

    page_texts: list[tuple[int, str]] = []
    total_chars = 0
    try:
        for page_number, page in enumerate(reader.pages, start=1):
            normalized = _normalize_page_text(page.extract_text() or "")
            total_chars += len(normalized)
            if total_chars > max_total_chars:
                return _rejected_result(
                    "PDF_TEXT_LIMIT_EXCEEDED",
                    f"PDF extracted text exceeds the {max_total_chars}-character limit.",
                    page_count=page_count,
                )
            if normalized:
                page_texts.append((page_number, normalized))
    except Exception as error:
        return _failed_result(
            "PDF_TEXT_EXTRACTION_FAILED",
            f"PDF text extraction failed: {error.__class__.__name__}.",
            page_count=page_count,
        )

    if not page_texts:
        return DisclosureExtractionResult(
            status="no_text",
            page_count=page_count,
            sections=[],
            diagnostics=[
                {
                    "source": "pdf_extraction",
                    "status": "no_text",
                    "severity": "warning",
                    "code": "PDF_NO_EXTRACTABLE_TEXT",
                    "message": "PDF contains no extractable text; OCR is not enabled.",
                }
            ],
        )

    extracted_sections: list[ExtractedDisclosureSection] = []
    for page_number, page_text in page_texts:
        page_heading = _detect_heading(page_text, page_number)
        chunks = _chunk_page_text(page_text, max_section_chars)
        for part_index, chunk in enumerate(chunks, start=1):
            heading = page_heading if len(chunks) == 1 else f"{page_heading} (part {part_index})"
            extracted_sections.append(
                ExtractedDisclosureSection(
                    section_index=len(extracted_sections),
                    page_number=page_number,
                    heading=heading[:512],
                    topic=_classify_topic(f"{heading}\n{chunk}"),
                    content_text=chunk,
                    content_hash=hashlib.sha256(chunk.encode("utf-8")).hexdigest(),
                )
            )
            if len(extracted_sections) > max_sections:
                return _rejected_result(
                    "PDF_SECTION_LIMIT_EXCEEDED",
                    f"PDF produces more than the {max_sections}-section extraction limit.",
                    page_count=page_count,
                )

    return DisclosureExtractionResult(
        status="extracted",
        page_count=page_count,
        sections=extracted_sections,
        diagnostics=[
            {
                "source": "pdf_extraction",
                "status": "ok",
                "severity": "info",
                "code": "PDF_TEXT_EXTRACTED",
                "message": (
                    f"Extracted {len(extracted_sections)} page-anchored sections "
                    f"from {page_count} PDF pages."
                ),
            }
        ],
    )


def _normalize_page_text(value: str) -> str:
    lines: list[str] = []
    previous = None
    for raw_line in value.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = " ".join(raw_line.replace("\x00", "").split()).strip()
        if not line or line == previous:
            continue
        lines.append(line)
        previous = line
    return "\n".join(lines)


def _chunk_page_text(value: str, limit: int) -> list[str]:
    chunks: list[str] = []
    current = ""
    for line in value.splitlines():
        remaining = line
        while remaining:
            available = limit - len(current) - (1 if current else 0)
            if available <= 0:
                chunks.append(current)
                current = ""
                available = limit
            piece = remaining[:available]
            current = f"{current}\n{piece}" if current else piece
            remaining = remaining[available:]
            if len(current) >= limit:
                chunks.append(current)
                current = ""
    if current:
        chunks.append(current)
    return chunks


def _detect_heading(value: str, page_number: int) -> str:
    lines = value.splitlines()
    for line in lines[:8]:
        candidate = line.strip()
        if len(candidate) <= 120 and HEADING_PATTERN.match(candidate):
            return candidate
    if lines:
        first = lines[0].strip()
        if 2 <= len(first) <= 80 and not first.endswith(("。", ".", "；", ";", "：", ":")):
            return first
    return f"Page {page_number}"


def _classify_topic(value: str) -> str:
    normalized = value.casefold()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(keyword.casefold() in normalized for keyword in keywords):
            return topic
    return "other"


def _failed_result(
    code: str,
    message: str,
    *,
    page_count: int | None = None,
) -> DisclosureExtractionResult:
    return DisclosureExtractionResult(
        status="failed",
        page_count=page_count,
        sections=[],
        diagnostics=[
            {
                "source": "pdf_extraction",
                "status": "failed",
                "severity": "warning",
                "code": code,
                "message": message,
            }
        ],
    )


def _rejected_result(
    code: str,
    message: str,
    *,
    page_count: int | None = None,
) -> DisclosureExtractionResult:
    return DisclosureExtractionResult(
        status="rejected",
        page_count=page_count,
        sections=[],
        diagnostics=[
            {
                "source": "pdf_extraction",
                "status": "rejected",
                "severity": "warning",
                "code": code,
                "message": message,
            }
        ],
    )
