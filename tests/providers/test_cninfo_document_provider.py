import hashlib
from datetime import datetime, timezone

import pytest

from packages.providers.cninfo_document_provider import (
    CninfoDocumentProviderError,
    DocumentHttpResponse,
    discover_cninfo_attachment,
    download_cninfo_pdf,
)


def valid_item(**overrides):
    item = {
        "secCode": "000001",
        "announcementId": "1225022887",
        "announcementTitle": "2025 annual report",
        "adjunctUrl": "finalpage/2026-03-21/1225022887.PDF",
        "adjunctSize": 1930,
        "adjunctType": "PDF",
        "announcementTypeName": "Annual report",
    }
    item.update(overrides)
    return item


def test_discover_cninfo_attachment_matches_exact_id_and_normalizes_url():
    captured = []

    def fake_post(url, *, data, timeout):
        captured.append((url, data, timeout))
        return {"totalAnnouncement": 1, "announcements": [valid_item()]}

    attachment = discover_cninfo_attachment(
        symbol="000001.SZ",
        org_id="gssz0000001",
        announcement_id="1225022887",
        published_at=datetime(2026, 3, 20, 16, tzinfo=timezone.utc),
        post_json=fake_post,
    )

    assert attachment.url == "https://static.cninfo.com.cn/finalpage/2026-03-21/1225022887.PDF"
    assert attachment.provider_size == 1930
    assert captured[0][1]["stock"] == "000001,gssz0000001"
    assert captured[0][1]["seDate"] == "2026-03-19~2026-03-23"


def test_discover_cninfo_attachment_does_not_substitute_title_match():
    def fake_post(url, *, data, timeout):
        return {
            "totalAnnouncement": 1,
            "announcements": [valid_item(announcementId="different-id")],
        }

    with pytest.raises(CninfoDocumentProviderError) as exc_info:
        discover_cninfo_attachment(
            symbol="000001",
            org_id="gssz0000001",
            announcement_id="1225022887",
            published_at=datetime(2026, 3, 21, tzinfo=timezone.utc),
            post_json=fake_post,
        )

    assert exc_info.value.code == "CNINFO_DOCUMENT_NOT_FOUND"


@pytest.mark.parametrize(
    ("overrides", "expected_code"),
    [
        ({"adjunctType": "HTML"}, "CNINFO_DOCUMENT_TYPE_REJECTED"),
        ({"adjunctUrl": "https://evil.example/a.pdf"}, "CNINFO_DOCUMENT_PATH_REJECTED"),
        ({"adjunctUrl": "finalpage/2026-03-21/other.PDF"}, "CNINFO_DOCUMENT_IDENTITY_MISMATCH"),
        ({"adjunctUrl": "../1225022887.PDF"}, "CNINFO_DOCUMENT_PATH_REJECTED"),
    ],
)
def test_discover_cninfo_attachment_rejects_unsafe_attachment(overrides, expected_code):
    def fake_post(url, *, data, timeout):
        return {"totalAnnouncement": 1, "announcements": [valid_item(**overrides)]}

    with pytest.raises(CninfoDocumentProviderError) as exc_info:
        discover_cninfo_attachment(
            symbol="000001",
            org_id="gssz0000001",
            announcement_id="1225022887",
            published_at=datetime(2026, 3, 21, tzinfo=timezone.utc),
            post_json=fake_post,
        )

    assert exc_info.value.code == expected_code


def test_discover_cninfo_attachment_sanitizes_provider_error():
    def failing_post(url, *, data, timeout):
        raise RuntimeError("raw response secret")

    with pytest.raises(CninfoDocumentProviderError) as exc_info:
        discover_cninfo_attachment(
            symbol="000001",
            org_id="gssz0000001",
            announcement_id="1225022887",
            published_at=datetime(2026, 3, 21, tzinfo=timezone.utc),
            post_json=failing_post,
        )

    assert exc_info.value.code == "CNINFO_DOCUMENT_PROVIDER_ERROR"
    assert "raw response secret" not in exc_info.value.message


def test_download_cninfo_pdf_validates_and_hashes_content():
    content = b"%PDF-1.4\nfixture"
    url = "https://static.cninfo.com.cn/finalpage/2026-03-21/1225022887.PDF"
    downloaded = download_cninfo_pdf(
        url,
        http_get=lambda requested_url, **kwargs: DocumentHttpResponse(
            status_code=200,
            url=requested_url,
            headers={"content-type": "application/pdf", "content-length": str(len(content))},
            content=content,
        ),
        retrieved_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
    )

    assert downloaded.byte_size == len(content)
    assert downloaded.sha256 == hashlib.sha256(content).hexdigest()


@pytest.mark.parametrize(
    ("response", "expected_code"),
    [
        (
            DocumentHttpResponse(302, "https://static.cninfo.com.cn/finalpage/a.pdf", {}, b""),
            "CNINFO_DOCUMENT_REDIRECT_REJECTED",
        ),
        (
            DocumentHttpResponse(
                200,
                "https://static.cninfo.com.cn/finalpage/a.pdf",
                {"content-type": "text/html"},
                b"%PDF-1.4",
            ),
            "CNINFO_DOCUMENT_MEDIA_TYPE_REJECTED",
        ),
        (
            DocumentHttpResponse(
                200,
                "https://static.cninfo.com.cn/finalpage/a.pdf",
                {"content-type": "application/pdf"},
                b"not-a-pdf",
            ),
            "CNINFO_DOCUMENT_SIGNATURE_REJECTED",
        ),
    ],
)
def test_download_cninfo_pdf_rejects_unsafe_responses(response, expected_code):
    url = response.url
    with pytest.raises(CninfoDocumentProviderError) as exc_info:
        download_cninfo_pdf(
            url,
            http_get=lambda requested_url, **kwargs: response,
        )
    assert exc_info.value.code == expected_code


def test_download_cninfo_pdf_rejects_oversized_bytes():
    url = "https://static.cninfo.com.cn/finalpage/a.pdf"
    with pytest.raises(CninfoDocumentProviderError) as exc_info:
        download_cninfo_pdf(
            url,
            max_bytes=8,
            http_get=lambda requested_url, **kwargs: DocumentHttpResponse(
                200,
                requested_url,
                {"content-type": "application/pdf"},
                b"%PDF-12345",
            ),
        )
    assert exc_info.value.code == "CNINFO_DOCUMENT_TOO_LARGE"
