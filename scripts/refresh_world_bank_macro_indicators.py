"""Refresh audited macro indicator observations from the World Bank API."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from typing import TextIO

from sqlalchemy.orm import Session

from packages.providers.world_bank_provider import WorldBankProviderError
from packages.services.market_indicators import MarketIndicatorSeedImportError
from packages.services.market_indicators import WorldBankMacroRefreshResult
from packages.services.market_indicators import refresh_world_bank_macro_indicators
from packages.shared.database import SessionLocal


SessionFactory = Callable[[], Session]
RefreshFunction = Callable[..., WorldBankMacroRefreshResult]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Refresh source-audited macro and valuation observations from the "
            "World Bank API. This writes only validated observations to the "
            "configured database."
        ),
    )
    parser.add_argument(
        "--target",
        default="all",
        help=(
            "World Bank target group, country, or indicator code. Examples: "
            "all, buffett, USA, buffett_indicator_us."
        ),
    )
    parser.add_argument(
        "--start-year",
        type=_parse_cli_year,
        default=None,
        help="Observation start year, for example 2020.",
    )
    parser.add_argument(
        "--end-year",
        type=_parse_cli_year,
        default=None,
        help="Observation end year, for example 2024.",
    )
    parser.add_argument(
        "--latest-only",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Persist only the latest usable observation per target. Use "
            "--no-latest-only to persist all returned observations."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and validate observations without writing database rows.",
    )
    return parser


def refresh_with_session(
    *,
    target: str,
    start_year: int | None,
    end_year: int | None,
    latest_only: bool,
    dry_run: bool,
    session_factory: SessionFactory,
    refresh_func: RefreshFunction = refresh_world_bank_macro_indicators,
) -> WorldBankMacroRefreshResult:
    session = session_factory()
    try:
        return refresh_func(
            session=session,
            target_group=target,
            start_year=start_year,
            end_year=end_year,
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
    refresh_func: RefreshFunction = refresh_world_bank_macro_indicators,
) -> int:
    output_stream = output if output is not None else sys.stdout
    args = build_parser().parse_args(argv)

    try:
        result = refresh_with_session(
            target=args.target,
            start_year=args.start_year,
            end_year=args.end_year,
            latest_only=args.latest_only,
            dry_run=args.dry_run,
            session_factory=session_factory,
            refresh_func=refresh_func,
        )
    except (WorldBankProviderError, MarketIndicatorSeedImportError, ValueError) as error:
        print(f"FAIL World Bank refresh: {error}", file=output_stream)
        return 1
    except OSError as error:
        print(f"FAIL World Bank refresh: {error}", file=output_stream)
        return 1

    status = "DRY-RUN" if result.dry_run else "OK"
    codes = ", ".join(result.codes) if result.codes else "none"
    print(
        (
            f"{status} World Bank refresh: observations={result.observations}, "
            f"fetched={result.fetched}, skipped={result.skipped}, codes={codes}, "
            f"latest_as_of={result.latest_as_of or 'none'}"
        ),
        file=output_stream,
    )
    for diagnostic in result.diagnostics:
        print(f"WARN World Bank refresh: {diagnostic}", file=output_stream)
    return 0


def _parse_cli_year(value: str) -> int:
    try:
        year = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("year must be a four-digit integer") from error
    if year < 1 or year > 9999:
        raise argparse.ArgumentTypeError("year must be between 1 and 9999")
    return year


if __name__ == "__main__":
    raise SystemExit(main())
