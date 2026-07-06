"""Refresh audited macro indicator observations from the official FRED API."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from datetime import date
from typing import TextIO

from sqlalchemy.orm import Session

from packages.providers.fred_provider import FredProviderConfigurationError
from packages.providers.fred_provider import FredProviderError
from packages.services.market_indicators import FredMacroRefreshResult
from packages.services.market_indicators import MarketIndicatorSeedImportError
from packages.services.market_indicators import refresh_fred_macro_indicators
from packages.shared.database import SessionLocal


SessionFactory = Callable[[], Session]
RefreshFunction = Callable[..., FredMacroRefreshResult]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Refresh source-audited US macro observations from FRED. "
            "This writes only validated observations to the configured database."
        ),
    )
    parser.add_argument(
        "--series",
        default="all",
        help="FRED target group or series. Examples: all, rates, inflation, liquidity, DGS10.",
    )
    parser.add_argument(
        "--start",
        type=_parse_cli_date,
        default=None,
        help="Observation start date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--end",
        type=_parse_cli_date,
        default=None,
        help="Observation end date in YYYY-MM-DD format. Defaults to today.",
    )
    parser.add_argument(
        "--latest-only",
        action="store_true",
        help="Persist only the latest usable observation per configured target.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and validate observations without writing database rows.",
    )
    return parser


def refresh_with_session(
    *,
    series: str,
    start: date | None,
    end: date | None,
    latest_only: bool,
    dry_run: bool,
    session_factory: SessionFactory,
    refresh_func: RefreshFunction = refresh_fred_macro_indicators,
) -> FredMacroRefreshResult:
    session = session_factory()
    try:
        return refresh_func(
            session=session,
            series_group=series,
            start=start,
            end=end,
            latest_only=latest_only,
            dry_run=dry_run,
        )
    finally:
        session.close()


def main(
    argv: Sequence[str] | None = None,
    *,
    output: TextIO | None = None,
    session_factory: SessionFactory = SessionLocal,
    refresh_func: RefreshFunction = refresh_fred_macro_indicators,
) -> int:
    output_stream = output if output is not None else sys.stdout
    args = build_parser().parse_args(argv)

    try:
        result = refresh_with_session(
            series=args.series,
            start=args.start,
            end=args.end,
            latest_only=args.latest_only,
            dry_run=args.dry_run,
            session_factory=session_factory,
            refresh_func=refresh_func,
        )
    except FredProviderConfigurationError as error:
        print(f"WARN FRED refresh: {error}", file=output_stream)
        return 0
    except (FredProviderError, MarketIndicatorSeedImportError, ValueError) as error:
        print(f"FAIL FRED refresh: {error}", file=output_stream)
        return 1
    except OSError as error:
        print(f"FAIL FRED refresh: {error}", file=output_stream)
        return 1

    status = "DRY-RUN" if result.dry_run else "OK"
    codes = ", ".join(result.codes) if result.codes else "none"
    print(
        (
            f"{status} FRED refresh: observations={result.observations}, "
            f"fetched={result.fetched}, skipped={result.skipped}, codes={codes}, "
            f"latest_as_of={result.latest_as_of or 'none'}"
        ),
        file=output_stream,
    )
    for diagnostic in result.diagnostics:
        print(f"WARN FRED refresh: {diagnostic}", file=output_stream)
    return 0


def _parse_cli_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("date must use YYYY-MM-DD format") from error


if __name__ == "__main__":
    raise SystemExit(main())
