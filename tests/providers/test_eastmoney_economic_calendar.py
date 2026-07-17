from datetime import date

import pytest

from packages.providers.eastmoney_economic_calendar import fetch_eastmoney_economic_calendar


class Response:
    status_code = 200

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


def test_normalizes_pages_nulls_and_shanghai_time():
    calls = []

    def get(*args, **kwargs):
        calls.append(kwargs["params"])
        page = int(kwargs["params"]["pageNumber"])
        row = {
            "MXID": f"m{page}",
            "INDICATOR_ID": "i",
            "STR_COUNTRY": "中国",
            "INDICATOR_NAME_NEW": "CPI",
            "PUBLISH_DATEH": f"2026-07-0{page} 09:30:00",
            "STAR": 3,
            "DEC_LINDEXVALUE": None,
            "DEC_FOREVALUE": "1.2",
            "DEC_INDEXVALUE": "",
            "UNIT": "%",
        }
        return Response({"success": True, "result": {"pages": 2, "data": [row]}})

    rows = fetch_eastmoney_economic_calendar(date(2026, 7, 1), date(2026, 7, 2), http_get=get)
    assert len(rows) == 2
    assert rows[0].scheduled_at.isoformat() == "2026-07-01T01:30:00+00:00"
    assert rows[0].previous_value is None and rows[0].actual_value is None
    assert str(rows[0].forecast_value) == "1.2"
    assert [item["pageNumber"] for item in calls] == ["1", "2"]


def test_rejects_ranges_over_62_days():
    with pytest.raises(ValueError):
        fetch_eastmoney_economic_calendar(date(2026, 1, 1), date(2026, 4, 1))


def test_builds_stable_fallback_identity_without_turning_nulls_into_zero():
    row = {
        "INDICATOR_ID": "i",
        "STR_COUNTRY": "美国",
        "STR_INDEXNAME": "Jobs",
        "PUBLISH_DATEH_Z": "2026-07-03 00:00:00",
        "PUBLISH_DATETME": "20:30",
        "STAR": 5,
        "DEC_INDEXVALUE": None,
    }

    def get(*args, **kwargs):
        return Response({"success": True, "result": {"pages": 1, "data": [row]}})

    one = fetch_eastmoney_economic_calendar(date(2026, 7, 3), date(2026, 7, 3), http_get=get)[0]
    two = fetch_eastmoney_economic_calendar(date(2026, 7, 3), date(2026, 7, 3), http_get=get)[0]
    assert one.external_event_id == two.external_event_id
    assert one.actual_value is None
    assert one.importance == 5
    assert one.scheduled_at.isoformat() == "2026-07-03T12:30:00+00:00"
