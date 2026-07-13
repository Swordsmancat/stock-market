from datetime import date, datetime, timezone

import pandas as pd
import pytest

from packages.providers.cninfo_disclosure_provider import (
    CninfoDisclosureProviderError,
    fetch_cninfo_disclosures,
    normalize_a_share_symbol,
)


def test_fetch_cninfo_disclosures_normalizes_valid_rows_and_rejects_invalid_rows():
    captured = {}

    def fake_fetcher(**kwargs):
        captured.update(kwargs)
        return pd.DataFrame(
            [
                {
                    "代码": "000001",
                    "简称": "平安银行",
                    "公告标题": "2025 年年度报告",
                    "公告时间": "2026-03-20 18:30:00",
                    "公告链接": (
                        "http://www.cninfo.com.cn/new/disclosure/detail?stockCode=000001&"
                        "announcementId=1212345678&orgId=gssz0000001"
                    ),
                },
                {
                    "代码": "000001",
                    "简称": "平安银行",
                    "公告标题": "Invalid host",
                    "公告时间": "2026-03-20 18:30:00",
                    "公告链接": "https://example.com/detail?announcementId=bad",
                },
            ]
        )

    result = fetch_cninfo_disclosures(
        symbol="000001.SZ",
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 31),
        category="年报",
        fetcher=fake_fetcher,
        retrieved_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
    )

    assert captured == {
        "symbol": "000001",
        "market": "沪深京",
        "keyword": "",
        "category": "年报",
        "start_date": "20260301",
        "end_date": "20260331",
    }
    assert len(result.items) == 1
    assert result.items[0].source_document_id == "1212345678"
    assert result.items[0].published_at.isoformat() == "2026-03-20T10:30:00+00:00"
    assert result.items[0].metadata["content_ingested"] is False
    assert len(result.rejections) == 1
    assert result.rejections[0].code == "CNINFO_ROW_REJECTED"


@pytest.mark.parametrize("symbol", ["", "1", "AAPL", "000001.XSHG"])
def test_normalize_a_share_symbol_rejects_invalid_symbols(symbol):
    with pytest.raises(ValueError, match="six-digit"):
        normalize_a_share_symbol(symbol)


def test_fetch_cninfo_disclosures_rejects_schema_changes_without_raw_payload():
    def fake_fetcher(**kwargs):
        return pd.DataFrame([{"代码": "000001"}])

    with pytest.raises(CninfoDisclosureProviderError) as exc_info:
        fetch_cninfo_disclosures(
            symbol="000001",
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 31),
            fetcher=fake_fetcher,
        )

    assert exc_info.value.code == "CNINFO_SCHEMA_ERROR"
    assert "代码" not in exc_info.value.message


def test_fetch_cninfo_disclosures_sanitizes_provider_failure():
    def failing_fetcher(**kwargs):
        raise RuntimeError("secret raw provider response")

    with pytest.raises(CninfoDisclosureProviderError) as exc_info:
        fetch_cninfo_disclosures(
            symbol="000001",
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 31),
            fetcher=failing_fetcher,
        )

    assert exc_info.value.code == "CNINFO_PROVIDER_ERROR"
    assert "secret raw provider response" not in exc_info.value.message


def test_fetch_cninfo_disclosures_rejects_unbounded_date_range_before_fetch():
    called = False

    def fake_fetcher(**kwargs):
        nonlocal called
        called = True

    with pytest.raises(ValueError, match="must not exceed 366 days"):
        fetch_cninfo_disclosures(
            symbol="000001",
            start_date=date(2024, 1, 1),
            end_date=date(2026, 3, 31),
            fetcher=fake_fetcher,
        )

    assert called is False
