import pytest

from packages.providers.world_bank_provider import WorldBankProviderError
from packages.services.market_indicators import WorldBankMacroRefreshResult
from scripts import refresh_world_bank_macro_indicators


class FakeSession:
    closed = False

    def close(self):
        self.closed = True


def fake_session_factory():
    return FakeSession()


def test_refresh_world_bank_macro_indicators_script_reports_dry_run(capsys):
    def fake_refresh(**kwargs):
        assert kwargs["target_group"] == "buffett_indicator_us"
        assert kwargs["start_year"] == 2020
        assert kwargs["end_year"] == 2024
        assert kwargs["latest_only"] is False
        assert kwargs["dry_run"] is True
        return WorldBankMacroRefreshResult(
            observations=3,
            fetched=6,
            skipped=1,
            dry_run=True,
            codes=("buffett_indicator_us",),
            latest_as_of="2024-12-31",
            diagnostics=("World Bank USA CM.MKT.LCAP.GD.ZS skipped 1 missing row.",),
        )

    exit_code = refresh_world_bank_macro_indicators.main(
        [
            "--target",
            "buffett_indicator_us",
            "--start-year",
            "2020",
            "--end-year",
            "2024",
            "--no-latest-only",
            "--dry-run",
        ],
        session_factory=fake_session_factory,
        refresh_func=fake_refresh,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "DRY-RUN World Bank refresh" in output
    assert "observations=3" in output
    assert "buffett_indicator_us" in output
    assert "WARN World Bank refresh" in output


def test_refresh_world_bank_macro_indicators_script_fails_on_provider_error(capsys):
    def fake_refresh(**_kwargs):
        raise WorldBankProviderError("World Bank request failed for USA/example: RuntimeError.")

    exit_code = refresh_world_bank_macro_indicators.main(
        ["--target", "USA"],
        session_factory=fake_session_factory,
        refresh_func=fake_refresh,
    )

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "FAIL World Bank refresh" in output
    assert "RuntimeError" in output


def test_refresh_world_bank_macro_indicators_script_rejects_bad_year(capsys):
    with pytest.raises(SystemExit) as raised_exit:
        refresh_world_bank_macro_indicators.main(
            ["--start-year", "bad-year"],
            session_factory=fake_session_factory,
        )

    output = capsys.readouterr().err
    assert raised_exit.value.code == 2
    assert "year must be a four-digit integer" in output
