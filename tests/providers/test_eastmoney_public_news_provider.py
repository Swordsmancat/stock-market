import json
import traceback
from datetime import timedelta

import pytest

from packages.providers.eastmoney_public_news import (
    EASTMONEY_NEWS_CALLBACK,
    EASTMONEY_NEWS_ENDPOINT,
    EASTMONEY_NEWS_HEADERS,
    EASTMONEY_NEWS_MAX_RESPONSE_BYTES,
    EastmoneyPublicNewsHttpResponse,
    EastmoneyPublicNewsProviderError,
    fetch_eastmoney_public_news,
)


def _valid_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "code": "202607162763554785",
        "title": "<em>宁德时代</em> 发布经营更新",
        "content": "<p>公司&nbsp;经营稳健。</p><script>discard me</script>",
        "date": "2026-07-16 14:30:00",
        "mediaName": "东方财富网",
        "url": "https://untrusted.example/private?token=secret",
        "image": "",
    }
    row.update(overrides)
    return row


def _success_payload(rows: list[object]) -> dict[str, object]:
    return {
        "bizCode": "",
        "bizMsg": "",
        "code": 0,
        "hitsTotal": len(rows),
        "msg": "OK",
        "result": {"cmsArticleWebOld": rows},
    }


def _response(
    payload: object,
    *,
    callback: str = EASTMONEY_NEWS_CALLBACK,
    status_code: int = 200,
    media_type: str = "text/javascript; charset=utf-8",
) -> EastmoneyPublicNewsHttpResponse:
    content = (
        f"{callback}({json.dumps(payload, ensure_ascii=False, separators=(',', ':'))})"
    ).encode()
    return EastmoneyPublicNewsHttpResponse(
        status_code=status_code,
        headers={"content-type": media_type, "content-length": str(len(content))},
        content=content,
    )


def test_fetch_eastmoney_public_news_uses_fixed_safe_request_and_normalizes_rows():
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_get(url: str, **kwargs: object) -> EastmoneyPublicNewsHttpResponse:
        calls.append((url, kwargs))
        return _response(_success_payload([_valid_row()]))

    items = fetch_eastmoney_public_news(
        "300750.SZ",
        timeout=4.5,
        http_get=fake_get,
    )

    assert len(calls) == 1
    url, request = calls[0]
    assert url == EASTMONEY_NEWS_ENDPOINT
    assert request["timeout"] == 4.5
    assert request["follow_redirects"] is False
    assert request["trust_env"] is False
    assert request["max_bytes"] == EASTMONEY_NEWS_MAX_RESPONSE_BYTES
    assert request["headers"] == EASTMONEY_NEWS_HEADERS
    assert not {"cookie", "authorization"} & {
        str(header).lower() for header in request["headers"]
    }

    params = request["params"]
    assert set(params) == {"cb", "param", "_"}
    assert params["cb"] == EASTMONEY_NEWS_CALLBACK
    query = json.loads(params["param"])
    assert query == {
        "uid": "",
        "keyword": "300750",
        "type": ["cmsArticleWebOld"],
        "client": "web",
        "clientType": "web",
        "clientVersion": "curr",
        "param": {
            "cmsArticleWebOld": {
                "searchScope": "default",
                "sort": "default",
                "pageIndex": 1,
                "pageSize": 10,
                "preTag": "<em>",
                "postTag": "</em>",
            }
        },
    }

    assert len(items) == 1
    item = items[0]
    assert item.symbol == "300750"
    assert item.title == "宁德时代 发布经营更新"
    assert item.summary == "公司 经营稳健。"
    assert item.publisher == "东方财富网"
    assert item.published_at.isoformat() == "2026-07-16T14:30:00+08:00"
    assert item.published_at.utcoffset() == timedelta(hours=8)
    assert item.url == (
        "https://finance.eastmoney.com/a/202607162763554785.html"
    )


def test_fetch_eastmoney_public_news_accepts_a_valid_empty_result():
    items = fetch_eastmoney_public_news(
        "300750",
        http_get=lambda *_args, **_kwargs: _response(_success_payload([])),
    )

    assert items == ()


