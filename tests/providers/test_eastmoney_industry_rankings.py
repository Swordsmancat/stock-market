from packages.providers.eastmoney_industry_rankings import SOURCE_URL, fetch_eastmoney_industry_history


class Response:
    status_code = 200
    def __init__(self, payload): self.payload = payload
    def json(self): return self.payload


def test_normalizes_universe_and_history_and_uses_cookie():
    calls = []
    def request(url, **kwargs):
        calls.append((url, kwargs))
        if "clist" in url:
            return Response({"data": {"diff": [{"f12": "BK0001", "f14": "银行"}]}})
        return Response({"data": {"klines": ["2026-07-16,1,1,1,1,1,1,1,2.26,1,1", "2026-07-17,1,1,1,1,1,1,1,1.24,1,1"]}})
    rows = fetch_eastmoney_industry_history(days=2, cookie="sid=private", requester=request)
    assert [(row.industry_code, str(row.change_percent)) for row in rows] == [("BK0001", "2.26"), ("BK0001", "1.24")]
    assert all(call[1]["headers"]["cookie"] == "sid=private" for call in calls)
    universe_call = calls[0]
    assert universe_call[1]["params"]["fs"] == "m:90 s:4"
    assert universe_call[1]["params"]["fields"] == "f12,f14,f3"
    assert universe_call[1]["params"]["ut"]
    assert universe_call[1]["headers"]["referer"] == SOURCE_URL
    assert SOURCE_URL.endswith("#industry_board_1")


def test_falls_back_to_proxy_once_after_direct_failure():
    proxies = []
    def request(url, **kwargs):
        proxies.append(kwargs["proxy"])
        if kwargs["proxy"] is None:
            raise OSError("blocked")
        if "clist" in url:
            return Response({"data": {"diff": [{"f12": "BK0001", "f14": "银行"}]}})
        return Response({"data": {"klines": []}})
    assert fetch_eastmoney_industry_history(days=1, proxy_url="http://proxy.test:8080", requester=request) == ()
    assert proxies == [None, "http://proxy.test:8080", None, "http://proxy.test:8080"]
