import json
from datetime import date

import pytest

from packages.providers.eastmoney_public_fundamentals import (
    EASTMONEY_COMPANY_ENDPOINT,
    EASTMONEY_FINANCIAL_ENDPOINT,
    EASTMONEY_FINANCIAL_MAX_RESPONSE_BYTES,
    EastmoneyPublicFundamentalsHttpResponse,
    EastmoneyPublicFundamentalsProviderError,
    fetch_eastmoney_public_company,
    fetch_eastmoney_public_fundamentals,
)


def _response(payload: object, *, media_type: str = "text/plain;charset=UTF-8"):
    content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return EastmoneyPublicFundamentalsHttpResponse(
        status_code=200,
        headers={"content-type": media_type, "content-length": str(len(content))},
        content=content,
    )


def _financial_payload(rows: list[object] | None = None):
    return {
        "success": True,
        "result": {
            "data": rows
            if rows is not None
            else [
                {
                    "SECURITY_CODE": "600519",
                    "SECUCODE": "600519.SH",
                    "REPORT_DATE": "2026-06-30 00:00:00",
                    "CURRENCY": "CNY",
                    "TOTALOPERATEREVETZ": "12.5",
                    "XSJLL": "51.25",
                    "ZCFZL": "18.75",
                }
            ]
        },
    }


def _company_payload(*, profile: str = "Premium spirits producer."):
    return {
        "jbzl": [
            {
                "SECURITY_CODE": "600519",
                "SECUCODE": "600519.SH",
                "ORG_NAME": "Kweichow Moutai Co., Ltd.",
                "INDUSTRYCSRC1": "Beverage manufacturing",
                "BUSINESS_SCOPE": "Production and sale of spirits.",
                "ORG_PROFILE": profile,
            }
        ],
        "fxxg": [],
    }


def test_fetch_eastmoney_public_fundamentals_uses_fixed_safe_requests_and_normalizes():
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_get(url: str, **kwargs: object):
        calls.append((url, kwargs))
        if url == EASTMONEY_FINANCIAL_ENDPOINT:
            return _response(
                _financial_payload(
                    [
                        {
                            "SECURITY_CODE": "600519",
                            "SECUCODE": "600519.SH",
                            "REPORT_DATE": "2026-09-30 00:00:00",
                            "CURRENCY": "CNY",
                            "TOTALOPERATEREVETZ": "99",
                            "XSJLL": "99",
                            "ZCFZL": "99",
                        },
                        _financial_payload()["result"]["data"][0],
                    ]
                )
            )
        assert url == EASTMONEY_COMPANY_ENDPOINT
        return _response(_company_payload(), media_type="application/json; charset=utf-8")

    snapshot = fetch_eastmoney_public_fundamentals(
        "600519",
        as_of=date(2026, 7, 16),
        http_get=fake_get,
    )

    assert snapshot is not None
    assert snapshot.symbol == "600519"
    assert snapshot.as_of == date(2026, 6, 30)
    assert snapshot.currency == "CNY"
    assert snapshot.pe_ratio is None
    assert snapshot.revenue_growth == pytest.approx(0.125)
    assert snapshot.net_margin == pytest.approx(0.5125)
    assert snapshot.debt_to_assets == pytest.approx(0.1875)
    assert snapshot.company is not None
    assert snapshot.company.industry == "Beverage manufacturing"
    assert snapshot.status == "ok"
    assert snapshot.diagnostics == ()
    assert snapshot.upstream_sources == (
        "eastmoney.RPT_F10_FINANCE_MAINFINADATA",
        "eastmoney.PC_HSF10.CompanySurvey.PageAjax",
    )

    assert [url for url, _kwargs in calls] == [
        EASTMONEY_FINANCIAL_ENDPOINT,
        EASTMONEY_COMPANY_ENDPOINT,
    ]
    financial_kwargs = calls[0][1]
    assert financial_kwargs["follow_redirects"] is False
    assert financial_kwargs["trust_env"] is False
    assert financial_kwargs["timeout"] == 8.0
    assert "Cookie" not in financial_kwargs["headers"]
    assert "Authorization" not in financial_kwargs["headers"]
    assert financial_kwargs["params"] == {
        "type": "RPT_F10_FINANCE_MAINFINADATA",
        "sty": "APP_F10_MAINFINADATA",
        "quoteColumns": "",
        "filter": '(SECUCODE="600519.SH")',
        "p": "1",
        "ps": "20",
        "sr": "-1",
        "st": "REPORT_DATE",
        "source": "HSF10",
        "client": "PC",
    }
    assert calls[1][1]["params"] == {"code": "SH600519"}


def test_fetch_eastmoney_public_company_uses_only_fixed_company_request():
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_get(url: str, **kwargs: object):
        calls.append((url, kwargs))
        return _response(_company_payload(), media_type="application/json")

    company = fetch_eastmoney_public_company("600519", http_get=fake_get)

    assert company is not None
    assert company.name == "Kweichow Moutai Co., Ltd."
    assert company.industry == "Beverage manufacturing"
    assert [url for url, _kwargs in calls] == [EASTMONEY_COMPANY_ENDPOINT]
    assert calls[0][1]["params"] == {"code": "SH600519"}
    assert calls[0][1]["follow_redirects"] is False
    assert calls[0][1]["trust_env"] is False
    assert calls[0][1]["timeout"] == 8.0
    assert "Cookie" not in calls[0][1]["headers"]
    assert "Authorization" not in calls[0][1]["headers"]


