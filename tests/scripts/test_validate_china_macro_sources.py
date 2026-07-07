from dataclasses import dataclass

import pytest

from scripts import validate_china_macro_sources


@dataclass(frozen=True)
class FakeResponse:
    status_code: int
    text: str


def test_default_no_network_outputs_warn_without_writes(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = validate_china_macro_sources.main([])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "WARN China macro source validation" in output
    assert "live probe skipped" in output
    assert "database_writes=none" in output
    assert "Summary: OK=0 WARN=" in output
    assert "FAIL=0" in output


def test_focused_source_selection_limits_output(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = validate_china_macro_sources.main(["--source", "pboc_cn_m2"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "pboc_cn_m2" in output
    assert "nbs_cn_macro" not in output
    assert "Summary: OK=0 WARN=1 FAIL=0" in output


def test_unknown_source_returns_fail(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = validate_china_macro_sources.main(["--source", "unknown"])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "FAIL China macro source validation" in output
    assert "unknown source: unknown" in output


def test_live_probe_with_fake_success_returns_ok(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_fetch(url: str, timeout_seconds: float) -> FakeResponse:
        assert "worldbank" in url
        assert timeout_seconds == 7.0
        return FakeResponse(status_code=200, text='[{"page":1},{"countryiso3code":"CHN"}]')

    monkeypatch.setattr(validate_china_macro_sources, "fetch_probe_url", fake_fetch)

    exit_code = validate_china_macro_sources.main(
        [
            "--source",
            "world_bank_china_macro",
            "--live-network",
            "--timeout",
            "7",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "OK China macro source validation" in output
    assert "world_bank_china_macro live probe returned expected marker" in output
    assert "database_writes=none" in output
    assert "Summary: OK=1 WARN=0 FAIL=0" in output


def test_live_probe_with_fake_schema_mismatch_returns_warn(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        validate_china_macro_sources,
        "fetch_probe_url",
        lambda url, timeout_seconds: FakeResponse(status_code=200, text='{"ok": true}'),
    )

    exit_code = validate_china_macro_sources.main(
        ["--source", "world_bank_china_macro", "--live-network"]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "WARN China macro source validation" in output
    assert "schema marker was not found" in output
    assert "Summary: OK=0 WARN=1 FAIL=0" in output


def test_live_probe_sanitizes_fetch_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_fetch(url: str, timeout_seconds: float) -> FakeResponse:
        raise RuntimeError("token=secret-value provider blew up")

    monkeypatch.setattr(validate_china_macro_sources, "fetch_probe_url", fake_fetch)

    exit_code = validate_china_macro_sources.main(
        ["--source", "nbs_cn_macro", "--live-network"]
    )

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "FAIL China macro source validation" in output
    assert "RuntimeError" in output
    assert "secret-value" not in output
    assert "token=" not in output
