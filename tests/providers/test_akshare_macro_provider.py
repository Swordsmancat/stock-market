from datetime import date, datetime, timezone
from decimal import Decimal

import pandas as pd

from packages.providers.akshare_macro_provider import AkShareMacroProvider


def test_akshare_macro_provider_normalizes_history_independent_of_source_order():
    provider = AkShareMacroProvider(
        fetchers={
            "lpr": lambda: pd.DataFrame(
                [
                    {"TRADE_DATE": "2026-06-22", "LPR1Y": 3.0, "LPR5Y": 3.5},
                    {"TRADE_DATE": "2026-04-20", "LPR1Y": 3.1, "LPR5Y": 3.6},
                    {"TRADE_DATE": "2026-05-20", "LPR1Y": 3.0, "LPR5Y": 3.5},
                ]
            )
        }
    )

    result = provider.fetch(
        family="lpr",
        history_limit=2,
        retrieved_at=datetime(2026, 7, 17, tzinfo=timezone.utc),
    )[0]

    assert result.status == "ok"
    assert [(item.code, item.as_of, item.value) for item in result.observations] == [
        ("cn_lpr_1y", date(2026, 5, 20), Decimal("3.0")),
        ("cn_lpr_1y", date(2026, 6, 22), Decimal("3.0")),
        ("cn_lpr_5y", date(2026, 5, 20), Decimal("3.5")),
        ("cn_lpr_5y", date(2026, 6, 22), Decimal("3.5")),
    ]
    assert result.observations[0].components["source_url"].startswith("https://")
    assert result.observations[0].components["retrieved_at"] == "2026-07-17T00:00:00+00:00"


def test_akshare_macro_provider_skips_missing_values_and_parses_month_end():
    provider = AkShareMacroProvider(
        fetchers={
            "cpi": lambda: pd.DataFrame(
                [
                    {"月份": "2026年05月份", "全国-同比增长": 1.2},
                    {"月份": "2026年06月份", "全国-同比增长": None},
                    {"月份": "bad-period", "全国-同比增长": 9.9},
                ]
            )
        }
    )

    result = provider.fetch(family="cpi")[0]

    assert result.status == "ok"
    assert result.skipped == 2
    assert len(result.observations) == 1
    assert result.observations[0].as_of == date(2026, 5, 31)
    assert result.observations[0].value == Decimal("1.2")


def test_akshare_macro_provider_reports_schema_mismatch_without_guessing():
    provider = AkShareMacroProvider(
        fetchers={"pmi": lambda: pd.DataFrame([{"月份": "2026年06月份", "wrong": 50.3}])}
    )

    result = provider.fetch(family="pmi")[0]

    assert result.status == "error"
    assert result.observations == ()
    assert result.diagnostics == ("pmi: schema_mismatch",)


def test_akshare_macro_provider_keeps_other_families_when_one_provider_fails():
    def fail():
        raise RuntimeError("upstream token=secret payload")

    provider = AkShareMacroProvider(
        fetchers={
            "lpr": fail,
            "cpi": lambda: pd.DataFrame(
                [{"月份": "2026年06月份", "全国-同比增长": 1.0}]
            ),
        }
    )

    lpr = provider.fetch(family="lpr")[0]
    cpi = provider.fetch(family="cpi")[0]

    assert lpr.status == "error"
    assert lpr.diagnostics == ("lpr: provider_error:RuntimeError",)
    assert "secret" not in str(lpr)
    assert cpi.status == "ok"
    assert cpi.observations[0].code == "cn_cpi_yoy"
