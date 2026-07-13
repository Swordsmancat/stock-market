from packages.analytics.disclosure_documents import extract_disclosure_pdf_sections
from tests.helpers.pdf_factory import make_pdf


def test_extract_disclosure_pdf_sections_anchors_text_to_pages_and_topics():
    content = make_pdf(
        [
            "1. Risk Factors Material risks include customer concentration.",
            "2. Financial Statements Revenue and cash flow information.",
        ]
    )

    result = extract_disclosure_pdf_sections(content)

    assert result.status == "extracted"
    assert result.page_count == 2
    assert [item.page_number for item in result.sections] == [1, 2]
    assert [item.topic for item in result.sections] == ["risks", "financials"]
    assert all(len(item.content_hash) == 64 for item in result.sections)


def test_extract_disclosure_pdf_sections_reports_no_text_without_ocr():
    result = extract_disclosure_pdf_sections(make_pdf([""]))

    assert result.status == "no_text"
    assert result.sections == []
    assert result.diagnostics[0]["code"] == "PDF_NO_EXTRACTABLE_TEXT"


def test_extract_disclosure_pdf_sections_rejects_encrypted_and_malformed_pdfs():
    encrypted = extract_disclosure_pdf_sections(make_pdf(["secret"], password="password"))
    malformed = extract_disclosure_pdf_sections(b"%PDF-not-valid")

    assert encrypted.status == "failed"
    assert encrypted.diagnostics[0]["code"] == "PDF_ENCRYPTED"
    assert malformed.status == "failed"
    assert malformed.diagnostics[0]["code"] == "PDF_PARSE_FAILED"


def test_extract_disclosure_pdf_sections_enforces_page_text_and_section_limits():
    two_pages = make_pdf(["page one", "page two"])
    page_limited = extract_disclosure_pdf_sections(two_pages, max_pages=1)
    text_limited = extract_disclosure_pdf_sections(two_pages, max_total_chars=5)
    section_limited = extract_disclosure_pdf_sections(
        make_pdf(["a long page of extracted text"]),
        max_section_chars=4,
        max_sections=1,
    )

    assert page_limited.status == "rejected"
    assert page_limited.diagnostics[0]["code"] == "PDF_PAGE_LIMIT_EXCEEDED"
    assert text_limited.status == "rejected"
    assert text_limited.diagnostics[0]["code"] == "PDF_TEXT_LIMIT_EXCEEDED"
    assert section_limited.status == "rejected"
    assert section_limited.sections == []
    assert section_limited.diagnostics[0]["code"] == "PDF_SECTION_LIMIT_EXCEEDED"