@pytest.mark.parametrize(
    ("status_code", "expected_code"),
    [
        (302, "EASTMONEY_NEWS_REDIRECT_REJECTED"),
        (503, "EASTMONEY_NEWS_HTTP_STATUS"),
    ],
)
def test_fetch_eastmoney_public_news_rejects_unexpected_status(
    status_code: int,
    expected_code: str,
):
    with pytest.raises(EastmoneyPublicNewsProviderError) as exc_info:
        fetch_eastmoney_public_news(
            "300750",
            http_get=lambda *_args, **_kwargs: _response(
                _success_payload([]),
                status_code=status_code,
            ),
        )

    assert exc_info.value.code == expected_code
    assert str(status_code) not in str(exc_info.value)


def test_fetch_eastmoney_public_news_rejects_unexpected_media_type():
    with pytest.raises(EastmoneyPublicNewsProviderError) as exc_info:
        fetch_eastmoney_public_news(
            "300750",
            http_get=lambda *_args, **_kwargs: _response(
                _success_payload([]),
                media_type="text/html; charset=utf-8",
            ),
        )

    assert exc_info.value.code == "EASTMONEY_NEWS_MEDIA_TYPE_REJECTED"


@pytest.mark.parametrize("oversize_kind", ["header", "body"])
def test_fetch_eastmoney_public_news_rejects_oversized_response(oversize_kind: str):
    response = _response(_success_payload([]))
    if oversize_kind == "header":
        response = EastmoneyPublicNewsHttpResponse(
            status_code=200,
            headers={
                "content-type": "text/javascript",
                "content-length": str(EASTMONEY_NEWS_MAX_RESPONSE_BYTES + 1),
            },
            content=response.content,
        )
    else:
        response = EastmoneyPublicNewsHttpResponse(
            status_code=200,
            headers={"content-type": "text/javascript"},
            content=b"x" * (EASTMONEY_NEWS_MAX_RESPONSE_BYTES + 1),
        )

    with pytest.raises(EastmoneyPublicNewsProviderError) as exc_info:
        fetch_eastmoney_public_news(
            "300750",
            http_get=lambda *_args, **_kwargs: response,
        )

    assert exc_info.value.code == "EASTMONEY_NEWS_RESPONSE_TOO_LARGE"


@pytest.mark.parametrize(
    "content",
    [
        b"otherCallback({})",
        f" {EASTMONEY_NEWS_CALLBACK}({{}})".encode(),
        f"{EASTMONEY_NEWS_CALLBACK}({{}});".encode(),
        f"{EASTMONEY_NEWS_CALLBACK}({{}}".encode(),
    ],
)
def test_fetch_eastmoney_public_news_requires_exact_jsonp_callback(content: bytes):
    response = EastmoneyPublicNewsHttpResponse(
        status_code=200,
        headers={"content-type": "text/javascript"},
        content=content,
    )

    with pytest.raises(EastmoneyPublicNewsProviderError) as exc_info:
        fetch_eastmoney_public_news(
            "300750",
            http_get=lambda *_args, **_kwargs: response,
        )

    assert exc_info.value.code == "EASTMONEY_NEWS_CALLBACK_REJECTED"


@pytest.mark.parametrize(
    ("payload", "expected_code"),
    [
        ([], "EASTMONEY_NEWS_SCHEMA_REJECTED"),
        ({"code": 1, "msg": "FAILED", "result": {}}, "EASTMONEY_NEWS_RESULT_REJECTED"),
        ({"code": 0, "msg": "unexpected", "result": {}}, "EASTMONEY_NEWS_RESULT_REJECTED"),
        ({"code": 0, "msg": "OK"}, "EASTMONEY_NEWS_SCHEMA_REJECTED"),
        ({"code": 0, "msg": "OK", "result": []}, "EASTMONEY_NEWS_SCHEMA_REJECTED"),
        (
            {"code": 0, "msg": "OK", "result": {"cmsArticleWebOld": {}}},
            "EASTMONEY_NEWS_SCHEMA_REJECTED",
        ),
        (
            _success_payload([_valid_row() for _ in range(21)]),
            "EASTMONEY_NEWS_ROW_COUNT_REJECTED",
        ),
    ],
)
def test_fetch_eastmoney_public_news_rejects_invalid_payload_schema(
    payload: object,
    expected_code: str,
):
    with pytest.raises(EastmoneyPublicNewsProviderError) as exc_info:
        fetch_eastmoney_public_news(
            "300750",
            http_get=lambda *_args, **_kwargs: _response(payload),
        )

    assert exc_info.value.code == expected_code