def test_company_text_is_bounded_without_invalidating_financial_metrics():
    def fake_get(url: str, **_kwargs: object):
        if url == EASTMONEY_FINANCIAL_ENDPOINT:
            return _response(_financial_payload())
        return _response(
            _company_payload(profile=" x " * 5000),
            media_type="application/json",
        )

    snapshot = fetch_eastmoney_public_fundamentals(
        "600519",
        as_of=date(2026, 7, 16),
        http_get=fake_get,
    )

    assert snapshot is not None
    assert snapshot.company is not None
    assert len(snapshot.company.profile or "") == 2000
    assert snapshot.status == "ok"


def test_empty_financial_result_returns_none_without_company_request():
    calls: list[str] = []

    def fake_get(url: str, **_kwargs: object):
        calls.append(url)
        return _response(_financial_payload([]))

    result = fetch_eastmoney_public_fundamentals(
        "600519",
        as_of=date(2026, 7, 16),
        http_get=fake_get,
    )

    assert result is None
    assert calls == [EASTMONEY_FINANCIAL_ENDPOINT]


def test_company_failure_degrades_without_discarding_financial_metrics():
    def fake_get(url: str, **_kwargs: object):
        if url == EASTMONEY_FINANCIAL_ENDPOINT:
            return _response(_financial_payload())
        raise TimeoutError("private upstream detail")

    snapshot = fetch_eastmoney_public_fundamentals(
        "600519",
        as_of=date(2026, 7, 16),
        http_get=fake_get,
    )

    assert snapshot is not None
    assert snapshot.revenue_growth == pytest.approx(0.125)
    assert snapshot.company is None
    assert snapshot.status == "degraded"
    assert snapshot.diagnostics == ("EASTMONEY_FUNDAMENTALS_TIMEOUT",)


@pytest.mark.parametrize(
    ("row_update", "expected_code"),
    [
        ({"SECURITY_CODE": "000001"}, "EASTMONEY_FUNDAMENTALS_IDENTITY_REJECTED"),
        ({"REPORT_DATE": "not-a-date"}, "EASTMONEY_FUNDAMENTALS_SCHEMA_REJECTED"),
        ({"XSJLL": "NaN"}, "EASTMONEY_FUNDAMENTALS_SCHEMA_REJECTED"),
    ],
)
def test_financial_rows_fail_closed_for_identity_date_and_numeric_errors(
    row_update,
    expected_code,
):
    row = dict(_financial_payload()["result"]["data"][0])
    row.update(row_update)

    with pytest.raises(EastmoneyPublicFundamentalsProviderError) as exc_info:
        fetch_eastmoney_public_fundamentals(
            "600519",
            as_of=date(2026, 7, 16),
            http_get=lambda *_args, **_kwargs: _response(_financial_payload([row])),
        )

    assert exc_info.value.code == expected_code


def test_redirect_and_oversized_response_are_rejected():
    redirect = EastmoneyPublicFundamentalsHttpResponse(
        status_code=302,
        headers={"content-type": "text/plain"},
        content=b"{}",
    )
    with pytest.raises(EastmoneyPublicFundamentalsProviderError) as redirect_error:
        fetch_eastmoney_public_fundamentals(
            "600519",
            as_of=date(2026, 7, 16),
            http_get=lambda *_args, **_kwargs: redirect,
        )
    assert redirect_error.value.code == "EASTMONEY_FUNDAMENTALS_RESPONSE_REJECTED"

    oversized = EastmoneyPublicFundamentalsHttpResponse(
        status_code=200,
        headers={
            "content-type": "text/plain",
            "content-length": str(EASTMONEY_FINANCIAL_MAX_RESPONSE_BYTES + 1),
        },
        content=b"{}",
    )
    with pytest.raises(EastmoneyPublicFundamentalsProviderError) as size_error:
        fetch_eastmoney_public_fundamentals(
            "600519",
            as_of=date(2026, 7, 16),
            http_get=lambda *_args, **_kwargs: oversized,
        )
    assert size_error.value.code == "EASTMONEY_FUNDAMENTALS_RESPONSE_TOO_LARGE"


def test_timeout_is_sanitized_without_retry():
    calls = 0

    def timeout_get(*_args: object, **_kwargs: object):
        nonlocal calls
        calls += 1
        raise TimeoutError("Cookie=session-secret https://private.example")

    with pytest.raises(EastmoneyPublicFundamentalsProviderError) as exc_info:
        fetch_eastmoney_public_fundamentals(
            "600519",
            as_of=date(2026, 7, 16),
            http_get=timeout_get,
        )

    assert calls == 1
    assert exc_info.value.code == "EASTMONEY_FUNDAMENTALS_TIMEOUT"
    assert "secret" not in str(exc_info.value).lower()


def test_invalid_symbol_is_rejected_before_network_call():
    def unexpected_get(*_args: object, **_kwargs: object):
        raise AssertionError("invalid symbol must not make a request")

    with pytest.raises(ValueError, match="six-digit"):
        fetch_eastmoney_public_fundamentals(
            "AAPL",
            as_of=date(2026, 7, 16),
            http_get=unexpected_get,
        )
