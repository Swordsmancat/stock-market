from datetime import date

import pytest

from packages.providers.fred_provider import FredProviderConfigurationError
from packages.services.market_indicators import FredMacroRefreshResult
from scripts import refresh_fred_macro_indicators


class FakeSession:
    closed = False

    def close(self):
        self.closed = True


def fake_session_factory():
    return FakeSession()


def test_refresh_fred_macro_indicators_script_reports_dry_run(capsys):
    def fake_refresh(**kwargs):
        assert kwargs["series_group"] == "rates"
        assert kwargs["start"] == date(2026, 7, 1)
        assert kwargs["end"] == date(2026, 7, 6)
        assert kwargs["latest_only"] is True
        assert kwargs["dry_run"] is True
        return FredMacroRefreshResult(
            observations=3,
            fetched=3,
            skipped=0,
            dry_run=True,
            codes=("us_10y_yield", "us_2y_yield"),
            latest_as_of="2026-07-03",
            diagnostics=(),
        )

    exit_code = refresh_fred_macro_indicators.main(
        [
            "--series",
            "rates",
            "--start",
            "2026-07-01",
            "--end",
            "2026-07-06",
            "--latest-only",
            "--dry-run",
        ],
        session_factory=fake_session_factory,
        refresh_func=fake_refresh,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "DRY-RUN FRED refresh" in output
    assert "observations=3" in output
    assert "us_10y_yield, us_2y_yield" in output


def test_refresh_fred_macro_indicators_script_warns_on_missing_api_key(capsys):
    def fake_refresh(**_kwargs):
        raise FredProviderConfigurationError("FRED API key is not configured.")

    exit_code = refresh_fred_macro_indicators.main(
        ["--series", "rates"],
        session_factory=fake_session_factory,
        refresh_func=fake_refresh,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "WARN FRED refresh" in output
    assert "FRED API key is not configured" in output


def test_refresh_fred_macro_indicators_script_rejects_bad_date(capsys):
    with pytest.raises(SystemExit) as raised_exit:
        refresh_fred_macro_indicators.main(
            ["--start", "bad-date"],
            session_factory=fake_session_factory,
        )

    output = capsys.readouterr().err
    assert raised_exit.value.code == 2
    assert "date must use YYYY-MM-DD format" in output