@pytest.mark.parametrize(
    "row",
    [
        "not-an-object",
        _valid_row(code=None),
        _valid_row(code="../private"),
        _valid_row(title="<em></em>"),
        _valid_row(content={"raw": "provider body"}),
        _valid_row(date="not-a-date"),
        _valid_row(mediaName=""),
    ],
)
def test_fetch_eastmoney_public_news_rejects_the_whole_invalid_row_batch(row: object):
    payload = _success_payload([_valid_row(), row])

    with pytest.raises(EastmoneyPublicNewsProviderError) as exc_info:
        fetch_eastmoney_public_news(
            "300750",
            http_get=lambda *_args, **_kwargs: _response(payload),
        )

    assert exc_info.value.code == "EASTMONEY_NEWS_ROW_REJECTED"


def test_fetch_eastmoney_public_news_sanitizes_transport_exceptions_without_retry():
    calls = 0

    def failing_get(*_args: object, **_kwargs: object) -> EastmoneyPublicNewsHttpResponse:
        nonlocal calls
        calls += 1
        raise RuntimeError("Cookie=session-secret; raw upstream body")

    with pytest.raises(EastmoneyPublicNewsProviderError) as exc_info:
        fetch_eastmoney_public_news("300750", http_get=failing_get)

    assert calls == 1
    assert exc_info.value.code == "EASTMONEY_NEWS_REQUEST_FAILED"
    rendered = "".join(traceback.format_exception(exc_info.value))
    assert "session-secret" not in rendered
    assert "raw upstream body" not in rendered
    assert exc_info.value.__cause__ is None


def test_fetch_eastmoney_public_news_classifies_timeout_without_retry():
    calls = 0

    def timeout_get(*_args: object, **_kwargs: object) -> EastmoneyPublicNewsHttpResponse:
        nonlocal calls
        calls += 1
        raise TimeoutError("request URL contains private query")

    with pytest.raises(EastmoneyPublicNewsProviderError) as exc_info:
        fetch_eastmoney_public_news("300750", http_get=timeout_get)

    assert calls == 1
    assert exc_info.value.code == "EASTMONEY_NEWS_TIMEOUT"
    assert "private query" not in "".join(traceback.format_exception(exc_info.value))


def test_fetch_eastmoney_public_news_rejects_invalid_symbol_before_request():
    called = False

    def fake_get(*_args: object, **_kwargs: object) -> EastmoneyPublicNewsHttpResponse:
        nonlocal called
        called = True
        return _response(_success_payload([]))

    with pytest.raises(ValueError, match="six-digit"):
        fetch_eastmoney_public_news("AAPL", http_get=fake_get)

    assert called is False


def test_fetch_eastmoney_public_news_uses_max_rows_for_request_and_result_bound():
    captured: dict[str, object] = {}
    rows = [
        _valid_row(code=f"20260716276355478{index}")
        for index in range(5)
    ]

    def fake_get(_url: str, **kwargs: object) -> EastmoneyPublicNewsHttpResponse:
        captured.update(kwargs)
        return _response(_success_payload(rows))

    items = fetch_eastmoney_public_news(
        "300750",
        max_rows=2,
        http_get=fake_get,
    )

    assert json.loads(captured["params"]["param"])["param"]["cmsArticleWebOld"][
        "pageSize"
    ] == 2
    assert [item.url for item in items] == [
        "https://finance.eastmoney.com/a/202607162763554780.html",
        "https://finance.eastmoney.com/a/202607162763554781.html",
    ]


@pytest.mark.parametrize("max_rows", [0, 21, True])
def test_fetch_eastmoney_public_news_rejects_invalid_max_rows_before_request(
    max_rows: object,
):
    called = False

    def fake_get(*_args: object, **_kwargs: object) -> EastmoneyPublicNewsHttpResponse:
        nonlocal called
        called = True
        return _response(_success_payload([]))

    with pytest.raises(ValueError, match="max_rows must be between 1 and 20"):
        fetch_eastmoney_public_news(
            "300750",
            max_rows=max_rows,
            http_get=fake_get,
        )

    assert called is False
